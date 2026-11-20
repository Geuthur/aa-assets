"""Location model: stations, structures and solar systems."""

# Django
from django.db import models

# Alliance Auth
from allianceauth.eveonline.evelinks import dotlan

# Alliance Auth (External Libs)
from eve_sde.models.map import SolarSystem
from eve_sde.models.types import ItemType

# AA Assets
from assets.managers.location import LocationManager
from assets.models.eveentity import EveEntity


class Location(models.Model):
    """An Eve Online location: Station or Upwell Structure or Solar System"""

    _SOLAR_SYSTEM_ID_START = 30_000_000
    _SOLAR_SYSTEM_ID_END = 33_000_000
    _STATION_ID_START = 60_000_000
    _STATION_ID_END = 64_000_000

    id = models.PositiveBigIntegerField(
        primary_key=True,
        help_text=(
            "Eve Online location ID, "
            "either item ID for stations or structure ID for structures"
        ),
    )
    parent = models.ForeignKey(
        "Location",
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        help_text=("Eve Online location ID of the parent object"),
        related_name="+",
    )

    name = models.CharField(
        max_length=100,
        help_text="In-game name of this station or structure",
    )
    eve_solar_system = models.ForeignKey(
        SolarSystem,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        related_name="+",
    )
    eve_type = models.ForeignKey(
        ItemType,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        related_name="+",
    )
    owner = models.ForeignKey(
        EveEntity,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        help_text="corporation this station or structure belongs to",
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = LocationManager()

    class Meta:
        default_permissions = ()

    def __str__(self) -> str:
        if self.name:
            return self.name
        if self.eve_type:
            return str(self.eve_type)
        return f"Location #{self.id}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, name='{self.name}')"

    @property
    def is_empty(self) -> bool:
        """Return True if this is an empty location, else False."""
        return not self.eve_solar_system and not self.eve_type and not self.parent_id

    @property
    def solar_system_url(self) -> str:
        """Return dotlan URL for this solar system."""
        try:
            return dotlan.solar_system_url(self.eve_solar_system.name)
        except AttributeError:
            return ""

    @property
    def is_solar_system(self) -> bool:
        """Return True if this location is a solar system, else False."""
        return self.is_solar_system_id(self.id)

    @property
    def is_station(self) -> bool:
        """Return True if this location is a station, else False."""
        return self.is_station_id(self.id)

    @classmethod
    def is_solar_system_id(cls, location_id: int) -> bool:
        """Return True if the given ID is a solar system ID, else False."""
        return cls._SOLAR_SYSTEM_ID_START <= location_id <= cls._SOLAR_SYSTEM_ID_END

    @classmethod
    def is_station_id(cls, location_id: int) -> bool:
        """Return True if the given ID is a station ID, else False."""
        return cls._STATION_ID_START <= location_id <= cls._STATION_ID_END

    def full_qualified_name(self) -> str:
        """Return the full qualified name of this location."""
        if self.parent:
            return f"{self.parent.full_qualified_name()} - {str(self)}"
        return str(self)
