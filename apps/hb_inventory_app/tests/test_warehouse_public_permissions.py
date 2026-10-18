"""Exercise the scanner controller with the real shared warehouse-scope code.

The fake ORM models an A-only user and a parent containing A and hidden B.  SQL
returns rows for the parameters actually supplied by the controller, so a query
that accidentally includes B exposes its sentinel and fails these tests. Native
session / User Permission enforcement is covered separately on the CI site.
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1] / "hb_inventory_app"
BIN_SOURCE = ROOT / "www" / "hbos_bin.py"
SCOPE_SOURCE = ROOT / "hbos_inventory" / "warehouse_scope.py"
A = "R3-A Shelf - TEST"
B = "R3-B Shelf - TEST"
GROUP = "R3-Group - TEST"
DISABLED = "R3-Disabled - TEST"


class Row(dict):
    def __getattr__(self, key):
        return self.get(key)


class Denied(Exception):
    pass


class Redirect(Exception):
    pass


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WarehousePublicPermissionsTest(unittest.TestCase):
    def setUp(self):
        self.readable = {A, GROUP}
        self.document_readable = {A, GROUP}
        self.inventory_queries = []
        self.warehouse_queries = []
        self.warehouses = [
            Row(name=GROUP, is_group=1, disabled=0, lft=1, rgt=8),
            Row(name=A, is_group=0, disabled=0, lft=2, rgt=3),
            Row(name=B, is_group=0, disabled=0, lft=4, rgt=5),
            Row(name=DISABLED, is_group=0, disabled=1, lft=6, rgt=7),
        ]
        self.frappe = types.SimpleNamespace(
            session=types.SimpleNamespace(user="restricted@example.test"),
            form_dict={},
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(path="/hbos_bin"),
                flags=types.SimpleNamespace(),
            ),
            utils=types.SimpleNamespace(flt=lambda value: float(value or 0)),
            db=types.SimpleNamespace(sql=self.sql),
            get_list=self.get_list,
            get_doc=self.get_doc,
            PermissionError=Denied,
            Redirect=Redirect,
            throw=self.throw,
            _=lambda value: value,
        )
        packaging = types.SimpleNamespace(
            hbos_packaging_spec=lambda batch: "10.00kg*10件",
            hbos_packaging_count=lambda batch: "10件",
        )
        self.modules = patch.dict(sys.modules, {
            "frappe": self.frappe,
            "hb_inventory_app.hbos_inventory.print_utils": packaging,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        scope = load_source("scanner_scope", SCOPE_SOURCE)
        self.scope_modules = patch.dict(sys.modules, {
            "hb_inventory_app.hbos_inventory.warehouse_scope": scope,
        })
        self.scope_modules.start()
        self.addCleanup(self.scope_modules.stop)
        self.page = load_source("scanner_page", BIN_SOURCE)

    def throw(self, message, exc=Denied):
        raise exc(message)

    def get_list(self, doctype, filters=None, pluck=None, **kwargs):
        self.assertEqual("Warehouse", doctype)
        filters = filters or {}
        rows = [row for row in self.warehouses if row.name in self.readable]
        rows = [row for row in rows if all(row.get(key) == value for key, value in filters.items())]
        return [row[pluck] for row in rows] if pluck else rows

    def get_doc(self, doctype, name):
        self.assertEqual("Warehouse", doctype)

        def check_permission(ptype):
            self.assertEqual("read", ptype)
            if name not in self.document_readable:
                raise Denied("Warehouse denied")

        row = next(row for row in self.warehouses if row.name == name)
        return types.SimpleNamespace(**row, check_permission=check_permission)

    def sql(self, query, values=None, pluck=False, **kwargs):
        values = values or {}
        if "`tabWarehouse`" in query:
            self.warehouse_queries.append((query, values))
            if "root" in values:
                root = next(row for row in self.warehouses if row.name == values["root"])
                return [row.name for row in self.warehouses if root.lft <= row.lft <= root.rgt]
            if "lft" in values:  # the old unscoped group expansion
                return [row.name for row in self.warehouses
                        if not row.is_group and values["lft"] <= row.lft <= values["rgt"]]
            return self.warehouses
        self.assertIn("`tabSerial and Batch Entry`", query)
        requested = sorted(value for key, value in values.items() if key.startswith("wh_"))
        self.inventory_queries.append(requested)
        return [Row(
            warehouse=name, item_code=f"ITEM-{name}", item_name=f"Item {name}",
            batch_no=f"BATCH-{name}", qty=100 if name == A else 1337,
            uom="Kg", supplier=f"SUPPLIER-{name}", manufacturer=f"MANUFACTURER-{name}",
            manufacturing_date="2026-01-01", expiry_date="2027-01-01",
            release_status="待检", certificate_no="CERT-A", release_date="2026-01-02",
            source_type="外购", supplier_batch_no="SUPPLIER-BATCH-A", workshop="WORKSHOP-A",
            shelf_life_type="有效期",
        ) for name in requested]

    def scan(self, code):
        self.frappe.form_dict = {"bin": code}
        context = types.SimpleNamespace()
        self.page.get_context(context)
        return context

    def test_guest_redirects_before_any_warehouse_or_inventory_query(self):
        self.frappe.session.user = "Guest"
        with self.assertRaises(Redirect):
            self.scan(A)
        self.assertIn("/login?redirect-to=%2Fhbos_bin%3Fbin%3D", self.frappe.local.flags.redirect_location)
        self.assertEqual([], self.inventory_queries)
        self.assertEqual([], self.warehouse_queries)

    def test_employee_without_warehouse_read_is_denied_before_stock_query(self):
        self.readable = self.document_readable = set()
        with self.assertRaises(Denied):
            self.scan(A)
        self.assertEqual([], self.inventory_queries)

    def test_hidden_leaf_full_short_and_prefix_are_denied(self):
        for code in (B, "R3-B Shelf", "R3-B"):
            with self.subTest(code=code), self.assertRaises(Denied):
                self.scan(code)
        self.assertEqual([], self.inventory_queries)

    def test_document_read_does_not_skip_the_orm_warehouse_scope(self):
        self.document_readable.add(B)
        with self.assertRaises(Denied):
            self.scan(B)
        self.assertEqual([], self.inventory_queries)

    def test_group_intersection_excludes_hidden_and_disabled_inventory(self):
        self.readable.add(DISABLED)
        self.document_readable.add(DISABLED)
        context = self.scan(GROUP)
        self.assertEqual([[A]], self.inventory_queries)
        self.assertTrue(context.is_group)
        self.assertEqual(100, context.total_qty)
        self.assertEqual(1, context.batch_count)
        self.assertEqual(1, context.item_count)
        self.assertEqual(f"SUPPLIER-{A}", context.rows[0]["supplier"])
        self.assertEqual(f"MANUFACTURER-{A}", context.rows[0]["manufacturer"])
        self.assertEqual("CERT-A", context.rows[0]["certificate_no"])
        self.assertEqual("10.00kg*10件", context.rows[0]["packaging_spec"])
        self.assertNotIn(f"BATCH-{B}", repr(vars(context)))

    def test_visible_leaf_preserves_all_fields_for_full_short_and_prefix(self):
        for code in (A, "R3-A Shelf", "R3-A"):
            with self.subTest(code=code):
                context = self.scan(code)
                self.assertEqual([[A]], self.inventory_queries[-1:])
                self.assertFalse(context.is_group)
                self.assertEqual("kg", context.rows[0]["uom"])
                self.assertEqual(f"SUPPLIER-{A}", context.rows[0]["supplier"])
                self.assertEqual("SUPPLIER-BATCH-A", context.rows[0]["supplier_batch_no"])

    def test_group_with_no_visible_leaves_does_not_query_all_inventory(self):
        self.readable = {GROUP}
        context = self.scan(GROUP)
        self.assertEqual([], context.rows)
        self.assertEqual([], self.inventory_queries)

    def test_revoked_scope_is_rechecked_on_the_next_scan(self):
        self.scan(A)
        self.readable.remove(A)
        with self.assertRaises(Denied):
            self.scan(A)
        self.assertEqual([[A]], self.inventory_queries)

    def test_missing_or_unknown_code_has_no_stock_query(self):
        for code in ("", "NO-SUCH-WAREHOUSE"):
            with self.subTest(code=code):
                context = self.scan(code)
                self.assertTrue(context.error)
                self.assertEqual([], context.rows)
        self.assertEqual([], self.inventory_queries)


if __name__ == "__main__":
    unittest.main()
