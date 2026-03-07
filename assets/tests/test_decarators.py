# Standard Library
from unittest.mock import patch

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

# AA Assets
from assets import __title__
from assets.decorators import (
    log_timing,
)
from assets.providers import AppLogger
from assets.tests import NoSocketsTestCase

logger = AppLogger(get_extension_logger(__name__), __title__)

DECORATOR_PATH = "assets.decorators."


@patch(DECORATOR_PATH + "ESI_STATUS_ROUTE_RATE_LIMIT", new=1)
class TestDecorators(NoSocketsTestCase):

    def test_log_timing(self):
        # given
        logger = AppLogger(get_extension_logger(__name__), __title__)

        @log_timing(logger)
        def trigger_log_timing():
            return "Log Timing"

        # when
        result = trigger_log_timing()
        # then
        self.assertEqual(result, "Log Timing")
