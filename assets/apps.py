"""App Configuration"""

# Django
from django.apps import AppConfig

# AA Assets
# AA Example App
from assets import __version__


class AssetsConfig(AppConfig):
    """App Config"""

    default_auto_field = "django.db.models.AutoField"
    author = "Geuthur"
    name = "assets"
    label = "assets"
    verbose_name = f"Assets v{__version__}"
