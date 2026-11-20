"""Manager of Owner: access to owners and their characters."""

# The access rules repeat per model; kept as they were before the split.
# pylint: disable=duplicate-code

# Standard Library
from typing import TYPE_CHECKING

# Django
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Case, Count, Q, Value, When

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

# AA Assets
from assets.managers.general import GeneralManager
from assets.models.helpers.update_manager import (
    OwnerUpdateSection,
    UpdateSectionResult,
    UpdateStatus,
)
from assets.providers import esi, logger

if TYPE_CHECKING:
    # AA Assets
    from assets.models.owner import Owner, OwnerUpdateStatus


class OwnerQuerySet(models.QuerySet):
    def visible_to(self, user):
        if GeneralManager.has_admin_access(user):
            logger.debug("Returning all for admin %s.", user)
            return self

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(character__user=user)]

            logger.debug(
                "%s queries for user %s visible characters.", len(queries), user
            )

            if GeneralManager.has_corporation_access(user):
                logger.debug(
                    "Returning own corporation for Corporation Manager %s.", user
                )
                queries.append(
                    models.Q(corporation__corporation_id=char.corporation_id)
                )

            query = queries.pop()
            for q in queries:
                query |= q
            return self.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return self.none()

    def manage_to(self, user: User):
        if GeneralManager.has_management_access(user):
            logger.debug("Returning all for manager %s.", user)
            return self

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(character__user=user)]

            logger.debug(
                "%s queries for user %s visible chracters.", len(queries), user
            )

            query = queries.pop()
            for q in queries:
                query |= q
            return self.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return self.none()


class OwnerManagerBase(models.Manager):
    def get_queryset(self):
        return OwnerQuerySet(self.model, using=self._db)

    @staticmethod
    def visible_eve_characters(user):
        qs = EveCharacter.objects.get_queryset()
        if GeneralManager.has_manage_requests_access(user):
            logger.debug("Returning all for Assets Manager %s.", user)
            return qs.all()

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(character_ownership__user=user)]

            logger.debug("%s queries for user %s visible.", len(queries), user)

            query = queries.pop()
            for q in queries:
                query |= q
            return qs.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return qs.none()

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)

    def manage_to(self, user):
        return self.get_queryset().manage_to(user)

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
