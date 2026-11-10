"""Tests for the models."""

# Third Party
from evesde_factory.allianceauth import EveCorporationInfoFactory

# AA Assets
from assets.models import Owner
from assets.tests import AuthTestCase


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
