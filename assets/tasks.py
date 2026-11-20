"""App Tasks"""

# Standard Library
import datetime

# Third Party
from celery import Task, shared_task

# Django
from django.utils import timezone

# Alliance Auth
from allianceauth.eveonline.models import Token
from allianceauth.services.tasks import QueueOnce
from esi.exceptions import HTTPNotModified

# Alliance Auth (External Libs)
from eve_sde.models.types import ItemType

# AA Assets
from assets import contexts
from assets.app_settings import ASSETS_CACHE_KEY, ASSETS_TASKS_TIME_LIMIT
from assets.constants import STANDARD_FLAG
from assets.models import Assets, Location, Owner
from assets.providers import esi, logger, retry_task_on_esi_error
from assets.task_helpers.location_helpers import fetch_location, fetch_parent_location

TZ_STRING = "%Y-%m-%dT%H:%M:%SZ"

MAX_RETRIES_DEFAULT = 3

# Default params for all tasks.
TASK_DEFAULTS = {
    "time_limit": ASSETS_TASKS_TIME_LIMIT,
    "max_retries": MAX_RETRIES_DEFAULT,
}

# Default params for tasks that need run once only.
TASK_DEFAULTS_ONCE = {**TASK_DEFAULTS, **{"base": QueueOnce}}
# Default params for tasks that need bind=True and run once only.
TASK_DEFAULTS_BIND_ONCE = {**TASK_DEFAULTS, **{"bind": True, "base": QueueOnce}}
# Default params for tasks that run once per owner and are bound to the task instance.
TASK_DEFAULTS_BIND_ONCE_OWNER = {
    **TASK_DEFAULTS_BIND_ONCE,
    **{"once": {"keys": ["owner_pk"], "graceful": True}},
}


@shared_task(**TASK_DEFAULTS_ONCE)
def update_all_assets(force_refresh: bool = False) -> int:
    """Queue an update for every active owner. Returns the number of queued updates."""
    owner_pks = list(Owner.objects.filter(is_active=True).values_list("pk", flat=True))
    for owner_pk in owner_pks:
        update_assets_for_owner.apply_async(
            args=[owner_pk], kwargs={"force_refresh": force_refresh}, priority=6
        )

    logger.info("Queued %s Assets Updates", len(owner_pks))
    return len(owner_pks)


@shared_task(**TASK_DEFAULTS_BIND_ONCE_OWNER)
def update_assets_for_owner(
    self: Task, owner_pk: int, force_refresh: bool = False
) -> bool:
    """
    Update the stale sections of one owner.

    ESI outages and limits retry the whole task through `retry_task_on_esi_error`,
    errors of a single section end up in its update status.

    Args:
        owner_pk (int): Primary key of the Owner to update.
        force_refresh (bool): If True, every section is fetched again.

    Returns:
        bool: True if at least one section was updated, False otherwise.
    """
    try:
        owner = Owner.objects.get(pk=owner_pk)
    except Owner.DoesNotExist:
        logger.warning("Owner with pk %s not found.", owner_pk)
        return False

    sections = owner.get_sections_to_update(force_refresh=force_refresh)
    if not sections:
        logger.info("No updates needed for %s", owner)
        return False

    with retry_task_on_esi_error(self):
        for section in sections:
            logger.debug("Updating %s for %s", section, owner)
            owner.execute_section(section, force_refresh=force_refresh)

    logger.debug("Executed %s section updates for %s", len(sections), owner)
    return True


@shared_task(**TASK_DEFAULTS_ONCE)
def update_all_locations(force_refresh=False, runs: int = 0):
    """Update all locations."""
    skip_date = timezone.now() - datetime.timedelta(days=7)

    assets_loc_ids = list(
        Assets.objects.filter(location_flag__in=STANDARD_FLAG).values_list(
            "location_id", flat=True
        )
    )

    location_ids = list(
        Location.objects.filter(
            updated_at__lte=skip_date, id__in=set(assets_loc_ids)
        ).values_list("id", flat=True)
    )

    all_locations = set(assets_loc_ids + location_ids)

    for location in all_locations:
        update_location.apply_async(
            args=[location], kwargs={"force_refresh": force_refresh}, priority=8
        )
        runs = runs + 1
    logger.debug("Queued %s/%s Structure Tasks", runs, len(all_locations))


@shared_task(**TASK_DEFAULTS_BIND_ONCE)
def update_location(self: Task, location_id, force_refresh=False):
    """Fetch and update a location from ESI."""
    asset = Assets.objects.filter(location_id=location_id).select_related(
        "owner__character__character"
    )

    char_ids = []
    if asset.exists():
        char_ids += asset.values_list(
            "owner__character__character__character_id", flat=True
        )
    char_ids = set(char_ids)

    with retry_task_on_esi_error(self):
        if location_id < 64_000_000:
            location = fetch_location(location_id, None, 0, force_refresh=force_refresh)
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
            location = fetch_location(
                location_id, None, char_id, force_refresh=force_refresh
            )
            if location is not None:
                location.save()
                count = Assets.objects.filter(
                    location_id=location_id, location__name=""
                ).update(location_id=location_id)
                logger.debug("Updated %s Assets with Location Name", count)
                return

    logger.debug("No Characters for Location ID: %s", location_id)
    return


@shared_task(**TASK_DEFAULTS_BIND_ONCE)
def update_all_parent_locations(self: Task, force_refresh=False):
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
            with retry_task_on_esi_error(self):
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
@shared_task(**TASK_DEFAULTS_BIND_ONCE)
def update_parent_location(
    self: Task, location_id, parent_id, character_id, eve_type_id, force_refresh=False
):
    parent_check = Location.objects.get(id=location_id)

    if parent_check.parent is not None:
        logger.debug("Location ID: %s Already has Parent ID", location_id)
        return

    with retry_task_on_esi_error(self):
        parent = fetch_parent_location(
            parent_id, character_id, force_refresh=force_refresh
        )
    if parent is not None:
        eve_type = ItemType.objects.get(id=eve_type_id)
        Location.objects.update_or_create(
            id=location_id,
            defaults={
                "parent": parent,
                "eve_type": eve_type,
            },
        )
        logger.debug("Parent Location: %s Updated for %s", parent_id, location_id)
        return
    logger.debug("Parent Location Task: %s Complete", location_id)
    return


@shared_task(base=QueueOnce)
def clear_all_etags():
    logger.debug("Clearing all etags")
    try:
        # Third Party
        # pylint: disable=import-outside-toplevel
        from django_redis import get_redis_connection

        _client = get_redis_connection("default")
    except (NotImplementedError, ModuleNotFoundError):
        # Django
        # pylint: disable=import-outside-toplevel
        from django.core.cache import caches

        default_cache = caches["default"]
        _client = default_cache.get_master_client()
    keys = _client.keys(f":?:{ASSETS_CACHE_KEY}-*")
    logger.info("Deleting %s etag keys", len(keys))
    if keys:
        deleted = _client.delete(*keys)
        logger.info("Deleted %s etag keys", deleted)
    else:
        logger.info("No etag keys to delete")
