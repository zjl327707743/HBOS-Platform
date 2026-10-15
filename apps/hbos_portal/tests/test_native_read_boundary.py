"""Synthetic ordinary-entry isolation for the eight controlled storage types."""
import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import quote

from hbos_portal.organization.native_read_boundary import (
    NativeReadProtectedDocument, before_request, deny_native_permission, deny_native_query,
    is_protected_request, protected_doctypes,
)
from hbos_portal.organization.write_guard import _controlled_write


PROTECTED = (
    "HBOS Position", "HBOS Position Revision", "HBOS Personnel Assignment",
    "HBOS Personnel Assignment Revision", "HBOS Organization Command Receipt",
    "HBOS Organization Write Lock", "HBOS Organization Management Policy",
    "HBOS Organization Management Policy Revision",
)


class NativePermissionError(Exception):
    pass


def fake_native(path, params=None, *, user="Administrator"):
    def throw(message, exception=None):
        raise (exception or NativePermissionError)(message)
    return SimpleNamespace(
        PermissionError=NativePermissionError, throw=throw,
        local=SimpleNamespace(request=SimpleNamespace(path=path)),
        form_dict=dict(params or {}), session=SimpleNamespace(user=user),
    )


class SyntheticProtectedDocument(NativeReadProtectedDocument):
    def __init__(self, doctype, name="synthetic-key", record_key="synthetic-key"):
        self.doctype, self.name, self.record_key = doctype, name, record_key
        self.flags = SimpleNamespace(ignore_permissions=True)

    def get(self, field):
        return getattr(self, field, None)


class NativeReadBoundaryTest(unittest.TestCase):
    def test_exact_eight_storage_types_do_not_include_native_personnel(self):
        self.assertEqual(set(protected_doctypes()), set(PROTECTED))
        for native in ("User", "Employee", "Company", "Department", "Designation", "Role"):
            self.assertNotIn(native, protected_doctypes())

    def test_v1_and_v2_collection_paths_are_denied_for_every_type(self):
        for doctype in PROTECTED:
            for prefix in ("/api/resource/", "/api/v1/resource/", "/api/v2/document/"):
                with self.subTest(doctype=doctype, prefix=prefix):
                    self.assertTrue(is_protected_request(prefix + quote(doctype), {}))
                    self.assertTrue(is_protected_request(prefix + doctype, {}))

    def test_resource_details_copy_and_document_methods_are_denied(self):
        for doctype in PROTECTED:
            for prefix in ("/api/resource/", "/api/v1/resource/", "/api/v2/document/"):
                for tail in ("/synthetic-id", "/synthetic-id/", "/synthetic-id/copy",
                             "/synthetic-id/method/get_synthetic/"):
                    with self.subTest(doctype=doctype, prefix=prefix, tail=tail):
                        self.assertTrue(is_protected_request(prefix + quote(doctype) + tail, {}))

    def test_v2_count_meta_and_controller_rpc_are_denied(self):
        for doctype in PROTECTED:
            for path in (f"/api/v2/doctype/{quote(doctype)}/count",
                         f"/api/v2/doctype/{quote(doctype)}/meta",
                         f"/api/v2/method/{quote(doctype)}/synthetic_method"):
                with self.subTest(path=path):
                    self.assertTrue(is_protected_request(path, {}))

    def test_native_client_list_count_detail_value_and_permission_rpc_are_denied(self):
        for method in ("get_list", "get_count", "get", "get_value", "get_single_value",
                       "get_doc_permissions", "set_value", "delete"):
            for prefix in ("/api/method/", "/api/v1/method/", "/api/v2/method/"):
                with self.subTest(method=method, prefix=prefix):
                    self.assertTrue(is_protected_request(prefix + "frappe.client." + method,
                        {"doctype": PROTECTED[0], "name": "synthetic-id"}))

    def test_legacy_cmd_dispatch_and_v1_suffix_dispatch_are_denied(self):
        params = {"cmd": "frappe.client.get_list", "doctype": PROTECTED[0]}
        for path in ("/", "/hbos/admin/people", "/api/resource/User"):
            with self.subTest(path=path):
                self.assertTrue(is_protected_request(path, params))
        self.assertTrue(is_protected_request("/api/method/frappe.client.get_list/legacy-suffix",
                                            {"doctype": PROTECTED[0]}))

    def test_legacy_short_run_doc_method_dispatch_cannot_skip_native_http_guard(self):
        for path in ("/api/method/run_doc_method", "/api/v1/method/run_doc_method",
                     "/api/v2/method/run_doc_method"):
            for params in ({"dt": PROTECTED[0], "dn": "synthetic-id", "method": "synthetic"},
                           {"docs": json.dumps({"doctype": PROTECTED[2], "name": "synthetic-id"}),
                            "method": "synthetic"}):
                with self.subTest(path=path, keys=tuple(params)):
                    self.assertTrue(is_protected_request(path, params))
        for path in ("/", "/hbos/admin/people"):
            self.assertTrue(is_protected_request(path, {"cmd": "run_doc_method", "dt": PROTECTED[0],
                                                        "dn": "synthetic-id", "method": "synthetic"}))

    def test_client_insert_and_save_document_json_are_denied(self):
        for method in ("frappe.client.insert", "frappe.client.save"):
            for doctype in PROTECTED:
                doc = {"doctype": doctype, "name": "synthetic-id", "flags": {"ignore_permissions": 1}}
                for value in (doc, json.dumps(doc)):
                    with self.subTest(method=method, doctype=doctype, json=isinstance(value, str)):
                        self.assertTrue(is_protected_request("/api/method/" + method, {"doc": value}))

    def test_nested_child_doc_cannot_hide_protected_storage_target(self):
        doc = {"doctype": "User", "name": "synthetic-user",
               "children": [{"doctype": PROTECTED[3], "snapshot_json": "synthetic"}]}
        for value in (doc, json.dumps(doc), [doc], json.dumps([doc])):
            with self.subTest(shape=type(value).__name__):
                self.assertTrue(is_protected_request("/api/method/frappe.client.save", {"doc": value}))

    def test_desk_savedocs_and_run_doc_method_document_targets_are_denied(self):
        for method, key in (("frappe.desk.form.save.savedocs", "doc"),
                            ("frappe.handler.run_doc_method", "docs"),
                            ("run_doc_method", "document")):
            doc = {"doctype": PROTECTED[0], "name": "synthetic-id"}
            for value in (doc, json.dumps(doc)):
                with self.subTest(method=method, key=key):
                    self.assertTrue(is_protected_request("/api/v2/method/" + method, {key: value}))

    def test_report_builder_form_and_link_search_targets_are_denied(self):
        methods = ("frappe.desk.reportview.get", "frappe.desk.reportview.get_list",
                   "frappe.desk.reportview.get_count", "frappe.desk.reportview.export_query",
                   "frappe.desk.form.load.getdoc", "frappe.desk.form.load.get_docinfo",
                   "frappe.desk.search.search_link", "frappe.desk.search.search_widget")
        for method in methods:
            with self.subTest(method=method):
                self.assertTrue(is_protected_request("/api/method/" + method,
                                                    {"doctype": PROTECTED[2]}))

    def test_data_export_and_import_template_targets_are_denied(self):
        for method in ("frappe.core.doctype.data_export.exporter.export_data",
                       "frappe.core.doctype.data_import.data_import.download_template"):
            with self.subTest(method=method):
                self.assertTrue(is_protected_request("/api/method/" + method,
                                                    {"doctype": PROTECTED[6]}))

    def test_named_query_report_uses_server_reference_not_client_target(self):
        resolved = []
        def resolver(name):
            resolved.append(name)
            return {"ref_doctype": PROTECTED[6], "report_type": "Query Report"}
        for method in ("frappe.desk.query_report.run", "frappe.desk.query_report.get_script"):
            with self.subTest(method=method):
                self.assertTrue(is_protected_request("/api/method/" + method,
                    {"report_name": "synthetic-controlled-report", "doctype": "User"}, resolver))
        self.assertEqual(resolved, ["synthetic-controlled-report"] * 2)

    def test_custom_report_reference_chain_cannot_hide_protected_target(self):
        reports = {"synthetic-custom": {"report_type": "Custom Report", "ref_doctype": "User",
                                       "reference_report": "synthetic-controlled"},
                   "synthetic-controlled": {"report_type": "Query Report", "ref_doctype": PROTECTED[1]}}
        self.assertTrue(is_protected_request("/api/v2/method/frappe.desk.query_report.run",
                                             {"report_name": "synthetic-custom"}, reports.get))

    def test_ordinary_native_report_remains_in_native_personnel_domain(self):
        for doctype in ("User", "Employee", "Company", "Role"):
            with self.subTest(doctype=doctype):
                self.assertFalse(is_protected_request("/api/method/frappe.desk.query_report.run",
                    {"report_name": "synthetic-native-report"},
                    lambda name: {"ref_doctype": doctype, "report_type": "Query Report"}))

    def test_native_personnel_rest_desk_and_existing_directory_are_not_taken_over(self):
        for doctype in ("User", "Employee", "Company", "Department", "Designation", "Role"):
            for prefix in ("/api/resource/", "/api/v1/resource/", "/api/v2/document/"):
                with self.subTest(doctype=doctype, prefix=prefix):
                    self.assertFalse(is_protected_request(prefix + doctype, {}))
            self.assertFalse(is_protected_request("/api/method/frappe.client.get_list", {"doctype": doctype}))
        for method in ("get_people", "get_organizations", "get_roles"):
            self.assertFalse(is_protected_request("/api/method/hbos_portal.api.people_access." + method,
                                                 {"source": "Employee", "phone": ""}))

    def test_fixed_controlled_methods_are_not_classified_as_native_storage_reads(self):
        for method in ("get_management_context", "list_positions", "get_person_assignments",
                       "lookup_people", "create_position", "update_position", "create_assignment",
                       "update_assignment"):
            with self.subTest(method=method):
                self.assertFalse(is_protected_request("/api/method/hbos_portal.api.organization_relations." + method,
                                                     {"employee_id": "synthetic-employee"}))

    def test_native_literal_collision_is_conservatively_denied_without_taking_over_directory(self):
        self.assertTrue(is_protected_request("/api/method/frappe.client.save",
                        {"doc": {"doctype": "User", "full_name": PROTECTED[0]}}))
        self.assertFalse(is_protected_request("/api/method/hbos_portal.api.people_access.get_people",
                                             {"source": "User", "name": PROTECTED[0]}))

    def test_native_nested_table_reference_cannot_hide_in_fields_or_filters(self):
        for params in ({"doctype": "User", "fields": ["name", "tab" + PROTECTED[0] + ".title"]},
                       {"doctype": "User", "filters": [[PROTECTED[0], "status", "=", "active"]]},
                       {"doctype": "User", "filters": json.dumps([[PROTECTED[2], "status", "=", "active"]])}):
            with self.subTest(params=params):
                self.assertTrue(is_protected_request("/api/method/frappe.client.get_list", params))

    def test_report_resolution_failure_missing_resolver_or_cycle_is_closed(self):
        path = "/api/method/frappe.desk.query_report.run"
        params = {"report_name": "synthetic-report"}
        self.assertTrue(is_protected_request(path, params))
        for resolver in (lambda name: None, lambda name: {},
                         lambda name: {"report_type": "Custom Report", "ref_doctype": "User",
                                       "reference_report": name}):
            with self.subTest(resolver=resolver):
                self.assertTrue(is_protected_request(path, params, resolver))
        def fails(name):
            raise RuntimeError("synthetic-private-report-failure")
        self.assertTrue(is_protected_request(path, params, fails))

    def test_report_reference_depth_and_native_input_complexity_are_bounded(self):
        def long_chain(name):
            return {"report_type": "Custom Report", "ref_doctype": "User",
                    "reference_report": str(int(name) + 1)}
        self.assertTrue(is_protected_request("/api/method/frappe.desk.query_report.run",
                                             {"report_name": "0"}, long_chain))
        doc = {"doctype": "User"}
        for _ in range(20):
            doc = {"nested": doc}
        for params in ({"doc": doc}, {"doc": {"doctype": "User", "x": "x" * 65537}},
                       {"doc": {"doctype": "User", "x": list(range(1100))}}):
            with self.subTest(shape=next(iter(params))):
                self.assertTrue(is_protected_request("/api/method/frappe.client.save", params))

    def test_document_hook_does_not_grant_administrator_role_or_flag_shortcuts(self):
        for user in ("Administrator", "synthetic-system-manager", "synthetic-reader", "Guest"):
            for ptype in ("read", "select", "report", "export", "write", "create", "delete", "share"):
                with self.subTest(user=user, ptype=ptype):
                    self.assertFalse(deny_native_permission(
                        doc=SimpleNamespace(doctype=PROTECTED[0], flags=SimpleNamespace(ignore_permissions=True)),
                        ptype=ptype, user=user, doctype=PROTECTED[0]))

    def test_query_hook_throws_instead_of_returning_share_bypassable_false_condition(self):
        native = fake_native("/api/resource/" + quote(PROTECTED[0]))
        with patch.dict(sys.modules, {"frappe": native}):
            for user in ("Administrator", "synthetic-shared-reader", "synthetic-reader"):
                with self.subTest(user=user), self.assertRaises(NativePermissionError):
                    deny_native_query(user=user, doctype=PROTECTED[0])

    def test_before_request_rejects_every_actor_without_native_domain_query_fallback(self):
        for user in ("Administrator", "synthetic-system-manager", "synthetic-reader", "Guest"):
            native = fake_native("/api/resource/" + quote(PROTECTED[0]), user=user)
            with self.subTest(user=user), self.assertRaises(NativePermissionError):
                before_request(native=native)
        self.assertIsNone(before_request(native=fake_native("/api/resource/Employee")))

    def test_controlled_exact_document_cap_preserves_create_write_only(self):
        native = fake_native("/api/resource/User")
        with patch.dict(sys.modules, {"frappe": native}):
            for doctype in PROTECTED:
                doc = SyntheticProtectedDocument(doctype)
                self.assertFalse(doc.has_permission("write", user="Administrator"))
                with _controlled_write(doctype, "synthetic-key"):
                    for ptype in ("create", "write"):
                        with self.subTest(doctype=doctype, ptype=ptype):
                            self.assertTrue(doc.has_permission(ptype))
                            self.assertIsNone(doc.check_permission(ptype))
                    for ptype in ("read", "select", "report", "export", "share", "delete", "rename"):
                        with self.subTest(doctype=doctype, ptype=ptype):
                            self.assertFalse(doc.has_permission(ptype))
                            with self.assertRaises(NativePermissionError):
                                doc.check_permission(ptype)
                self.assertFalse(doc.has_permission("create"))
                with self.assertRaises(NativePermissionError):
                    doc.check_permission("write")

    def test_controlled_new_document_permission_uses_exact_autoname_key(self):
        native = fake_native("/api/resource/User")
        with patch.dict(sys.modules, {"frappe": native}):
            doc = SyntheticProtectedDocument(PROTECTED[0], name=None)
            with _controlled_write(PROTECTED[0], "synthetic-key"):
                self.assertTrue(doc.has_permission("create"))
                self.assertIsNone(doc.check_permission("create"))
                self.assertFalse(doc.has_permission("read"))
            self.assertFalse(doc.has_permission("create"))

    def test_controlled_cap_cannot_authorize_neighbor_type_key_or_mismatched_record(self):
        native = fake_native("/api/resource/User")
        with patch.dict(sys.modules, {"frappe": native}), _controlled_write(PROTECTED[0], "synthetic-key"):
            for doc in (SyntheticProtectedDocument(PROTECTED[1]),
                        SyntheticProtectedDocument(PROTECTED[0], name="synthetic-other", record_key="synthetic-other"),
                        SyntheticProtectedDocument(PROTECTED[0], name="synthetic-key", record_key="synthetic-other")):
                with self.subTest(doctype=doc.doctype, name=doc.name, key=doc.record_key):
                    self.assertFalse(doc.has_permission("create"))
                    self.assertFalse(doc.has_permission("write"))
                    with self.assertRaises(NativePermissionError):
                        doc.check_permission("write")


if __name__ == "__main__":
    unittest.main()
