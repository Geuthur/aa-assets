# Standard Library
import datetime as dt
from typing import Any, List, Tuple

import requests

# Django
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models
from django.db.models import Case, F, Q, Value, When
from django.db.models.functions import Concat
from django.utils.timezone import now

# Alliance Auth
from eveuniverse.models import EveEntity, EveSolarSystem, EveType

from allianceauth.eveonline.models import EveCharacter

# AA Voices of War
from assets import __version__
from assets.app_settings import ASSETS_LOCATION_STALE_HOURS, STORAGE_BASE_KEY
from assets.hooks import get_extension_logger
from assets.providers import esi

logger = get_extension_logger(__name__)

USERAGENT = f"assets v{__version__}"
EVE_TYPE_ID_SOLAR_SYSTEM = 5


def build_market_price_cache_tag(item_id):
    return f"{STORAGE_BASE_KEY}{item_id}"


def set_market_price_cache(item_id: int, price: float):
    """Set location cache for a location object."""
    return cache.set(build_market_price_cache_tag(item_id), price, (60 * 60 * 2))


def get_market_price(item_id: int) -> float:
    """Get location cache for a location object."""
    return cache.get(build_market_price_cache_tag(item_id))


class AssetsQuerySet(models.QuerySet):
    def annotate_owner_name(self) -> models.QuerySet:
        """Add owner_name Annotation to query."""
        return self.select_related(
            "owner__character__character", "owner__corporation"
        ).annotate(
            owner_name=Case(
                When(
                    owner__corporation=None,
                    then=F("owner__character__character__character_name"),
                ),
                default=F("owner__corporation__corporation_name"),
                output_field=models.CharField(),
            )
        )

    def annotate_location_name(self) -> models.QuerySet:
        """Annotate calculated location name field
        with parent locations up to 3 levels up.
        """
        return self.annotate(
            location_name=Case(
                When(~Q(location__name=""), then=F("location__name")),
                When(
                    ~Q(location__parent=None) & ~Q(location__parent__name=""),
                    then=F("location__parent__name"),
                ),
                When(
                    ~Q(location__parent=None)
                    & ~Q(location__parent__parent=None)
                    & ~Q(location__parent__parent__name=""),
                    then=F("location__parent__parent__name"),
                ),
                When(
                    ~Q(location__parent=None)
                    & ~Q(location__parent__parent=None)
                    & ~Q(location__parent__parent__parent=None)
                    & ~Q(location__parent__parent__parent__name=""),
                    then=F("location__parent__parent__parent__name"),
                ),
                default=Concat(
                    Value("Location #"), "location__id", output_field=models.CharField()
                ),
                output_field=models.CharField(),
            )
        )

    def update_or_create_prices(self, item_ids: List[int]) -> dict:
        """Calculate prices for all assets of this owner."""
        tradehub = 60003760
        headers = {
            "User-Agent": USERAGENT,
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }
        data = {}

        # Split item_ids into chunks
        for i in range(0, len(item_ids), 100):
            chunk = item_ids[i : i + 100]
            item_id_list = ",".join(str(item_id) for item_id in chunk)
            url = f"https://market.fuzzwork.co.uk/aggregates/?station={tradehub}&types={item_id_list}"

            try:
                request_result = requests.get(url=url, headers=headers)
                request_result.raise_for_status()
                response_data = request_result.json()
                # Update cache with new data
                for item_id in chunk:
                    if str(item_id) in response_data:
                        set_market_price_cache(
                            item_id, response_data[str(item_id)]["buy"]["max"]
                        )
            except requests.RequestException as e:
                logger.warning("Request failed: %s, using Cache Data", e)
        data = {item_id: get_market_price(item_id) for item_id in item_ids}

        # Return the buy max prices
        return {
            item_id: data[item_id] for item_id in item_ids if data[item_id] is not None
        }


class AssetsManagerBase(models.Manager):
    pass


AssetsManager = AssetsManagerBase.from_queryset(AssetsQuerySet)


class LocationQuerySet(models.QuerySet):
    pass


class LocationManagerBase(models.Manager):
    """A manager for the Location model."""

    _UPDATE_EMPTY_GRACE_MINUTES = 360

    def get_or_create_esi(self, location_id: int) -> Tuple[Any, bool]:
        """Get or create location object with data fetched from ESI."""
        empty_threshold = now() - dt.timedelta(minutes=self._UPDATE_EMPTY_GRACE_MINUTES)
        stale_threshold = now() - dt.timedelta(hours=ASSETS_LOCATION_STALE_HOURS)
        try:
            location = (
                self.exclude(
                    eve_type__isnull=True,
                    eve_solar_system__isnull=True,
                    updated_at__lt=empty_threshold,
                )
                .exclude(updated_at__lt=stale_threshold)
                .get(id=location_id)
            )
            created = False
        except self.model.DoesNotExist:
            location, created = self.update_or_create_esi(location_id=location_id)

        return location, created

    def update_or_create_esi(self, location_id: int) -> Tuple[Any, bool]:
        """Update or create location object with data fetched from ESI."""
        if self.model.is_solar_system_id(location_id):
            eve_solar_system, _ = EveSolarSystem.objects.get_or_create_esi(
                id=location_id
            )
            eve_type, _ = EveType.objects.get_or_create_esi(id=EVE_TYPE_ID_SOLAR_SYSTEM)
            location, created = self.update_or_create(
                id=location_id,
                defaults={
                    "name": eve_solar_system.name,
                    "eve_solar_system": eve_solar_system,
                    "eve_type": eve_type,
                },
            )
        elif self.model.is_station_id(location_id):
            logger.info("%s: Fetching station from ESI", location_id)
            station = esi.client.Universe.get_universe_stations_station_id(
                station_id=location_id
            ).results()
            location, created = self._station_update_or_create_dict(
                location_id=location_id, station=station
            )

        else:
            # Create ID for structure
            location, created = self.get_or_create(id=location_id)

        return location, created

    def _station_update_or_create_dict(
        self, location_id: int, station: dict
    ) -> Tuple[Any, bool]:
        if station.get("system_id"):
            eve_solar_system, _ = EveSolarSystem.objects.get_or_create_esi(
                id=station.get("system_id")
            )
        else:
            eve_solar_system = None

        if station.get("type_id"):
            eve_type, _ = EveType.objects.get_or_create_esi(id=station.get("type_id"))
        else:
            eve_type = None

        if station.get("owner"):
            owner, _ = EveEntity.objects.get_or_create_esi(id=station.get("owner"))
        else:
            owner = None

        return self.update_or_create(
            id=location_id,
            defaults={
                "name": station.get("name", ""),
                "eve_solar_system": eve_solar_system,
                "eve_type": eve_type,
                "owner": owner,
            },
        )


LocationManager = LocationManagerBase.from_queryset(LocationQuerySet)


class OwnerQuerySet(models.QuerySet):
    def visible_to(self, user):
        # superusers get all visible
        if user.is_superuser:
            logger.debug("Returning all for superuser %s.", user)
            return self

        if user.has_perm("assets.manage_requests"):
            logger.debug("Returning all for %s.", user)
            return self

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(requesting_user=user)]

            logger.debug(
                "%s queries for user %s visible chracters.", len(queries), user
            )

            query = queries.pop()
            for q in queries:
                query |= q
            return self.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return self.none()

    def manage_to(self, user):
        # superusers get all visible
        if user.is_superuser:
            logger.debug(
                "Returning all for superuser %s.",
                user,
            )
            return self

        if user.has_perm("assets.manage_requests"):
            logger.debug("Returning all for Assets Manager %s.", user)
            return self

        try:
            char = user.profile.main_character
            assert char
            query = None

            logger.debug("Returning own for User %s.", user)

            if query is None:
                return self.none()

            return self.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return self.none()


class OwnerManagerBase(models.Manager):
    def get_queryset(self):
        return OwnerQuerySet(self.model, using=self._db)

    @staticmethod
    def visible_eve_characters(user):
        qs = EveCharacter.objects.get_queryset()
        if user.is_superuser:
            logger.debug("Returning all for superuser %s.", user)
            return qs.all()

        if user.has_perm("assets.manage_requests"):
            logger.debug("Returning all for Assets Manager %s.", user)
            return qs.all()

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(character_ownership__user=user)]

            logger.debug("%s queries for user %s visible.", len(queries), user)

            query = queries.pop()
            for q in queries:
                query |= q
            return qs.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return qs.none()

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)


OwnerManager = OwnerManagerBase.from_queryset(OwnerQuerySet)


class RequestQuerySet(models.QuerySet):
    def visible_to(self, user):
        # superusers get all visible
        if user.is_superuser:
            logger.debug("Returning all for superuser %s.", user)
            return self

        if user.has_perm("assets.manage_requests"):
            logger.debug("Returning all for Assets Manager %s.", user)
            return self

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(requesting_user=user)]

            logger.debug("%s queries for user %s visible.", len(queries), user)

            query = queries.pop()
            for q in queries:
                query |= q
            return self.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return self.none()

    def manage_to(self, user):
        # superusers get all visible
        if user.is_superuser:
            logger.debug(
                "Returning all corps for superuser %s.",
                user,
            )
            return self

        if user.has_perm("assets.manage_requests"):
            logger.debug("Returning all for Assets Manager %s.", user)
            return self

        try:
            char = user.profile.main_character
            assert char
            query = None

            logger.debug("Returning own for User %s.", user)

            if query is None:
                return self.none()

            return self.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return self.none()

    def requests_open(self) -> models.QuerySet:
        """Add filter to only include requests with open status."""
        request_query = self.filter(
            Q(closed_at=None) & Q(status=self.model.STATUS_OPEN)
        )
        return request_query

    def my_requests_open(self, user) -> models.QuerySet:
        """Add filter to only include requests with open status."""
        request_query = self.filter(
            Q(closed_at=None)
            & Q(status=self.model.STATUS_OPEN)
            & Q(requesting_user=user)
        )
        return request_query


class RequestManagerBase(models.Manager):
    def get_queryset(self):
        return RequestQuerySet(self.model, using=self._db)

    @staticmethod
    def visible_eve_characters(user):
        qs = EveCharacter.objects.get_queryset()
        if user.is_superuser:
            logger.debug("Returning all for superuser %s.", user)
            return qs.all()

        if user.has_perm("assets.manage_requests"):
            logger.debug("Returning all for Assets Manager %s.", user)
            return qs.all()

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(character_ownership__user=user)]

            logger.debug("%s queries for user %s visible.", len(queries), user)

            query = queries.pop()
            for q in queries:
                query |= q
            return qs.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return qs.none()

    @staticmethod
    def manage_eve_characters(user):
        qs = EveCharacter.objects.get_queryset()
        if user.is_superuser:
            logger.debug("Returning all for superuser %s.", user)
            return qs.all()

        if user.has_perm("assets.manage_requests"):
            logger.debug("Returning all for Assets Manager %s.", user)
            return qs.all()

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(character_ownership__user=user)]

            logger.debug("%s queries for user %s visible.", len(queries), user)

            query = queries.pop()
            for q in queries:
                query |= q
            return qs.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return qs.none()

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)

    def select_related_default(self) -> models.QuerySet:
        """Add default select related to this query."""
        return self.select_related(
            "requesting_user__profile__main_character",
        )

    def open_requests_total_count(self) -> int:
        """Return total count of open requests for user"""
        return self.all().requests_open().count()

    def my_requests_total_count(self, user: User) -> int:
        """Return total count of open requests for user"""
        return self.all().my_requests_open(user).count()


RequestManager = RequestManagerBase.from_queryset(RequestQuerySet)
