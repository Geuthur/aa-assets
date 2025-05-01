"""
App Settings
"""

import sys

# Django
from app_utils.app_settings import clean_setting

# Set Test Mode True or False
IS_TESTING = sys.argv[1:2] == ["test"]

# Caching Key for Caching System
STORAGE_BASE_KEY = "assets_storage_"

# Set Naming on Auth Hook
ASSETS_APP_NAME = clean_setting("ASSETS_APP_NAME", "Assets")

# zKillboard - https://zkillboard.com/
EVE_BASE_URL = "https://esi.evetech.net/"
EVE_API_URL = "https://esi.evetech.net/latest/"
EVE_BASE_URL_REGEX = r"^http[s]?:\/\/esi.evetech\.net\/"

# fuzzwork
FUZZ_BASE_URL = "https://www.fuzzwork.co.uk/"
FUZZ_API_URL = "https://www.fuzzwork.co.uk/api/"
FUZZ_BASE_URL_REGEX = r"^http[s]?:\/\/(www\.)?fuzzwork\.co\.uk\/"

# If True you need to set up the Logger
ASSETS_LOGGER_USE = clean_setting("ASSETS_LOGGER_USE", False)

# Hours after a existing location (e.g. structure) becomes stale and gets updated
# e.g. for name changes of structures
ASSETS_LOCATION_STALE_HOURS = clean_setting("ASSETS_LOCATION_STALE_HOURS", 168)

# Set the Stale Status for Ledger Updates in Minutes
ASSETS_UPDATE_PERIOD = clean_setting("ASSETS_UPDATE_PERIOD", 60)  # in minutes
