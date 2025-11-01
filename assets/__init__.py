"""Initialize the app"""

__version__ = "0.2.0"
__title__ = "Assets"

__package_name__ = "aa-assets"
__app_name__ = "assets"
__esi_compatibility_date__ = "2025-08-26"
__app_name_useragent__ = "AA-Assets"

__github_url__ = f"https://github.com/Geuthur/{__package_name__}"

__character_operations__ = [
    "GetCharactersCharacterIdAssets",
]

__corporation_operations__ = [
    "GetCorporationsCorporationIdAssets",
]

__universe_operations__ = [
    "GetUniverseStationsStationId",
    "GetUniverseStructuresStructureId",
]
