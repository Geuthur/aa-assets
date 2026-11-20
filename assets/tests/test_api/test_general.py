"""Tests for the general endpoints of the API."""

# Standard Library
import json
from http import HTTPStatus
from unittest.mock import patch

# Django
from django.urls import reverse

# AA Assets
from assets.models import UserSettings
from assets.tests import AuthTestCase
from assets.tests.testdata.factory import UserMainFactory
from assets.tests.testdata.orders import create_asset, create_order, create_owner


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


class TestMenuApi(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url = f"{reverse('assets:index')}api/menu/"
        cls.manager = UserMainFactory(
            permissions__=[
                "assets.basic_access",
                "assets.manage_requests",
                "assets.manage_corporation",
            ]
        )

    def _names(self, links):
        return [link["name"] for link in links]

    def test_get_menu_should_return_basic_links(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.get(self.url)

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(
            self._names(data["left_links"]), ["Locations", "My Requests", "Settings"]
        )
        self.assertEqual(self._names(data["right_links"]), ["Add Character"])
        self.assertFalse(data["left_links"][1]["has_errors"])
        self.assertEqual(data["right_links"][0]["link"], reverse("assets:add_char"))
        self.assertTrue(data["right_links"][0]["is_external"])

    def test_get_menu_should_return_manager_links_with_badge(self):
        # Test Data
        create_order(self.user, create_asset(create_owner(self.user)))
        self.client.force_login(self.manager)

        # Test Action
        response = self.client.get(self.url)

        # Expected Result
        data = response.json()
        self.assertEqual(
            self._names(data["left_links"]), ["Locations", "Requests", "Settings"]
        )
        self.assertEqual(data["left_links"][1]["badge"], 1)
        self.assertTrue(data["left_links"][1]["has_errors"])
        self.assertEqual(
            self._names(data["right_links"]), ["Add Character", "Add Corporation"]
        )

    def test_get_menu_should_return_administration_for_superuser(self):
        # Test Data
        self.client.force_login(self.superuser)

        # Test Action
        response = self.client.get(self.url)

        # Expected Result
        self.assertIn("Administration", self._names(response.json()["right_links"]))


class TestUserApi(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url = f"{reverse('assets:index')}api/user/"

    def test_get_user_should_return_main_character_and_rights(self):
        # Test Data
        self.client.force_login(self.user)
        main = self.user.profile.main_character

        # Test Action
        response = self.client.get(self.url)

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["user_id"], self.user.pk)
        self.assertEqual(data["character_id"], main.character_id)
        self.assertEqual(data["corporation_name"], main.corporation_name)
        self.assertIn(str(main.character_id), data["portrait"])
        self.assertFalse(data["is_admin"])
        self.assertFalse(data["can_manage_requests"])
        self.assertFalse(data["can_add_corporation"])

    def test_get_user_should_return_admin_rights_for_superuser(self):
        # Test Data
        self.client.force_login(self.superuser)

        # Test Action
        response = self.client.get(self.url)

        # Expected Result
        data = response.json()
        self.assertTrue(data["is_admin"])
        self.assertTrue(data["can_manage_requests"])
        self.assertTrue(data["can_add_corporation"])


@patch("assets.helpers.admin.update_all_parent_locations")
@patch("assets.helpers.admin.update_all_locations")
@patch("assets.helpers.admin.update_all_assets")
@patch("assets.helpers.admin.clear_all_etags")
class TestAdminTasksApi(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url = f"{reverse('assets:index')}api/admin/tasks/"

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_admin_tasks_should_queue_selected_tasks(
        self, clear_etags, update_assets, update_locations, update_parents
    ):
        # Test Data
        self.client.force_login(self.superuser)

        # Test Action
        response = self._post(
            {"force_refresh": True, "update_assets": True, "clear_etags": True}
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "success": True,
                "message": "Queued Clear All ETags Queued Update All Assets",
            },
        )
        clear_etags.apply_async.assert_called_once_with(priority=1)
        update_assets.apply_async.assert_called_once_with(
            kwargs={"force_refresh": True}, priority=7
        )
        update_locations.apply_async.assert_not_called()
        update_parents.apply_async.assert_not_called()

    def test_admin_tasks_should_return_403_for_non_superuser(
        self, clear_etags, update_assets, update_locations, update_parents
    ):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self._post({"update_assets": True})

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(response.json(), {"error": "Permission Denied"})
        update_assets.apply_async.assert_not_called()
