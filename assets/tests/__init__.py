# Standard Library
import socket
from unittest.mock import Mock

# Django
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.handlers.wsgi import WSGIRequest
from django.test import RequestFactory, TestCase
from django.urls import reverse

# AA Assets
from assets.tests.testdata.factory import UserMainFactory
from assets.views import add_char, add_corp


class SocketAccessError(Exception):
    """Error raised when a test script accesses the network"""


class NoSocketsTestCase(TestCase):
    """Variation of Django's TestCase class that prevents any network use.

    Example:

        .. code-block:: python

            class TestMyStuff(BaseTestCase):
                def test_should_do_what_i_need(self): ...

    """

    @classmethod
    def setUpClass(cls):
        cls.socket_original = socket.socket
        socket.socket = cls.guard
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        socket.socket = cls.socket_original
        return super().tearDownClass()

    @staticmethod
    def guard(*args, **kwargs):
        raise SocketAccessError("Attempted to access network")


class AssetsTestCase(NoSocketsTestCase):
    """
    Preloaded Testcase class for Assets tests without Network access.

    Pre-Load:
        * Test users with a main character, created by `UserMainFactory`

    Available Request Factory:
        `self.factory`

    Available test users:
        * `user` User with standard Assets access.
            * 'assets.basic_access' Permission
        * `user2` Second user with standard Assets access.
            * 'assets.basic_access' Permission
        * `superuser` Superuser.
            * Access to whole Application
        * `manage_own_user` User with manage own corporation access.
            * 'assets.basic_access' Permission
            * 'assets.corporation_access' Permission
            * 'assets.manage_corporation' Permission
            * 'assets.manage_requests' Permission
        * `manage_user` User with manage corporations access.
            * 'assets.basic_access' Permission
            * 'assets.corporation_access' Permission
            * 'assets.admin_access' Permission
            * 'assets.manage_corporation' Permission
            * 'assets.manage_requests' Permission

    Example:
        .. code-block:: python

            class TestMyAssetsStuff(AssetsTestCase):
                def test_should_do_what_i_need(self):
                    user = self.user
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Request Factory
        cls.factory = RequestFactory()

        cls.user = UserMainFactory()
        cls.user2 = UserMainFactory()
        cls.superuser = UserMainFactory(permissions=[], is_superuser=True)
        cls.manage_own_user = UserMainFactory(
            permissions=[
                "assets.basic_access",
                "assets.corporation_access",
                "assets.manage_corporation",
                "assets.manage_requests",
            ]
        )
        cls.manage_user = UserMainFactory(
            permissions=[
                "assets.basic_access",
                "assets.corporation_access",
                "assets.admin_access",
                "assets.manage_corporation",
                "assets.manage_requests",
            ]
        )

    def _add_character(self, user, token):
        request = self.factory.get(reverse("assets:add_char"))
        request.user = user
        request.token = token
        middleware = SessionMiddleware(Mock())
        middleware.process_request(request)
        orig_view = add_char.__wrapped__.__wrapped__.__wrapped__
        return orig_view(request, token)

    def _add_corporation(self, user, token):
        request = self.factory.get(reverse("assets:add_corp"))
        request.user = user
        request.token = token
        middleware = SessionMiddleware(Mock())
        middleware.process_request(request)
        orig_view = add_corp.__wrapped__.__wrapped__.__wrapped__
        return orig_view(request, token)

    def _middleware_process_request(self, request: WSGIRequest):
        """Helper method to process middleware for a request."""
        session_middleware = SessionMiddleware(Mock())
        session_middleware.process_request(request)
        message_middleware = MessageMiddleware(Mock())
        message_middleware.process_request(request)
