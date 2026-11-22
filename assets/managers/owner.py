"""Manager of Owner: access to owners and their characters."""

# Standard Library
from typing import TYPE_CHECKING

# Django
from django.db import models
from django.db.models import Case, Count, Q, Value, When

# AA Assets
from assets.managers.general import AccessManager, AccessQuerySet, GeneralManager
from assets.models.helpers.update_manager import (
    OwnerUpdateSection,
    UpdateSectionResult,
    UpdateStatus,
)
from assets.providers import esi, logger

if TYPE_CHECKING:
    # AA Assets
    from assets.models.owner import Owner, OwnerUpdateStatus


class OwnerQuerySet(AccessQuerySet["Owner"]):
    """
    Owners of the user's characters, with `corporation_access` also the owner
    of the main character's corporation. Managing stays with the own characters.
    """

    has_manage_rule = True

    def owned_by_q(self, user) -> models.Q:
        return models.Q(character__user=user)

    def visible_q(self, user) -> models.Q:
        query = self.owned_by_q(user)
        if GeneralManager.has_corporation_access(user):
            query |= models.Q(
                corporation__corporation_id=user.profile.main_character.corporation_id
            )
        return query


class OwnerManagerBase(AccessManager["Owner"]):
    def get_queryset(self):
        return OwnerQuerySet(self.model, using=self._db)

    # ESI section: the owner's `update_<section>` method calls this
    def update_assets_esi(
        self, owner: "Owner", force_refresh: bool = False
    ) -> UpdateSectionResult:
        """Update the assets of an owner from ESI."""
        return owner.update_manager.update_section_if_changed(
            section=OwnerUpdateSection.ASSETS,
            fetch_func=self._fetch_assets_esi,
            force_refresh=force_refresh,
        )

    def _fetch_assets_esi(self, owner: "Owner", force_refresh: bool = False) -> int:
        """Fetch the assets from ESI and replace the assets of the owner."""
        token = owner.valid_token(owner.get_esi_scopes())

        if owner.corporation:
            operation = esi.client.Assets.GetCorporationsCorporationIdAssets(
                corporation_id=owner.corporation_strict.corporation_id,
                token=token,
            )
        else:
            operation = esi.client.Assets.GetCharactersCharacterIdAssets(
                character_id=owner.eve_character_strict.character_id,
                token=token,
            )
        assets = operation.results(force_refresh=force_refresh)

        # An empty list is a real state (e.g. everything sold or moved):
        # 304 and HTTP errors raise before, so the old assets must go too.
        items = owner.process_assets(assets)
        owner.replace_assets(items)
        logger.info("Updated %s assets for %s", len(items), owner.name)
        return len(items)


OwnerManager = OwnerManagerBase.from_queryset(OwnerQuerySet)


class OwnerUpdateStatusQuerySet(models.QuerySet["OwnerUpdateStatus"]):
    def get_status(self) -> UpdateStatus:
        """Return the current aggregate update status."""
        total_update_status = (
            self.annotate_total_update_status()
            .values_list("total_update_status", flat=True)
            .order_by("total_update_status")
            .first()
        )

        if total_update_status is None:
            return UpdateStatus.INCOMPLETE
        return UpdateStatus(total_update_status)

    def annotate_total_update_status(self):
        """Annotate one aggregate status per owner over all sections."""
        sections = OwnerUpdateSection.get_sections()
        total_sections = len(sections)
        qs = (
            self.values("owner_id", "owner__is_active")
            .annotate(num_sections_found=Count("pk", filter=Q(section__in=sections)))
            .annotate(
                num_sections_ok=Count(
                    "pk", filter=Q(section__in=sections, is_success=True)
                )
            )
            .annotate(
                num_sections_failed=Count(
                    "pk", filter=Q(section__in=sections, is_success=False)
                )
            )
            .annotate(
                num_sections_token_error=Count(
                    "pk", filter=Q(section__in=sections, has_token_error=True)
                )
            )
            # pylint: disable=no-member
            .annotate(
                total_update_status=Case(
                    When(owner__is_active=False, then=Value(UpdateStatus.DISABLED)),
                    When(
                        num_sections_token_error__gt=0,
                        then=Value(UpdateStatus.TOKEN_ERROR),
                    ),
                    When(num_sections_failed__gt=0, then=Value(UpdateStatus.ERROR)),
                    When(num_sections_ok=total_sections, then=Value(UpdateStatus.OK)),
                    When(
                        num_sections_found__lt=total_sections,
                        then=Value(UpdateStatus.INCOMPLETE),
                    ),
                    default=Value(UpdateStatus.IN_PROGRESS),
                )
            )
        )

        return qs


class OwnerUpdateStatusManager(models.Manager["OwnerUpdateStatus"]):
    def get_queryset(self):
        return OwnerUpdateStatusQuerySet(model=self.model, using=self._db)

    def get_status(self) -> UpdateStatus:
        """Return the current aggregate update status."""
        return self.get_queryset().get_status()

    def annotate_total_update_status(self):
        """Annotate one aggregate status per owner over all sections."""
        return self.get_queryset().annotate_total_update_status()
