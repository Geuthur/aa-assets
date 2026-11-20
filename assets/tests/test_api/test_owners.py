"""Tests for the owner status endpoints of the API."""

# Standard Library
from http import HTTPStatus

# AA Assets
from assets import __app_name__
from assets.models.helpers.update_manager import OwnerUpdateSection, UpdateStatus
from assets.tests import AuthTestCase
from assets.tests.testdata.factory import UserMainFactory
from assets.tests.testdata.orders import create_owner
from assets.tests.testdata.owner import OwnerUpdateStatusFactory

API = f"/{__app_name__}/api"


class TestOwnersApi(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = create_owner(cls.user)
        cls.status = OwnerUpdateStatusFactory(
            owner=cls.owner, section=OwnerUpdateSection.ASSETS
        )
        cls.other_owner = create_owner(UserMainFactory())

    def test_list_owners_should_return_visible_owners_with_status(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.get(f"{API}/owners/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual([row["id"] for row in data], [self.owner.pk])
        row = data[0]
        self.assertEqual(row["name"], self.owner.name)
        self.assertEqual(row["owner_type"], "character")
        self.assertEqual(
            row["character_id"],
            self.user.profile.main_character.character_id,
        )
        self.assertIsNone(row["corporation_id"])
        self.assertTrue(row["active"])
        self.assertEqual(row["update_status"], UpdateStatus.OK.value)
        self.assertIsNotNone(row["last_update"])

    def test_list_owners_should_return_all_owners_for_superuser(self):
        # Test Data
        self.client.force_login(self.superuser)

        # Test Action
        response = self.client.get(f"{API}/owners/")

        # Expected Result
        self.assertEqual(
            {row["id"] for row in response.json()},
            {self.owner.pk, self.other_owner.pk},
        )

    def test_get_owner_should_return_sections(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.get(f"{API}/owners/{self.owner.pk}/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        sections = response.json()["sections"]
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["section"], "assets")
        self.assertEqual(sections[0]["section_label"], "Assets")
        self.assertTrue(sections[0]["is_success"])

    def test_get_owner_should_return_403_for_owner_of_other_user(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.get(f"{API}/owners/{self.other_owner.pk}/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(response.json(), {"error": "Permission Denied"})

    def test_get_owner_should_return_404_for_unknown_owner(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.get(f"{API}/owners/999999/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(response.json(), {"error": "Owner not found"})
