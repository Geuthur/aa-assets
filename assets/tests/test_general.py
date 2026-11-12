"""Tests for the permission definitions in General."""

# Standard Library
import re
from pathlib import Path

# Django
from django.test import SimpleTestCase

# AA Assets
import assets
from assets.models import General

APP_DIR = Path(assets.__file__).parent
CODENAMES = {codename for codename, _ in General._meta.permissions}
# `assets.<codename>` in permission checks and `perms.assets.<codename>` in templates
PERM_PATTERN = re.compile(
    r"""(?:has_perm|permissions?_required)\(\s*\[?\s*["']assets\.(\w+)["']"""
    r"""|perms\.assets\.(\w+)"""
)


class TestGeneralPermissions(SimpleTestCase):
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
