"""EveEntity model: alliances, corporations and characters."""

# Django
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth.eveonline.models import (
    EveAllianceInfo,
    EveCharacter,
    EveCorporationInfo,
)

# AA Assets
from assets.helpers.eveonline import (
    get_alliance_logo_url,
    get_character_portrait_url,
    get_corporation_logo_url,
)
from assets.managers.eveentity import EveEntityManager


class EveEntity(models.Model):
    """An Eve entity like a corporation or a character"""

    objects: EveEntityManager = EveEntityManager()

    class Meta:
        default_permissions = ()

    CATEGORY_ALLIANCE = "alliance"
    CATEGORY_CHARACTER = "character"
    CATEGORY_CORPORATION = "corporation"

    CATEGORY_CHOICES = (
        (CATEGORY_ALLIANCE, "Alliance"),
        (CATEGORY_CORPORATION, "Corporation"),
        (CATEGORY_CHARACTER, "Character"),
    )

    id = models.IntegerField(
        primary_key=True, validators=[MinValueValidator(0)], verbose_name=_("ID")
    )
    category = models.CharField(
        max_length=32, choices=CATEGORY_CHOICES, verbose_name=_("Category")
    )
    name = models.CharField(max_length=254, verbose_name=_("Name"))

    # optionals for character/corp
    corporation = models.ForeignKey(
        "EveEntity",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        related_name="corp",
    )
    alliance = models.ForeignKey(
        "EveEntity",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        related_name="alli",
    )
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.name)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self.id}, category='{self.category}', "
            f"name='{self.name}')"
        )

    @property
    def is_alliance(self) -> bool:
        """Return True if entity is an alliance, else False."""
        return self.category == self.CATEGORY_ALLIANCE

    @property
    def is_corporation(self) -> bool:
        """Return True if entity is an corporation, else False."""
        return self.category == self.CATEGORY_CORPORATION

    @property
    def is_character(self) -> bool:
        """Return True if entity is a character, else False."""
        return self.category == self.CATEGORY_CHARACTER

    def get_portrait(self, size=64, as_html=False) -> str:
        """
        Get the portrait URL for this entity.

        Args:
            size (int, optional): The size of the portrait.
            as_html (bool, optional): Whether to return the portrait as an HTML img tag.
        Returns:
            str: The URL of the portrait or an HTML img tag.
        """
        if self.category == self.CATEGORY_ALLIANCE:
            return get_alliance_logo_url(
                alliance_id=self.id,
                size=size,
                alliance_name=self.name,
                as_html=as_html,
            )

        if self.category == self.CATEGORY_CORPORATION:
            return get_corporation_logo_url(
                corporation_id=self.id,
                size=size,
                corporation_name=self.name,
                as_html=as_html,
            )

        if self.category == self.CATEGORY_CHARACTER:
            return get_character_portrait_url(
                character_id=self.id,
                size=size,
                character_name=self.name,
                as_html=as_html,
            )
        return ""

    def icon_url(self, size=128) -> str:
        """Url to an icon image for this organization."""
        if self.category == self.CATEGORY_ALLIANCE:
            return EveAllianceInfo.generic_logo_url(self.id, size=size)

        if self.category == self.CATEGORY_CORPORATION:
            return EveCorporationInfo.generic_logo_url(self.id, size=size)

        if self.category == self.CATEGORY_CHARACTER:
            return EveCharacter.generic_portrait_url(self.id, size=size)

        raise NotImplementedError(
            f"Avatar URL not implemented for category {self.category}"
        )

    def needs_update(self):
        return self.last_update + timezone.timedelta(days=7) < timezone.now()
