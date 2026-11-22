"""Manager of Assets: access, name annotations and market prices."""

# Standard Library
from typing import TYPE_CHECKING

# Third Party
import requests

# Django
from django.core.cache import cache
from django.db import models
from django.db.models import Case, F, Q, Value, When
from django.db.models.functions import Concat

# AA Assets
from assets import __version__
from assets.app_settings import STORAGE_BASE_KEY
from assets.managers.general import AccessManager, AccessQuerySet, GeneralManager
from assets.providers import logger

if TYPE_CHECKING:
    # AA Assets
    from assets.models.assets import Assets

USERAGENT = f"assets v{__version__}"


def build_market_price_cache_tag(item_id):
    return f"{STORAGE_BASE_KEY}{item_id}"


def set_market_price_cache(item_id: int, price: float):
    """Set location cache for a location object."""
    return cache.set(build_market_price_cache_tag(item_id), price, (60 * 60 * 2))


def get_market_price(item_id: int) -> float:
    """Get location cache for a location object."""
    return cache.get(build_market_price_cache_tag(item_id))


class AssetsQuerySet(AccessQuerySet["Assets"]):
    """Assets of the user's character owners, with `corporation_access` also of the main character's corporation."""

    def owned_by_q(self, user) -> models.Q:
        return models.Q(owner__character__user=user)

    def visible_q(self, user) -> models.Q:
        query = self.owned_by_q(user)
        if GeneralManager.has_corporation_access(user):
            query |= models.Q(
                owner__corporation__corporation_id=user.profile.main_character.corporation_id
            )
        return query

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

    def update_or_create_prices(self, item_ids: list[int]) -> dict:
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


class AssetsManagerBase(AccessManager["Assets"]):
    """A manager for the Assets model."""

    def get_queryset(self):
        return AssetsQuerySet(self.model, using=self._db)


AssetsManager = AssetsManagerBase.from_queryset(AssetsQuerySet)
