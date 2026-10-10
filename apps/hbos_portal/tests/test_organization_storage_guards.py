"""Controller and repository boundaries; no framework/database installation."""
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.frappe_repository import FrappeRelationRepository
from hbos_portal.organization.storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, LOCK_KEY, POSITION, POSITION_REVISION, PROVIDER,
    RECEIPT, WRITE_LOCK, canonical_json, digest, revision_key, validate_storage_record,
)
from hbos_portal.organization.write_guard import _controlled_write, is_controlled_write


class StorageGuardTests(unittest.TestCase):
    def setUp(self):
        class Document:
            def __init__(self, data): self.__dict__.update(data); self.writes = 0
            def get(self, key): return getattr(self, key, None)
            def is_new(self): return True
            def db_insert(self, *args, **kwargs): self.writes += 1
            def db_update(self, *args, **kwargs): self.writes += 1
        def throw(message, error): raise error(message)
        self.native = types.SimpleNamespace(throw=throw, PermissionError=PermissionError)
        modules = {"frappe": self.native, "frappe.model": types.ModuleType("frappe.model"),
                   "frappe.model.document": types.SimpleNamespace(Document=Document)}
        with patch.dict(sys.modules, modules):
            module = importlib.import_module("hbos_portal.organization.protected_document")
        self.module = module
        self.binding = patch.object(module, "frappe", self.native); self.binding.start()
        self.master = dict(doctype=POSITION, name=str(uuid4()), revision=1, authorization_generation=1,
                           source_provider=PROVIDER)
        self.master.update(record_key=self.master["name"], source_key=self.master["name"])

    def tearDown(self): self.binding.stop()

    def test_client_flags_cannot_bypass_validate_or_database_write_guard(self):
        doc = self.module.ProtectedRelationDocument({**self.master, "flags": {"ignore_validate": True,
            "ignore_permissions": True, "hbos_relation_authority": self.master["name"]}})
        for method in (doc.validate, doc.db_insert, doc.db_update):
            with self.assertRaises(PermissionError): method()
        self.assertEqual(doc.writes, 0)

    def test_capability_is_exact_and_resets_after_exception(self):
        doc = self.module.ProtectedRelationDocument(self.master)
        with _controlled_write(POSITION, "other"):
            with self.assertRaises(PermissionError): doc.db_insert()
        with self.assertRaises(RuntimeError):
            with _controlled_write(POSITION, doc.name):
                doc.db_insert(); raise RuntimeError("synthetic")
        self.assertEqual(doc.writes, 1)
        self.assertFalse(is_controlled_write(POSITION, doc.name))

    def test_nested_capabilities_restore_outer_scope(self):
        with _controlled_write(POSITION, "outer"):
            with _controlled_write(ASSIGNMENT, "inner"):
                self.assertFalse(is_controlled_write(POSITION, "outer"))
            self.assertTrue(is_controlled_write(POSITION, "outer"))
        self.assertFalse(is_controlled_write(POSITION, "outer"))

    def test_history_update_delete_rename_and_partial_update_are_rejected(self):
        doc = self.module.ProtectedRelationDocument(dict(doctype=POSITION_REVISION, name="synthetic"))
        with _controlled_write(POSITION_REVISION, doc.name):
            for method in (doc.db_update, doc.on_trash, doc.before_rename, doc.db_set):
                with self.assertRaises(PermissionError): method()
        self.assertEqual(doc.writes, 0)

    def test_snapshot_identity_and_digest_cannot_be_rewritten(self):
        parent = str(uuid4()); facts = {"record_key": parent, "revision": 1}
        row = dict(record_key=revision_key(POSITION, parent, 1), position=parent, revision=1,
                   previous_revision=0, snapshot_json=canonical_json(facts), content_digest=digest(facts))
        validate_storage_record(POSITION_REVISION, row["record_key"], row.get)
        for key, value in (("snapshot_json", canonical_json({**facts, "extra": True})),
                           ("record_key", "other"), ("previous_revision", False)):
            mutated = {**row, key: value}
            with self.assertRaises(ContractError): validate_storage_record(POSITION_REVISION, mutated["record_key"], mutated.get)
        boolean_revision = {**facts, "revision": True}
        mutated = {**row, "snapshot_json": canonical_json(boolean_revision), "content_digest": digest(boolean_revision)}
        with self.assertRaises(ContractError): validate_storage_record(POSITION_REVISION, mutated["record_key"], mutated.get)

    def test_six_schema_definitions_have_physical_keys_and_no_general_write_permission(self):
        base = Path(__file__).resolve().parents[1] / "hbos_portal/hbos_portal/doctype"
        for kind in (POSITION, ASSIGNMENT, POSITION_REVISION, ASSIGNMENT_REVISION, RECEIPT, WRITE_LOCK):
            slug = kind.lower().replace(" ", "_"); metadata = json.loads((base/slug/(slug+".json")).read_text())
            fields = {field["fieldname"]: field for field in metadata["fields"]}
            self.assertEqual(metadata["autoname"], "field:record_key")
            self.assertEqual(fields["record_key"]["unique"], 1)
            self.assertEqual(metadata["permissions"], [])
            self.assertEqual(metadata["allow_rename"], 0)
            self.assertEqual(metadata["allow_import"], 0)


class FrappeRepositoryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.native = types.SimpleNamespace(db=Mock(), get_doc=Mock(), get_all=Mock(),
                                            local=types.SimpleNamespace(site="synthetic-site"))
        self.repo = FrappeRelationRepository(native=self.native, enabled=True)

    def test_repository_default_closed_before_accessing_framework(self):
        repo = FrappeRelationRepository(native=self.native)
        with self.assertRaises(ContractError):
            with repo.transaction(): pass
        self.native.db.savepoint.assert_not_called()
        self.native.get_doc.assert_not_called()

    def test_savepoint_failure_rolls_back_and_never_commits(self):
        with self.assertRaises(RuntimeError):
            with self.repo.transaction(): raise RuntimeError("synthetic")
        point = self.native.db.savepoint.call_args.args[0]
        self.native.db.rollback.assert_called_once_with(save_point=point)
        self.native.db.commit.assert_not_called()

    def test_success_leaves_commit_to_caller(self):
        with self.repo.transaction(): pass
        self.native.db.commit.assert_not_called()
        self.native.db.rollback.assert_not_called()

    def test_missing_write_lock_fails_without_automatic_bootstrap(self):
        self.native.db.sql.return_value = []
        with self.assertRaises(ContractError) as caught: self.repo.lock_writer()
        self.assertEqual(caught.exception.code, "STORAGE_NOT_READY")
        self.native.get_doc.assert_not_called()

    def test_source_locks_use_fixed_order_and_parameterized_keys(self):
        self.native.db.sql.return_value = [("synthetic",)]
        self.repo.lock_sources((("Department", "department"), ("Employee", "employee"), ("User", "user'; DROP TABLE x; --")))
        calls = self.native.db.sql.call_args_list
        self.assertIn("`tabUser`", calls[0].args[0])
        self.assertIn("`tabEmployee`", calls[1].args[0])
        self.assertIn("`tabDepartment`", calls[2].args[0])
        self.assertNotIn("DROP", calls[0].args[0])
        self.assertEqual(calls[0].args[1], ("user'; DROP TABLE x; --",))
        self.native.db.sql.reset_mock()
        with self.assertRaises(ContractError): self.repo.lock_sources((("arbitrary.sql", "x"),))
        self.native.db.sql.assert_not_called()

    def test_stale_native_revision_rejected_without_save(self):
        doc = types.SimpleNamespace(revision=2, save=Mock())
        self.native.get_doc.return_value = doc
        with self.assertRaises(ContractError): self.repo.save_master(POSITION, {"record_key": str(uuid4())}, expected_revision=1)
        doc.save.assert_not_called()

    def test_interval_scan_requests_all_rows_and_normalizes_storage_values(self):
        row = {"record_key": str(uuid4()), "is_primary": 1, "subject_user": "", "valid_until_utc": None,
               "valid_from_utc": "2026-10-10 01:00:00"}
        def query(sql, *, as_dict):
            self.assertIn("FOR UPDATE", sql)
            self.assertNotIn("LIMIT", sql)
            return [dict(row) for _ in range(27)]
        self.native.db.sql.side_effect = query
        rows = self.repo.list_assignments()
        self.assertEqual(len(rows), 27)
        self.assertIs(rows[0]["is_primary"], True)
        self.assertIsNone(rows[0]["subject_user"])
        self.assertEqual(rows[0]["valid_from_utc"], "2026-10-10 01:00:00.000000")

    def test_controlled_insert_releases_capability_on_native_failure(self):
        key = str(uuid4())
        record = dict(record_key=key, revision=1, authorization_generation=1, source_provider=PROVIDER, source_key=key)
        def insert(**kwargs):
            self.assertTrue(is_controlled_write(POSITION, key))
            raise RuntimeError("synthetic native insert failure")
        self.native.get_doc.return_value = types.SimpleNamespace(insert=insert)
        with self.assertRaises(RuntimeError): self.repo.save_master(POSITION, record, expected_revision=0)
        self.assertFalse(is_controlled_write(POSITION, key))


if __name__ == "__main__": unittest.main()
