"""Tests for the user notifications."""

# Standard Library
from unittest.mock import patch

# AA Assets
from assets.helpers.discord import send_user_notification
from assets.models import UserSettings
from assets.tests import AuthTestCase

MODULE_PATH = "assets.helpers.discord"


@patch(MODULE_PATH + "._discordbot_send_direct_message")
@patch(MODULE_PATH + ".allianceauth_discordbot_installed", return_value=True)
@patch(MODULE_PATH + ".notify")
class TestSendUserNotification(AuthTestCase):
    def _send(self):
        send_user_notification(
            user_id=self.user.pk,
            title="Test Title",
            message="Test Message",
            embed_message=True,
            level="info",
        )

    def test_send_user_notification_should_send_nothing_if_notifications_disabled(
        self, mock_notify, _, mock_send_discordbot
    ):
        # Test Data
        UserSettings.objects.create(user=self.user, disable_notifications=True)

        # Test Action
        self._send()

        # Expected Result
        mock_notify.info.assert_not_called()
        mock_send_discordbot.assert_not_called()

    def test_send_user_notification_should_send_if_user_has_no_settings(
        self, mock_notify, _, __
    ):
        # Test Action
        self._send()

        # Expected Result
        self.assertFalse(UserSettings.objects.filter(user=self.user).exists())
        mock_notify.info.assert_called_once_with(
            user=self.user, title="Test Title", message="Test Message"
        )

    def test_send_user_notification_should_send_if_notifications_not_disabled(
        self, mock_notify, _, __
    ):
        # Test Data
        UserSettings.objects.create(user=self.user, disable_notifications=False)

        # Test Action
        self._send()

        # Expected Result
        mock_notify.info.assert_called_once_with(
            user=self.user, title="Test Title", message="Test Message"
        )

    def test_send_user_notification_should_ignore_settings_of_other_users(
        self, mock_notify, _, __
    ):
        # Test Data
        UserSettings.objects.create(user=self.superuser, disable_notifications=True)

        # Test Action
        self._send()

        # Expected Result
        mock_notify.info.assert_called_once_with(
            user=self.user, title="Test Title", message="Test Message"
        )
