# Standard Library
from http import HTTPStatus

# Django
from django.urls import reverse

# AA Assets
from assets import views
from assets.tests import AuthTestCase
from assets.tests.testdata.factory import UserMainFactory


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
