"""Access control for the app: querysets and managers with `visible_to` and `manage_to`."""

# Standard Library
from typing import Generic, TypeVar

# Django
from django.contrib.auth.models import User
from django.db import models

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

# AA Assets
from assets.providers import logger

T = TypeVar("T", bound=models.Model)


class GeneralManager(models.Manager):
    """Manager for General: the app's own permission rules.

    The API, its helpers and the menu hook check permissions only through this
    manager; the Django views keep `@permissions_required("assets.<perm>")`.
    The querysets call it instead of checking permissions themselves.
    General is unmanaged, so this manager never queries the database.
    """

    @staticmethod
    def has_basic_access(user: User) -> bool:
        """Users with `basic_access` may use the app."""
        return bool(user.has_perm("assets.basic_access"))

    @staticmethod
    def has_corporation_access(user: User) -> bool:
        """Users with `corporation_access` also see their corporation's data."""
        return bool(user.has_perm("assets.corporation_access"))

    @staticmethod
    def has_manage_corporation_access(user: User) -> bool:
        """Users with `manage_corporation` may add corporations."""
        return bool(user.has_perm("assets.manage_corporation"))

    @staticmethod
    def has_manage_requests_access(user: User) -> bool:
        """Superusers and users with `manage_requests` manage all requests."""
        return bool(user.is_superuser or user.has_perm("assets.manage_requests"))

    @staticmethod
    def has_admin_access(user: User) -> bool:
        """Superusers and users with `admin_access` see everything."""
        return bool(user.is_superuser or user.has_perm("assets.admin_access"))

    @staticmethod
    def has_management_access(user: User) -> bool:
        """Superusers, `admin_access` and `manage_requests` may manage."""
        return bool(
            user.is_superuser
            or user.has_perm("assets.admin_access")
            or user.has_perm("assets.manage_requests")
        )


class AccessQuerySet(models.QuerySet[T], Generic[T]):
    """
    A QuerySet with access control methods for the whole Application.

    Same shape as the app template (aa-example). A subclass only states its
    rules: `owned_by_q` (and `visible_q`/`manage_q` when they differ) for
    the users who see a part, `sees_all`/`manages_all` for who gets everything.

    Deviations from the template, because the rules of this app differ per model:

    - `sees_all` and `manages_all` replace the single `has_full_access` check:
      who gets everything depends on the model and on seeing or managing
      (`admin_access`, `manage_requests` or both).
    - `owned_by_q` has no default: the owner lookup is named differently on
      every model.
    - `manage_to` works only with `has_manage_rule = True`: only `Owner` has
      a manage rule. Any other model raises `NotImplementedError` for every
      user instead of silently getting a rule nobody decided on.
    - `_restricted_to` takes the Q method instead of the Q object and calls it
      only after the main character check: the rules for `corporation_access`
      read the main character, which a user without one does not have.

    Methods:
        visible_to(user): Returns objects visible to the given user.
        manage_to(user): Returns objects the given user can manage.
    """

    has_manage_rule = False

    def sees_all(self, user) -> bool:
        """Whether the user sees every object without a filter."""
        return GeneralManager.has_admin_access(user)

    def manages_all(self, user) -> bool:
        """Whether the user manages every object without a filter."""
        return GeneralManager.has_management_access(user)

    def owned_by_q(self, user) -> models.Q:
        """Q object for the objects that belong to the user."""
        raise NotImplementedError(
            f"{type(self).__name__} must define its own `owned_by_q`."
        )

    def visible_q(self, user) -> models.Q:
        """Q object for the objects a user who does not see all may see."""
        return self.owned_by_q(user)

    def manage_q(self, user) -> models.Q:
        """Q object for the objects a user who does not manage all may manage."""
        return self.owned_by_q(user)

    def _restricted_to(self, user, has_all: bool, query, what: str):
        if has_all:
            logger.debug("Returning all %s objects for %s.", what, user)
            return self

        if not getattr(user.profile, "main_character", None):
            logger.debug("User %s has no main character. Nothing %s.", user, what)
            return self.none()

        return self.filter(query(user))

    def visible_to(self, user):
        """Get all objects visible to the user."""
        return self._restricted_to(user, self.sees_all(user), self.visible_q, "visible")

    def manage_to(self, user):
        """Get QuerySet of objects that the user can manage."""
        if not self.has_manage_rule:
            raise NotImplementedError(f"{type(self).__name__} has no manage rule.")
        return self._restricted_to(
            user, self.manages_all(user), self.manage_q, "manageable"
        )


class AccessManager(models.Manager[T], Generic[T]):
    """
    A Manager with access control methods for the whole Application

    This manager provides methods to filter querysets based on user permissions,
    such as `visible_to` and `manage_to`, ensuring that users only see or manage
    the objects they are allowed to.

    Deviation from the template: `visible_eve_characters` returns all characters
    for `has_manage_requests_access` (superuser or `manage_requests`), the rule
    this app always had, not for a full access permission.
    """

    def get_queryset(self) -> AccessQuerySet[T]:
        return AccessQuerySet(self.model, using=self._db)

    def visible_to(self, user):
        return self.get_queryset().visible_to(user)

    def manage_to(self, user):
        return self.get_queryset().manage_to(user)

    @staticmethod
    def visible_eve_characters(user):
        """EveCharacters a user may pick, e.g. when adding an owner."""
        qs = EveCharacter.objects.get_queryset()
        if GeneralManager.has_manage_requests_access(user):
            logger.debug("Returning all characters for %s.", user)
            return qs.all()

        if not getattr(user.profile, "main_character", None):
            logger.debug("User %s has no main character. Nothing visible.", user)
            return qs.none()

        return qs.filter(character_ownership__user=user)
