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
from hb_inventory_app.hbos_inventory.portal.summary import (
    _load_permission_aware_inventory,
    project_inventory_summary,
)


class InventoryPortalManifestTest(unittest.TestCase):
    def test_hook_registers_provider(self):
        self.assertEqual(
            ["hb_inventory_app.hbos_inventory.portal.provider.get_provider"],
            hooks.hbos_portal_provider,
        )

    def test_manifest_registers_stable_legacy_entry_with_summary(self):
        manifest = get_manifest()
        self.assertEqual(1, manifest["contract_version"])
        self.assertEqual("inventory", manifest["id"])
        self.assertEqual("/hbos/inventory", manifest["route"])
        self.assertEqual("legacy", manifest["migration_mode"])
        self.assertEqual(["summary"], manifest["capabilities"])


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


class InventoryPortalSummaryTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("frappe", None)

    def test_projection_counts_without_adding_cross_uom_quantities(self):
        summary = project_inventory_summary(
            ["WH-A", "WH-B"],
            [
                {"item_code": "ITEM-A", "actual_qty": 2, "projected_qty": 1},
                {"item_code": "ITEM-A", "actual_qty": 3, "projected_qty": -1},
                {"item_code": "ITEM-B", "actual_qty": -2, "projected_qty": -2},
                {"item_code": "ITEM-C", "actual_qty": 0, "projected_qty": 5},
            ],
        )

        self.assertEqual("attention", summary["status"])
        self.assertEqual(
            {
                "inventory_visible_warehouses": 2,
                "inventory_stocked_items": 2,
                "inventory_negative_bins": 1,
                "inventory_projected_shortage_bins": 2,
            },
            {metric["id"]: metric["value"] for metric in summary["metrics"]},
        )

    def test_loader_constrains_bin_query_to_permission_visible_warehouses(self):
        calls = []

        def get_list(doctype, **kwargs):
            calls.append((doctype, kwargs))
            if doctype == "Warehouse":
                return ["WH-ALLOWED"]
            if doctype == "Bin":
                self.assertEqual(
                    {"warehouse": ["in", ["WH-ALLOWED"]]},
                    kwargs["filters"],
                )
                return [
                    {
                        "warehouse": "WH-ALLOWED",
                        "item_code": "ITEM-A",
                        "actual_qty": 1,
                        "projected_qty": 1,
                    }
                ]
            raise AssertionError(f"unexpected DocType: {doctype}")

        sys.modules["frappe"] = types.SimpleNamespace(get_list=get_list)

        warehouses, bins = _load_permission_aware_inventory()

        self.assertEqual(["WH-ALLOWED"], warehouses)
        self.assertEqual("WH-ALLOWED", bins[0]["warehouse"])
        self.assertEqual(["Warehouse", "Bin"], [doctype for doctype, _ in calls])

    def test_loader_does_not_query_bins_when_no_warehouse_is_visible(self):
        calls = []

        def get_list(doctype, **kwargs):
            calls.append(doctype)
            if doctype == "Warehouse":
                return []
            raise AssertionError("Bin must not be queried without visible warehouses")

        sys.modules["frappe"] = types.SimpleNamespace(get_list=get_list)

        warehouses, bins = _load_permission_aware_inventory()

        self.assertEqual([], warehouses)
        self.assertEqual([], bins)
        self.assertEqual(["Warehouse"], calls)


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
