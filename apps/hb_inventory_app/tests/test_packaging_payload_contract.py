"""包装构成校验 —— 允许「只有件数、没有单件重量」。

## 为什么这条要专门钉住

`HBOS Packaging Detail.unit_weight` 在 DocType 里**不是必填**，
`print_utils.hbos_packaging_spec()` 也明确支持这种形态：

    if r.unit_weight: f"{w}kg*{n}{type}"     # 有重量
    else:             f"{n}{type}"           # 只有件数 → "10瓶"

也就是说「10 瓶，重量没维护」是**合法的真实数据**。曾经有一版接口强制
`unit_weight > 0`，直接把这批合法包装判死 —— 与本文件下方用例冲突。

现在只拦**负数与非有限值**：负重量会印到货位卡上，是真的错误。
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _install_frappe_stub():
    """最小 frappe 替身。

    ⚠️ 其他测试文件也会装替身，且各自装的属性不同（例如 `test_bin_page_contract`
    不需要 `whitelist`）。所以这里**不早退**，而是把缺的属性补齐 —— 早先
    `if _hbos_stub: return` 会让本文件在全量 discover 时拿到一个缺
    `whitelist` 的替身，11 个用例集体 import 失败。
    """
    frappe = sys.modules.get("frappe")
    if frappe is None:
        frappe = types.ModuleType("frappe")
        sys.modules["frappe"] = frappe
    frappe._hbos_stub = True

    class PermissionError_(Exception):
        pass

    frappe.PermissionError = getattr(frappe, "PermissionError", PermissionError_)
    frappe.ValidationError = getattr(
        frappe, "ValidationError", type("ValidationError", (Exception,), {})
    )

    def _throw(msg, exc=None, title=None):
        raise (exc or frappe.ValidationError)(str(msg))

    frappe.throw = _throw
    frappe._ = lambda s: s
    frappe.whitelist = lambda *a, **kw: (lambda fn: fn)
    frappe.parse_json = __import__("json").loads
    frappe.get_meta = lambda doctype: types.SimpleNamespace(
        get_field=lambda name: types.SimpleNamespace(
            options="件\n听\n瓶\n桶\n袋\n箱"
        )
    )

    utils = sys.modules.get("frappe.utils")
    if utils is None:
        utils = types.ModuleType("frappe.utils")
        sys.modules["frappe.utils"] = utils
    utils.cint = lambda v: int(v or 0)
    utils.flt = lambda v: float(v or 0)
    frappe.utils = utils

    return frappe


class ParsePackagingTest(unittest.TestCase):
    def setUp(self):
        _install_frappe_stub()
        # `api.py` 顶层 import `ocr_client`，后者依赖 `requests`（本机测试环境没装）。
        # 本用例只测 `_parse_packaging`，用替身挡掉这条无关依赖。
        ocr_stub = types.ModuleType("hb_inventory_app.hbos_inventory.ocr_client")
        ocr_stub.__dict__.update(
            {k: (lambda *a, **kw: None) for k in ("recognize", "health", "OcrUnavailable")}
        )
        ocr_stub.OcrUnavailable = type("OcrUnavailable", (Exception,), {})
        sys.modules.setdefault("hb_inventory_app.hbos_inventory.ocr_client", ocr_stub)
        for mod in list(sys.modules):
            if mod.startswith("hb_inventory_app.hbos_inventory.api") or mod == "hb_inventory_app.hbos_inventory.api":
                del sys.modules[mod]
        from hb_inventory_app.hbos_inventory.api import _parse_packaging

        self.parse = _parse_packaging

    def test_none_means_leave_untouched(self):
        self.assertIsNone(self.parse(None))

    def test_empty_list_means_clear(self):
        self.assertEqual([], self.parse([]))

    def test_count_only_without_weight_is_allowed(self):
        """只有件数、没有单件重量 —— 合法（打印会输出「10瓶」）。"""
        rows = self.parse([{"container_type": "瓶", "unit_weight": None, "count": 10}])
        self.assertEqual(1, len(rows))
        self.assertEqual(0, rows[0]["unit_weight"])
        self.assertEqual(10, rows[0]["count"])

    def test_zero_weight_is_allowed(self):
        rows = self.parse([{"container_type": "瓶", "unit_weight": 0, "count": 3}])
        self.assertEqual(0, rows[0]["unit_weight"])

    def test_negative_weight_is_rejected(self):
        with self.assertRaises(Exception):
            self.parse([{"container_type": "瓶", "unit_weight": -1, "count": 3}])

    def test_non_finite_weight_is_rejected(self):
        with self.assertRaises(Exception):
            self.parse([{"container_type": "瓶", "unit_weight": float("inf"), "count": 3}])

    def test_count_must_be_positive(self):
        with self.assertRaises(Exception):
            self.parse([{"container_type": "瓶", "unit_weight": 5, "count": 0}])

    def test_container_required_when_other_fields_present(self):
        with self.assertRaises(Exception):
            self.parse([{"container_type": "", "unit_weight": 5, "count": 3}])

    def test_blank_row_is_skipped(self):
        self.assertEqual([], self.parse([{"container_type": "", "unit_weight": None, "count": 0}]))

    def test_unknown_container_rejected(self):
        with self.assertRaises(Exception):
            self.parse([{"container_type": "托盘", "unit_weight": 1, "count": 1}])

    def test_json_string_input_is_accepted(self):
        rows = self.parse('[{"container_type": "瓶", "count": 2}]')
        self.assertEqual(1, len(rows))


class PrintUtilsCountOnlyTest(unittest.TestCase):
    def test_print_spec_supports_count_only(self):
        """打印逻辑必须仍然支持「只有件数」—— 这是上面允许它的依据。"""
        src = (
            ROOT / "hb_inventory_app" / "hbos_inventory" / "print_utils.py"
        ).read_text(encoding="utf-8")
        self.assertIn("if r.unit_weight:", src)
        self.assertIn('f"{r.count}{r.container_type}"', src)


if __name__ == "__main__":
    unittest.main()
