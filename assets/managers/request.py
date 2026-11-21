"""Manager of Request: access, open requests and their counts."""

# Standard Library
from typing import TYPE_CHECKING

# Django
from django.db import models
from django.db.models import Q

# AA Assets
from assets.managers.general import AccessManager, AccessQuerySet, GeneralManager

if TYPE_CHECKING:
    # AA Assets
    from assets.models.request import Request


class RequestQuerySet(AccessQuerySet["Request"]):
    """Requests of the user; `manage_requests` instead of `admin_access` sees all."""

    def sees_all(self, user) -> bool:
        return GeneralManager.has_manage_requests_access(user)

    def owned_by_q(self, user) -> models.Q:
        return models.Q(requesting_user=user)

    def requests_open(self) -> models.QuerySet:
        """Add filter to only include requests with open status."""
        request_query = self.filter(
            Q(closed_at=None) & Q(status=self.model.STATUS_OPEN)
        )
        return request_query


class RequestManagerBase(AccessManager["Request"]):
    def get_queryset(self):
        return RequestQuerySet(self.model, using=self._db)

    def select_related_default(self) -> models.QuerySet:
        """Add default select related to this query."""
        return self.select_related(
            "requesting_user__profile__main_character",
        )

    def open_requests_total_count(self) -> int:
        """Return total count of open requests for user"""
        return self.all().requests_open().count()


RequestManager = RequestManagerBase.from_queryset(RequestQuerySet)
