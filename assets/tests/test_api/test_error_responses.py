"""Tests the error bodies of the API: every error is `{"error": "<text>"}`."""

# Standard Library
from http import HTTPStatus

# AA Assets
from assets import __app_name__
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
