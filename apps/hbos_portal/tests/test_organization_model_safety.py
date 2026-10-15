"""Exercise each shipped controller/hook using synthetic ORM and request inputs.

These contracts do not initialize Frappe or replace native Site acceptance.
"""
from contextlib import contextmanager
import importlib
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import quote
from uuid import uuid4

from hbos_portal import hooks
from hbos_portal.organization import native_read_boundary
from hbos_portal.organization.management_storage import POLICY, POLICY_REVISION, policy_record, stored_time
from hbos_portal.organization.storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, IMMUTABLE, LOCK_KEY, POSITION, POSITION_REVISION,
    PROVIDER, RECEIPT, WRITE_LOCK, canonical_json, digest, receipt_key, revision_key,
)
from hbos_portal.organization.write_guard import _controlled_write, is_controlled_write
from tests.test_management_storage import NOW, OPERATOR, policy


APP = Path(__file__).resolve().parents[1] / "hbos_portal"
# Independent explicit expectations: neither paths nor controller identities are
# inferred from the production scope allowlist or a mutable JSON name.
MODELS = (
    ("hbos_position", POSITION, "HBOSPosition", "relation"),
    ("hbos_position_revision", POSITION_REVISION, "HBOSPositionRevision", "relation"),
    ("hbos_personnel_assignment", ASSIGNMENT, "HBOSPersonnelAssignment", "relation"),
    ("hbos_personnel_assignment_revision", ASSIGNMENT_REVISION, "HBOSPersonnelAssignmentRevision", "relation"),
    ("hbos_organization_command_receipt", RECEIPT, "HBOSOrganizationCommandReceipt", "relation"),
    ("hbos_organization_write_lock", WRITE_LOCK, "HBOSOrganizationWriteLock", "relation"),
    ("hbos_organization_management_policy", POLICY, "HBOSOrganizationManagementPolicy", "policy"),
    ("hbos_organization_management_policy_revision", POLICY_REVISION,
     "HBOSOrganizationManagementPolicyRevision", "policy"),
)


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def shipped_controllers():
    """Load real controller source without leaking fake Frappe into other tests."""
    class Document:
        def __init__(self, data):
            self.__dict__.update(data)
            self.writes = 0

        def get(self, key):
            return getattr(self, key, None)

        def is_new(self):
            return True

        def db_insert(self, *args, **kwargs):
            self.writes += 1

        def db_update(self, *args, **kwargs):
            self.writes += 1

    def throw(message, error):
        raise error(message)

    native = types.SimpleNamespace(throw=throw, PermissionError=PermissionError)
    modules = {
        "frappe": native,
        "frappe.model": types.ModuleType("frappe.model"),
        "frappe.model.document": types.SimpleNamespace(Document=Document),
    }
    with patch.dict(sys.modules, modules):
        relation = load_source("hbos_portal.organization._ci_relation_guard", APP / "organization/protected_document.py")
        policy_guard = load_source("hbos_portal.organization._ci_policy_guard", APP / "organization/protected_policy_document.py")
        guards = {"relation": relation.ProtectedRelationDocument, "policy": policy_guard.ProtectedPolicyDocument}
        with patch.dict(sys.modules, {
            "hbos_portal.organization.protected_document": relation,
            "hbos_portal.organization.protected_policy_document": policy_guard,
        }):
            controllers = {}
            for slug, kind, class_name, guard in MODELS:
                module = load_source("_ci_controller_" + slug, APP / "hbos_portal/doctype" / slug / (slug + ".py"))
                controllers[kind] = (getattr(module, class_name), guards[guard])
            yield controllers, native


def records():
    """Valid synthetic storage records; no table, account or permission changes."""
    result = {}
    for kind in (POSITION, ASSIGNMENT):
        key = str(uuid4())
        result[kind] = dict(record_key=key, revision=1, authorization_generation=1,
                            source_provider=PROVIDER, source_key=key)
        version = POSITION_REVISION if kind == POSITION else ASSIGNMENT_REVISION
        parent = "position" if kind == POSITION else "assignment"
        result[version] = dict(record_key=revision_key(kind, key, 1), **{parent: key},
            revision=1, previous_revision=0, snapshot_json=canonical_json(result[kind]),
            content_digest=digest(result[kind]))
    receipt = dict(site_id="synthetic-site", actor=OPERATOR, command_type="create_position", request_key=str(uuid4()))
    result[RECEIPT] = dict(record_key=receipt_key(**receipt), **receipt)
    result[WRITE_LOCK] = dict(record_key=LOCK_KEY)
    row = policy()
    result[POLICY] = policy_record(row)
    result[POLICY_REVISION] = dict(record_key=revision_key(POLICY, row.policy_id, 1), policy=row.policy_id,
        revision=1, previous_revision=0, snapshot_json=canonical_json(result[POLICY]),
        snapshot_digest=digest(result[POLICY]), actor=OPERATOR, reason="合成受控路径",
        approval_source_ref="SYNTHETIC-OWNER-RECORD", recorded_at_utc=stored_time(NOW))
    return result


class ShippedOrganizationModelSafetyTests(unittest.TestCase):
    def setUp(self):
        scope = shipped_controllers()
        self.controllers, self.native = scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.records = records()

    def document(self, kind):
        record = self.records[kind]
        return self.controllers[kind][0](dict(doctype=kind, name=record["record_key"], **record,
            flags={"ignore_permissions": True, "ignore_validate": True}))

    def test_every_actual_controller_inherits_its_write_and_native_read_guards(self):
        for _, kind, _, _ in MODELS:
            with self.subTest(doctype=kind):
                controller, guard = self.controllers[kind]
                self.assertEqual(controller.__bases__, (guard,))
                self.assertTrue(issubclass(controller, native_read_boundary.NativeReadProtectedDocument))
                for method in ("has_permission", "check_permission", "validate", "db_insert", "db_update",
                               "db_set", "on_trash", "before_rename"):
                    self.assertIs(getattr(controller, method), getattr(guard, method))

    def test_each_actual_controller_rejects_uncontrolled_read_and_write_with_client_flags(self):
        for _, kind, _, _ in MODELS:
            doc = self.document(kind)
            with self.subTest(doctype=kind):
                for ptype in ("read", "select", "export", "write", "create", "delete", "share"):
                    self.assertFalse(doc.has_permission(ptype, user="Administrator"))
                    with self.assertRaises(PermissionError):
                        doc.check_permission(ptype)
                for method in (doc.validate, doc.db_insert, doc.db_update, doc.db_set, doc.on_trash, doc.before_rename):
                    with self.assertRaises(PermissionError):
                        method()
                self.assertEqual(doc.writes, 0)

    def test_exact_controlled_capability_allows_valid_insert_and_expires_for_each_model(self):
        for _, kind, _, _ in MODELS:
            doc = self.document(kind)
            with self.subTest(doctype=kind):
                with _controlled_write(kind, doc.name):
                    self.assertIsNone(doc.check_permission("create"))
                    doc.validate()
                    doc.db_insert()
                    self.assertEqual(doc.writes, 1)
                    # A write capability never opens the ordinary native read path.
                    with self.assertRaises(PermissionError):
                        doc.check_permission("read")
                self.assertFalse(is_controlled_write(kind, doc.name))
                with self.assertRaises(PermissionError):
                    doc.db_insert()
                self.assertEqual(doc.writes, 1)

    def test_wrong_model_or_key_capability_cannot_write_any_actual_controller(self):
        for _, kind, _, _ in MODELS:
            doc = self.document(kind)
            other = POLICY if kind != POLICY else POSITION
            for cap_kind, cap_key in ((kind, "synthetic-other-key"), (other, doc.name)):
                with self.subTest(doctype=kind, cap_kind=cap_kind, cap_key=cap_key):
                    with _controlled_write(cap_kind, cap_key), self.assertRaises(PermissionError):
                        doc.db_insert()
                    self.assertEqual(doc.writes, 0)

    def test_capability_preserves_mutable_heads_and_immutable_history_for_all_models(self):
        for _, kind, _, _ in MODELS:
            doc = self.document(kind)
            with self.subTest(doctype=kind), _controlled_write(kind, doc.name):
                if kind in IMMUTABLE or kind == POLICY_REVISION:
                    with self.assertRaises(PermissionError):
                        doc.db_update()
                    self.assertEqual(doc.writes, 0)
                else:
                    doc.db_update()
                    self.assertEqual(doc.writes, 1)
                for method in (doc.db_set, doc.on_trash, doc.before_rename):
                    with self.assertRaises(PermissionError):
                        method()

    def test_hooks_resolve_and_reject_native_permission_query_and_requests_for_every_model(self):
        request_guard = "hbos_portal.organization.native_read_boundary.before_request"
        self.assertIn(request_guard, hooks.before_request)
        self.assertEqual(set(hooks.has_permission), set(self.controllers))
        self.assertEqual(set(hooks.permission_query_conditions), set(self.controllers))
        for _, kind, _, _ in MODELS:
            with self.subTest(doctype=kind):
                for reference, expected in ((hooks.has_permission[kind], native_read_boundary.deny_native_permission),
                                            (hooks.permission_query_conditions[kind], native_read_boundary.deny_native_query)):
                    module_name, function = reference.rsplit(".", 1)
                    self.assertIs(getattr(importlib.import_module(module_name), function), expected)
                self.assertFalse(native_read_boundary.deny_native_permission(
                    doc=self.document(kind), ptype="read", user="Administrator", doctype=kind))
                with self.assertRaises(PermissionError):
                    native_read_boundary.deny_native_query(user="Administrator", doctype=kind)
                # Exercise the hook itself, including read and write request
                # shapes, rather than asserting the classifier's boolean alone.
                for path, params in (("/api/resource/" + quote(kind), {}),
                                     ("/api/method/frappe.client.save", {"doc": {"doctype": kind}})):
                    self.native.local = types.SimpleNamespace(request=types.SimpleNamespace(path=path))
                    self.native.form_dict = params
                    with self.assertRaises(PermissionError):
                        native_read_boundary.before_request(native=self.native)

    def test_native_hook_allows_fixed_controlled_service_and_native_personnel_requests(self):
        for path in ("/api/method/hbos_portal.api.organization_relations.list_positions",
                     "/api/method/hbos_portal.api.organization_relations.create_position",
                     "/api/resource/Employee"):
            with self.subTest(path=path):
                self.native.local = types.SimpleNamespace(request=types.SimpleNamespace(path=path))
                self.native.form_dict = {}
                self.assertIsNone(native_read_boundary.before_request(native=self.native))


if __name__ == "__main__":
    unittest.main()
