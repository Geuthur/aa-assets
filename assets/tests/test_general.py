"""Tests for the permission definitions in General."""

# Standard Library
import re
from pathlib import Path

# Django
from django.test import TestCase

# AA Assets
import assets
from assets.managers import GeneralManager
from assets.models import General
from assets.tests.testdata.factory import UserMainFactory

APP_DIR = Path(assets.__file__).parent
CODENAMES = {codename for codename, _ in General._meta.permissions}
# `assets.<codename>` in permission checks and `perms.assets.<codename>` in templates
PERM_PATTERN = re.compile(
    r"""(?:has_perm|permissions?_required)\(\s*\[?\s*["']assets\.(\w+)["']"""
    r"""|perms\.assets\.(\w+)"""
)


class TestGeneralPermissions(TestCase):
    def test_codenames_are_unchanged(self):
        """Codenames hang on groups in installations and must not change."""
        self.assertEqual(
            sorted(CODENAMES),
            sorted(
                [
                    "basic_access",
                    "corporation_access",
                    "admin_access",
                    "manage_corporation",
                    "manage_requests",
                ]
            ),
        )

    def test_used_permissions_are_defined(self):
        """Every permission string used in code and templates exists in General."""
        used = set()
        for path in [*APP_DIR.rglob("*.py"), *APP_DIR.rglob("*.html")]:
            if "migrations" in path.parts or "tests" in path.parts:
                continue
            for match in PERM_PATTERN.finditer(path.read_text(encoding="utf-8")):
                used.add((match.group(1) or match.group(2), path.name))
        self.assertTrue(used)
        unknown = {(name, file) for name, file in used if name not in CODENAMES}
        self.assertEqual(unknown, set())

    def test_has_basic_access(self):
        none = UserMainFactory(permissions__=[])
        basic = UserMainFactory(permissions__=["assets.basic_access"])
        self.assertFalse(GeneralManager.has_basic_access(none))
        self.assertTrue(GeneralManager.has_basic_access(basic))

    def test_has_corporation_access(self):
        basic = UserMainFactory()
        corp = UserMainFactory(permissions__=["assets.corporation_access"])
        self.assertFalse(GeneralManager.has_corporation_access(basic))
        self.assertTrue(GeneralManager.has_corporation_access(corp))

    def test_has_manage_requests_access(self):
        basic = UserMainFactory()
        manager = UserMainFactory(permissions__=["assets.manage_requests"])
        admin = UserMainFactory(permissions__=["assets.admin_access"])
        superuser = UserMainFactory(is_superuser=True)
        self.assertFalse(GeneralManager.has_manage_requests_access(basic))
        self.assertFalse(GeneralManager.has_manage_requests_access(admin))
        self.assertTrue(GeneralManager.has_manage_requests_access(manager))
        self.assertTrue(GeneralManager.has_manage_requests_access(superuser))

    def test_has_admin_access(self):
        basic = UserMainFactory()
        manager = UserMainFactory(permissions__=["assets.manage_requests"])
        admin = UserMainFactory(permissions__=["assets.admin_access"])
        superuser = UserMainFactory(is_superuser=True)
        self.assertFalse(GeneralManager.has_admin_access(basic))
        self.assertFalse(GeneralManager.has_admin_access(manager))
        self.assertTrue(GeneralManager.has_admin_access(admin))
        self.assertTrue(GeneralManager.has_admin_access(superuser))

    def test_has_management_access(self):
        basic = UserMainFactory()
        manager = UserMainFactory(permissions__=["assets.manage_requests"])
        admin = UserMainFactory(permissions__=["assets.admin_access"])
        superuser = UserMainFactory(is_superuser=True)
        self.assertFalse(GeneralManager.has_management_access(basic))
        self.assertTrue(GeneralManager.has_management_access(manager))
        self.assertTrue(GeneralManager.has_management_access(admin))
        self.assertTrue(GeneralManager.has_management_access(superuser))
        # Still reachable through the model manager
        self.assertTrue(General.objects.has_management_access(admin))
