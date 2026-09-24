from __future__ import annotations

import sys
import types
import unittest

from hb_inventory_app import hooks
from hb_inventory_app.hbos_inventory.portal.access import (
    INVENTORY_PORTAL_ROLES,
    READ_CAPABILITY,
    build_access_context,
)
from hb_inventory_app.hbos_inventory.portal.manifest import get_manifest
from hb_inventory_app.hbos_inventory.portal.provider import get_provider
from hb_inventory_app.hbos_inventory.portal.routes import resolve_stable_route


class InventoryPortalManifestTest(unittest.TestCase):
    def test_hook_registers_provider(self):
        self.assertEqual(
            ["hb_inventory_app.hbos_inventory.portal.provider.get_provider"],
            hooks.hbos_portal_provider,
        )

    def test_manifest_registers_stable_legacy_entry_only(self):
        manifest = get_manifest()
        self.assertEqual(1, manifest["contract_version"])
        self.assertEqual("inventory", manifest["id"])
        self.assertEqual("/hbos/inventory", manifest["route"])
        self.assertEqual("legacy", manifest["migration_mode"])
        self.assertEqual([], manifest["capabilities"])


class InventoryPortalAccessTest(unittest.TestCase):
    def test_guest_and_unrelated_employee_cannot_enter(self):
        self.assertFalse(build_access_context("Guest", ["Stock User"])["can_enter"])
        self.assertFalse(build_access_context("emp@example.com", ["Employee"])["can_enter"])

    def test_current_inventory_roles_can_enter(self):
        for role in sorted(INVENTORY_PORTAL_ROLES):
            with self.subTest(role=role):
                access = build_access_context("stock@example.com", [role])
                self.assertTrue(access["can_enter"])
                self.assertEqual([READ_CAPABILITY], access["capabilities"])

    def test_administrator_break_glass_entry(self):
        self.assertTrue(build_access_context("Administrator", [])["can_enter"])

    def test_access_does_not_expose_raw_roles(self):
        access = build_access_context("stock@example.com", ["Stock User"])
        self.assertEqual(
            {"app_id", "can_enter", "capabilities", "scopes"},
            set(access),
        )
        self.assertNotIn("Stock User", str(access))


class InventoryPortalRouteTest(unittest.TestCase):
    def test_root_and_intake_map_to_current_page(self):
        self.assertEqual(
            "/app/hbos-photo-intake",
            resolve_stable_route("/hbos/inventory"),
        )
        self.assertEqual(
            "/app/hbos-photo-intake",
            resolve_stable_route("/hbos/inventory/intake"),
        )

    def test_unregistered_or_unsafe_paths_are_rejected(self):
        for path in (
            "/hbos/inventory/batches",
            "/hbos/lims",
            "https://evil.example/hbos/inventory",
            "/hbos/inventory/%2e%2e/admin",
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    resolve_stable_route(path)


class InventoryPortalProviderRuntimeBoundaryTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("frappe", None)

    def test_provider_uses_frappe_session_identity(self):
        fake_frappe = types.SimpleNamespace(
            session=types.SimpleNamespace(user="stock@example.com"),
            get_roles=lambda user: ["Stock User"] if user == "stock@example.com" else [],
        )
        sys.modules["frappe"] = fake_frappe

        access = get_provider().access_context()
        self.assertTrue(access["can_enter"])
        self.assertEqual([READ_CAPABILITY], access["capabilities"])


if __name__ == "__main__":
    unittest.main()
