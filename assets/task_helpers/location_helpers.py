# Django
from django.core.cache import cache

# Alliance Auth
from esi.exceptions import HTTPClientError, HTTPNotModified
from esi.models import Token

# Alliance Auth (External Libs)
from eve_sde.models.map import SolarSystem

# AA Assets
from assets import contexts
from assets.app_settings import ASSETS_CACHE_KEY
from assets.constants import STANDARD_FLAG
from assets.models import Location
from assets.providers import esi, logger


def get_cache_key(location_id):
    return f"{ASSETS_CACHE_KEY}-{location_id}_no_permission"


def is_solar_system(location_id) -> bool:
    """Check if the location_id is in the ID range of solar systems"""
    return 30_000_000 < location_id < 33_000_000


def is_station(location_id) -> bool:
    """Check if the location_id is in the ID range of stations"""
    return 60_000_000 < location_id < 64_000_000


def get_location_type(location_id) -> tuple[Location | None, Location | None]:
    """Check if location is already in DB or is a special location type"""
    existing_location = Location.objects.filter(id=location_id)
    current_loc = existing_location.exists()

    if current_loc and location_id < 64_000_000:
        return existing_location.first(), existing_location

    existing_location = existing_location.first()

    if location_id == 2004:
        # ASSET SAFETY
        return Location(id=location_id, name="Asset Safety"), existing_location
    # Location is a Solar System
    if is_solar_system(location_id):
        system = SolarSystem.objects.filter(id=location_id).first()
        logger.debug("Fetched Solar System: %s", system)
        if not system:
            return None, existing_location

        return (
            Location(
                id=location_id,
                name=system.name,
                eve_solar_system=system,
            ),
            existing_location,
        )
    # Location is a Station
    if is_station(location_id):
        try:
            station = esi.client.Universe.GetUniverseStationsStationId(
                station_id=location_id
            ).result()
            station: contexts.GetUniverseStationsStationIdContext
        except HTTPNotModified:
            logger.debug("No Updates for Station: %s", location_id)
            return existing_location, existing_location

        logger.debug("Fetched Station: %s", station)
        return (
            Location(
                id=location_id,
                name=station.name,
                eve_solar_system_id=station.system_id,
            ),
            existing_location,
        )
    # Location is a Structure
    return None, existing_location


# pylint: disable=too-many-return-statements
def fetch_location(
    location_id, location_flag, character_id, force_refresh=False
) -> Location | None:
    """Takes a location_id and character_id and returns a location model for items in a station/structure or in space"""

    # Check if we have a cached no-permission flag
    if cache.get(get_cache_key(location_id)):
        logger.debug(
            "Skipping fetch for location_id %s due to cached no-permission flag",
            location_id,
        )
        return None

    if location_flag not in STANDARD_FLAG:
        # Skip unnecessary locations (e.g. Fits, Drone Bay, etc.)
        if location_flag is not None:
            logger.debug("Skipping location flag: %s", location_flag)
            return None

    # Check which location type it is
    location, existing_location = get_location_type(location_id)

    # Exit if location already exists and is a Solar System or Station
    if location:
        return location

    # Unknown Solar System, it is no structure
    if is_solar_system(location_id):
        logger.debug("Unknown Solar System: %s", location_id)
        return None

    # Station without update and not in DB yet, it is no structure
    if is_station(location_id):
        logger.debug("No Station data for: %s", location_id)
        return None

    req_scopes = ["esi-universe.read_structures.v1"]

    token = Token.get_token(character_id, req_scopes)

    if not token:
        return None

    try:
        structure = esi.client.Universe.GetUniverseStructuresStructureId(
            structure_id=location_id, token=token
        ).result(force_refresh=force_refresh)
        structure: contexts.GetUniverseStructuresStructureIdContext
    except HTTPNotModified:
        logger.debug("No Updates for Location: %s", location_id)
        return existing_location
    except HTTPClientError as e:
        if e.status_code == 403:
            logger.debug("Failed to get location %s due to 403 Forbidden", location_id)
            cache.set(
                get_cache_key(location_id), 1, (60 * 60 * 24 * 7)
            )  # Cache for 7 days
            return None
        logger.debug("Failed to get: %s", e)
        logger.info(
            "Failed to get location:%s, Headers:%s, Data: %s",
            location_id,
            e.headers,
            e.data,
        )
        return None

    system = SolarSystem.objects.filter(id=structure.solar_system_id).first()

    if not system:
        logger.debug("Failed to get Solar System: %s", system)
        return None

    if existing_location:
        existing_location.name = structure.name
        existing_location.eve_solar_system = system
        existing_location.eve_type_id = structure.type_id
        existing_location.owner_id = structure.owner_id
        return existing_location

    return Location(
        id=location_id,
        name=structure.name,
        eve_solar_system_id=structure.solar_system_id,
        eve_type_id=structure.type_id,
        owner_id=structure.owner_id,
    )


def fetch_parent_location(
    parent_id, character_id, force_refresh=False
) -> Location | None:
    """Takes a parent_id and character_id and returns a location model for items in a station/structure or in space"""

    # Check if we have a cached no-permission flag
    if cache.get(get_cache_key(parent_id)):
        logger.debug(
            "Skipping fetch for parent_id %s due to cached no-permission flag",
            parent_id,
        )
        return None

    # Check which location type it is
    location, existing = get_location_type(parent_id)
    if location:
        return location

    # Unknown Solar System, it is no structure
    if is_solar_system(parent_id):
        logger.debug("Unknown Solar System: %s", parent_id)
        return None

    # Station without update and not in DB yet, it is no structure
    if is_station(parent_id):
        logger.debug("No Station data for: %s", parent_id)
        return None

    req_scopes = ["esi-universe.read_structures.v1"]

    token = Token.get_token(character_id, req_scopes)

    if not token:
        return None

    try:
        structure = esi.client.Universe.GetUniverseStructuresStructureId(
            structure_id=parent_id, token=token
        ).result(force_refresh=force_refresh)
        structure: contexts.GetUniverseStructuresStructureIdContext
    except HTTPNotModified:
        logger.debug("No Updates for Parent Location: %s", parent_id)
        return existing
    except HTTPClientError as e:
        if e.status_code == 403:
            logger.debug("Failed to get location %s due to 403 Forbidden", parent_id)
            cache.set(
                get_cache_key(parent_id), 1, (60 * 60 * 24 * 7)
            )  # Cache for 7 days
            return None
        logger.debug("Failed to get: %s", e)
        logger.debug(
            "Failed to get location:%s, Headers:%s, Data: %s",
            parent_id,
            e.headers,
            e.data,
        )
        return None

    system = SolarSystem.objects.filter(id=structure.solar_system_id).first()

    if not system:
        logger.debug("Failed to get Solar System: %s", system)
        return None

    logger.debug("Fetched Structure: %s", structure.name)

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
