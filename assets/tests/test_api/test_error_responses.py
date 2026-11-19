"""Tests the error bodies of the API: every error is `{"error": "<text>"}`."""

# Standard Library
from http import HTTPStatus
from unittest.mock import patch

# AA Assets
from assets import __app_name__
from assets.managers import GeneralManager
from assets.models import Request
from assets.tests import AuthTestCase

API = f"/{__app_name__}/api"


class TestApiErrorResponses(AuthTestCase):
    """The endpoints answer their own 403 with an `error` body."""

    def setUp(self):
        self.client.force_login(self.user)

    def _assert_denied(self, response, text):
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(response.json(), {"error": text})

    def test_get_assets_should_return_error_body_without_visible_assets(self):
        # Test Action
        response = self.client.get(f"{API}/location/1/flag/all/")

        # Expected Result
        self._assert_denied(response, "Permission Denied")

    def test_get_locations_should_return_error_body_without_visible_owner(self):
        # Test Action
        response = self.client.get(f"{API}/location/")

        # Expected Result
        self._assert_denied(response, "Permission Denied")

    def test_get_requests_should_return_error_body_when_nothing_is_visible(self):
        # Test Data
        with patch.object(Request.objects, "visible_to", return_value=None):
            # Test Action
            response = self.client.get(f"{API}/requests/")

        # Expected Result
        self._assert_denied(response, "Permission Denied")

    def test_get_my_requests_should_return_error_body_when_nothing_is_visible(self):
        # Test Data
        with patch.object(Request.objects, "visible_to", return_value=None):
            # Test Action
            response = self.client.get(f"{API}/requests/myrequests/")

        # Expected Result
        self._assert_denied(response, "Permission Denied")

    def test_get_requests_statistics_should_return_error_body_without_access(self):
        # Test Data: the first call is the decorator, the second the endpoint
        with patch.object(
            GeneralManager, "has_basic_access", side_effect=[True, False]
        ):
            # Test Action
            response = self.client.get(f"{API}/requests/statistics/")

        # Expected Result
        self._assert_denied(response, "Permission Denied")

    def test_get_request_order_should_return_error_body_without_access(self):
        # Test Data: the first call is the decorator, the second the endpoint
        with patch.object(
            GeneralManager, "has_basic_access", side_effect=[True, False]
        ):
            # Test Action
            response = self.client.get(f"{API}/requests/order/1/")

        # Expected Result
        self._assert_denied(response, "Permission Denied")

    def test_get_request_order_should_return_error_body_for_unknown_request(self):
        # Test Action
        response = self.client.get(f"{API}/requests/order/999999/")

        # Expected Result: the status code stays 403
        self._assert_denied(response, "Request does not exist")
