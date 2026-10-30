"""货位扫码页的服务端逻辑 —— 纯静态/纯函数断言，不需要 site。

## 为什么值得单测

这个页面有两条**看起来能用、其实会给出错误业务事实**的老问题：

1. **跨 UOM 求和**：同一货位可能同时放 kg、瓶、袋，`sum(qty)` 得到的数字
   没有业务意义，模板还把它硬编码成 `kg` 印在页面上。
2. **前缀静默取第一个**：`startswith` 命中多个货位时按 `lft` 顺序取一个，
   操作员看到的是**另一个货位**的库存，而且没有任何提示。

另外，`_plausible` 之外的正确性靠「不合格就明确报错」：命中多个必须报
「候选不唯一」，不能自动选。

用 `frappe` 的替身模块来跑纯函数 —— 本文件不建 Site、不连数据库。
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _install_frappe_stub():
    """最小 frappe 替身：只提供 import 期与纯函数用到的属性。"""
    if "frappe" in sys.modules and getattr(sys.modules["frappe"], "_hbos_stub", False):
        return sys.modules["frappe"]

    frappe = types.ModuleType("frappe")
    frappe._hbos_stub = True
    frappe.form_dict = {}
    frappe.local = types.SimpleNamespace(request=types.SimpleNamespace(path="/hbos-bin"))
    frappe.session = types.SimpleNamespace(user="Administrator")
    frappe.Redirect = type("Redirect", (Exception,), {})

    utils = types.ModuleType("frappe.utils")
    utils.flt = lambda v: float(v or 0)
    utils.now = lambda: "2026-10-27 12:00:00"
    frappe.utils = utils

    db = types.SimpleNamespace(sql=lambda *a, **kw: [], get_value=lambda *a, **kw: None)
    frappe.db = db
    frappe.get_doc = lambda *a, **kw: None

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    return frappe


class GroupByUomTest(unittest.TestCase):
    def setUp(self):
        _install_frappe_stub()
        from hb_inventory_app.www.hbos_bin import _group_by_uom

        self.group = _group_by_uom

    def test_separates_units(self):
        rows = [
            {"uom": "kg", "qty": 10.0},
            {"uom": "kg", "qty": 2.5},
            {"uom": "瓶", "qty": 3.0},
        ]
        result = self.group(rows)
        self.assertEqual(
            [{"uom": "kg", "qty": 12.5}, {"uom": "瓶", "qty": 3.0}],
            result,
        )

    def test_missing_uom_gets_own_bucket(self):
        """没有单位的行不能混进 kg —— 那是猜。"""
        result = self.group([{"uom": None, "qty": 1.0}, {"uom": "kg", "qty": 2.0}])
        self.assertEqual(2, len(result))

    def test_empty_rows(self):
        self.assertEqual([], self.group([]))


class ResolveWarehouseAmbiguityTest(unittest.TestCase):
    """前缀命中多个货位时必须报「候选不唯一」，不能取第一个。"""

    def setUp(self):
        frappe = _install_frappe_stub()
        self.frappe = frappe

    def _run_with(self, warehouses):
        frappe = self.frappe
        # 真实 frappe 返回 `frappe._dict`（属性访问），不是普通 dict
        rows = [types.SimpleNamespace(**w) for w in warehouses]
        frappe.db = types.SimpleNamespace(
            sql=lambda sql, params=None, as_dict=False, pluck=False: (
                rows if "from `tabWarehouse`" in sql else []
            ),
            get_value=lambda *a, **kw: None,
        )
        frappe.get_doc = lambda doctype, name: types.SimpleNamespace(name=name)

        for mod in list(sys.modules):
            if mod.startswith("hb_inventory_app.www.hbos_bin"):
                del sys.modules[mod]
        from hb_inventory_app.www.hbos_bin import _Ambiguous, _resolve_warehouse

        self._Ambiguous = _Ambiguous
        return _resolve_warehouse

    def test_multiple_prefix_hits_report_candidates(self):
        rows = [
            {"name": "3904 六车间 - HB", "is_group": 0, "lft": 1, "rgt": 2},
            {"name": "3905 六车间 - HB", "is_group": 0, "lft": 3, "rgt": 4},
        ]
        resolve = self._run_with(rows)
        result, doc, is_group = resolve("390")
        self.assertIsInstance(result, self._Ambiguous)
        self.assertEqual(["3904 六车间", "3905 六车间"], result.candidates)
        self.assertIsNone(doc)
        self.assertFalse(is_group)

    def test_single_prefix_hit_still_resolves(self):
        rows = [{"name": "3904 六车间 - HB", "is_group": 0, "lft": 1, "rgt": 2}]
        resolve = self._run_with(rows)
        result, doc, is_group = resolve("390")
        self.assertEqual(["3904 六车间 - HB"], result)
        self.assertFalse(is_group)

    def test_exact_short_code_wins_over_prefix(self):
        """短码**完全相等**时优先，不该因为另一个货位也以它为前缀就报歧义。"""
        rows = [
            {"name": "3904 - HB", "is_group": 0, "lft": 1, "rgt": 2},
            {"name": "39041 - HB", "is_group": 0, "lft": 3, "rgt": 4},
        ]
        resolve = self._run_with(rows)
        result, _doc, _is_group = resolve("3904")
        self.assertEqual(["3904 - HB"], result)

    def test_shared_prefix_without_exact_match_is_ambiguous(self):
        """`3904 六车间` 与 `3904A` 共享前缀、都不等于 `3904` → 必须报歧义。"""
        rows = [
            {"name": "3904 六车间 - HB", "is_group": 0, "lft": 1, "rgt": 2},
            {"name": "3904A - HB", "is_group": 0, "lft": 3, "rgt": 4},
        ]
        resolve = self._run_with(rows)
        result, _doc, _is_group = resolve("3904")
        self.assertIsInstance(result, self._Ambiguous)

    def test_duplicate_short_code_across_companies_is_ambiguous(self):
        """不同公司可能有同名货位（短码相同、公司后缀不同）——同样必须报歧义。

        早先「短码精确匹配」直接取第一个，扫码人可能看到**另一个公司**的库存。
        """
        rows = [
            {"name": "3904 六车间 - HB", "is_group": 0, "lft": 1, "rgt": 2},
            {"name": "3904 六车间 - HB2", "is_group": 0, "lft": 3, "rgt": 4},
        ]
        resolve = self._run_with(rows)
        result, _doc, _is_group = resolve("3904 六车间")
        self.assertIsInstance(result, self._Ambiguous)
        self.assertEqual(2, len(result.candidates))


class PackagingBatchLoadTest(unittest.TestCase):
    """包装明细**一次批量取**，不能在循环里逐批查（N+1）。

    早先每行调 `hbos_packaging_spec()` + `hbos_packaging_count()`，
    两个函数各查一次子表 —— 一屏 50 个批次就是 100 次查询。
    """

    def setUp(self):
        self.frappe = _install_frappe_stub()
        self.calls: list = []

        def get_all(doctype, **kwargs):
            self.calls.append(kwargs.get("filters"))
            # 真实 frappe 返回 `frappe._dict`（属性访问），不是普通 dict
            return [
                types.SimpleNamespace(parent="B1", container_type="件", unit_weight=5.0, count=9, is_tail=0),
                types.SimpleNamespace(parent="B1", container_type="听", unit_weight=0.03, count=4, is_tail=0),
                types.SimpleNamespace(parent="B2", container_type="瓶", unit_weight=0, count=10, is_tail=0),
            ]

        self.frappe.get_all = get_all
        for mod in list(sys.modules):
            if mod.startswith("hb_inventory_app.hbos_inventory.print_utils"):
                del sys.modules[mod]
        from hb_inventory_app.hbos_inventory import print_utils

        self.pu = print_utils

    def test_single_query_for_many_batches(self):
        mapping = self.pu.load_packaging_map(["B1", "B2", "B1"])
        self.assertEqual(1, len(self.calls), f"查了 {len(self.calls)} 次，应为 1 次")
        self.assertEqual(["in", ["B1", "B2"]], self.calls[0]["parent"])

    def test_format_helpers_match_documented_forms(self):
        mapping = self.pu.load_packaging_map(["B1"])
        self.assertEqual("5.00kg*9件  0.03kg*4听", self.pu.format_packaging_spec(mapping["B1"]))
        self.assertEqual("9件4听", self.pu.format_packaging_count(mapping["B1"]))

    def test_count_only_row_still_supported(self):
        mapping = self.pu.load_packaging_map(["B2"])
        self.assertEqual("10瓶", self.pu.format_packaging_spec(mapping["B2"]))
        self.assertEqual("10瓶", self.pu.format_packaging_count(mapping["B2"]))

    def test_missing_batch_returns_blank(self):
        self.assertEqual(self.pu.BLANK, self.pu.format_packaging_spec(None))
        self.assertEqual(self.pu.BLANK, self.pu.format_packaging_count(None))

    def test_bin_page_does_not_loop_query(self):
        src = (ROOT / "hb_inventory_app" / "www" / "hbos_bin.py").read_text(encoding="utf-8")
        self.assertIn("load_packaging_map", src)
        self.assertNotIn("hbos_packaging_spec(r.batch_no)", src)


class TemplateNoHardcodedKgTest(unittest.TestCase):
    def test_template_sums_per_uom(self):
        html = (ROOT / "hb_inventory_app" / "www" / "hbos_bin.html").read_text(encoding="utf-8")
        self.assertIn("uom_totals", html)
        # 早先是 `合计 {{ "%.3f"|format(total_qty) }} kg` —— 跨单位相加并写死 kg
        self.assertNotRegex(html, r'format\(total_qty\)\s*\}\}\s*kg')


if __name__ == "__main__":
    unittest.main()
