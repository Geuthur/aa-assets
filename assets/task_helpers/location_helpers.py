from bravado.exception import HTTPForbidden

from django.core.cache import cache
from esi.exceptions import HTTPNotModified
from esi.models import Token
from eveuniverse.models import EveSolarSystem

from assets import contexts
from assets.hooks import get_extension_logger
from assets.models import Location
from assets.providers import esi

logger = get_extension_logger(__name__)


def set_error_count_flag():
    return cache.set("esi_errors_timeout", 1, 60)


def get_location_type(location_id):
    existing = Location.objects.filter(id=location_id)
    current_loc = existing.exists()

    if current_loc and location_id < 64_000_000:
        return existing.first(), existing

    existing = existing.first()

    if location_id == 2004:
        # ASSET SAFETY
        return Location(id=location_id, name="Asset Safety"), existing
    if 30_000_000 < location_id < 33_000_000:
        system, _ = EveSolarSystem.objects.get_or_create_esi(id=location_id)
        logger.debug("Fetched Solar System: %s", system)
        if not system:
            return None

        system = system.first()
        return (
            Location(
                id=location_id,
                name=system.name,
                eve_solar_system=system,
            ),
            existing,
        )
    if 60_000_000 < location_id < 64_000_000:
        try:
            station = esi.client.Universe.GetUniverseStationsStationId(
                station_id=location_id
            ).result()
            station: contexts.GetUniverseStationsStationIdContext
        except HTTPNotModified:
            logger.debug("No Updates for Station: %s", location_id)
            return existing, existing

        logger.debug("Fetched Station: %s", station)
        return (
            Location(
                id=location_id,
                name=station.name,
                eve_solar_system_id=station.system_id,
            ),
            existing,
        )
    return None, existing


# pylint: disable=too-many-return-statements
def fetch_location(location_id, location_flag, character_id):
    """Takes a location_id and character_id and returns a location model for items in a station/structure or in space"""

    standard_location_flags = [
        "AssetSafety",
        "Deliveries",
        "Hangar",
        "HangarAll",
        "solar_system",
        "OfficeFolder",
    ]
    corp_location_flags = ["CorpDeliveries"]

    accepted_flags = standard_location_flags + corp_location_flags

    if location_flag not in accepted_flags:
        # Skip unnecessary locations (e.g. Fits, Drone Bay, etc.)
        if location_flag is not None:
            logger.debug("Skipping location flag: %s", location_flag)
            return None

    # Check which location type it is
    location, existing = get_location_type(location_id)
    if location:
        return location

    req_scopes = ["esi-universe.read_structures.v1"]

    token = Token.get_token(character_id, req_scopes)

    if not token:
        return None

    try:
        structure = esi.client.Universe.GetUniverseStructuresStructureId(
            structure_id=location_id, token=token
        ).result()
        structure: contexts.GetUniverseStructuresStructureIdContext
    except HTTPForbidden as e:
        logger.debug("Failed to get: %s", e)
        if int(e.response.headers.get("x-esi-error-limit-remain")) < 50:
            set_error_count_flag()
        logger.debug(
            "Failed to get location:%s, Error:%s, Errors Remaining:%s, Time Remaining: %s",
            location_id,
            e.message,
            e.response.headers.get("x-esi-error-limit-remain"),
            e.response.headers.get("x-esi-error-limit-reset"),
        )
        return None
    except HTTPNotModified:
        logger.debug("No Updates for Location: %s", location_id)
        return existing

    system, _ = EveSolarSystem.objects.get_or_create_esi(id=structure.solar_system_id)

    if not system:
        logger.debug("Failed to get Solar System: %s", system)
        return None

    if existing:
        existing.name = structure.name
        existing.eve_solar_system = system
        existing.eve_type_id = structure.type_id
        existing.owner_id = structure.owner_id
        return existing

    return Location(
        id=location_id,
        name=structure.name,
        eve_solar_system_id=structure.solar_system_id,
        eve_type_id=structure.type_id,
        owner_id=structure.owner_id,
    )


def fetch_parent_location(parent_id, character_id):
    """Takes a parent_id and character_id and returns a location model for items in a station/structure or in space"""

    # Check which location type it is
    location, existing = get_location_type(parent_id)
    if location:
        return location

    req_scopes = ["esi-universe.read_structures.v1"]

    token = Token.get_token(character_id, req_scopes)

    if not token:
        return None

    try:
        structure = esi.client.Universe.GetUniverseStructuresStructureId(
            structure_id=parent_id, token=token
        ).result()
        structure: contexts.GetUniverseStructuresStructureIdContext
    except HTTPForbidden as e:
        logger.debug("Failed to get: %s", e)
        if int(e.response.headers.get("x-esi-error-limit-remain")) < 50:
            set_error_count_flag()
        logger.debug(
            "Failed to get location:%s, Error:%s, Errors Remaining:%s, Time Remaining: %s",
            parent_id,
            e.message,
            e.response.headers.get("x-esi-error-limit-remain"),
            e.response.headers.get("x-esi-error-limit-reset"),
        )
        return None
    except HTTPNotModified:
        logger.debug("No Updates for Parent Location: %s", parent_id)
        return existing

    system, _ = EveSolarSystem.objects.get_or_create_esi(id=structure.solar_system_id)

    if not system:
        logger.debug("Failed to get Solar System: %s", system)
        return None

    if existing:
        existing.name = structure.name
        existing.eve_solar_system = system
        existing.eve_type_id = structure.type_id
        existing.owner_id = structure.owner_id
        return existing

    return Location(
        id=parent_id,
        name=structure.name,
        eve_solar_system_id=structure.solar_system_id,
        eve_type_id=structure.type_id,
        owner_id=structure.owner_id,
    )
