# Standard Library
from unittest.mock import MagicMock, patch

# Django
from django.utils.safestring import SafeString

# AA Assets
from assets.api import helpers
from assets.api.requests import helper as request_helper
from assets.tests import NoSocketsTestCase


class TestApiHelpers(NoSocketsTestCase):
    @patch("assets.api.helpers.render_to_string")
    def test_generate_button_should_return_safe_html(self, mock_render):
        mock_render.return_value = '<a class="btn">{x}</a>'

        result = helpers.generate_button("tpl.html", MagicMock(), {}, MagicMock())

        self.assertIsInstance(result, SafeString)
        self.assertEqual(result, '<a class="btn">{x}</a>')

    @patch("assets.api.requests.helper.generate_button")
    @patch("assets.api.requests.helper.resolve_url", return_value="/x/")
    def test_request_list_should_return_safe_html(self, _resolve, mock_button):
        mock_button.return_value = SafeString("<button>info</button>")

        result = request_helper._request_list(MagicMock(pk=1), True, MagicMock())

        self.assertIsInstance(result, SafeString)
        self.assertEqual(result, "<button>info</button>")
