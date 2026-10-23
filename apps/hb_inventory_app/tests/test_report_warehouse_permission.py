from __future__ import annotations

"""四张库存报表的货位可见范围契约测试。

## 为什么有这份测试

四张报表都用 raw SQL 查 `Serial and Batch Entry`，而 **raw SQL 不走 Frappe 的
权限过滤**。修法是把货位范围与 `frappe.get_list("Warehouse")` 的结果求交。
这份测试钉住三件事：

1. **未指定货位时只返回可见货位**，不是全部 —— 这是跨仓读取的修复点；
2. 请求**不可见**的货位 → 明确抛错，**不静默返回空**（空结果与「这里没有库存」
   无法区分，会把越权失败伪装成正常空结果）；
3. 「含下级」展开后**仍与可见范围求交** —— 下层不可见的货位不得混进来。

后半部分是一组静态断言：**四张报表都必须走这个入口**，防止将来新增第五张报表
时又回到裸 SQL。

## 为什么用存根而不是真 site

CI 的 inventory 门禁跑的是纯 unittest（无 site），真 site 只用于运行态验收。
用最小 frappe 存根把 `get_list` / `throw` / `db.sql` 换成受控实现，
就能在无数据库环境下把「可见范围」这件事测透 —— 权限过滤本身由 Frappe 负责，
本测试只验证**报表是否正确地用了它**。
"""

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
REPORT_DIR = ROOT / "hb_inventory_app" / "hbos_inventory" / "report"

#: 用户**可见**的叶子货位（仓库 A、仓库 B）
LEAF_A = "16-03-221 - HB"
LEAF_B = "16-03-222 - HB"
LEAF_READABLE = [LEAF_A, LEAF_B]

#: 用户**不可见**的叶子货位（仓库 C）
LEAF_HIDDEN = "16-03-999 - HB"

#: 一棵「层」树：层本身是分组节点，后代里混着一个不可见货位
TREE = {
    "第一层 - HB": ["第一层 - HB", LEAF_A, LEAF_B, LEAF_HIDDEN],
}


class _PermissionError(Exception):
    pass


def _install_frappe_stub(readable_leaf):
    """装一个最小 frappe 存根；`get_list` 只返回它该看到的那部分。"""
    thrown = []

    def _get_list(doctype, filters=None, fields=None, pluck=None,
                  order_by=None, limit_page_length=None, **kwargs):
        filters = filters or {}
        # 叶子 + 启用 → 可见叶子集合（User Permission 已由真实 Frappe 施加）
        if "is_group" in filters:
            return list(readable_leaf)
        # 能不能读到这个具体货位（含分组节点）
        name = filters.get("name")
        if name is not None:
            return [name] if (name in readable_leaf or name in TREE) else []
        return []

    def _throw(message, *args, **kwargs):
        thrown.append(str(message))
        exc = args[0] if args else _PermissionError
        raise exc(str(message))

    def _sql(query, params=None, pluck=False, **kwargs):
        return list(TREE.get((params or {}).get("root"), []))

    frappe = types.SimpleNamespace(
        PermissionError=_PermissionError,
        ValidationError=Exception,
        throw=_throw,
        get_list=_get_list,
        db=types.SimpleNamespace(sql=_sql, get_all=lambda *a, **k: []),
        _=lambda s: s,
        session=types.SimpleNamespace(user="wh@example.com"),
    )
    frappe._thrown = thrown
    sys.modules["frappe"] = frappe
    # 每次换存根后重新求值该模块，避免读到上一个场景的 frappe
    sys.modules.pop("hb_inventory_app.hbos_inventory.warehouse_scope", None)
    return frappe


class WarehouseScopeTest(unittest.TestCase):
    """`warehouse_scope.resolve_scope` —— 权限正反例。"""

    def setUp(self):
        self.frappe = _install_frappe_stub(LEAF_READABLE)

    def _scope(self, filters):
        from hb_inventory_app.hbos_inventory.warehouse_scope import resolve_scope

        return resolve_scope(filters)

    # ---- 核心修复：默认即受限 ----

    def test_no_filter_restricts_to_visible_not_all(self):
        """未指定货位 → 只给可见货位。绝不能是「全部」。"""
        scope = self._scope({})
        self.assertEqual(LEAF_READABLE, scope)
        self.assertNotIn(LEAF_HIDDEN, scope)

    def test_empty_filters_same_as_missing(self):
        self.assertEqual(LEAF_READABLE, self._scope(None))

    # ---- 正例：请求自己有权看的仓库 A ----

    def test_request_visible_warehouse_sees_it(self):
        self.assertEqual([LEAF_A], self._scope({"warehouse": LEAF_A}))

    def test_request_visible_warehouse_b_sees_it(self):
        self.assertEqual([LEAF_B], self._scope({"warehouse": LEAF_B}))

    # ---- 反例：请求自己无权看的仓库 C ----

    def test_request_hidden_warehouse_is_rejected(self):
        """不可见的货位必须**明确拒绝**，不能静默返回空。"""
        with self.assertRaises(_PermissionError):
            self._scope({"warehouse": LEAF_HIDDEN})
        self.assertTrue(self.frappe._thrown, "应当抛出一条可读的拒绝原因")

    # ---- 含下级：展开后仍求交 ----

    def test_children_expansion_excludes_hidden_leaves(self):
        scope = self._scope({"warehouse": "第一层 - HB", "include_children": 1})
        self.assertEqual(LEAF_READABLE, scope)
        self.assertNotIn(LEAF_HIDDEN, scope)
        # 分组节点本身不是叶子，不该出现在 SQL 的 in (...) 里
        self.assertNotIn("第一层 - HB", scope)

    def test_group_without_children_visible_but_no_leaf_yields_empty(self):
        """能读到「层」节点但没有可见叶子 → 空集合，而不是报错。"""
        _install_frappe_stub([])
        self.assertEqual([], self._scope({"warehouse": "第一层 - HB", "include_children": 1}))

    # ---- 无任何可见货位 ----

    def test_no_visible_warehouse_yields_empty_scope(self):
        _install_frappe_stub([])
        self.assertEqual([], self._scope({}))


class ReportsUseSharedScopeTest(unittest.TestCase):
    """静态断言：四张报表都必须走共享入口，不得回退到裸 SQL 拼用户输入。"""

    REPORTS = ("货位明细表", "按批号查货位", "效期预警", "库级盘点三对账")

    def _source(self, name: str) -> str:
        return (REPORT_DIR / name / f"{name}.py").read_text(encoding="utf-8")

    def test_every_report_resolves_scope_before_sql(self):
        for name in self.REPORTS:
            src = self._source(name)
            with self.subTest(report=name):
                self.assertIn(
                    "from hb_inventory_app.hbos_inventory.warehouse_scope import resolve_scope",
                    src,
                )
                self.assertIn("scope = resolve_scope(filters)", src)
                # 空范围必须直接返回，不得继续拼 `in ()`
                self.assertIn("if not scope:", src)

    def test_no_report_takes_warehouse_filter_raw(self):
        """旧写法直接把用户传的货位拼进 SQL —— 那正是跨仓读取的成因。"""
        for name in self.REPORTS:
            src = self._source(name)
            with self.subTest(report=name):
                self.assertNotIn("sbe.warehouse = %(warehouse)s", src)

    def test_report_list_matches_actual_directories(self):
        """报表清单若与实际目录脱节，上面两条断言会静默漏测。"""
        actual = {
            p.name for p in REPORT_DIR.iterdir()
            if p.is_dir() and (p / f"{p.name}.py").exists()
        }
        self.assertEqual(set(self.REPORTS), actual)


if __name__ == "__main__":
    unittest.main()
