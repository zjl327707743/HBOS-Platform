from __future__ import annotations

import re
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

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
            "/hbos/inventory/entry",
            "/hbos/inventory/pick",
            "/hbos/inventory/reconcile",
            "/hbos/inventory/batch",
            "/hbos/inventory/entry/MAT-STE-2026-00026",
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

    def test_every_registered_native_route_has_a_portal_page(self):
        """**凡后端放行、留在 SPA 内的路由，前端必须真有对应的页面。**

        ## 这条测试要挡的是什么

        2026-09-25 发现「批次」与「库存余额」两页**早就做好了**，但
        `inventoryNav.ts` 里仍写着 `implemented: false`——**页面在，入口被
        「尚未实现」页挡住**。用户点不到已经做完的功能。

        根因是**同一件事写在两处、改一处忘了另一处**（后端路由 + 前端导航）。
        这里把「两边必须对得上」变成断言。

        ## 为什么从 router 文件读、不手写路径

        手写路径列表的话，「路由改了而测试没改」会**假通过**——测试绿着，
        实际已经漂了。从 `router/index.ts` 读，它才是前端路由的 Authority。

        ## 覆盖不到的

        只做**结构性**检查（路由存在）。导航项是否把 `implemented` 写对、
        `stablePath` 是否指向这些路由，属于 `inventoryNav.ts` 自身的一致性，
        由前端类型与运行时暴露——这里不假装覆盖。
        """
        router_file = (
            ROOT.parents[1]
            / "frontend"
            / "hbos-portal-web"
            / "src"
            / "router"
            / "index.ts"
        )
        self.assertTrue(router_file.exists(), f"找不到 {router_file}")

        source = router_file.read_text(encoding="utf-8")
        # 抠出 `path: 'xxx'`（只取库存那一段之后的，避免把 Portal/LIMS 的算进来）
        inv_start = source.index("path: '/hbos/inventory'")
        inv_part = source[inv_start:]
        rel_paths = re.findall(r"path:\s*'([^']*)'", inv_part)

        # 拼成绝对路径：'' → /hbos/inventory；'batch' → /hbos/inventory/batch
        absolute = set()
        for rel in rel_paths:
            if rel.startswith("/"):
                absolute.add(rel)
                continue
            absolute.add("/hbos/inventory" + ("/" + rel if rel else ""))

        # 每个静态段（去掉 :param）都该能被后端放行
        checked = 0
        for path in sorted(absolute):
            static = re.sub(r"/:[^/]+", "", path)
            if ":" in path or not static:
                continue  # 带参数的由已有的用例覆盖；根路径也已有用例
            with self.subTest(path=static):
                resolved = resolve_stable_route(static)
                self.assertFalse(
                    resolved.startswith("/app/"),
                    f"路由 {static} 在前端已注册，但后端把它解析去了 Desk（{resolved}）",
                )
                checked += 1
        self.assertGreater(checked, 0, "没扫到任何静态路由，测试失效")

    def test_bare_document_prefix_is_rejected(self):
        """`/draft/` 这种没有单号的半截路径不算已注册——否则前端会拿到空单号。

        报表的 `/report/<id>` 同理。

        注意 `/hbos/inventory/item` 与 `/hbos/inventory/warehouse`（**无参**）是
        合法的**主从页入口**，与 `/batch` 同构——进来先给列表/树，选中后才带代码。
        它们曾被误列为「半截路径」而拒绝，导致这两页的入口在走
        `openBusinessRoute` 时全部 `CONTRACT_MISMATCH`。见
        `test_every_nav_entry_resolves_to_itself`。
        """
        for path in (
            "/hbos/inventory/draft",
            "/hbos/inventory/draft/",
            "/hbos/inventory/report",
            "/hbos/inventory/report/",
            "/hbos/inventory/pending/x",
            "/hbos/inventory/entry/",
            "/hbos/inventory/pick/",
            "/hbos/inventory/reconcile/",
            "/hbos/inventory/item/",
            "/hbos/inventory/warehouse/",
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    resolve_stable_route(path)

    def test_master_landing_paths_resolve_to_themselves(self):
        """主数据三页的**无参入口**必须解析到自身（留在 SPA），与 `/batch` 一致。"""
        for path in (
            "/hbos/inventory/batch",
            "/hbos/inventory/item",
            "/hbos/inventory/warehouse",
        ):
            with self.subTest(path=path):
                self.assertEqual(path, resolve_stable_route(path))

    def test_every_nav_entry_resolves_to_itself(self):
        """**导航里 `implemented: true` 的每个入口，后端都必须放行。**

        从 `inventoryNav.ts` 读（那是真正生成链接的地方），不手写路径——
        手写的话「导航改了而测试没改」会假通过。

        这条挡的正是 2026-09-28 实测到的那类缺陷：侧边栏点得动（直接跳 SPA
        路由，不经后端），但凡是走 `openBusinessRoute` 的入口
        （Portal 首页 / 应用中心 / 命令面板 / 我的工作 / 概览页）都会被后端拒。
        「页面在、入口被挡」——同一类问题在本项目已出现过两次。
        """
        nav_file = (
            ROOT.parents[1]
            / "frontend"
            / "hbos-portal-web"
            / "src"
            / "data"
            / "inventoryNav.ts"
        )
        self.assertTrue(nav_file.exists(), f"找不到 {nav_file}")
        source = nav_file.read_text(encoding="utf-8")

        # 换算常量引用（两个都在同文件里定义）
        master = dict(
            re.findall(
                r"(\w+):\s*'([^']*)'",
                re.search(
                    r"export const INVENTORY_MASTER_PATHS\s*=\s*\{([^}]*)\}", source
                ).group(1),
            )
        )
        source = re.sub(
            r"INVENTORY_MASTER_PATHS\.(\w+)",
            lambda m: f"'{master[m.group(1)]}'",
            source,
        )
        for const_name, pattern in (
            ("INVENTORY_OVERVIEW_PATH", r"export const INVENTORY_OVERVIEW_PATH\s*=\s*'([^']*)'"),
        ):
            found = re.search(pattern, source)
            if found:
                source = source.replace(const_name, f"'{found.group(1)}'")

        # 逐对象取 (implemented, stablePath)
        entries = []
        entry = None
        for line in source.splitlines():
            stripped = line.strip()
            if re.match(r"id:\s*'[^']+',", stripped):
                if entry and entry.get("implemented") is not None:
                    entries.append(entry)
                entry = {"implemented": None, "path": ""}
                continue
            if entry is None:
                continue
            matched_impl = re.match(r"implemented:\s*(true|false),", stripped)
            if matched_impl:
                entry["implemented"] = matched_impl.group(1) == "true"
            matched_path = re.match(r"stablePath:\s*(.+?),?\s*$", stripped)
            if matched_path and not entry["path"]:
                entry["path"] = (
                    matched_path.group(1).strip().rstrip(",").strip().strip("'").strip('"')
                )
        if entry and entry.get("implemented") is not None:
            entries.append(entry)

        self.assertGreater(len(entries), 5, "没解析出导航条目，测试失效")

        checked = 0
        for item in entries:
            if not item["implemented"] or not item["path"]:
                continue
            with self.subTest(path=item["path"]):
                self.assertEqual(
                    item["path"],
                    resolve_stable_route(item["path"]),
                    f"导航里已实现的入口 {item['path']} 后端不放行——"
                    "侧边栏点得动，但走 openBusinessRoute 的入口会被拒",
                )
                checked += 1
        self.assertGreater(checked, 5, "已实现的入口扫得太少，测试失效")

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


class InventoryNavEntryTypeContractTest(unittest.TestCase):
    """侧边栏的下一级菜单（库存单据 → 物料入库 / 领用出库 / 移库）。

    这一层有两个**重复的事实**，必然漂移，所以要拿测试钉住：

    1. `inventoryNav.ts` 的 `children[].entryType` 写的是前端自己的类型键
       （`receipt` / `issue` / `transfer`）；
    2. `inventoryEntry.ts` 的 `ENTRY_TYPES[].key` 才是页面真正认的值。

    键写错**不会报错**——页面查不到就静默回落到第一个类型（物料入库）。
    于是点「移库」跳过去、停在「物料入库」，看起来只是「没生效」，很难查。
    2026-09-28 实测点过三种，键值全部对上。
    """

    NAV = (
        ROOT.parents[1] / "frontend" / "hbos-portal-web" / "src" / "data" / "inventoryNav.ts"
    )
    ENTRY = (
        ROOT.parents[1]
        / "frontend"
        / "hbos-portal-web"
        / "src"
        / "services"
        / "inventoryEntry.ts"
    )

    def test_child_entry_types_exist_in_entry_types(self):
        nav = self.NAV.read_text(encoding="utf-8")
        entry = self.ENTRY.read_text(encoding="utf-8")

        declared = set(re.findall(r"^\s*key:\s*'([^']+)',", entry, re.M))
        self.assertGreaterEqual(len(declared), 3, "没解析出 ENTRY_TYPES 的 key，测试失效")

        used = re.findall(r"entryType:\s*'([^']+)'", nav)
        self.assertEqual(
            ["receipt", "issue", "transfer"],
            used,
            "侧边栏下一级应恰好是入库 / 领用出库 / 移库三种",
        )
        for key in used:
            with self.subTest(entryType=key):
                self.assertIn(
                    key,
                    declared,
                    f"导航里的 entryType={key!r} 在 ENTRY_TYPES 里不存在——"
                    "页面会静默回落到第一个类型",
                )

    def test_child_paths_carry_the_type_query(self):
        """子项的 stablePath 必须与父项**同路径**、只靠 `?type=` 区分。

        否则就不是「同一个页面的几种形态」，而是另一条路由——那需要单独的后端放行，
        且当前没有对应的页面组件。
        """
        nav = self.NAV.read_text(encoding="utf-8")
        pairs = re.findall(r"stablePath:\s*'([^']*\?type=[^']+)'", nav)
        self.assertEqual(3, len(pairs), "应有三个带 ?type= 的子项路径")
        for path in pairs:
            with self.subTest(path=path):
                base, _, query = path.partition("?")
                self.assertEqual("/hbos/inventory/entry", base)
                self.assertRegex(query, r"^type=(receipt|issue|transfer)$")
                # 查询串不参与后端路由解析——解析的是 base，必须仍然放行
                self.assertEqual(base, resolve_stable_route(base))


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
