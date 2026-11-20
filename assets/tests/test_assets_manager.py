"""Tests for the access rules of the Assets queryset."""

# AA Assets
from assets.models import Assets
from assets.tests import AuthTestCase
from assets.tests.testdata.factory import UserMainFactory
from assets.tests.testdata.orders import create_asset, create_owner


class TestAssetsVisibleTo(AuthTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.own_asset = create_asset(create_owner(cls.user), item_id=1)
        cls.other_asset = create_asset(create_owner(UserMainFactory()), item_id=2)

    def test_visible_to_should_return_assets_of_own_characters(self):
        # Test Action
        visible = Assets.objects.visible_to(self.user)

        # Expected Result
        self.assertEqual(list(visible), [self.own_asset])

    def test_visible_to_should_return_all_assets_for_superuser(self):
        # Test Action
        visible = Assets.objects.visible_to(self.superuser)

        # Expected Result
        self.assertEqual(set(visible), {self.own_asset, self.other_asset})
