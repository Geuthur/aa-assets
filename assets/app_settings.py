"""
App Settings
"""

# Django
from django.conf import settings

# Caching Key for Caching System
STORAGE_BASE_KEY = "assets_storage_"

# Set Naming on Auth Hook
ASSETS_APP_NAME = getattr(settings, "ASSETS_APP_NAME", "Assets")

# Global timeout for tasks in seconds to reduce task accumulation during outages.
ASSETS_TASKS_TIME_LIMIT = getattr(settings, "ASSETS_TASKS_TIME_LIMIT", 600)

# Hours after a existing location (e.g. structure) becomes stale and gets updated
# e.g. for name changes of structures
ASSETS_LOCATION_STALE_HOURS = getattr(settings, "ASSETS_LOCATION_STALE_HOURS", 168)

# Set the Stale Status for Assets Updates in Minutes
ASSETS_UPDATE_PERIOD = getattr(settings, "ASSETS_UPDATE_PERIOD", 60)  # in minutes

# Minutes after which a section counts as stale and is fetched from ESI again.
# One entry per update section (see `models/helpers/update_manager.py`).
ASSETS_STALE_TYPES = getattr(
    settings,
    "ASSETS_STALE_TYPES",
    {
        "assets": ASSETS_UPDATE_PERIOD,
    },
)

# Assets Cache System
ASSETS_CACHE_KEY = getattr(settings, "ASSETS_CACHE_KEY", "ASSETS")

ASSETS_BULK_BATCH_SIZE = getattr(settings, "ASSETS_BULK_BATCH_SIZE", 500)
