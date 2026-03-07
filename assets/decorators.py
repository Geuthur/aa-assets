"""
Decorators
"""

# Standard Library
import time

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

# AA Assets
from assets import __title__
from assets.providers import AppLogger

logger = AppLogger(get_extension_logger(__name__), __title__)

ESI_STATUS_ROUTE_RATE_LIMIT = 5
ESI_STATUS_KEY = "esi-is-available-status"


def log_timing(logs):
    """
    Ein Dekorator, der die Ausführungszeit einer Funktion misst und in die Logdatei schreibt.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            logs.debug(
                "TIME: %s run for %s seconds with args: %s",
                end_time - start_time,
                func.__name__,
                args,
            )
            return result

        return wrapper

    return decorator
