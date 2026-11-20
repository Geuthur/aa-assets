"""Tests for the asset and location endpoints of the API."""

# Standard Library
from http import HTTPStatus

# AA Assets
from assets import __app_name__
from assets.tests import AuthTestCase
from assets.tests.testdata.orders import (
    LOCATION_ID,
    create_asset,
    create_owner,
)

API = f"/{__app_name__}/api"


class TestAssetsApi(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.asset = create_asset(create_owner(cls.user), quantity=7)

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_assets_should_return_type_id(self):
        # Test Action
        response = self.client.get(f"{API}/location/{LOCATION_ID}/flag/all/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["location_flag"], "all")
        row = data["assets"][0]
        self.assertEqual(row["asset_pk"], self.asset.pk)
        self.assertEqual(row["type_id"], self.asset.eve_type.id)
        self.assertEqual(row["name"], self.asset.eve_type.name)
        self.assertEqual(row["quantity"], 7)

    def test_get_locations_should_return_location(self):
        # Test Action
        response = self.client.get(f"{API}/location/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        row = response.json()[0]
        self.assertEqual(row["location_id"], LOCATION_ID)
        self.assertIn("View Assets", row["view"])
