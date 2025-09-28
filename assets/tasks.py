"""App Tasks"""

import datetime
import json

from celery import shared_task

from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from eveuniverse.models import EveType

from allianceauth.eveonline.models import Token
from allianceauth.services.tasks import QueueOnce
from app_utils.allianceauth import get_redis_client

from assets.app_settings import ASSETS_CACHE_KEY, ASSETS_UPDATE_PERIOD
from assets.decorators import when_esi_is_available
from assets.hooks import get_extension_logger
from assets.models import Assets, Location, Owner
from assets.providers import esi
from assets.task_helpers.etag_helpers import NotModifiedError, etag_results
from assets.task_helpers.location_helpers import fetch_location, fetch_parent_location

TZ_STRING = "%Y-%m-%dT%H:%M:%SZ"
logger = get_extension_logger(__name__)


def build_loc_cache_tag(location_id):
    return f"loc_id_{location_id}"


def build_loc_cooldown_cache_tag(location_id):
    return f"cooldown_loc_id_{location_id}"


def get_loc_cooldown(location_id):
    return cache.get(build_loc_cooldown_cache_tag(location_id), False)


def set_loc_cooldown(location_id):
    """Set a 7 days cooldown for a location_id"""
    return cache.set(
        build_loc_cooldown_cache_tag(location_id), True, (60 * 60 * 24 * 7)
    )


def location_get(location_id):
    cache_tag = build_loc_cache_tag(location_id)
    data = json.loads(cache.get(cache_tag, '{"date":false, "characters":[]}'))
    if data.get("date") is not False:
        try:
            data["date"] = datetime.datetime.strptime(
                data.get("date"), TZ_STRING
            ).replace(tzinfo=datetime.timezone.utc)
        except (ValueError, TypeError):
            data["date"] = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    return data


def location_set(location_id, character_id):
    cache_tag = build_loc_cache_tag(location_id)
    date = timezone.now() - datetime.timedelta(days=7)
    data = location_get(location_id)
    if data.get("date") is not False:
        if data.get("date") > date:
            data.get("characters").append(character_id)
            cache.set(cache_tag, json.dumps(data, cls=DjangoJSONEncoder), None)
            return True

        data["date"] = timezone.now().strftime(TZ_STRING)
        data["characters"] = [character_id]
        cache.set(cache_tag, json.dumps(data, cls=DjangoJSONEncoder), None)

    if character_id not in data.get("characters"):
        data.get("characters").append(character_id)
        data["date"] = timezone.now().strftime(TZ_STRING)
        cache.set(cache_tag, json.dumps(data, cls=DjangoJSONEncoder), None)
        return True

    return False


def get_error_count_flag():
    return cache.get("esi_errors_timeout", False)


@when_esi_is_available
@shared_task(bind=True, base=QueueOnce)
# pylint: disable=unused-argument
def update_all_assets(self, runs: int = 0, force_refresh=False):
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


@shared_task(bind=True, base=QueueOnce, max_retries=None)
# pylint: disable=unused-argument
def update_assets_for_owner(self, owner_pk: int, force_refresh=False):
    """Fetch all assets for an owner from ESI."""
    owner = Owner.objects.get(pk=owner_pk)
    owner.update_assets_esi(force_refresh=force_refresh)


@shared_task(bind=True, base=QueueOnce, max_retries=None)
def update_location(self, location_id, force_refresh=False):
    if get_error_count_flag():
        self.retry(countdown=300)

    if get_loc_cooldown(location_id):
        if force_refresh:
            pass
        else:
            logger.debug("Cooldown on Location ID: %s", location_id)
            return f"Cooldown on Location ID: {location_id}"

    # Get Cached location data
    cached_data = location_get(location_id)
    skip_date = timezone.now() - datetime.timedelta(days=7)

    asset = Assets.objects.filter(location_id=location_id).select_related(
        "owner__character__character"
    )

    if cached_data.get("date") is not False:
        if cached_data.get("date") > skip_date:
            asset = asset.exclude(
                owner__character__character__character_id__in=cached_data.get(
                    "characters"
                )
            )

    char_ids = []
    if asset.exists():
        char_ids += asset.values_list(
            "owner__character__character__character_id", flat=True
        )

    char_ids = set(char_ids)

    if location_id < 64_000_000:
        location = fetch_location(location_id, None, 0)
        if location is not None:
            location.save()
            count = Assets.objects.filter(
                location_id=location_id, location__name=""
            ).update(location_id=location_id)
            logger.debug("Updated %s Assets with Location Name", count)
            return count
        if get_error_count_flag():
            self.retry(countdown=300)

    if len(char_ids) == 0:
        set_loc_cooldown(location_id)
        logger.debug("No Characters for Location ID: %s", location_id)
        return f"No Characters for Location ID: {location_id}"

    for char_id in char_ids:
        location = fetch_location(location_id, None, char_id)
        if location is not None:
            location.save()
            count = Assets.objects.filter(
                location_id=location_id, location__name=""
            ).update(location_id=location_id)
            logger.debug("Updated %s Assets with Location Name", count)
            return count

        location_set(location_id, char_id)
        if get_error_count_flag():
            self.retry(countdown=300)

    set_loc_cooldown(location_id)
    logger.debug("No Characters for Location ID: %s, Set Cooldown", location_id)
    return f"No Characters for Location ID: {location_id}, Set Cooldown"


@when_esi_is_available
@shared_task(bind=True, base=QueueOnce)
# pylint: disable=unused-argument
def update_all_locations(self, force_refresh=False, runs: int = 0):
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
        if not get_loc_cooldown(location):
            update_location.apply_async(
                args=[location], kwargs={"force_refresh": force_refresh}, priority=8
            )
            runs = runs + 1
    logger.debug("Queued %s/%s Structure Tasks", runs, len(all_locations))
    return f"Queued {runs} Structure Tasks"


@shared_task(bind=True, base=QueueOnce, max_retries=None)
def update_all_parent_locations(self, force_refresh=False):
    if get_error_count_flag():
        self.retry(countdown=300)

    assets = Assets.objects.all().select_related("owner__character__character")

    owners = Owner.objects.filter(is_active=True)

    if not owners.exists():
        logger.debug("No Characters found skip Update")
        return "No Characters found skip Update"

    asset_ids = []
    asset_locations = {}
    assets_by_id = {}

    count = 0
    for owner in owners:
        owner_id = owner.character.character.character_id
        if owner.corporation is None:
            req_scopes = [
                "esi-universe.read_structures.v1",
                "esi-assets.read_assets.v1",
            ]
            token = Token.get_token(owner_id, req_scopes)

            assets_esi = esi.client.Assets.get_characters_character_id_assets(
                character_id=owner.character.character.character_id,
                token=token.valid_access_token(),
            )

            assets = etag_results(assets_esi, token, force_refresh=force_refresh)
        else:
            req_scopes = [
                "esi-universe.read_structures.v1",
                "esi-assets.read_corporation_assets.v1",
            ]
            token = Token.get_token(owner_id, req_scopes)

            assets_esi = esi.client.Assets.get_corporations_corporation_id_assets(
                corporation_id=owner.corporation.corporation_id,
                token=token.valid_access_token(),
            )

            assets = etag_results(assets_esi, token, force_refresh=force_refresh)

        try:
            for asset in assets:
                asset_ids.append(asset["item_id"])
                assets_by_id[asset["item_id"]] = asset
                if asset["location_id"] in asset_ids:
                    location_id = asset["location_id"]
                    asset_locations[location_id] = [asset["item_id"]]
            for location_id in asset_locations:
                asset = assets_by_id[location_id]
                parent_id = asset["location_id"]
                eve_type = asset["type_id"]

                update_parent_location.apply_async(
                    args=[location_id, parent_id, owner_id, eve_type],
                    kwargs={"force_refresh": force_refresh},
                    priority=8,
                )
                count = count + 1
        except NotModifiedError:
            logger.debug("No Updates for Parent Locations")
            return "No Updates for Parent Locations"

    logger.debug("Queued %s Parent Locations Updated Tasks", count)
    return f"Queued {count} Parent Locations Updated Tasks"


# pylint: disable=too-many-positional-arguments
@shared_task(bind=True, base=QueueOnce, max_retries=None)
def update_parent_location(
    self, location_id, parent_id, character_id, eve_type_id, force_refresh=False
):
    if get_error_count_flag():
        self.retry(countdown=300)

    if get_loc_cooldown(parent_id):
        if force_refresh:
            pass
        else:
            logger.debug("Cooldown on Location ID: %s", parent_id)
            return f"Cooldown on Location ID: {parent_id}"

    skip_date = timezone.now() - datetime.timedelta(days=7)
    parent_check = Location.objects.get(id=location_id)

    # Get Cached location data
    cached_data = location_get(parent_id)
    if cached_data.get("date") is not False:
        if cached_data.get("date") > skip_date:
            logger.debug(
                "Excluding Parent ID: %s from %s",
                parent_id,
                cached_data.get("characters"),
            )
            return (
                f"Excluding Parent ID: {parent_id} from {cached_data.get('characters')}"
            )

    if parent_check.parent is not None:
        logger.debug("Location ID: %s Already has Parent ID", location_id)
        return f"Location ID: {location_id} Already has Parent ID"

    parent = fetch_parent_location(parent_id, character_id)
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
        return f"Parent Location: {location_id} Updated"

    location_set(parent_id, character_id)
    if get_error_count_flag():
        self.retry(countdown=300)

    set_loc_cooldown(parent_id)
    logger.debug("Parent Location Task: %s Complete, Set Cooldown", location_id)
    return f"Parent Location Task: {location_id} Complete, Set Cooldown"


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
