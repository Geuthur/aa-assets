"""Tests for the ESI error handling of the tasks."""

# Standard Library
from http import HTTPStatus
from unittest.mock import patch

# Third Party
import pook
from aiopenapi3 import RequestError
from celery.exceptions import Retry

# Django
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

# Alliance Auth
from esi.exceptions import ESIErrorLimitException, HTTPServerError

# AA Assets
from assets import tasks
from assets.errors import DownTimeError
from assets.models import Location, Owner
from assets.providers import DOWNTIME_TIMER
from assets.task_helpers.location_helpers import get_cache_key
from assets.tests import AuthTestCase
from assets.tests.testdata.esi_urls import (
    character_assets_url,
    clear_esi_limits,
    station_url,
    structure_url,
)
from assets.tests.testdata.factory import UserMainFactory

STATION_ID = 60003760
STRUCTURE_ID = 1_000_000_000_001
LOCATION_ID = 1_000_000_000_002
SERVER_ERRORS = [
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
]


class EsiTaskTestCase(AuthTestCase):
    """Owner of the main character and clean ESI limits for every test."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        esi_user = UserMainFactory()
        cls.character = esi_user.profile.main_character
        cls.owner = Owner.objects.create(character=cls.character.character_ownership)

    def setUp(self):
        super().setUp()
        clear_esi_limits()
        self.addCleanup(clear_esi_limits)

    def _assert_retried(self, mock_retry, exc_type, countdown_min: float):
        mock_retry.assert_called_once()
        kwargs = mock_retry.call_args.kwargs
        self.assertIsInstance(kwargs["exc"], exc_type)
        self.assertGreaterEqual(kwargs["countdown"], countdown_min)

    def _error_limit(self, url: str):
        pook.get(
            url,
            reply=420,
            response_json={"error": "Error limited"},
            response_headers={"X-RateLimit-Reset": "30"},
        )


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
@patch.object(tasks.update_assets_for_owner, "retry", side_effect=Retry)
class TestUpdateAssetsForOwner(EsiTaskTestCase):
    def test_should_retry_on_esi_server_errors(self, mock_retry):
        for status_code in SERVER_ERRORS:
            with self.subTest(status_code=status_code), pook.use():
                # Test Data
                mock_retry.reset_mock()
                pook.get(
                    character_assets_url(self.character.character_id),
                    reply=status_code,
                    response_json={"error": status_code.phrase},
                )

                # Test Action
                with self.assertRaises(Retry):
                    tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

                # Expected Result
                self._assert_retried(mock_retry, HTTPServerError, DOWNTIME_TIMER)

    @pook.on
    def test_should_retry_on_the_esi_error_limit(self, mock_retry):
        # Test Data
        self._error_limit(character_assets_url(self.character.character_id))

        # Test Action
        with self.assertRaises(Retry):
            tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        self._assert_retried(mock_retry, ESIErrorLimitException, 30)

    @pook.on
    @patch("esi.app_settings.ESI_SERVER_ERROR_MAX_RETRIES", 1)
    def test_should_retry_on_request_errors(self, mock_retry):
        # Test Data
        pook.get(character_assets_url(self.character.character_id)).error(
            ConnectionError("Connection reset")
        )

        # Test Action
        with self.assertRaises(Retry):
            tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        self._assert_retried(mock_retry, RequestError, DOWNTIME_TIMER)

    @pook.on
    def test_should_not_retry_on_esi_client_errors(self, mock_retry):
        # Test Data
        pook.get(
            character_assets_url(self.character.character_id),
            reply=HTTPStatus.NOT_FOUND,
            response_json={"error": "Not found"},
        )

        # Test Action
        tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        mock_retry.assert_not_called()

    @override_settings(DISABLE_DAILY_DOWNTIME_CHECK=False)
    @patch(tasks.__name__ + ".Owner.update_assets_esi", autospec=True)
    def test_should_retry_during_daily_downtime(self, mock_update, mock_retry):
        # Test Data
        with patch("assets.providers.timezone.now") as mock_now:
            mock_now.return_value = timezone.datetime.strptime("11:05", "%H:%M")

            # Test Action
            with self.assertRaises(Retry):
                tasks.update_assets_for_owner(self.owner.pk)

        # Expected Result
        self._assert_retried(mock_retry, DownTimeError, DOWNTIME_TIMER)
        mock_update.assert_not_called()


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
@patch.object(tasks.update_location, "retry", side_effect=Retry)
class TestUpdateLocation(EsiTaskTestCase):
    def test_should_retry_on_esi_server_errors(self, mock_retry):
        for status_code in SERVER_ERRORS:
            with self.subTest(status_code=status_code), pook.use():
                # Test Data
                mock_retry.reset_mock()
                pook.get(
                    station_url(STATION_ID),
                    reply=status_code,
                    response_json={"error": status_code.phrase},
                )

                # Test Action
                with self.assertRaises(Retry):
                    tasks.update_location(STATION_ID)

                # Expected Result
                self._assert_retried(mock_retry, HTTPServerError, DOWNTIME_TIMER)

    @pook.on
    def test_should_retry_on_the_esi_error_limit(self, mock_retry):
        # Test Data
        self._error_limit(station_url(STATION_ID))

        # Test Action
        with self.assertRaises(Retry):
            tasks.update_location(STATION_ID)

        # Expected Result
        self._assert_retried(mock_retry, ESIErrorLimitException, 30)


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
@patch.object(tasks.update_parent_location, "retry", side_effect=Retry)
class TestUpdateParentLocation(EsiTaskTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Location.objects.create(id=LOCATION_ID)

    def setUp(self):
        super().setUp()
        cache.delete(get_cache_key(STRUCTURE_ID))
        self.addCleanup(cache.delete, get_cache_key(STRUCTURE_ID))

    def _run(self):
        tasks.update_parent_location(
            LOCATION_ID,
            STRUCTURE_ID,
            self.character.character_id,
            35832,
            force_refresh=True,
        )

    def test_should_retry_on_esi_server_errors(self, mock_retry):
        for status_code in SERVER_ERRORS:
            with self.subTest(status_code=status_code), pook.use():
                # Test Data
                mock_retry.reset_mock()
                pook.get(
                    structure_url(STRUCTURE_ID),
                    reply=status_code,
                    response_json={"error": status_code.phrase},
                )

                # Test Action
                with self.assertRaises(Retry):
                    self._run()

                # Expected Result
                self._assert_retried(mock_retry, HTTPServerError, DOWNTIME_TIMER)

    @pook.on
    def test_should_retry_on_the_esi_error_limit(self, mock_retry):
        # Test Data
        self._error_limit(structure_url(STRUCTURE_ID))

        # Test Action
        with self.assertRaises(Retry):
            self._run()

        # Expected Result
        self._assert_retried(mock_retry, ESIErrorLimitException, 30)

    @pook.on
    def test_should_cache_forbidden_structures_without_retry(self, mock_retry):
        # Test Data
        pook.get(
            structure_url(STRUCTURE_ID),
            reply=HTTPStatus.FORBIDDEN,
            response_json={"error": "Forbidden"},
        )

        # Test Action
        self._run()

        # Expected Result
        mock_retry.assert_not_called()
        self.assertEqual(cache.get(get_cache_key(STRUCTURE_ID)), 1)
        self.assertIsNone(Location.objects.get(id=LOCATION_ID).parent)


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
@patch.object(tasks.update_all_parent_locations, "retry", side_effect=Retry)
class TestUpdateAllParentLocations(EsiTaskTestCase):
    def test_should_retry_on_esi_server_errors(self, mock_retry):
        for status_code in SERVER_ERRORS:
            with self.subTest(status_code=status_code), pook.use():
                # Test Data
                mock_retry.reset_mock()
                pook.get(
                    character_assets_url(self.character.character_id),
                    reply=status_code,
                    response_json={"error": status_code.phrase},
                )

                # Test Action
                with self.assertRaises(Retry):
                    tasks.update_all_parent_locations(force_refresh=True)

                # Expected Result
                self._assert_retried(mock_retry, HTTPServerError, DOWNTIME_TIMER)

    @pook.on
    def test_should_retry_on_the_esi_error_limit(self, mock_retry):
        # Test Data
        self._error_limit(character_assets_url(self.character.character_id))

        # Test Action
        with self.assertRaises(Retry):
            tasks.update_all_parent_locations(force_refresh=True)

        # Expected Result
        self._assert_retried(mock_retry, ESIErrorLimitException, 30)
