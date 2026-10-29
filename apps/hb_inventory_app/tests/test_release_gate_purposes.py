from __future__ import annotations

"""出库放行门禁的 purpose 分类契约测试。

## 为什么有这份测试

`release_gate` 靠「purpose 是不是出库方向」决定要不要拦。这个判断原先**只认
`Material Issue`**，于是 **`Send to Subcontractor`（发外协）—— 我方批次明明
离开了公司 —— 反而不过放行门禁**，未放行批次可以借着发外协出去。

反向也要钉住：`Material Transfer`（库位 / 货位间移库，**含移入不合格品库、
退回产品区这类「正常内部隔离移库」**）**必须不被拦**，否则仓管挪不动货。

## 覆盖必须完整

ERPNext 的 purpose 是闭集（`erpnext...stock_entry.validate_purpose`）。
这里把**那份闭集字面量**抄下来做断言——抄的是上游事实，不是被测对象，
所以「上游加了 purpose 而本模块没分类」会在这里红，逼人做决定。

## 为什么用存根

`is_outward_stock_entry` 只在未分类时报错，其余是纯判断。存根一个 frappe 即可，
无需 site。
"""

import sys
import types
import unittest

#: ERPNext `Stock Entry.purpose` 的全部取值（抄自上游 `validate_purpose`，
#: 2026-10-12 对照 `erpnext/stock/doctype/stock_entry/stock_entry.py`）。
ERPNEXT_PURPOSES = (
    "Material Issue",
    "Material Receipt",
    "Material Transfer",
    "Material Transfer for Manufacture",
    "Manufacture",
    "Repack",
    "Send to Subcontractor",
    "Material Consumption for Manufacture",
    "Disassemble",
    "Receive from Customer",
    "Return Raw Material to Customer",
    "Subcontracting Delivery",
    "Subcontracting Return",
)


class _Throw(Exception):
    pass


def _install_frappe_stub():
    def _throw(message, *args, **kwargs):
        raise _Throw(str(message))

    frappe = types.SimpleNamespace(throw=_throw, _=lambda s: s)
    sys.modules["frappe"] = frappe
    sys.modules.pop("hb_inventory_app.hbos_inventory.release_gate", None)
    return frappe


def _gate():
    from hb_inventory_app.hbos_inventory import release_gate

    return release_gate


class PurposeClassificationTest(unittest.TestCase):
    def setUp(self):
        _install_frappe_stub()

    # ---- 覆盖完整性 ----

    def test_classification_covers_every_erpnext_purpose(self):
        g = _gate()
        classified = set(g.OUTWARD_STOCK_ENTRY_PURPOSES) | set(g.INTERNAL_STOCK_ENTRY_PURPOSES)
        missing = set(ERPNEXT_PURPOSES) - classified
        self.assertEqual(
            set(),
            missing,
            f"以下 purpose 未分类：{sorted(missing)}；"
            f"ERPNext 新增用途时必须在此决定拦或不拦，不能静默漏拦",
        )

    def test_no_unknown_purpose_is_classified(self):
        """反向：分类里不许出现 ERPNext 没有的取值（拼错也测得出）。"""
        g = _gate()
        classified = set(g.OUTWARD_STOCK_ENTRY_PURPOSES) | set(g.INTERNAL_STOCK_ENTRY_PURPOSES)
        self.assertEqual(set(), classified - set(ERPNEXT_PURPOSES))

    def test_the_two_sets_are_disjoint(self):
        g = _gate()
        self.assertEqual(
            set(),
            set(g.OUTWARD_STOCK_ENTRY_PURPOSES) & set(g.INTERNAL_STOCK_ENTRY_PURPOSES),
        )

    # ---- 正例：发外协必须被拦 ----

    def test_send_to_subcontractor_is_outward(self):
        """发外协：原辅料发到受托方，我方批次离开公司 → 必须过放行门禁。"""
        self.assertTrue(_gate().is_outward_stock_entry({"purpose": "Send to Subcontractor"}))

    def test_material_issue_is_outward(self):
        self.assertTrue(_gate().is_outward_stock_entry({"purpose": "Material Issue"}))

    # ---- 反例：内部隔离移库不得被拦 ----

    def test_material_transfer_is_internal(self):
        """库位/货位间移库——含移入不合格品库、退回产品区——不得被拦。"""
        self.assertFalse(_gate().is_outward_stock_entry({"purpose": "Material Transfer"}))

    def test_material_receipt_is_internal(self):
        self.assertFalse(_gate().is_outward_stock_entry({"purpose": "Material Receipt"}))

    def test_manufacture_and_repack_are_internal(self):
        for purpose in ("Manufacture", "Repack", "Disassemble",
                        "Material Transfer for Manufacture"):
            with self.subTest(purpose=purpose):
                self.assertFalse(_gate().is_outward_stock_entry({"purpose": purpose}))

    # ---- 未分类 → 报错，不静默放过 ----

    def test_unclassified_purpose_raises(self):
        with self.assertRaises(_Throw):
            _gate().is_outward_stock_entry({"purpose": "Some Future Purpose"})

    def test_empty_purpose_raises(self):
        with self.assertRaises(_Throw):
            _gate().is_outward_stock_entry({"purpose": ""})


class OutwardRowsTest(unittest.TestCase):
    """`_outward_rows` 对不同单据的取行范围。"""

    def setUp(self):
        _install_frappe_stub()

    def test_delivery_note_rows_are_all_outward(self):
        doc = types.SimpleNamespace(
            doctype="Delivery Note", items=[{"batch_no": "B1"}], get=lambda k, d=None: None
        )
        self.assertEqual([{"batch_no": "B1"}], _gate()._outward_rows(doc))

    def test_delivery_note_return_is_not_gated(self):
        doc = types.SimpleNamespace(
            doctype="Delivery Note", items=[{"batch_no": "B1"}],
            get=lambda k, d=None: 1 if k == "is_return" else None,
        )
        self.assertEqual([], _gate()._outward_rows(doc))

    def test_subcontract_row_without_source_warehouse_is_skipped(self):
        """`Send to Subcontractor` 但行上没有来源仓库 → 没有我方批次可查。"""
        row_with = {"batch_no": "B1", "s_warehouse": "16-03-221 - HB"}
        row_without = {"batch_no": "B2"}
        doc = types.SimpleNamespace(
            doctype="Stock Entry", purpose="Send to Subcontractor",
            items=[row_with, row_without], get=lambda k, d=None: "Send to Subcontractor",
        )
        self.assertEqual([row_with], _gate()._outward_rows(doc))

    def test_internal_purpose_yields_no_rows(self):
        doc = types.SimpleNamespace(
            doctype="Stock Entry", purpose="Material Transfer",
            items=[{"batch_no": "B1", "s_warehouse": "16-03-221 - HB"}],
            get=lambda k, d=None: "Material Transfer",
        )
        self.assertEqual([], _gate()._outward_rows(doc))


if __name__ == "__main__":
    unittest.main()
