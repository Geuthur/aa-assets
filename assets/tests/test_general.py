"""Tests for the General permission helpers."""

# Django
from django.contrib.auth.models import AnonymousUser, Permission
from django.test import TestCase

# AA Assets
from assets.models import Assets, General
from assets.tests.testdata.factory import UserMainFactory


class TestGeneralPermissions(TestCase):
    def test_codenames_are_unchanged(self):
        """Codenames hang on groups in installations and must not change."""
        self.assertEqual(
            [value for value, _ in General.Permission.choices],
            [
                "basic_access",
                "corporation_access",
                "admin_access",
                "manage_corporation",
                "manage_requests",
            ],
        )
        self.assertEqual(
            [codename for codename, _ in General._meta.permissions],
            [value for value, _ in General.Permission.choices],
        )

    def test_get_perm(self):
        self.assertEqual(
            General.get_perm(General.Permission.BASIC_ACCESS), "assets.basic_access"
        )
        self.assertEqual(General.get_perm("basic_access"), "assets.basic_access")

    def test_has_perm_without_user(self):
        self.assertFalse(General.has_perm(None, General.Permission.BASIC_ACCESS))
        self.assertFalse(
            General.has_perm(AnonymousUser(), General.Permission.BASIC_ACCESS)
        )

    def test_has_perm_and_has_any_perm(self):
        user = UserMainFactory(permissions__=["assets.manage_requests"])
        self.assertTrue(General.has_perm(user, General.Permission.MANAGE_REQUESTS))
        self.assertFalse(General.has_perm(user, General.Permission.ADMIN_ACCESS))
        self.assertTrue(
            General.has_any_perm(
                user,
                General.Permission.ADMIN_ACCESS,
                General.Permission.MANAGE_REQUESTS,
            )
        )
        self.assertFalse(General.has_any_perm(user, General.Permission.ADMIN_ACCESS))

    def test_has_management_access(self):
        basic = UserMainFactory()
        manager = UserMainFactory(permissions__=["assets.manage_requests"])
        self.assertFalse(General.has_management_access(basic))
        self.assertTrue(General.has_management_access(manager))

    def test_admin_access_sees_all_assets(self):
        """`admin_access` is checked with the real codename (it was `admin_Access`)."""
        user = UserMainFactory(permissions__=["assets.admin_access"])
        self.assertTrue(Permission.objects.filter(codename="admin_access").exists())
        self.assertEqual(
            list(Assets.objects.visible_to(user)), list(Assets.objects.all())
        )
