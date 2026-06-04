# Standard Library
from http import HTTPStatus

# Django
from django.urls import reverse

# AA Assets
from assets import views
from assets.tests import AssetsTestCase


class TestViews(AssetsTestCase):
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
