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

    def test_manifest_registers_hybrid_entry_with_summary(self):
        manifest = get_manifest()
        self.assertEqual(1, manifest["contract_version"])
        self.assertEqual("inventory", manifest["id"])
        self.assertEqual("/hbos/inventory", manifest["route"])
        # 概览页已原生、拍照识别仍在 Desk，故为 hybrid
        self.assertEqual("hybrid", manifest["migration_mode"])
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
    def test_root_stays_in_portal_spa(self):
        # 概览页已原生，基础路由必须返回自身，前端才留在 SPA 内
        self.assertEqual(
            "/hbos/inventory",
            resolve_stable_route("/hbos/inventory"),
        )
        self.assertEqual(
            "/hbos/inventory",
            resolve_stable_route("/hbos/inventory/"),
        )

    def test_intake_is_now_native_too(self):
        """入库拍照识别于 2026-09-25 前端化，不再跳去 Desk。

        前端化之前这条路由解析到 ``/app/hbos-photo-intake``；现在必须返回自身，
        否则 Portal 会整页跳出 SPA（Owner 报过的现象）。
        """
        self.assertEqual(
            "/hbos/inventory/intake",
            resolve_stable_route("/hbos/inventory/intake"),
        )

    def test_no_route_resolves_into_desk(self):
        """本 App 已不再是「有入口指向 Desk」的状态，守住这条回归。"""
        for path in (
            "/hbos/inventory",
            "/hbos/inventory/intake",
            "/hbos/inventory/draft/MAT-STE-2026-00042",
            "/hbos/inventory/batch/B2609503",
            "/hbos/inventory/report/location-detail",
            "/hbos/inventory/report/stock-balance",
            "/hbos/inventory/pending",
            "/hbos/inventory/item/13000900",
            "/hbos/inventory/warehouse/16-03-205%20-%20HB",
        ):
            with self.subTest(path=path):
                self.assertFalse(resolve_stable_route(path).startswith("/app/"))

    def test_document_routes_keep_their_document_number(self):
        """带单据号的路由必须**原样**返回，前端要靠后缀取单号。"""
        self.assertEqual(
            "/hbos/inventory/draft/MAT-STE-2026-00042",
            resolve_stable_route("/hbos/inventory/draft/MAT-STE-2026-00042"),
        )
        self.assertEqual(
            "/hbos/inventory/batch/B2609503",
            resolve_stable_route("/hbos/inventory/batch/B2609503"),
        )

    def test_bare_document_prefix_is_rejected(self):
        """`/draft/` 这种没有单号的半截路径不算已注册——否则前端会拿到空单号。

        报表的 `/report/<id>`、主数据的 `/item/<code>`、`/warehouse/<name>` 同理。
        """
        for path in (
            "/hbos/inventory/draft",
            "/hbos/inventory/draft/",
            "/hbos/inventory/batch",
            "/hbos/inventory/report",
            "/hbos/inventory/report/",
            "/hbos/inventory/pending/x",
            "/hbos/inventory/item",
            "/hbos/inventory/item/",
            "/hbos/inventory/warehouse",
            "/hbos/inventory/warehouse/",
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    resolve_stable_route(path)

    def test_url_encoded_warehouse_name_is_unquoted_safely(self):
        """货位名带空格与连字符，前端会编码后拼进来；解码后必须校验**解码后的**
        路径段，而不是拿编码串去判——否则 `%2e%2e` 这类会被当合法字符放过去。
        """
        self.assertEqual(
            "/hbos/inventory/warehouse/16-03-205 - HB",
            resolve_stable_route("/hbos/inventory/warehouse/16-03-205%20-%20HB"),
        )
        with self.assertRaises(ValueError):
            resolve_stable_route("/hbos/inventory/warehouse/%2e%2e%2fadmin")

    def test_query_string_is_preserved(self):
        self.assertEqual(
            "/hbos/inventory?tab=anomaly",
            resolve_stable_route("/hbos/inventory?tab=anomaly"),
        )
        self.assertEqual(
            "/hbos/inventory/draft/MAT-STE-2026-00042?print=1",
            resolve_stable_route("/hbos/inventory/draft/MAT-STE-2026-00042?print=1"),
        )

    def test_unregistered_or_unsafe_paths_are_rejected(self):
        for path in (
            "/hbos/inventory/batches",
            "/hbos/lims",
            "https://evil.example/hbos/inventory",
            "/hbos/inventory/%2e%2e/admin",
            "/hbos/inventory/draft/%2e%2e/admin",
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
