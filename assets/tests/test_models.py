"""Tests for the models."""

# Standard Library
from unittest.mock import Mock, patch

# Third Party
from evesde_factory.allianceauth import EveCorporationInfoFactory

# AA Assets
from assets.models import Owner, Request
from assets.models.helpers.update_manager import OwnerUpdateSection, UpdateStatus
from assets.tests import AuthTestCase
from assets.tests.testdata.factory import UserMainFactory
from assets.tests.testdata.owner import OwnerUpdateStatusFactory


class TestOwnerGetEsiScopes(AuthTestCase):
    def test_should_return_corporation_scopes_for_corporation_owner(self):
        # Test Data
        owner = Owner.objects.create(corporation=EveCorporationInfoFactory())

        # Test Action
        result = owner.get_esi_scopes()

        # Expected Result
        self.assertEqual(
            result,
            [
                "esi-universe.read_structures.v1",
                "esi-assets.read_corporation_assets.v1",
            ],
        )

    def test_should_return_character_scopes_for_character_owner(self):
        # Test Data
        owner = Owner.objects.create(
            character=self.user.profile.main_character.character_ownership
        )

        # Test Action
        result = owner.get_esi_scopes()

        # Expected Result
        self.assertEqual(
            result,
            ["esi-universe.read_structures.v1", "esi-assets.read_assets.v1"],
        )


@patch("assets.models.request.send_user_notification")
@patch.object(Request, "approvers")
@patch.object(Request, "convert_order_to_notifiy", return_value="\nTritanium x 5")
class TestRequestNotifications(AuthTestCase):
    """The notification texts are filled with `.format()`, so they can be translated."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.requestor = UserMainFactory()
        cls.approver = UserMainFactory()
        cls.order = Request.objects.create(
            requesting_user=cls.requestor, approver_user=cls.approver
        )

    def _sent(self, send_mock):
        return send_mock.delay.call_args.kwargs

    def test_notify_new_request_should_fill_title_and_message(
        self, _items, approvers, send
    ):
        # Test Data
        approvers.return_value = [self.approver]

        # Test Action
        self.order.notify_new_request()

        # Expected Result
        sent = self._sent(send)
        self.assertEqual(sent["title"], f"{self.requestor} has Requested a Order")
        self.assertEqual(
            sent["message"],
            f"{self.requestor} has requested the following items:\nTritanium x 5\n",
        )

    def test_notify_request_completed_should_fill_title_and_message(
        self, _items, _approvers, send
    ):
        # Test Action
        self.order.notify_request_completed()

        # Expected Result
        sent = self._sent(send)
        self.assertEqual(
            sent["title"],
            f"{self.approver} has completed the Order for {self.requestor} ID: {self.order.pk}.",
        )
        self.assertEqual(
            sent["message"],
            f"{self.approver} has completed the following items:\nTritanium x 5\n",
        )

    def test_notify_request_canceled_should_fill_title_and_message(
        self, _items, approvers, send
    ):
        # Test Data
        approvers.return_value = [self.approver]

        # Test Action
        self.order.notify_request_canceled(user=self.requestor)

        # Expected Result
        sent = self._sent(send)
        self.assertEqual(
            sent["title"],
            f"{self.requestor} has canceled the Order for {self.requestor} ID: {self.order.pk}.",
        )
        self.assertEqual(
            sent["message"],
            f"{self.requestor} has canceled the following items:\nTritanium x 5\n",
        )

    def test_notify_request_open_should_fill_title_and_message(
        self, _items, _approvers, send
    ):
        # Test Data
        request = Mock(user=self.approver)

        # Test Action
        self.order.notify_request_open(request)

        # Expected Result
        sent = self._sent(send)
        self.assertEqual(
            sent["title"],
            f"{self.approver} has reopened the Order for {self.requestor} ID: {self.order.pk}.",
        )
        self.assertEqual(
            sent["message"],
            f"{self.approver} has reopened the following items:\nTritanium x 5\n",
        )


class TestOwnerUpdateStatus(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = Owner.objects.create(
            character=cls.user.profile.main_character.character_ownership
        )

    def test_get_status_should_be_incomplete_without_status_rows(self):
        # Test Action & Expected Result
        self.assertEqual(self.owner.get_status, UpdateStatus.INCOMPLETE)

    def test_get_status_should_be_ok_when_all_sections_succeeded(self):
        # Test Data
        OwnerUpdateStatusFactory(
            owner=self.owner, section=OwnerUpdateSection.ASSETS, is_success=True
        )

        # Test Action & Expected Result
        self.assertEqual(self.owner.get_status, UpdateStatus.OK)

    def test_get_status_should_be_token_error_when_a_section_has_one(self):
        # Test Data
        OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            is_success=False,
            has_token_error=True,
        )

        # Test Action & Expected Result
        self.assertEqual(self.owner.get_status, UpdateStatus.TOKEN_ERROR)

    def test_get_status_should_be_disabled_for_inactive_owners(self):
        # Test Data
        owner = Owner.objects.create(
            corporation=EveCorporationInfoFactory(), is_active=False
        )

        # Test Action & Expected Result
        self.assertEqual(owner.get_status, UpdateStatus.DISABLED)

    def test_update_status_str_should_name_owner_and_section(self):
        # Test Data
        status = OwnerUpdateStatusFactory(
            owner=self.owner, section=OwnerUpdateSection.ASSETS
        )

        # Test Action & Expected Result
        self.assertEqual(str(status), f"{self.owner} - assets")
