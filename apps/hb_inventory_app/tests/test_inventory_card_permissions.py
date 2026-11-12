"""Inventory snapshot authorization, with deliberately permissive native shortcuts.

File's native owner / DocShare checks are modelled as successful. The tests
require the added warehouse boundary to deny access *before* those shortcuts,
and require unrelated files to keep the original native result. Actual HTTP
download, ORM hooks and PDF rendering are verified on the isolated CI site.
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1] / "hb_inventory_app" / "hbos_inventory"
PRINT_SOURCE = ROOT / "print_utils.py"
DOC_GEN_SOURCE = ROOT / "doc_gen.py"
WAREHOUSES = {"A", "B", "Group", "Disabled historical warehouse"}
CARD = {
    "name": "old-card", "file_name": "HBOS-BATCH-待检证+货位卡.pdf",
    "file_url": "/private/files/HBOS-BATCH-待检证+货位卡.pdf",
    "attached_to_doctype": "Batch", "attached_to_name": "BATCH", "is_private": 1,
}


class Denied(Exception):
    pass


class AttrDict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class ReceiptRecord(AttrDict):
    def get_doc_before_save(self):
        return self.previous


class NativeFile(dict):
    """Model the permissive owner/share case without bypassing the tested mixin."""

    def __init__(self, data, native_allowed=True):
        super().__init__(data)
        self.native_allowed = native_allowed
        self.native_calls = []
        self.flags = types.SimpleNamespace(ignore_permissions=False)

    def has_permission(self, permtype="read", *, debug=False, user=None):
        self.native_calls.append(("permission", permtype, user))
        return self.native_allowed

    def is_downloadable(self):
        self.native_calls.append(("download",))
        return self.native_allowed

    def get_content(self, *args, **kwargs):
        self.native_calls.append(("content",))
        return b"PDF with warehouse A and warehouse B"

    def validate(self):
        self.native_calls.append(("validate",))

    def before_insert(self):
        self.native_calls.append(("physical-write",))


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InventoryCardPermissionsTest(unittest.TestCase):
    def setUp(self):
        self.visible = {"restricted": {"A"}, "unrestricted": set(WAREHOUSES), "employee": set()}
        self.records = {CARD["name"]: dict(CARD)}
        self.sql_calls = []
        self.scope_users = []
        self.batch_writable = False
        self.batch_checks = []
        self.side_effects = []
        self.stock_submit = True
        self.persisted_receipt = {"docstatus": 1, "purpose": "Material Receipt"}
        self.posted_batches = ["BATCH"]
        self.frappe = types.SimpleNamespace(
            session=types.SimpleNamespace(user="restricted"),
            flags=AttrDict(), form_dict=AttrDict(),
            utils=types.SimpleNamespace(cint=lambda value: int(value or 0), flt=lambda value: float(value or 0)),
            PermissionError=Denied,
            throw=self.throw, _=lambda message: message,
            has_permission=self.has_permission,
            get_list=self.get_list,
            get_all=lambda doctype, **kwargs: list(WAREHOUSES),
            get_doc=self.get_doc,
            db=types.SimpleNamespace(get_value=self.get_value, exists=lambda *args: True, sql=self.sql),
            whitelist=self.whitelist,
            get_roles=lambda: ["Stock User"],
            msgprint=lambda *args, **kwargs: None,
            log_error=lambda **kwargs: self.side_effects.append(("log", kwargs)),
        )
        pdf = types.SimpleNamespace(get_pdf=lambda *args, **kwargs: b"rendered")
        self.modules = patch.dict(sys.modules, {"frappe": self.frappe, "frappe.utils.pdf": pdf})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.policy = load_source("card_permissions_tested", ROOT / "card_permissions.py")
        self.policy_module = patch.dict(sys.modules, {
            "hb_inventory_app.hbos_inventory.card_permissions": self.policy,
        })
        self.policy_module.start()
        self.addCleanup(self.policy_module.stop)
        self.file_class = type("ExtendedFile", (self.policy.InventoryCardFileMixin, NativeFile), {})
        self.printing = load_source("card_printing_tested", PRINT_SOURCE)
        self.generator = load_source("card_generation_tested", DOC_GEN_SOURCE)

    def throw(self, message, exc=Denied):
        raise exc(message)

    @staticmethod
    def whitelist(**kwargs):
        def decorate(fn):
            fn.allowed_methods = kwargs.get("methods")
            return fn
        return decorate

    def has_permission(self, doctype, ptype, user=None, doc=None):
        if doctype == "Stock Entry":
            self.assertEqual("submit", ptype)
            self.assertEqual("RECEIPT", doc.name)
            self.assertEqual(self.frappe.session.user, user)
            return self.stock_submit
        self.assertEqual(("Warehouse", "read"), (doctype, ptype))
        return user in {"restricted", "unrestricted"}

    def get_list(self, doctype, user=None, **kwargs):
        self.assertEqual("Warehouse", doctype)
        self.scope_users.append(user)
        return list(self.visible.get(user, set()))

    def get_value(self, doctype, name, fieldname, **kwargs):
        if doctype == "File":
            return self.records.get(name)
        if doctype == "Stock Entry":
            self.assertEqual("RECEIPT", name)
            return self.persisted_receipt
        self.assertEqual("Batch", doctype)
        return "BATCH" if fieldname == "batch_id" else "自产"

    def get_doc(self, doctype, name):
        self.assertEqual(("Batch", "BATCH"), (doctype, name))

        def check_permission(ptype):
            self.batch_checks.append(ptype)
            if not self.batch_writable and self.frappe.session.user != "Administrator":
                raise Denied("Batch is read-only")
        return types.SimpleNamespace(check_permission=check_permission)

    def sql(self, query, values=None, **kwargs):
        self.sql_calls.append((query, values))
        if isinstance(values, dict) and "entry" in values:
            self.assertEqual({"entry": "RECEIPT"}, values)
            return self.posted_batches
        return []

    @staticmethod
    def receipt(**changes):
        return ReceiptRecord({
            "name": "RECEIPT", "doctype": "Stock Entry", "purpose": "Material Receipt",
            "docstatus": 1, "_action": "submit", "previous": {"docstatus": 0},
            "items": [AttrDict(batch_no="BATCH")],
            "flags": AttrDict(ignore_permissions=True, automatic_card=True),
            **changes,
        })

    def test_owner_and_share_shortcuts_do_not_open_a_full_warehouse_pdf(self):
        doc = self.file_class(CARD, native_allowed=True)
        self.assertFalse(doc.has_permission())
        self.assertFalse(doc.is_downloadable())
        with self.assertRaises(Denied):
            doc.get_content()
        self.assertEqual([], doc.native_calls)

    def test_explicit_user_is_checked_instead_of_the_current_admin_session(self):
        self.frappe.session.user = "Administrator"
        doc = self.file_class(CARD)
        self.assertFalse(doc.has_permission(user="restricted"))
        self.assertEqual(["restricted"], self.scope_users)

    def test_unrestricted_file_access_still_requires_the_native_permission(self):
        self.frappe.session.user = "unrestricted"
        allowed = self.file_class(CARD, native_allowed=True)
        denied = self.file_class(CARD, native_allowed=False)
        self.assertTrue(allowed.is_downloadable())
        self.assertTrue(allowed.has_permission())
        self.assertFalse(denied.is_downloadable())
        self.assertFalse(denied.has_permission())
        self.assertIn(b"warehouse B", allowed.get_content())

    def test_scope_revocation_and_disabled_historical_warehouse_are_not_cached(self):
        self.frappe.session.user = "unrestricted"
        doc = self.file_class(CARD)
        self.assertTrue(doc.is_downloadable())
        self.visible["unrestricted"].remove("Disabled historical warehouse")
        self.assertFalse(doc.is_downloadable())
        with self.assertRaises(Denied):
            doc.get_content()

    def test_employee_with_file_share_but_no_warehouse_read_is_denied(self):
        self.frappe.session.user = "employee"
        self.assertFalse(self.file_class(CARD, native_allowed=True).is_downloadable())

    def test_lims_coa_and_generic_private_files_keep_the_native_behavior(self):
        self.frappe.session.user = "employee"
        for doctype, name in (("HBOS COA", "COA-R3.pdf"), ("Stock Entry", "label.png"), (None, "note.txt")):
            for native_allowed in (True, False):
                with self.subTest(doctype=doctype, allowed=native_allowed):
                    data = {"name": f"file-{name}", "file_name": name, "file_url": f"/private/files/{name}",
                            "attached_to_doctype": doctype, "attached_to_name": "OTHER", "is_private": 1}
                    doc = self.file_class(data, native_allowed=native_allowed)
                    self.assertEqual(native_allowed, doc.has_permission())
                    self.assertEqual(native_allowed, doc.is_downloadable())
                    doc.before_insert()
                    doc.validate()
        self.assertEqual([], self.scope_users)

    def test_mutating_all_identity_fields_does_not_hide_the_stored_card(self):
        disguised = dict(CARD, file_name="innocent.pdf", file_url="/files/innocent.pdf",
                         attached_to_doctype="ToDo", attached_to_name="OTHER", is_private=0)
        doc = self.file_class(disguised)
        doc.flags.ignore_permissions = True
        self.assertFalse(doc.has_permission("write"))
        self.assertFalse(doc.is_downloadable())
        with self.assertRaises(Denied):
            doc.validate()
        with self.assertRaises(Denied):
            doc.get_content()
        self.assertEqual([], doc.native_calls)

    def test_existing_card_identity_or_privacy_cannot_be_removed_even_by_admin(self):
        self.frappe.session.user = "Administrator"
        for change in ({"file_name": "other.pdf"}, {"file_url": "/private/files/other.pdf"},
                       {"attached_to_doctype": "ToDo", "attached_to_name": "OTHER"}, {"is_private": 0}):
            with self.subTest(change=change), self.assertRaises(Denied):
                self.file_class(dict(CARD, **change)).validate()
        unchanged = self.file_class(CARD)
        unchanged.validate()
        self.assertEqual([("validate",)], unchanged.native_calls)

    def test_same_blob_cannot_be_relinked_or_disguised_in_a_second_file(self):
        disguised = dict(CARD, name="second-file", file_name="innocent.pdf",
                         attached_to_doctype="ToDo", attached_to_name="OTHER")
        doc = self.file_class(disguised)
        self.assertFalse(doc.is_downloadable())
        with self.assertRaises(Denied):
            doc.get_content()
        self.frappe.session.user = "Administrator"
        with self.assertRaises(Denied):
            doc.validate()

    def test_legacy_collision_suffix_and_percent_encoded_url_remain_protected(self):
        from urllib.parse import quote

        for suffix in ("", "aB19x0"):
            filename = f"HBOS-BATCH-待检证+货位卡{suffix}.pdf"
            data = dict(CARD, name="older", file_name="previously-renamed.pdf",
                        file_url="/private/files/" + quote(filename))
            self.assertFalse(self.file_class(data).is_downloadable())

    def test_card_sql_is_never_run_for_a_restricted_print_request(self):
        for method in ("hbos_batch_bins", "hbos_first_receipt_date", "hbos_batch_flow"):
            with self.subTest(method=method), self.assertRaises(Denied):
                getattr(self.printing, method)("BATCH")
        self.assertEqual([], self.sql_calls)

    def test_full_card_print_keeps_complete_warehouse_sql_for_authorized_user(self):
        self.frappe.session.user = "unrestricted"
        self.printing.hbos_batch_bins("BATCH")
        self.printing.hbos_batch_flow("BATCH")
        self.printing.hbos_first_receipt_date("BATCH")
        self.assertEqual(3, len(self.sql_calls))
        self.assertTrue(all(params == {"batch": "BATCH"} for _, params in self.sql_calls))

    def test_regeneration_requires_batch_write_before_render_or_delete(self):
        self.frappe.session.user = "unrestricted"
        with self.assertRaises(Denied):
            self.generator.regenerate_for_batch("BATCH")
        self.assertEqual(["write"], self.batch_checks)
        self.assertEqual([], self.sql_calls)
        self.assertEqual(["POST"], self.generator.regenerate_for_batch.allowed_methods)

    def test_batch_write_does_not_authorize_a_restricted_full_snapshot(self):
        self.batch_writable = True
        with self.assertRaises(Denied):
            self.generator.regenerate_for_batch("BATCH")
        self.assertEqual(["write"], self.batch_checks)
        self.assertEqual([], self.sql_calls)

    def test_native_file_creation_requires_batch_write_despite_file_ownership(self):
        self.frappe.session.user = "unrestricted"
        doc = self.file_class(dict(CARD, name="new-card"), native_allowed=True)
        with self.assertRaises(Denied):
            doc.validate()
        self.assertEqual([], doc.native_calls)
        self.batch_writable = True
        doc.validate()
        self.assertEqual([("validate",)], doc.native_calls)

    def test_readonly_full_scope_is_denied_before_native_file_writes_bytes(self):
        self.frappe.session.user = "unrestricted"
        for extra in ({"content": b"new bytes"}, {"file_name": "innocent.pdf"}):
            with self.subTest(extra=extra):
                doc = self.file_class(dict(CARD, name="new-card", **extra), native_allowed=True)
                doc.flags.ignore_permissions = True
                with self.assertRaises(Denied):
                    doc.before_insert()
                self.assertEqual([], doc.native_calls)
        self.batch_writable = True
        doc = self.file_class(dict(CARD, name="new-card"))
        doc.before_insert()
        self.assertEqual([("physical-write",)], doc.native_calls)

    def test_known_print_formats_fail_before_jinja_and_leave_other_formats_alone(self):
        batch = AttrDict(name="BATCH", meta=AttrDict(default_print_format=None))
        for field in ("format", "print_format"):
            for format_name in self.policy.CARD_PRINT_FORMATS:
                with self.subTest(field=field, format=format_name):
                    self.frappe.form_dict.clear()
                    self.frappe.form_dict[field] = format_name
                    with self.assertRaises(Denied):
                        self.policy.validate_inventory_card_print(batch)
        self.assertEqual([], self.sql_calls)
        self.frappe.form_dict.clear()
        batch.meta.default_print_format = "HBOS 自产货位卡"
        with self.assertRaises(Denied):
            self.policy.validate_inventory_card_print(batch)
        self.frappe.session.user = "unrestricted"
        self.policy.validate_inventory_card_print(batch)
        self.frappe.session.user = "employee"
        self.frappe.form_dict.print_format = "HBOS COA"
        self.policy.validate_inventory_card_print(batch)

    def test_automatic_context_rejects_forged_flags_and_non_submit_transitions(self):
        for changes in ({"doctype": "Delivery Note"}, {"purpose": "Material Transfer"},
                        {"docstatus": 0}, {"_action": "save"}, {"previous": {"docstatus": 1}},
                        {"previous": None}):
            with self.subTest(changes=changes), self.assertRaises(Denied):
                with self.policy._automatic_receipt_card(self.receipt(**changes), "BATCH"):
                    self.fail("Unsubmitted data acquired an automatic card capability")
            self.assertIsNone(self.policy._AUTOMATIC_CARD.get())
        self.stock_submit = False
        with self.assertRaises(Denied):
            with self.policy._automatic_receipt_card(self.receipt(), "BATCH"):
                self.fail("doc.flags.ignore_permissions bypassed native Stock Entry.submit")
        self.stock_submit = True
        self.frappe.session.user = "Guest"
        with self.assertRaises(Denied):
            with self.policy._automatic_receipt_card(self.receipt(), "BATCH"):
                self.fail("A guest acquired an automatic card capability")
        self.assertEqual([], self.sql_calls)
        for method in (self.policy._automatic_receipt_card, self.policy._automatic_print_permission,
                       self.generator.generate_for_stock_entry, self.generator.generate_for_batch):
            self.assertFalse(hasattr(method, "allowed_methods"))

    def test_automatic_context_requires_posted_database_proof_for_this_batch(self):
        for persisted in (None, {"docstatus": 0, "purpose": "Material Receipt"},
                          {"docstatus": 1, "purpose": "Material Transfer"}):
            self.persisted_receipt = persisted
            with self.subTest(persisted=persisted), self.assertRaises(Denied):
                with self.policy._automatic_receipt_card(self.receipt(), "BATCH"):
                    self.fail("A forged in-memory document replaced the persisted receipt")
            self.assertIsNone(self.policy._AUTOMATIC_CARD.get())
        self.persisted_receipt = {"docstatus": 1, "purpose": "Material Receipt"}
        self.posted_batches = ["OTHER"]
        with self.assertRaises(Denied):
            with self.policy._automatic_receipt_card(self.receipt(), "BATCH"):
                self.fail("A different batch acquired the receipt capability")
        self.assertIsNone(self.policy._AUTOMATIC_CARD.get())

    def test_real_receipt_scope_can_create_its_artifact_but_cannot_download_it(self):
        new_card = self.file_class(dict(CARD, name="new-card", content=b"freshly rendered PDF"))
        old_card = self.file_class(CARD)
        with self.policy._automatic_receipt_card(self.receipt(), "BATCH"):
            self.assertEqual(("restricted", "RECEIPT", "BATCH"), self.policy._AUTOMATIC_CARD.get())
            self.policy.require_full_card_scope(batch_name="BATCH")
            self.printing.hbos_batch_bins("BATCH")
            self.assertTrue(new_card.has_permission("create"))
            new_card.before_insert()
            new_card.validate()
            self.assertIn(b"warehouse B", new_card.get_content())
            self.assertEqual([], self.batch_checks)
            # The generation capability never grants list, read or download.
            self.assertTrue(self.policy.inventory_file_query_conditions())
            for doc in (new_card, old_card):
                self.assertFalse(doc.has_permission("read"))
                self.assertFalse(doc.is_downloadable())
            with self.assertRaises(Denied):
                old_card.get_content()
            with self.assertRaises(Denied):
                self.policy.require_full_card_scope(batch_name="OTHER")
            for changes in ({"is_private": 0}, {"attached_to_name": "OTHER"},
                            {"attached_to_doctype": "ToDo"}):
                with self.subTest(changes=changes), self.assertRaises(Denied):
                    self.file_class(dict(new_card, **changes)).before_insert()
            self.frappe.session.user = "employee"
            self.assertFalse(self.policy._is_automatic_batch("BATCH"))
            with self.assertRaises(Denied):
                new_card.before_insert()
            self.frappe.session.user = "restricted"
        self.assertIsNone(self.policy._AUTOMATIC_CARD.get())
        with self.assertRaises(Denied):
            new_card.get_content()

    def test_print_flag_is_bound_and_restored_even_when_rendering_raises(self):
        def failing_print(doctype, name, print_format, as_pdf):
            self.assertTrue(self.frappe.flags.ignore_print_permissions)
            self.frappe.form_dict.format = print_format
            self.policy.validate_inventory_card_print(AttrDict(name=name, meta=AttrDict()))
            raise RuntimeError("render failure")

        self.frappe.get_print = failing_print
        for original in (None, False, True):
            with self.subTest(original=original):
                self.frappe.flags.clear()
                if original is not None:
                    self.frappe.flags.ignore_print_permissions = original
                before = dict(self.frappe.flags)
                with self.assertRaisesRegex(RuntimeError, "render failure"):
                    with self.policy._automatic_receipt_card(self.receipt(), "BATCH"):
                        self.generator._render("Batch", "BATCH", "HBOS 待检证", {})
                self.assertEqual(before, self.frappe.flags)
                self.assertIsNone(self.policy._AUTOMATIC_CARD.get())
        self.frappe.flags.clear()
        with self.policy._automatic_receipt_card(self.receipt(), "BATCH"):
            for args in (("Item", "BATCH", "HBOS 待检证"), ("Batch", "OTHER", "HBOS 待检证"),
                         ("Batch", "BATCH", "HBOS COA")):
                with self.subTest(args=args), self.policy._automatic_print_permission(*args):
                    self.assertNotIn("ignore_print_permissions", self.frappe.flags)

    def test_automatic_hook_failure_keeps_receipt_and_leaves_no_capability(self):
        def fail_generation(batch_name):
            self.assertTrue(self.policy._is_automatic_batch(batch_name))
            raise RuntimeError("PDF generation failed after the receipt was posted")

        with patch.object(self.generator, "generate_for_batch", side_effect=fail_generation):
            self.generator.generate_for_stock_entry(self.receipt())
        self.assertIsNone(self.policy._AUTOMATIC_CARD.get())
        self.assertNotIn("ignore_print_permissions", self.frappe.flags)
        self.assertEqual(1, self.persisted_receipt["docstatus"])
        self.assertEqual(1, len(self.side_effects))
        self.assertIn("PDF generation failed", self.side_effects[0][1]["message"])


if __name__ == "__main__":
    unittest.main()
