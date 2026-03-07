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
from assets.tests.testdata.integrations.allianceauth import load_allianceauth
from assets.tests.testdata.integrations.eveentity import load_eveentity
from assets.tests.testdata.utils import create_user_from_evecharacter
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
        * Alliance Auth Characters, Corporation, Alliance Data
        * Eve Entity Data
        * Taken User IDs: 1001, 1002, 1003, 1004, 1005

    Available Request Factory:
        `self.factory`

    Available test users:
        * `user` User with standard Assets access.
            * 'assets.basic_access' Permission
            * Character ID 1001
            * Corporation ID 2001
            * Alliance ID 3001
        * `user2` Second user with standard Assets access.
            * 'assets.basic_access' Permission
            * Character ID 1002
            * Corporation ID 2002
            * Alliance ID 3002
        * `superuser` Superuser.
            * Access to whole Application
            * Character ID 1003
        * `manage_own_user` User with manage own corporation access.
            * 'assets.basic_access' Permission
            * 'assets.corporation_access' Permission
            * 'assets.manage_corporation' Permission
            * 'assets.manage_requests' Permission
            * Character ID 1004
            * Corporation ID 2001
            * Alliance ID 3001
        * `manage_user` User with manage corporations access.
            * 'assets.basic_access' Permission
            * 'assets.corporation_access' Permission
            * 'assets.admin_access' Permission
            * 'assets.manage_requests' Permission
            * Character ID 1005
            * Corporation ID 2001
            * Alliance ID 3001

    Example:
        .. code-block:: python

            class TestMyAssetsStuff(AssetsTestCase):
                def test_should_do_what_i_need(self):
                    user = self.user
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Initialize Alliance Auth test data
        load_allianceauth()
        load_eveentity()

        # Request Factory
        cls.factory = RequestFactory()

        # User with Standard Access - Corporation 2001
        cls.user, cls.user_character = create_user_from_evecharacter(
            character_id=1001,
            permissions=["assets.basic_access"],
        )
        # User with Standard Access - Corporation 2002
        cls.user2, cls.user2_character = create_user_from_evecharacter(
            character_id=1002,
            permissions=["assets.basic_access"],
        )
        # User with Superuser Access - Corporation 2003
        cls.superuser, cls.superuser_character = create_user_from_evecharacter(
            character_id=1003,
            permissions=[],
        )
        cls.superuser.is_superuser = True
        cls.superuser.save()
        # User with Manage Own Corporation Access - Corporation 2001
        cls.manage_own_user, cls.manage_own_character = create_user_from_evecharacter(
            character_id=1004,
            permissions=[
                "assets.basic_access",
                "assets.corporation_access",
                "assets.manage_corporation",
                "assets.manage_requests",
            ],
        )
        # User with Manage Corporations Access - Corporation 2001
        cls.manage_user, cls.manage_character = create_user_from_evecharacter(
            character_id=1005,
            permissions=[
                "assets.basic_access",
                "assets.corporation_access",
                "assets.admin_access",
                "assets.manage_corporation",
                "assets.manage_requests",
            ],
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
