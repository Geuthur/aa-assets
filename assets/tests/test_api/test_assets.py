"""Tests for the asset and location endpoints of the API."""

# Standard Library
from http import HTTPStatus

# AA Assets
from assets import __app_name__
from assets.tests import AuthTestCase
from assets.tests.testdata.factory import UserMainFactory
from assets.tests.testdata.orders import (
    LOCATION_ID,
    create_asset,
    create_owner,
)

API = f"/{__app_name__}/api"
OTHER_LOCATION_ID = 60008494


class TestAssetsApi(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.asset = create_asset(create_owner(cls.user), quantity=7)
        cls.other_user = UserMainFactory()
        other_owner = create_owner(cls.other_user)
        cls.other_asset = create_asset(other_owner, item_id=2)
        create_asset(other_owner, item_id=3, location_id=OTHER_LOCATION_ID)

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

    def test_get_assets_should_return_total_price(self):
        # Test Data
        self.asset.price = 2.5
        self.asset.save()

        # Test Action
        response = self.client.get(f"{API}/location/{LOCATION_ID}/flag/all/")

        # Expected Result
        self.assertEqual(response.json()["assets"][0]["price"], 17.5)

    def test_get_assets_should_return_null_price_without_price(self):
        # Test Data
        self.asset.price = None
        self.asset.save()

        # Test Action
        response = self.client.get(f"{API}/location/{LOCATION_ID}/flag/all/")

        # Expected Result
        self.assertIsNone(response.json()["assets"][0]["price"])

    def test_get_locations_should_return_location(self):
        # Test Action
        response = self.client.get(f"{API}/location/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        row = response.json()[0]
        self.assertEqual(row["location_id"], LOCATION_ID)
        self.assertNotIn("view", row)

    def test_get_assets_should_return_only_visible_assets(self):
        # Test Action
        response = self.client.get(f"{API}/location/{LOCATION_ID}/flag/all/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        asset_pks = [row["asset_pk"] for row in response.json()["assets"]]
        self.assertEqual(asset_pks, [self.asset.pk])

    def test_get_assets_should_return_forbidden_without_visible_asset(self):
        # Test Data
        user = UserMainFactory()
        self.client.force_login(user)

        # Test Action
        response = self.client.get(f"{API}/location/{LOCATION_ID}/flag/all/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(response.json(), {"error": "Permission Denied"})

    def test_get_locations_should_return_only_visible_locations(self):
        # Test Action
        response = self.client.get(f"{API}/location/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        location_ids = [row["location_id"] for row in response.json()]
        self.assertEqual(location_ids, [LOCATION_ID])

    def test_get_locations_should_return_forbidden_without_visible_owner(self):
        # Test Data
        user = UserMainFactory()
        self.client.force_login(user)

        # Test Action
        response = self.client.get(f"{API}/location/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(response.json(), {"error": "Permission Denied"})
