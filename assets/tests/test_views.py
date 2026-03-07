# Standard Library
from http import HTTPStatus

# Django
from django.urls import reverse

# AA Assets
from assets.tests import AssetsTestCase


class TestViews(AssetsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_index_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("assets:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
