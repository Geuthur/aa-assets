"""App Tasks"""

# Standard Library
import datetime

# Third Party
from celery import shared_task

# Django
from django.utils import timezone

# Alliance Auth
from allianceauth.eveonline.models import Token
from allianceauth.services.tasks import QueueOnce
from esi.exceptions import HTTPNotModified

# Alliance Auth (External Libs)
from app_utils.allianceauth import get_redis_client
from eveuniverse.models import EveType

# AA Assets
from assets import contexts
from assets.app_settings import (
    ASSETS_CACHE_KEY,
    ASSETS_TASKS_TIME_LIMIT,
    ASSETS_UPDATE_PERIOD,
)
from assets.decorators import when_esi_is_available
from assets.hooks import get_extension_logger
from assets.models import Assets, Location, Owner
from assets.providers import esi
from assets.task_helpers.location_helpers import fetch_location, fetch_parent_location

TZ_STRING = "%Y-%m-%dT%H:%M:%SZ"
logger = get_extension_logger(__name__)

MAX_RETRIES_DEFAULT = 3

# Default params for all tasks.
TASK_DEFAULTS = {
    "time_limit": ASSETS_TASKS_TIME_LIMIT,
    "max_retries": MAX_RETRIES_DEFAULT,
}

# Default params for tasks that need run once only.
TASK_DEFAULTS_ONCE = {**TASK_DEFAULTS, **{"base": QueueOnce}}


@shared_task(**TASK_DEFAULTS_ONCE)
@when_esi_is_available
def update_all_assets(runs: int = 0, force_refresh=False):
    """Update all assets."""
    owners = Owner.objects.filter(is_active=True)
    skip_date = timezone.now() - datetime.timedelta(minutes=ASSETS_UPDATE_PERIOD)

    for owner in owners:
        if owner.last_update <= skip_date or force_refresh:
            update_assets_for_owner.apply_async(
                kwargs={"owner_pk": owner.pk, "force_refresh": force_refresh},
                priority=6,
            )
            runs = runs + 1
    logger.info("Queued %s Assets Updates", len(owners))


@shared_task(**TASK_DEFAULTS_ONCE)
def update_assets_for_owner(owner_pk: int, force_refresh=False):
    """Fetch all assets for an owner from ESI."""
    owner = Owner.objects.get(pk=owner_pk)
    owner.update_assets_esi(force_refresh=force_refresh)


@shared_task(**TASK_DEFAULTS_ONCE)
@when_esi_is_available
def update_all_locations(force_refresh=False, runs: int = 0):
    """Fetch all assets for an owner from ESI."""
    location_flags = ["Deliveries", "Hangar", "HangarAll", "AssetSafety"]
    corp_flags = ["CorpDeliveries"]

    location_flags = location_flags + corp_flags

    skip_date = timezone.now() - datetime.timedelta(days=7)

    assets_loc_ids = list(
        Assets.objects.filter(location_flag__in=location_flags).values_list(
            "location_id", flat=True
        )
    )

    location_ids = list(
        Location.objects.filter(
            updated_at__lte=skip_date, id__in=set(assets_loc_ids)
        ).values_list("id", flat=True)
    )

    all_locations = set(assets_loc_ids + location_ids)

    logger.debug("Queued %s Structure Updates", len(all_locations))

    for location in all_locations:
        update_location.apply_async(
            args=[location], kwargs={"force_refresh": force_refresh}, priority=8
        )
        runs = runs + 1
    logger.debug("Queued %s/%s Structure Tasks", runs, len(all_locations))


@shared_task(bind=True, **TASK_DEFAULTS_ONCE)
def update_location(self, location_id, force_refresh=False):
    asset = Assets.objects.filter(location_id=location_id).select_related(
        "owner__character__character"
    )

    char_ids = []
    if asset.exists():
        char_ids += asset.values_list(
            "owner__character__character__character_id", flat=True
        )
    char_ids = set(char_ids)

    if location_id < 64_000_000:
        location, limit_exceeded = fetch_location(
            location_id, None, 0, force_refresh=force_refresh
        )
        if location is not None:
            location.save()
            count = Assets.objects.filter(
                location_id=location_id, location__name=""
            ).update(location_id=location_id)
            logger.debug("Updated %s Assets with Location Name", count)
            return

    if len(char_ids) == 0:
        logger.debug("No Characters for Location ID: %s", location_id)
        return

    for char_id in char_ids:
        location, limit_exceeded = fetch_location(
            location_id, None, char_id, force_refresh=force_refresh
        )
        if location is not None:
            location.save()
            count = Assets.objects.filter(
                location_id=location_id, location__name=""
            ).update(location_id=location_id)
            logger.debug("Updated %s Assets with Location Name", count)
            return

    if limit_exceeded:
        logger.debug(
            "ESI limit exceeded when fetching Parent Location: %s - Retry Later",
            location_id,
        )
        self.retry(countdown=300)
        return

    logger.debug("No Characters for Location ID: %s", location_id)
    return


@shared_task(**TASK_DEFAULTS_ONCE)
def update_all_parent_locations(force_refresh=False):
    assets = Assets.objects.all().select_related("owner__character__character")

    owners = Owner.objects.filter(is_active=True)

    if not owners.exists():
        logger.debug("No Characters found skip Update")
        return

    asset_ids = []
    asset_locations = {}
    assets_by_id = {}

    count = 0
    for owner in owners:
        owner_id = owner.character.character.character_id
        try:
            if owner.corporation is None:
                req_scopes = [
                    "esi-universe.read_structures.v1",
                    "esi-assets.read_assets.v1",
                ]
                token = Token.get_token(owner_id, req_scopes)
                assets_esi = esi.client.Assets.GetCharactersCharacterIdAssets(
                    character_id=owner.character.character.character_id,
                    token=token,
                )
                assets, response = assets_esi.results(
                    return_response=True,
                    force_refresh=force_refresh,
                )
                logger.debug("Response Status: %s", response.status_code)
            else:
                req_scopes = [
                    "esi-universe.read_structures.v1",
                    "esi-assets.read_corporation_assets.v1",
                ]
                token = Token.get_token(owner_id, req_scopes)

                assets_esi = esi.client.Assets.GetCorporationsCorporationIdAssets(
                    corporation_id=owner.corporation.corporation_id,
                    token=token,
                )

                assets, response = assets_esi.results(
                    return_response=True,
                    force_refresh=force_refresh,
                )
                logger.debug("Response Status: %s", response.status_code)
        except HTTPNotModified:
            logger.debug("No Updates for: %s", owner.name)
            continue

        # Collect all location ids
        for asset in assets:
            asset: contexts.GetAssetsContext

            asset_ids.append(asset.item_id)
            assets_by_id[asset.item_id] = asset
            if asset.location_id in asset_ids:
                location_id = asset.location_id
                asset_locations[location_id] = [asset.item_id]

        # Update all parent locations
        for location_id in asset_locations:
            asset = assets_by_id[location_id]
            parent_id = asset.location_id
            eve_type = asset.type_id

            update_parent_location.apply_async(
                args=[location_id, parent_id, owner_id, eve_type],
                kwargs={"force_refresh": force_refresh},
                priority=8,
            )
            count += 1

    logger.debug("Queued %s Parent Locations Updated Tasks", count)
    return


# pylint: disable=too-many-positional-arguments
@shared_task(bind=True, **TASK_DEFAULTS_ONCE)
def update_parent_location(
    self, location_id, parent_id, character_id, eve_type_id, force_refresh=False
):
    parent_check = Location.objects.get(id=location_id)

    if parent_check.parent is not None:
        logger.debug("Location ID: %s Already has Parent ID", location_id)
        return

    parent, limit_exceeded = fetch_parent_location(
        parent_id, character_id, force_refresh=force_refresh
    )
    if parent is not None:
        eve_type, _ = EveType.objects.get_or_create_esi(id=eve_type_id)
        Location.objects.update_or_create(
            id=location_id,
            defaults={
                "parent": parent,
                "eve_type": eve_type,
            },
        )
        logger.debug("Parent Location: %s Updated for %s", parent_id, location_id)
        return
    if limit_exceeded:
        logger.debug(
            "ESI limit exceeded when fetching Parent Location: %s - Retry Later",
            parent_id,
        )
        self.retry(countdown=300)
    logger.debug("Parent Location Task: %s Complete", location_id)
    return


@shared_task(base=QueueOnce)
def clear_all_etags():
    logger.debug("Clearing all etags")
    _client = get_redis_client()
    keys = _client.keys(f":?:{ASSETS_CACHE_KEY}-*")
    logger.info("Deleting %s etag keys", len(keys))
    if keys:
        deleted = _client.delete(*keys)
        logger.info("Deleted %s etag keys", deleted)
    else:
        logger.info("No etag keys to delete")
