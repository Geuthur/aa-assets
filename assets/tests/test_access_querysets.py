"""Tests for the access rules of all querysets and managers, one test per rule."""

# Third Party
from evesde_factory.allianceauth import EveCharacterFactory, UserFactory

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo

# AA Assets
from assets.models import Assets, EveEntity, Location, Owner, Request
from assets.tests import AuthTestCase
from assets.tests.testdata.factory import UserMainFactory
from assets.tests.testdata.orders import create_asset, create_owner


class AccessRulesTestCase(AuthTestCase):
    """
    Users and objects for every access rule.

    `self.user` and `self.corp_user` are in the same corporation, `self.other`
    is in another one. Every user with a main character owns one character
    owner, both corporations have a corporation owner.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.corporation = EveCorporationInfo.objects.get(
            corporation_id=cls.user.profile.main_character.corporation_id
        )

        # Users
        cls.corp_user = UserMainFactory(
            permissions__=["assets.basic_access", "assets.corporation_access"],
            main_character__character=EveCharacterFactory(corporation=cls.corporation),
        )
        cls.other = UserMainFactory()
        cls.other_corporation = EveCorporationInfo.objects.get(
            corporation_id=cls.other.profile.main_character.corporation_id
        )
        cls.admin = UserMainFactory(
            permissions__=["assets.basic_access", "assets.admin_access"]
        )
        cls.manager = UserMainFactory(
            permissions__=["assets.basic_access", "assets.manage_requests"]
        )
        cls.no_main = UserFactory(
            permissions__=["assets.basic_access", "assets.corporation_access"]
        )
        cls.no_main_admin = UserFactory(
            permissions__=[
                "assets.basic_access",
                "assets.admin_access",
                "assets.manage_requests",
            ]
        )
        cls.users_with_main = [
            cls.user,
            cls.superuser,
            cls.corp_user,
            cls.other,
            cls.admin,
            cls.manager,
        ]

        # Owners
        cls.owners = {user: create_owner(user) for user in cls.users_with_main}
        cls.corp_owner = Owner.objects.create(corporation=cls.corporation)
        cls.other_corp_owner = Owner.objects.create(corporation=cls.other_corporation)
        cls.all_owners = {*cls.owners.values(), cls.corp_owner, cls.other_corp_owner}

        # Assets, one per owner
        cls.assets = {
            owner: create_asset(owner, item_id=number)
            for number, owner in enumerate(cls.all_owners, start=1)
        }
        cls.all_assets = set(cls.assets.values())

        # Locations
        cls.locations = {
            name: Location.objects.create(
                id=1_000_000_000_000 + number,
                name=name,
                owner=(
                    EveEntity.objects.create(id=owner_id, name=name, category=category)
                    if owner_id
                    else None
                ),
            )
            for number, (name, owner_id, category) in enumerate(
                [
                    (
                        "user",
                        cls.user.profile.main_character.character_id,
                        EveEntity.CATEGORY_CHARACTER,
                    ),
                    (
                        "corp_user",
                        cls.corp_user.profile.main_character.character_id,
                        EveEntity.CATEGORY_CHARACTER,
                    ),
                    (
                        "corporation",
                        cls.corporation.corporation_id,
                        EveEntity.CATEGORY_CORPORATION,
                    ),
                    (
                        "other_corporation",
                        cls.other_corporation.corporation_id,
                        EveEntity.CATEGORY_CORPORATION,
                    ),
                    ("no_owner", None, None),
                ]
            )
        }
        # create_asset adds the station of the assets
        cls.all_locations = set(Location.objects.all())

        # Requests
        cls.requests = {
            user: Request.objects.create(requesting_user=user)
            for user in [cls.user, cls.other, cls.admin, cls.manager, cls.no_main]
        }
        cls.all_requests = set(cls.requests.values())


class TestAssetsVisibleTo(AccessRulesTestCase):
    def test_user_sees_assets_of_own_characters(self):
        self.assertEqual(
            set(Assets.objects.visible_to(self.user)),
            {self.assets[self.owners[self.user]]},
        )

    def test_corporation_access_adds_assets_of_own_corporation(self):
        self.assertEqual(
            set(Assets.objects.visible_to(self.corp_user)),
            {self.assets[self.owners[self.corp_user]], self.assets[self.corp_owner]},
        )

    def test_admin_access_sees_all(self):
        self.assertEqual(set(Assets.objects.visible_to(self.admin)), self.all_assets)

    def test_superuser_sees_all(self):
        self.assertEqual(
            set(Assets.objects.visible_to(self.superuser)), self.all_assets
        )

    def test_manage_requests_sees_only_own(self):
        self.assertEqual(
            set(Assets.objects.visible_to(self.manager)),
            {self.assets[self.owners[self.manager]]},
        )

    def test_user_without_main_sees_nothing(self):
        self.assertFalse(Assets.objects.visible_to(self.no_main).exists())

    def test_admin_access_without_main_sees_all(self):
        self.assertEqual(
            set(Assets.objects.visible_to(self.no_main_admin)), self.all_assets
        )

    def test_visible_to_keeps_previous_filters(self):
        own = self.assets[self.owners[self.user]]
        queryset = Assets.objects.exclude(pk=own.pk)
        self.assertFalse(queryset.visible_to(self.user).exists())
        self.assertEqual(set(queryset.visible_to(self.admin)), self.all_assets - {own})


class TestLocationVisibleTo(AccessRulesTestCase):
    def test_user_sees_locations_of_main_character(self):
        self.assertEqual(
            set(Location.objects.visible_to(self.user)), {self.locations["user"]}
        )

    def test_corporation_access_adds_locations_of_own_corporation(self):
        self.assertEqual(
            set(Location.objects.visible_to(self.corp_user)),
            {self.locations["corp_user"], self.locations["corporation"]},
        )

    def test_admin_access_sees_all(self):
        self.assertEqual(
            set(Location.objects.visible_to(self.admin)), self.all_locations
        )

    def test_superuser_sees_all(self):
        self.assertEqual(
            set(Location.objects.visible_to(self.superuser)), self.all_locations
        )

    def test_manage_requests_sees_only_own(self):
        self.assertFalse(Location.objects.visible_to(self.manager).exists())

    def test_user_without_main_sees_nothing(self):
        self.assertFalse(Location.objects.visible_to(self.no_main).exists())

    def test_admin_access_without_main_sees_all(self):
        self.assertEqual(
            set(Location.objects.visible_to(self.no_main_admin)), self.all_locations
        )


class TestOwnerVisibleTo(AccessRulesTestCase):
    def test_user_sees_own_character_owners(self):
        self.assertEqual(
            set(Owner.objects.visible_to(self.user)), {self.owners[self.user]}
        )

    def test_corporation_access_adds_owner_of_own_corporation(self):
        self.assertEqual(
            set(Owner.objects.visible_to(self.corp_user)),
            {self.owners[self.corp_user], self.corp_owner},
        )

    def test_admin_access_sees_all(self):
        self.assertEqual(set(Owner.objects.visible_to(self.admin)), self.all_owners)

    def test_superuser_sees_all(self):
        self.assertEqual(set(Owner.objects.visible_to(self.superuser)), self.all_owners)

    def test_manage_requests_sees_only_own(self):
        self.assertEqual(
            set(Owner.objects.visible_to(self.manager)), {self.owners[self.manager]}
        )

    def test_user_without_main_sees_nothing(self):
        self.assertFalse(Owner.objects.visible_to(self.no_main).exists())

    def test_admin_access_without_main_sees_all(self):
        self.assertEqual(
            set(Owner.objects.visible_to(self.no_main_admin)), self.all_owners
        )


class TestOwnerManageTo(AccessRulesTestCase):
    def test_user_manages_own_character_owners(self):
        self.assertEqual(
            set(Owner.objects.manage_to(self.user)), {self.owners[self.user]}
        )

    def test_corporation_access_adds_nothing(self):
        self.assertEqual(
            set(Owner.objects.manage_to(self.corp_user)),
            {self.owners[self.corp_user]},
        )

    def test_admin_access_manages_all(self):
        self.assertEqual(set(Owner.objects.manage_to(self.admin)), self.all_owners)

    def test_manage_requests_manages_all(self):
        self.assertEqual(set(Owner.objects.manage_to(self.manager)), self.all_owners)

    def test_superuser_manages_all(self):
        self.assertEqual(set(Owner.objects.manage_to(self.superuser)), self.all_owners)

    def test_user_without_main_manages_nothing(self):
        self.assertFalse(Owner.objects.manage_to(self.no_main).exists())

    def test_management_access_without_main_manages_all(self):
        self.assertEqual(
            set(Owner.objects.manage_to(self.no_main_admin)), self.all_owners
        )

    def test_manage_to_keeps_previous_filters(self):
        queryset = Owner.objects.filter(corporation__isnull=False)
        self.assertFalse(queryset.manage_to(self.user).exists())
        self.assertEqual(
            set(queryset.manage_to(self.manager)),
            {self.corp_owner, self.other_corp_owner},
        )


class TestRequestVisibleTo(AccessRulesTestCase):
    def test_user_sees_own_requests(self):
        self.assertEqual(
            set(Request.objects.visible_to(self.user)), {self.requests[self.user]}
        )

    def test_corporation_access_adds_nothing(self):
        self.assertFalse(Request.objects.visible_to(self.corp_user).exists())

    def test_manage_requests_sees_all(self):
        self.assertEqual(
            set(Request.objects.visible_to(self.manager)), self.all_requests
        )

    def test_superuser_sees_all(self):
        self.assertEqual(
            set(Request.objects.visible_to(self.superuser)), self.all_requests
        )

    def test_admin_access_sees_only_own(self):
        self.assertEqual(
            set(Request.objects.visible_to(self.admin)), {self.requests[self.admin]}
        )

    def test_user_without_main_sees_nothing(self):
        self.assertFalse(Request.objects.visible_to(self.no_main).exists())

    def test_manage_requests_without_main_sees_all(self):
        self.assertEqual(
            set(Request.objects.visible_to(self.no_main_admin)), self.all_requests
        )


class TestVisibleEveCharactersRules(AccessRulesTestCase):
    def test_user_sees_own_characters(self):
        self.assertEqual(
            set(Owner.objects.visible_eve_characters(self.user)),
            {self.user.profile.main_character},
        )

    def test_manage_requests_sees_all(self):
        self.assertEqual(
            set(Owner.objects.visible_eve_characters(self.manager)),
            set(EveCharacter.objects.all()),
        )

    def test_superuser_sees_all(self):
        self.assertEqual(
            set(Owner.objects.visible_eve_characters(self.superuser)),
            set(EveCharacter.objects.all()),
        )

    def test_admin_access_sees_only_own(self):
        self.assertEqual(
            set(Owner.objects.visible_eve_characters(self.admin)),
            {self.admin.profile.main_character},
        )

    def test_corporation_access_adds_nothing(self):
        self.assertEqual(
            set(Owner.objects.visible_eve_characters(self.corp_user)),
            {self.corp_user.profile.main_character},
        )

    def test_user_without_main_sees_nothing(self):
        self.assertFalse(Owner.objects.visible_eve_characters(self.no_main).exists())

    def test_manage_requests_without_main_sees_all(self):
        self.assertEqual(
            set(Owner.objects.visible_eve_characters(self.no_main_admin)),
            set(EveCharacter.objects.all()),
        )
