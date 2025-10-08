# Standard Library
from http import HTTPStatus

# Django
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from django.urls import reverse

# Alliance Auth (External Libs)
from app_utils.testdata_factories import UserMainFactory


class TestViews(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = RequestFactory()
        cls.user = UserMainFactory(
            permissions=[
                "assets.basic_access",
            ]
        )

    def test_index_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("assets:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
