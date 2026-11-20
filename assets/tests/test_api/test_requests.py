"""Tests for the order endpoints of the API."""

# Standard Library
import json
from http import HTTPStatus
from unittest.mock import patch

# Django
from django.core.cache import cache

# AA Assets
from assets import __app_name__
from assets.helpers.orders import build_apr_cooldown_cache_tag, set_apr_cooldown
from assets.models import Request, RequestAssets
from assets.tests import AuthTestCase
from assets.tests.testdata.factory import UserMainFactory
from assets.tests.testdata.orders import create_asset, create_order, create_owner

API = f"/{__app_name__}/api"


@patch("assets.models.request.send_user_notification")
class TestPostOrder(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = create_owner(cls.user)
        cls.other_user = UserMainFactory()
        cls.other_owner = create_owner(cls.other_user)

    def setUp(self):
        self.client.force_login(self.user)
        self.asset = create_asset(self.owner, quantity=10, item_id=1)
        self.asset_two = create_asset(self.owner, quantity=5, item_id=2)

    def _post(self, items):
        return self.client.post(
            f"{API}/orders/",
            data=json.dumps({"items": items}),
            content_type="application/json",
        )

    def test_post_order_should_create_order_with_all_items(self, send):
        # Test Action
        response = self._post(
            [
                {"asset_pk": self.asset.pk, "amount": 3},
                {"asset_pk": self.asset_two.pk, "amount": 2},
            ]
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {"success": True, "message": "Order created successfully."},
        )
        order = Request.objects.get(requesting_user=self.user)
        self.assertEqual(order.status, Request.STATUS_OPEN)
        quantities = dict(
            RequestAssets.objects.filter(request=order).values_list(
                "asset_pk", "quantity"
            )
        )
        self.assertEqual(quantities, {self.asset.pk: 3, self.asset_two.pk: 2})

    def test_post_order_should_sum_the_same_asset(self, send):
        # Test Action
        response = self._post(
            [
                {"asset_pk": self.asset.pk, "amount": 3},
                {"asset_pk": self.asset.pk, "amount": 4},
            ]
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        item = RequestAssets.objects.get(request__requesting_user=self.user)
        self.assertEqual(item.quantity, 7)

    def test_post_order_should_return_404_for_unknown_asset(self, send):
        # Test Action
        response = self._post([{"asset_pk": 999999, "amount": 1}])

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(response.json(), {"error": "The asset does not exist."})
        self.assertFalse(Request.objects.exists())

    def test_post_order_should_return_404_for_asset_of_other_user(self, send):
        # Test Data
        other_asset = create_asset(self.other_owner, item_id=3)

        # Test Action
        response = self._post(
            [
                {"asset_pk": self.asset.pk, "amount": 1},
                {"asset_pk": other_asset.pk, "amount": 1},
            ]
        )

        # Expected Result: nothing is created
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertFalse(Request.objects.exists())

    def test_post_order_should_return_409_when_no_item_is_available(self, send):
        # Test Data
        create_order(self.other_user, self.asset, quantity=9)

        # Test Action
        response = self._post([{"asset_pk": self.asset.pk, "amount": 2}])

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        self.assertEqual(
            response.json(),
            {"error": "Requested amount exceeds available quantity."},
        )
        self.assertFalse(Request.objects.filter(requesting_user=self.user).exists())

    def test_post_order_should_return_409_above_stock_without_open_orders(self, send):
        # Test Action
        response = self._post([{"asset_pk": self.asset.pk, "amount": 11}])

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        self.assertFalse(Request.objects.exists())

    def test_post_order_should_create_partial_order_and_return_409(self, send):
        # Test Data
        create_order(self.other_user, self.asset, quantity=9)

        # Test Action
        response = self._post(
            [
                {"asset_pk": self.asset.pk, "amount": 2},
                {"asset_pk": self.asset_two.pk, "amount": 1},
            ]
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        self.assertIn(self.asset.eve_type.name, response.json()["error"])
        item = RequestAssets.objects.get(request__requesting_user=self.user)
        self.assertEqual(item.asset_pk, self.asset_two.pk)

    def test_post_order_should_reject_amount_below_one(self, send):
        # Test Action
        response = self._post([{"asset_pk": self.asset.pk, "amount": 0}])

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertFalse(Request.objects.exists())

    def test_post_order_should_reject_empty_items(self, send):
        # Test Action
        response = self._post([])

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)


@patch("assets.models.request.send_user_notification")
class TestRequestStatusChange(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = UserMainFactory(
            permissions__=["assets.basic_access", "assets.manage_requests"]
        )
        cls.other_user = UserMainFactory()
        cls.asset = create_asset(create_owner(cls.user))

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.order = create_order(self.user, self.asset)

    def _post(self, action, request_id=None):
        return self.client.post(
            f"{API}/requests/{request_id or self.order.pk}/{action}/"
        )

    def test_cancel_should_close_own_order(self, send):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self._post("cancel")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response.json()["success"])
        self.assertIn("closed as cancelled", response.json()["message"])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Request.STATUS_CANCELLED)
        self.assertIsNotNone(self.order.closed_at)
        self.assertTrue(
            cache.get(
                build_apr_cooldown_cache_tag(self.user, self.order.pk, "canceled")
            )
        )

    def test_cancel_should_return_403_for_order_of_other_user(self, send):
        # Test Data
        self.client.force_login(self.other_user)

        # Test Action
        response = self._post("cancel")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertIn("has failed", response.json()["error"])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Request.STATUS_OPEN)
        send.delay.assert_not_called()

    def test_cancel_should_return_404_for_unknown_order(self, send):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self._post("cancel", request_id=999999)

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(response.json(), {"error": "Request does not exist"})

    def test_cancel_should_return_429_on_cooldown(self, send):
        # Test Data
        set_apr_cooldown(self.user, self.order.pk, "canceled")
        self.client.force_login(self.user)

        # Test Action
        response = self._post("cancel")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.TOO_MANY_REQUESTS)
        self.assertEqual(
            response.json(),
            {
                "error": "You are on cooldown. Please wait 60 seconds before trying again."
            },
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Request.STATUS_OPEN)

    def test_complete_should_close_order_and_set_approver(self, send):
        # Test Data
        self.client.force_login(self.manager)

        # Test Action
        response = self._post("complete")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("closed as completed", response.json()["message"])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Request.STATUS_COMPLETED)
        self.assertEqual(self.order.approver_user, self.manager)
        send.delay.assert_called_once()
        self.assertEqual(send.delay.call_args.kwargs["user_id"], self.user.pk)

    def test_complete_and_reopen_should_return_403_without_manage_requests(self, send):
        # Test Data
        self.client.force_login(self.user)

        for action in ("complete", "reopen"):
            with self.subTest(action=action):
                # Test Action
                response = self._post(action)

                # Expected Result
                self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
                self.assertEqual(response.json(), {"error": "Permission Denied"})

    def test_status_change_should_return_409_from_wrong_status(self, send):
        # Test Data
        self.client.force_login(self.manager)
        cases = (
            ("cancel", Request.STATUS_COMPLETED),
            ("complete", Request.STATUS_CANCELLED),
            ("reopen", Request.STATUS_OPEN),
            ("reopen", Request.STATUS_COMPLETED),
        )

        for action, status in cases:
            with self.subTest(action=action, status=status):
                self.order.status = status
                self.order.save()

                # Test Action
                response = self._post(action)

                # Expected Result
                self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
                self.order.refresh_from_db()
                self.assertEqual(self.order.status, status)
        send.delay.assert_not_called()

    def test_reopen_should_open_cancelled_order(self, send):
        # Test Data
        self.order.status = Request.STATUS_CANCELLED
        self.order.save()
        self.client.force_login(self.manager)

        # Test Action
        response = self._post("reopen")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("has been reopened", response.json()["message"])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Request.STATUS_OPEN)
        self.assertIsNone(self.order.closed_at)
        self.assertEqual(send.delay.call_args.kwargs["user_id"], self.user.pk)


class TestGetRequest(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_user = UserMainFactory()
        cls.asset = create_asset(create_owner(cls.user))
        cls.order = create_order(cls.user, cls.asset, quantity=4)

    def test_get_request_should_return_order_with_items(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.get(f"{API}/requests/{self.order.pk}/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["id"], self.order.pk)
        self.assertEqual(data["status"], Request.STATUS_OPEN)
        self.assertEqual(data["status_label"], "Open")
        self.assertEqual(data["requestor"], self.user.username)
        self.assertIsNone(data["approver"])
        self.assertEqual(
            data["items"],
            [
                {
                    "type_id": self.asset.eve_type.id,
                    "name": self.asset.eve_type.name,
                    "quantity": 4,
                }
            ],
        )

    def test_get_request_should_return_403_for_order_of_other_user(self):
        # Test Data
        self.client.force_login(self.other_user)

        # Test Action
        response = self.client.get(f"{API}/requests/{self.order.pk}/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(response.json(), {"error": "Permission Denied"})

    def test_get_request_should_return_404_for_unknown_order(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.get(f"{API}/requests/999999/")

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class TestRequestListPermissions(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = UserMainFactory(
            permissions__=["assets.basic_access", "assets.manage_requests"]
        )
        asset = create_asset(create_owner(cls.user))
        cls.open_order = create_order(cls.user, asset)
        cls.cancelled_order = create_order(
            cls.user, asset, status=Request.STATUS_CANCELLED
        )

    def _flags(self, url):
        rows = {row["id"]: row for row in self.client.get(url).json()}
        return {
            pk: (row["can_cancel"], row["can_complete"], row["can_reopen"])
            for pk, row in rows.items()
        }

    def test_requests_should_return_flags_for_requestor(self):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        flags = self._flags(f"{API}/requests/myrequests/")

        # Expected Result
        self.assertEqual(flags[self.open_order.pk], (True, False, False))
        self.assertEqual(flags[self.cancelled_order.pk], (False, False, False))

    def test_requests_should_return_flags_for_manager(self):
        # Test Data
        self.client.force_login(self.manager)

        # Test Action
        flags = self._flags(f"{API}/requests/")

        # Expected Result
        self.assertEqual(flags[self.open_order.pk], (True, True, False))
        self.assertEqual(flags[self.cancelled_order.pk], (False, False, True))
