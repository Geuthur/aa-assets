"""Tests for the settings endpoints of the API."""

# Standard Library
import json
from http import HTTPStatus

# Django
from django.urls import reverse

# AA Assets
from assets.models import UserSettings
from assets.tests import AuthTestCase


class TestUserSettingsApi(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url = f"{reverse('assets:index')}api/settings/"

    def _put(self, payload: dict):
        return self.client.put(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_get_settings_should_return_defaults_and_create_settings(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.get(self.url)

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"disable_notifications": False})
        self.assertTrue(UserSettings.objects.filter(user=self.user).exists())

    def test_get_settings_should_return_stored_settings(self):
        # Test Data
        UserSettings.objects.create(user=self.user, disable_notifications=True)
        self.client.force_login(self.user)

        # Test Action
        response = self.client.get(self.url)

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"disable_notifications": True})

    def test_update_settings_should_save_settings(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self._put({"disable_notifications": True})

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"disable_notifications": True})
        self.assertTrue(UserSettings.objects.get(user=self.user).disable_notifications)

    def test_update_settings_should_only_change_own_settings(self):
        # Test Data
        UserSettings.objects.create(user=self.superuser, disable_notifications=False)
        self.client.force_login(self.user)

        # Test Action
        self._put({"disable_notifications": True})

        # Expected Result
        self.assertFalse(
            UserSettings.objects.get(user=self.superuser).disable_notifications
        )

    def test_update_settings_should_return_422_without_field(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self._put({})

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertFalse(UserSettings.objects.filter(user=self.user).exists())
