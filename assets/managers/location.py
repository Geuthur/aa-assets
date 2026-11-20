"""Manager of Location: access, name annotations and ESI fetch."""

# The access rules repeat per model; kept as they were before the split.
# pylint: disable=duplicate-code

# Standard Library
import datetime as dt
from typing import Any

# Django
from django.db import models
from django.db.models import Case, F, Q, Value, When
from django.db.models.functions import Concat
from django.utils.timezone import now

# Alliance Auth (External Libs)
from eve_sde.models.map import SolarSystem
from eve_sde.models.types import ItemType

# AA Assets
from assets import contexts
from assets.app_settings import ASSETS_LOCATION_STALE_HOURS
from assets.managers.general import GeneralManager
from assets.providers import esi, logger

EVE_TYPE_ID_SOLAR_SYSTEM = 5


class LocationQuerySet(models.QuerySet):
    def visible_to(self, user):
        if GeneralManager.has_admin_access(user):
            logger.debug("Returning all for admin %s.", user)
            return self

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(owner_id=char.character_id)]

            logger.debug(
                "%s queries for user %s visible characters.", len(queries), user
            )

            if GeneralManager.has_corporation_access(user):
                logger.debug(
                    "Returning own corporation for Corporation Manager %s.", user
                )
                queries.append(models.Q(owner_id=char.corporation_id))

            query = queries.pop()
            for q in queries:
                query |= q
            return self.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return self.none()

    def annotate_location_name(self) -> models.QuerySet:
        """Annotate calculated location name field
        with parent locations up to 3 levels up.
        """
        return self.annotate(
            location_name=Case(
                When(~Q(name=""), then=F("name")),
                When(
                    ~Q(parent=None) & ~Q(parent__name=""),
                    then=F("parent__name"),
                ),
                When(
                    ~Q(parent=None)
                    & ~Q(parent__parent=None)
                    & ~Q(parent__parent__name=""),
                    then=F("parent__parent__name"),
                ),
                When(
                    ~Q(parent=None)
                    & ~Q(parent__parent=None)
                    & ~Q(parent__parent__parent=None)
                    & ~Q(parent__parent__parent__name=""),
                    then=F("parent__parent__parent__name"),
                ),
                default=Concat(
                    Value("Location #"), "id", output_field=models.CharField()
                ),
                output_field=models.CharField(),
            )
        )

    def annotate_system_name(self) -> models.QuerySet:
        """Annotate calculated system name field
        with parent locations up to 3 levels up.
        """
        return self.annotate(
            system_name=Case(
                When(~Q(eve_solar_system=None), then=F("eve_solar_system__name")),
                When(
                    ~Q(parent=None) & ~Q(parent__eve_solar_system=None),
                    then=F("parent__eve_solar_system__name"),
                ),
                When(
                    ~Q(parent=None)
                    & ~Q(parent__parent=None)
                    & ~Q(parent__parent__eve_solar_system=None),
                    then=F("parent__parent__eve_solar_system__name"),
                ),
                When(
                    ~Q(parent=None)
                    & ~Q(parent__parent=None)
                    & ~Q(parent__parent__parent=None)
                    & ~Q(parent__parent__parent__eve_solar_system=None),
                    then=F("parent__parent__parent__eve_solar_system__name"),
                ),
                default=Value("N/A"),
                output_field=models.CharField(),
            )
        )


class LocationManagerBase(models.Manager):
    """A manager for the Location model."""

    def get_queryset(self):
        return LocationQuerySet(self.model, using=self._db)

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)

    _UPDATE_EMPTY_GRACE_MINUTES = 360

    def get_or_create_esi(self, location_id: int) -> tuple[Any, bool]:
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

    def update_or_create_esi(self, location_id: int) -> tuple[Any, bool]:
        """Update or create location object with data fetched from ESI."""
        if self.model.is_solar_system_id(location_id):
            eve_solar_system = SolarSystem.objects.get(id=location_id)
            eve_type = ItemType.objects.get(id=EVE_TYPE_ID_SOLAR_SYSTEM)
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
            station = esi.client.Universe.GetUniverseStationsStationId(
                station_id=location_id
            ).result()

            location, created = self._station_update_or_create_dict(
                location_id=location_id, station=station
            )

        else:
            # Create ID for structure
            location, created = self.get_or_create(id=location_id)

        return location, created

    def _station_update_or_create_dict(
        self, location_id: int, station: contexts.GetUniverseStationsStationIdContext
    ) -> tuple[Any, bool]:
        # pylint: disable=import-outside-toplevel
        # AA Assets
        from assets.models.eveentity import EveEntity

        logger.debug("Updating or creating station %s", station)
        if station.system_id:
            eve_solar_system = SolarSystem.objects.get(id=station.system_id)
        else:
            eve_solar_system = None

        if station.type_id:
            eve_type = ItemType.objects.get(id=station.type_id)
        else:
            eve_type = None

        if station.owner:
            owner, _ = EveEntity.objects.get_or_create_esi(eve_id=station.owner)
        else:
            owner = None

        return self.update_or_create(
            id=location_id,
            defaults={
                "name": station.name,
                "eve_solar_system": eve_solar_system,
                "eve_type": eve_type,
                "owner": owner,
            },
        )


LocationManager = LocationManagerBase.from_queryset(LocationQuerySet)
