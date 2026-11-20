"""General model: the app's permissions."""

# Django
from django.db import models
from django.utils.translation import gettext_lazy as _

# AA Assets
from assets.managers.general import GeneralManager


class General(models.Model):
    """General model for app permissions"""

    objects = GeneralManager()

    class Meta:
        managed = False
        verbose_name = "AA-Assets"
        verbose_name_plural = "AA-Assets"
        permissions = (
            ("basic_access", _("Can access this app")),
            ("corporation_access", _("Can access own corporation assets")),
            ("admin_access", _("Can access all assets.")),
            ("manage_corporation", _("Can add corporation assets")),
            ("manage_requests", _("Can manage requests")),
        )
        default_permissions = ()
