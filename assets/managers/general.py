"""Manager of General: the app's permission rules."""

# Django
from django.contrib.auth.models import User
from django.db import models


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
