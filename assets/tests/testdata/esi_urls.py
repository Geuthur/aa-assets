"""Helpers for ESI tests with pook."""

# Django
from django.core.cache import cache

ESI_BASE_URL = "https://esi.evetech.net"


def character_assets_url(character_id: int) -> str:
    """Return the ESI URL of the assets of a character."""
    return f"{ESI_BASE_URL}/characters/{character_id}/assets"


def station_url(station_id: int) -> str:
    """Return the ESI URL of a station."""
    return f"{ESI_BASE_URL}/universe/stations/{station_id}"


def structure_url(structure_id: int) -> str:
    """Return the ESI URL of a structure."""
    return f"{ESI_BASE_URL}/universe/structures/{structure_id}"


def clear_esi_limits() -> None:
    """Remove the ESI error limit from the cache."""
    cache.delete("esi_error_limit_reset")
