"""Manager of Owner: access to owners and their characters."""

# The access rules repeat per model; kept as they were before the split.
# pylint: disable=duplicate-code

# Django
from django.contrib.auth.models import User
from django.db import models

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

# AA Assets
from assets.managers.general import GeneralManager
from assets.providers import logger


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


OwnerManager = OwnerManagerBase.from_queryset(OwnerQuerySet)
