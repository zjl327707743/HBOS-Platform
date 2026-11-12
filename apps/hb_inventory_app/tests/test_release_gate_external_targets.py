"""Fast quality-gate regression tests; native posting evidence is separate.

A submitted native subcontract order identifies physical third-party custody even
when both warehouses belong to the same accounting company. An ordinary Material
Transfer must not bypass quality release for that destination. Internal movement
and returns remain possible without releasing a pending batch.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import types
import unittest
from unittest.mock import patch


class _QualityBlocked(Exception):
    pass


class _Row(dict):
    __getattr__ = dict.__getitem__


def _doc(rows, purpose="Material Transfer", **values):
    fields = {"doctype": "Stock Entry", "purpose": purpose, "company": "HBOS", **values}
    return types.SimpleNamespace(**fields, items=rows, get=fields.get)


def _row(batch="PENDING", source="Stores - HBOS", target="Job Worker - HBOS"):
    return _Row(batch_no=batch, s_warehouse=source, t_warehouse=target)


def _order(warehouse="Job Worker - HBOS", **values):
    return {
        "company": "HBOS", "docstatus": 1, "supplier_warehouse": warehouse,
        **values,
    }


def _quality(released):
    return types.SimpleNamespace(
        hbos_release_status="已放行" if released else "待检",
        hbos_release_date="2026-10-18" if released else None,
        hbos_certificate_no="COA-1" if released else "",
        hbos_certificate_file="/private/files/COA-1.pdf" if released else "",
        hbos_lims_reference="LIMS-1" if released else "",
        hbos_release_source="LIMS" if released else "",
    )


class ExternalTargetReleaseGateTest(unittest.TestCase):
    def setUp(self):
        self.orders = {"Subcontracting Order": [], "Purchase Order": []}
        self.order_queries = []
        self.batch_reads = []
        self.batches = {"PENDING": _quality(False), "RELEASED": _quality(True)}

        def get_all(doctype, *, filters, pluck):
            self.order_queries.append((doctype, filters, pluck))

            def matches(record):
                for key, expected in filters.items():
                    if isinstance(expected, list):
                        self.assertEqual("in", expected[0])
                        if record.get(key) not in expected[1]:
                            return False
                    elif record.get(key) != expected:
                        return False
                return True

            return [record.get(pluck) for record in self.orders[doctype] if matches(record)]

        def get_value(doctype, name, fields, *, as_dict):
            self.assertEqual("Batch", doctype)
            self.assertTrue(as_dict)
            self.batch_reads.append(name)
            return self.batches.get(name)

        def throw(message, **kwargs):
            raise _QualityBlocked(str(message))

        frappe = types.SimpleNamespace(
            _=lambda text: text, throw=throw, get_all=get_all,
            db=types.SimpleNamespace(get_value=get_value),
        )
        path = Path(__file__).resolve().parents[1] / "hb_inventory_app/hbos_inventory/release_gate.py"
        spec = importlib.util.spec_from_file_location("_external_target_release_gate", path)
        self.gate = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"frappe": frappe}):
            spec.loader.exec_module(self.gate)

    def test_same_company_registered_destination_blocks_pending_without_order_link(self):
        self.orders["Subcontracting Order"] = [_order()]
        # No Stock Entry supplier/subcontracting_order hint: native order facts
        # must identify the destination even when a caller omits these fields.
        with self.assertRaisesRegex(_QualityBlocked, "PENDING.*放行"):
            self.gate.validate_release(_doc([_row()]))
        self.assertEqual(["PENDING"], self.batch_reads)

    def test_released_batch_can_move_to_registered_supplier_warehouse(self):
        self.orders["Subcontracting Order"] = [_order()]
        self.gate.validate_release(_doc([_row("RELEASED")]))
        self.assertEqual(["RELEASED"], self.batch_reads)

    def test_internal_and_quarantine_transfers_allow_pending_batches(self):
        self.orders["Subcontracting Order"] = [_order()]
        rows = [_row(target="Finished Goods - HBOS"), _row(target="Quarantine - HBOS")]
        self.gate.validate_release(_doc(rows))
        self.assertEqual([], self.batch_reads)

    def test_return_from_supplier_to_internal_warehouse_allows_pending_batch(self):
        self.orders["Subcontracting Order"] = [_order()]
        self.gate.validate_release(_doc([
            _row(source="Job Worker - HBOS", target="Quarantine - HBOS"),
        ]))
        self.assertEqual([], self.batch_reads)

    def test_mixed_rows_only_require_release_for_external_destination(self):
        self.orders["Subcontracting Order"] = [_order()]
        self.gate.validate_release(_doc([
            _row("PENDING", target="Quarantine - HBOS"),
            _row("RELEASED"),
        ]))
        self.assertEqual(["RELEASED"], self.batch_reads)

    def test_pending_external_row_blocks_mixed_transfer(self):
        self.orders["Subcontracting Order"] = [_order()]
        with self.assertRaisesRegex(_QualityBlocked, "PENDING"):
            self.gate.validate_release(_doc([
                _row("RELEASED", target="Finished Goods - HBOS"),
                _row("PENDING"),
            ]))
        self.assertEqual(["PENDING"], self.batch_reads)

    def test_submitted_subcontracted_purchase_order_also_registers_destination(self):
        self.orders["Purchase Order"] = [_order(is_subcontracted=1)]
        with self.assertRaisesRegex(_QualityBlocked, "PENDING"):
            self.gate.validate_release(_doc([_row()]))

    def test_draft_cancelled_other_company_and_non_subcontract_orders_are_not_authority(self):
        self.orders["Subcontracting Order"] = [
            _order(docstatus=0), _order(docstatus=2), _order(company="Other Company"),
        ]
        self.orders["Purchase Order"] = [
            _order(is_subcontracted=0), _order(is_subcontracted=1, docstatus=0),
        ]
        self.gate.validate_release(_doc([_row()]))
        self.assertEqual([], self.batch_reads)

    def test_incomplete_lims_certificate_still_blocks_registered_destination(self):
        self.orders["Subcontracting Order"] = [_order()]
        self.batches["RELEASED"].hbos_certificate_file = ""
        with self.assertRaisesRegex(_QualityBlocked, "无合格证附件"):
            self.gate.validate_release(_doc([_row("RELEASED")]))

    def test_unknown_purpose_fails_before_any_registry_or_batch_query(self):
        with self.assertRaisesRegex(_QualityBlocked, "未分类"):
            self.gate.validate_release(_doc([_row()], purpose="Future Purpose"))
        self.assertEqual([], self.order_queries)
        self.assertEqual([], self.batch_reads)

    def test_registry_lookup_is_batched_for_one_hundred_rows(self):
        self.orders["Subcontracting Order"] = [_order()]
        self.gate.validate_release(_doc([_row("RELEASED") for _ in range(100)]))
        self.assertEqual(2, len(self.order_queries))
        for _, filters, _ in self.order_queries:
            self.assertEqual(["in", ["Job Worker - HBOS"]], filters["supplier_warehouse"])
        self.assertEqual(["RELEASED"], self.batch_reads)

    def test_row_without_source_is_left_for_native_stock_validation(self):
        self.orders["Subcontracting Order"] = [_order()]
        self.gate.validate_release(_doc([_row(source=None)]))
        self.assertEqual([], self.order_queries)
        self.assertEqual([], self.batch_reads)


if __name__ == "__main__":
    unittest.main()
