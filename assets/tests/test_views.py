# Standard Library
from http import HTTPStatus
from unittest.mock import patch

# Django
from django.core.cache import cache
from django.urls import reverse

# AA Assets
from assets import views
from assets.helpers.orders import set_apr_cooldown
from assets.models import Request, RequestAssets
from assets.tests import AuthTestCase
from assets.tests.testdata.factory import UserMainFactory
from assets.tests.testdata.orders import (
    LOCATION_ID,
    create_asset,
    create_order,
    create_owner,
)


class TestViews(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_index_view(self):
        # Test Data
        request = self.factory.get(reverse("assets:index"))
        request.user = self.superuser

        # Test Action
        response = views.index(request)

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)


class TestViewsRequireBasicAccess(AuthTestCase):
    """Views that manage things need `basic_access` in addition to their own permission."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.only_manage_corporation = UserMainFactory(
            permissions__=["assets.manage_corporation"]
        )
        cls.only_manage_requests = UserMainFactory(
            permissions__=["assets.manage_requests"]
        )
        cls.basic_only = UserMainFactory(permissions__=["assets.basic_access"])
        cls.basic_manage_corporation = UserMainFactory(
            permissions__=["assets.basic_access", "assets.manage_corporation"]
        )
        cls.basic_manage_requests = UserMainFactory(
            permissions__=["assets.basic_access", "assets.manage_requests"]
        )

    def _assert_login_redirect(self, response):
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn("/account/login/", response["Location"])

    def _assert_reaches_token_decorator(self, response):
        # Without a token ESI shows its token page (200) or starts the SSO (302)
        self.assertIn(response.status_code, (HTTPStatus.OK, HTTPStatus.FOUND))
        if response.status_code == HTTPStatus.FOUND:
            self.assertNotIn("/account/login/", response["Location"])

    def test_add_corp_should_redirect_to_login_without_basic_access(self):
        # Test Data
        self.client.force_login(self.only_manage_corporation)

        # Test Action
        response = self.client.get(reverse("assets:add_corp"))

        # Expected Result: the permission check comes before the SSO detour
        self._assert_login_redirect(response)

    def test_add_corp_should_redirect_to_login_without_manage_corporation(self):
        # Test Data
        self.client.force_login(self.basic_only)

        # Test Action
        response = self.client.get(reverse("assets:add_corp"))

        # Expected Result
        self._assert_login_redirect(response)

    def test_add_corp_should_start_sso_with_both_permissions(self):
        # Test Data
        self.client.force_login(self.basic_manage_corporation)

        # Test Action
        response = self.client.get(reverse("assets:add_corp"))

        # Expected Result: the token decorator takes over
        self._assert_reaches_token_decorator(response)

    def test_add_char_should_redirect_to_login_without_basic_access(self):
        # Test Data
        user = UserMainFactory(permissions__=["assets.manage_corporation"])
        self.client.force_login(user)

        # Test Action
        response = self.client.get(reverse("assets:add_char"))

        # Expected Result: the permission check comes before the SSO detour
        self._assert_login_redirect(response)

    def test_add_char_should_start_sso_with_basic_access(self):
        # Test Data
        self.client.force_login(self.basic_only)

        # Test Action
        response = self.client.get(reverse("assets:add_char"))

        # Expected Result
        self._assert_reaches_token_decorator(response)

    def test_mark_request_views_should_redirect_to_login_without_basic_access(self):
        # Test Data
        self.client.force_login(self.only_manage_requests)

        for name in ("assets:request_completed", "assets:request_open"):
            with self.subTest(view=name):
                # Test Action
                response = self.client.post(reverse(name, kwargs={"request_id": 1}))

                # Expected Result
                self._assert_login_redirect(response)

    def test_mark_request_views_should_redirect_to_login_without_manage_requests(self):
        # Test Data
        self.client.force_login(self.basic_only)

        for name in ("assets:request_completed", "assets:request_open"):
            with self.subTest(view=name):
                # Test Action
                response = self.client.post(reverse(name, kwargs={"request_id": 1}))

                # Expected Result
                self._assert_login_redirect(response)

    def test_mark_request_views_should_run_with_both_permissions(self):
        # Test Data
        self.client.force_login(self.basic_manage_requests)

        for name in ("assets:request_completed", "assets:request_open"):
            with self.subTest(view=name):
                # Test Action
                response = self.client.post(reverse(name, kwargs={"request_id": 1}))

                # Expected Result: the view runs and finds no such request
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


@patch("assets.models.request.send_user_notification")
class TestOrderViews(AuthTestCase):
    """The order views answer as before after moving their logic to helpers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = create_owner(cls.user)
        cls.manager = UserMainFactory(
            permissions__=["assets.basic_access", "assets.manage_requests"]
        )

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.asset = create_asset(self.owner, quantity=10)
        self.url = reverse(
            "assets:create_order",
            kwargs={"location_id": LOCATION_ID, "location_flag": "all"},
        )

    def test_create_order_should_create_single_order(self, send):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.post(
            self.url, data={"amount": 3, "asset_pk": self.asset.pk}
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(), {"success": True, "message": "Order created successfully."}
        )
        self.assertEqual(
            RequestAssets.objects.get(request__requesting_user=self.user).quantity, 3
        )

    def test_create_order_should_return_403_when_single_amount_exceeds(self, send):
        # Test Data
        create_order(self.manager, self.asset, quantity=9)
        self.client.force_login(self.user)

        # Test Action
        response = self.client.post(
            self.url, data={"amount": 2, "asset_pk": self.asset.pk}
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "success": False,
                "message": "Requested amount exceeds available quantity.",
            },
        )
        self.assertFalse(Request.objects.filter(requesting_user=self.user).exists())

    def test_create_order_should_create_multi_order(self, send):
        # Test Data
        self.client.force_login(self.user)

        # Test Action
        response = self.client.post(self.url, data={f"item_id_{self.asset.pk}": 4})

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            RequestAssets.objects.get(request__requesting_user=self.user).quantity, 4
        )

    def test_create_order_should_return_409_when_multi_amount_exceeds(self, send):
        # Test Data
        create_order(self.manager, self.asset, quantity=9)
        self.client.force_login(self.user)

        # Test Action
        response = self.client.post(self.url, data={f"item_id_{self.asset.pk}": 4})

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        self.assertFalse(response.json()["success"])
        self.assertIn(self.asset.eve_type.name, response.json()["message"])

    def test_create_order_should_return_404_for_single_asset_of_other_user(self, send):
        # Test Data
        other_asset = create_asset(
            create_owner(UserMainFactory()), quantity=10, item_id=2
        )
        self.client.force_login(self.user)

        # Test Action
        response = self.client.post(
            self.url, data={"amount": 1, "asset_pk": other_asset.pk}
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertFalse(Request.objects.filter(requesting_user=self.user).exists())

    def test_create_order_should_return_404_for_multi_asset_of_other_user(self, send):
        # Test Data
        other_asset = create_asset(
            create_owner(UserMainFactory()), quantity=10, item_id=2
        )
        self.client.force_login(self.user)

        # Test Action
        response = self.client.post(self.url, data={f"item_id_{other_asset.pk}": 1})

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertFalse(Request.objects.filter(requesting_user=self.user).exists())

    def test_mark_request_canceled_should_cancel_own_order(self, send):
        # Test Data
        order = create_order(self.user, self.asset)
        self.client.force_login(self.user)

        # Test Action
        response = self.client.post(
            reverse("assets:request_canceled", kwargs={"request_id": order.pk})
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response.json()["success"])
        order.refresh_from_db()
        self.assertEqual(order.status, Request.STATUS_CANCELLED)

    def test_mark_request_canceled_should_return_400_for_other_user(self, send):
        # Test Data
        order = create_order(self.manager, self.asset)
        self.client.force_login(self.user)

        # Test Action
        response = self.client.post(
            reverse("assets:request_canceled", kwargs={"request_id": order.pk})
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertFalse(response.json()["success"])
        self.assertIn("has failed", response.json()["message"])

    def test_mark_request_views_should_return_403_on_cooldown(self, send):
        # Test Data
        order = create_order(self.user, self.asset)
        self.client.force_login(self.manager)
        cases = (
            ("assets:request_canceled", "canceled", True),
            ("assets:request_completed", "completed", False),
            ("assets:request_open", "open", True),
        )

        for name, mode, success in cases:
            with self.subTest(view=name):
                set_apr_cooldown(self.manager, order.pk, mode)

                # Test Action
                response = self.client.post(
                    reverse(name, kwargs={"request_id": order.pk})
                )

                # Expected Result
                self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
                self.assertEqual(response.json()["success"], success)

    def test_mark_request_completed_and_open_should_change_status(self, send):
        # Test Data
        order = create_order(self.user, self.asset)
        self.client.force_login(self.manager)

        # Test Action
        completed = self.client.post(
            reverse("assets:request_completed", kwargs={"request_id": order.pk})
        )
        reopened = self.client.post(
            reverse("assets:request_open", kwargs={"request_id": order.pk})
        )

        # Expected Result
        self.assertEqual(completed.status_code, HTTPStatus.OK)
        self.assertEqual(reopened.status_code, HTTPStatus.OK)
        order.refresh_from_db()
        self.assertEqual(order.status, Request.STATUS_OPEN)
        self.assertIsNone(order.closed_at)


@patch("assets.helpers.admin.update_all_assets")
@patch("assets.helpers.admin.clear_all_etags")
class TestAdminView(AuthTestCase):
    def test_admin_should_queue_selected_tasks(self, clear_etags, update_assets):
        # Test Data
        self.client.force_login(self.superuser)

        # Test Action
        response = self.client.post(
            reverse("assets:admin"),
            data={"force_refresh": "on", "run_update_all_assets": "on"},
        )

        # Expected Result
        self.assertEqual(response.status_code, HTTPStatus.OK)
        update_assets.apply_async.assert_called_once_with(
            kwargs={"force_refresh": True}, priority=7
        )
        clear_etags.apply_async.assert_not_called()
