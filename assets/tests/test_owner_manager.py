"""Tests for the access methods of the Owner manager."""

# Third Party
from evesde_factory.allianceauth import UserFactory

# Django
from django.test import TestCase

# AA Assets
from assets.models import Owner
from assets.tests.testdata.factory import UserMainFactory


class TestVisibleEveCharacters(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()
        cls.other = UserMainFactory()
        cls.manager = UserMainFactory(
            permissions__=["assets.basic_access", "assets.manage_requests"]
        )

    def test_user_sees_own_characters(self):
        result = Owner.objects.visible_eve_characters(self.user)
        self.assertQuerySetEqual(
            result, [self.user.profile.main_character], ordered=False
        )

    def test_manager_sees_all_characters(self):
        result = Owner.objects.visible_eve_characters(self.manager)
        self.assertQuerySetEqual(
            result,
            [
                self.user.profile.main_character,
                self.other.profile.main_character,
                self.manager.profile.main_character,
            ],
            ordered=False,
        )

    def test_user_without_main_sees_nothing(self):
        user = UserFactory()
        self.assertFalse(Owner.objects.visible_eve_characters(user).exists())
