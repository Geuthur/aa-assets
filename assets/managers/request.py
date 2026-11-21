"""Manager of Request: access, open requests and their counts."""

# The access rules repeat per model; kept as they were before the split.
# pylint: disable=duplicate-code

# Django
from django.db import models
from django.db.models import Q

# AA Assets
from assets.managers.general import GeneralManager
from assets.providers import logger


class RequestQuerySet(models.QuerySet):
    def visible_to(self, user):
        if GeneralManager.has_manage_requests_access(user):
            logger.debug("Returning all for Assets Manager %s.", user)
            return self

        try:
            char = user.profile.main_character
            assert char
            queries = [models.Q(requesting_user=user)]

            logger.debug("%s queries for user %s visible.", len(queries), user)

            query = queries.pop()
            for q in queries:
                query |= q
            return self.filter(query)
        except AssertionError:
            logger.debug("User %s has no main character. Nothing visible.", user)
            return self.none()

    def requests_open(self) -> models.QuerySet:
        """Add filter to only include requests with open status."""
        request_query = self.filter(
            Q(closed_at=None) & Q(status=self.model.STATUS_OPEN)
        )
        return request_query


class RequestManagerBase(models.Manager):
    def get_queryset(self):
        return RequestQuerySet(self.model, using=self._db)

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)

    def select_related_default(self) -> models.QuerySet:
        """Add default select related to this query."""
        return self.select_related(
            "requesting_user__profile__main_character",
        )

    def open_requests_total_count(self) -> int:
        """Return total count of open requests for user"""
        return self.all().requests_open().count()


RequestManager = RequestManagerBase.from_queryset(RequestQuerySet)
