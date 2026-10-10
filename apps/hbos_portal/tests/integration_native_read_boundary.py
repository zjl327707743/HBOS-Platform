"""Exact existing Preview native WSGI ordinary-entry isolation acceptance.

No schema action, new Site, service start, persisted management configuration or
original-site activation. Compose the previous exact synthetic dataset and real
password session; remove synthetic Report/DocShare IDs before its proven cleanup.
Administrator is exercised only as an in-process model identity, never by making
an Administrator HTTP session or modifying the original Administrator account.
"""
import argparse
import hashlib
import json
import unittest
from unittest.mock import patch
from urllib.parse import quote
from uuid import uuid4

if __package__:
    from .integration_management_http import ORIGIN, find_field
    from .integration_management_queries import NativeManagementQueryCases
    from .integration_management_relations import POLICY_KINDS
    from .integration_management_storage import policy_presence, policy_schema_check
    from .integration_organization_storage import (
        SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check,
    )
else:
    from integration_management_http import ORIGIN, find_field
    from integration_management_queries import NativeManagementQueryCases
    from integration_management_relations import POLICY_KINDS
    from integration_management_storage import policy_presence, policy_schema_check
    from integration_organization_storage import (
        SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check,
    )


PROTECTED = (
    "HBOS Position", "HBOS Position Revision", "HBOS Personnel Assignment",
    "HBOS Personnel Assignment Revision", "HBOS Organization Command Receipt",
    "HBOS Organization Write Lock", "HBOS Organization Management Policy",
    "HBOS Organization Management Policy Revision",
)
EXTRA_TABLES = ("tabReport", "tabDocShare")
NATIVE_SPEC_READY = True


def extra_fingerprints(native):
    """Hash locally without disclosing existing reports or share identities."""
    result = {}
    for table in EXTRA_TABLES:
        rows = native.db.sql(f"SELECT * FROM `{table}`", as_dict=True)
        encoded = sorted(json.dumps(dict(row), sort_keys=True, default=str) for row in rows)
        result[table] = hashlib.sha256(json.dumps(encoded).encode()).hexdigest()
    return result


class NativeReadBoundaryCases(unittest.TestCase):
    native = None
    # Only category/count summaries survive test teardown; target IDs, SID and
    # native SQL rows never enter the final report.
    request_counts = {}
    model_checks = 0
    trusted_internal_share_query = "NOT_RUN"

    def setUp(self):
        self.query = NativeManagementQueryCases()
        self.query.native = self.native
        self.report_ids, self.share_ids = [], []
        self.addCleanup(self.cleanup)
        self.query.setUp()
        self.query._cleanups.clear()
        self.http, self.fixture = self.query.http, self.query.fixture
        f = self.http.reconnect()
        self.extra_before = extra_fingerprints(f)
        self.rows, self.sensitive_ids = {}, set()
        for doctype in PROTECTED:
            names = f.db.sql(f"SELECT name FROM `tab{doctype}` ORDER BY name")
            self.assertTrue(names)
            self.rows[doctype] = names[0][0]
            self.sensitive_ids.update(row[0] for row in names)
        self.initial_counts = self.query.counts()
        # The manager has approved controlled read policies. The beneficiary has
        # a real native System Manager role and no controlled management policy.
        self.native_client = self.query.query_client(self.http.native_application)
        self.native_token = self.http.login(
            self.native_client, self.fixture.beneficiary, self.http.ordinary_password)

    def cleanup(self):
        if hasattr(self, "fixture"):
            f = self.http.reconnect()
            for key in self.share_ids:
                f.db.sql("DELETE FROM `tabDocShare` WHERE name=%s", (key,))
            for key in self.report_ids:
                f.db.sql("DELETE FROM `tabReport` WHERE name=%s", (key,))
                f.clear_document_cache("Report", key)
            f.db.commit()
            if hasattr(self, "extra_before"):
                self.assertEqual(extra_fingerprints(f), self.extra_before)
        self.query.cleanup()

    def call(self, category, path, params=None, *, method="GET", client=None,
             token=None, form=False):
        cls = type(self)
        cls.request_counts[category] = cls.request_counts.get(category, 0) + 1
        headers = {"Accept": "application/json", "Origin": ORIGIN,
                   "X-Requested-With": "XMLHttpRequest",
                   "X-Frappe-CSRF-Token": token or self.native_token}
        options = {"method": method, "base_url": ORIGIN, "headers": headers, "buffered": True}
        if method in ("GET", "HEAD"):
            options["query_string"] = params or {}
        elif form:
            options["data"] = params or {}
        else:
            options["json"] = params or {}
        response = (client or self.native_client).open(path, **options)
        try:
            return response.status_code, response.get_json(silent=True), response.get_data(as_text=True)
        finally:
            response.close()

    def assert_forbidden(self, response):
        status, body, raw = response
        self.assertEqual(status, 403)
        self.assertIsInstance(body, dict)
        for name in self.sensitive_ids:
            self.assertNotIn(name, raw)
        for sensitive in (self.fixture.manager, self.fixture.approver, self.fixture.beneficiary,
                          self.fixture.employee, self.fixture.manager_employee,
                          "公开人员", "隐藏公司人员", "SYNTH-PRIVATE", "SYNTHETIC-PREVIEW-APPROVAL",
                          "snapshot_json", "policy_id", "subject_user", "content_digest"):
            self.assertNotIn(sensitive, raw)
        # Native Frappe PermissionError may retain a constant exception/stack
        # envelope. Its response must not include any target identity or facts.
        for key in ("items", "total", "docs"):
            self.assertIsNone(find_field(body, key))

    def unchanged(self):
        self.assertEqual(self.query.counts(), self.initial_counts)

    def test_rest_v1_v2_list_document_count_copy_meta_all_eight_types(self):
        for doctype, key in self.rows.items():
            encoded, record = quote(doctype, safe=""), quote(key, safe="")
            paths = (
                f"/api/resource/{encoded}", f"/api/resource/{encoded}/{record}",
                f"/api/v1/resource/{encoded}", f"/api/v1/resource/{encoded}/{record}",
                f"/api/v2/document/{encoded}", f"/api/v2/document/{encoded}/{record}",
                f"/api/v2/document/{encoded}/{record}/copy",
                f"/api/v2/doctype/{encoded}/count", f"/api/v2/doctype/{encoded}/meta",
            )
            for path in paths:
                with self.subTest(doctype=doctype, endpoint=path.split("/")[2:4]):
                    self.assert_forbidden(self.call("rest_v1_v2", path))
        self.unchanged()

    def test_native_client_rpc_list_count_document_value_permission_all_types(self):
        for doctype, key in self.rows.items():
            for method, params in (
                ("get_list", {"doctype": doctype, "fields": '["name"]'}),
                ("get_count", {"doctype": doctype}),
                ("get", {"doctype": doctype, "name": key}),
                ("get_value", {"doctype": doctype, "filters": key, "fieldname": "name"}),
                ("get_single_value", {"doctype": doctype, "field": "name"}),
                ("get_doc_permissions", {"doctype": doctype, "docname": key}),
            ):
                with self.subTest(doctype=doctype, method=method):
                    self.assert_forbidden(self.call("native_client_reads", "/api/method/frappe.client." + method, params))
            for prefix in ("/api/v1/method/", "/api/v2/method/"):
                self.assert_forbidden(self.call("native_client_reads", prefix + "frappe.client.get_list",
                                               {"doctype": doctype, "fields": '["name"]'}))
        self.unchanged()

    def test_desk_reportview_form_load_link_search_export_all_types(self):
        methods = (
            "frappe.desk.reportview.get", "frappe.desk.reportview.get_list",
            "frappe.desk.reportview.get_count", "frappe.desk.reportview.export_query",
            "frappe.desk.form.load.getdoc", "frappe.desk.form.load.get_docinfo",
            "frappe.desk.search.search_link", "frappe.desk.search.search_widget",
            "frappe.core.doctype.data_export.exporter.export_data",
            "frappe.core.doctype.data_import.data_import.download_template",
        )
        for doctype, key in self.rows.items():
            params = {"doctype": doctype, "name": key, "txt": "", "fields": '["name"]',
                      "file_format_type": "CSV"}
            for method in methods:
                with self.subTest(doctype=doctype, method=method):
                    self.assert_forbidden(self.call("desk_reads_export", "/api/method/" + method, params))
            for prefix in ("/desk/", "/app/"):
                self.assert_forbidden(self.call("desk_reads_export", prefix + doctype.lower().replace(" ", "-")))
        self.unchanged()

    def test_nested_client_insert_save_and_desk_flags_cannot_bypass(self):
        for doctype, key in self.rows.items():
            child = {"doctype": doctype, "name": key,
                     "flags": {"ignore_permissions": 1, "ignore_validate": 1}}
            nested = {"doctype": "User", "name": self.fixture.beneficiary,
                      "synthetic_children": [child], "flags": {"ignore_permissions": 1}}
            for method, doc in (("frappe.client.insert", child), ("frappe.client.save", child),
                                ("frappe.client.insert", nested), ("frappe.client.save", nested),
                                ("frappe.desk.form.save.savedocs", child)):
                with self.subTest(doctype=doctype, method=method, nested=doc is nested):
                    self.assert_forbidden(self.call("native_document_writes", "/api/method/" + method,
                        {"doc": json.dumps(doc), "action": "Save"}, method="POST", form=True))
        self.unchanged()

    def test_document_method_routes_and_legacy_cmd_cannot_return_protected_doc(self):
        for doctype, key in self.rows.items():
            doc = json.dumps({"doctype": doctype, "name": key, "flags": {"ignore_permissions": 1}})
            for method in ("frappe.handler.run_doc_method", "run_doc_method"):
                self.assert_forbidden(self.call("document_methods_legacy", "/api/method/" + method,
                    {"docs": doc, "method": "as_dict"}, method="POST", form=True))
            self.assert_forbidden(self.call("document_methods_legacy", "/api/v1/method/run_doc_method",
                {"dt": doctype, "dn": key, "method": "as_dict"}, method="POST", form=True))
            self.assert_forbidden(self.call("document_methods_legacy",
                f"/api/v2/document/{quote(doctype, safe='')}/{quote(key, safe='')}/method/as_dict",
                {}, method="POST"))
            self.assert_forbidden(self.call("document_methods_legacy", "/api/v2/method/run_doc_method",
                {"document": doc, "method": "as_dict"}, method="POST", form=True))
            self.assert_forbidden(self.call("document_methods_legacy",
                "/api/v2/method/" + quote(doctype, safe="") + "/as_dict", {}))
            self.assert_forbidden(self.call("document_methods_legacy", "/",
                {"cmd": "frappe.client.get", "doctype": doctype, "name": key}, method="POST", form=True))
            self.assert_forbidden(self.call("document_methods_legacy", "/",
                {"cmd": "run_doc_method", "dt": doctype, "dn": key, "method": "as_dict"}, method="POST", form=True))
        self.unchanged()

    def seed_report(self, doctype, *, reference=None):
        f = self.http.reconnect()
        key = self.fixture.prefix + "-READ-REPORT-" + uuid4().hex
        self.report_ids.append(key)
        f.db.sql("INSERT INTO `tabReport` (name,report_name,ref_doctype,report_type,is_standard,"
                 "disabled,reference_report,module,modified) VALUES (%s,%s,%s,%s,'No',0,%s,'HBOS Portal',NOW(6))",
                 (key, key, doctype, "Custom Report" if reference else "Query Report", reference))
        f.db.commit()
        return key

    def test_named_and_custom_reference_reports_resolve_server_protected_target(self):
        for doctype in PROTECTED:
            direct = self.seed_report(doctype)
            disguised = self.seed_report("User", reference=direct)
            for report in (direct, disguised):
                for method in ("frappe.desk.query_report.run", "frappe.desk.query_report.get_script"):
                    with self.subTest(doctype=doctype, custom=report == disguised, method=method):
                        self.assert_forbidden(self.call("named_custom_reports", "/api/method/" + method,
                            {"report_name": report, "doctype": "User", "filters": "{}"}))
        self.unchanged()

    def test_admin_and_system_manager_model_permission_and_query_guard(self):
        f = self.http.reconnect()
        for user in ("Administrator", self.fixture.beneficiary):
            f.set_user(user)
            for doctype, key in self.rows.items():
                doc = f.get_doc(doctype, key)
                # Internal load is not a public query. The document's permission
                # overrides must also reject Administrator and client flags.
                for ignore in (False, True):
                    doc.flags.ignore_permissions = ignore
                    self.assertIs(doc.has_permission("read"), False)
                    with self.assertRaises(f.PermissionError):
                        doc.check_permission("read")
                    type(self).model_checks += 2
                with self.assertRaises(f.PermissionError):
                    f.get_list(doctype, fields=["name"], limit_page_length=1)
                type(self).model_checks += 1
        f.set_user("Administrator")
        self.unchanged()

    def test_explicit_native_docshare_does_not_open_managed_storage(self):
        f = self.http.reconnect()
        for doctype, key in self.rows.items():
            share = self.fixture.prefix + "-READ-SHARE-" + uuid4().hex
            self.share_ids.append(share)
            f.db.sql("INSERT INTO `tabDocShare` (name,share_doctype,share_name,user,`read`,`write`,"
                     "`share`,everyone,modified) VALUES (%s,%s,%s,%s,1,0,0,0,NOW(6))",
                     (share, doctype, key, self.fixture.beneficiary))
        f.db.commit()
        f.clear_cache(user=self.fixture.beneficiary)
        for doctype, key in self.rows.items():
            for method, params in (("get", {"doctype": doctype, "name": key}),
                                   ("get_list", {"doctype": doctype, "fields": '["name"]'})):
                self.assert_forbidden(self.call("docshare_reads", "/api/method/frappe.client." + method, params))
        # Frappe's trusted-server no-role shared-row branch can bypass permission
        # query conditions. This is not an externally callable SQL sandbox: the
        # HTTP request guard above must reject before that native branch runs.
        f = self.http.reconnect()
        f.set_user(self.fixture.beneficiary)
        try:
            values = f.get_list(PROTECTED[0], fields=["name"], limit_page_length=1)
        except f.PermissionError:
            type(self).trusted_internal_share_query = "DENIED"
        else:
            self.assertLessEqual(len(values), 1)
            type(self).trusted_internal_share_query = (
                "NATIVE_SHARED_ROW_BRANCH_ALLOWED_TRUSTED_SERVER_ONLY" if values else "NO_ROWS")
        f.set_user("Administrator")
        self.unchanged()

    def test_personnel_directory_phone_rejected_before_query_and_name_is_literal(self):
        path = "/api/method/hbos_portal.api.people_access.get_people"
        original = self.native.get_list
        selected = []

        def observe(doctype, *args, **kwargs):
            if getattr(self.native.local, "request", None) and self.native.local.request.path == path:
                selected.append(doctype)
            return original(doctype, *args, **kwargs)

        with patch.object(self.native, "get_list", observe):
            for source in ("User", "Employee"):
                response = self.call("native_personnel_directory", path, {"source": source, "phone": "138"})
                # Existing Portal call_safely contract carries semantic errors
                # in the ordinary HTTP 200 envelope, without running a query.
                self.assertEqual(response[0], 200)
                self.assertEqual(find_field(response[1], "code"), "INVALID_REQUEST")
                self.assertIsNone(find_field(response[1], "items"))
        self.assertEqual(selected, [])
        f = self.http.reconnect()
        label = "目录字面%_\\尾"
        f.db.sql("UPDATE `tabUser` SET full_name=%s WHERE name=%s", (label, self.fixture.beneficiary))
        f.db.commit()
        f.clear_cache(user=self.fixture.beneficiary)
        for keyword, expected in (("%_\\", 1), ("未出现%_", 0)):
            response = self.call("native_personnel_directory", path, {"source": "User", "name": keyword})
            self.assertEqual(response[0], 200)
            data = find_field(response[1], "data")
            self.assertIsInstance(data, dict)
            self.assertEqual(data["total"], expected)
            self.assertEqual(data["authorization_domain"], "native_personnel")
            self.assertIs(data["management_policy_applied"], False)
            self.assertIs(data["position_authorization_connected"], False)
            for item in data["items"]:
                self.assertNotIn("SYNTH-PRIVATE", item["phone"])
        self.unchanged()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("preflight", "test"), default="preflight")
    parser.add_argument("--expected-database-sha256", required=True)
    args = parser.parse_args()
    if args.phase == "test" and not NATIVE_SPEC_READY:
        raise RuntimeError("NATIVE_BOUNDARY_ACCEPTANCE_SPEC_REQUIRED")
    import frappe
    frappe.init(site=SITE, sites_path=".")
    frappe.connect()
    try:
        frappe.db.sql("START TRANSACTION READ ONLY")
        report = check_target(frappe, args.expected_database_sha256)
        report["preflight"] = preflight(frappe)
        report["policy_tables_present"] = policy_presence(frappe)
        if not all(report["preflight"]["tables_present"].values()) or not all(report["policy_tables_present"].values()):
            raise RuntimeError("MANAGED_SCHEMA_REQUIRED")
        if any(frappe.db.count(kind) for kind in (*KINDS, *POLICY_KINDS)):
            raise RuntimeError("MANAGED_TABLES_NOT_EMPTY")
        report["relation_schema"] = schema_check(frappe)
        report["policy_schema"] = policy_schema_check(frappe)
        frappe.db.rollback()
        if args.phase == "test":
            before, extra_before = native_fingerprints(frappe), extra_fingerprints(frappe)
            hook = "hbos_portal.organization.native_read_boundary.before_request"
            if hook not in frappe.get_hooks("before_request", app_name="hbos_portal"):
                raise RuntimeError("NATIVE_BOUNDARY_HOOK_NOT_REGISTERED")
            # Explicit test-phase only. Redis keys are scoped to this exact
            # Preview Site; preflight and original-site caches remain untouched.
            frappe.cache.delete_value("app_hooks")
            if hook not in frappe.get_hooks("before_request"):
                raise RuntimeError("NATIVE_BOUNDARY_HOOK_NOT_LOADED")
            report["preview_hooks_cache_refresh"] = "Exact Preview site-scoped app_hooks key in explicit test phase only"
            NativeReadBoundaryCases.native = frappe
            NativeReadBoundaryCases.request_counts, NativeReadBoundaryCases.model_checks = {}, 0
            NativeReadBoundaryCases.trusted_internal_share_query = "NOT_RUN"
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeReadBoundaryCases)
            names = [test.id().rsplit(".", 1)[1] for test in suite]
            if len(names) != 9:
                raise RuntimeError("NATIVE_BOUNDARY_ACCEPTANCE_CASES_INCOMPLETE")
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            frappe.init(site=SITE, sites_path=".", force=True)
            frappe.connect()
            frappe.set_user("Administrator")
            report["tests_run"] = result.testsRun
            report["test_names"] = names
            report["test_status"] = "PASS" if result.wasSuccessful() else "FAIL"
            report["native_preservation"] = "PASS" if native_fingerprints(frappe) == before else "FAIL"
            report["report_docshare_preservation"] = "PASS" if extra_fingerprints(frappe) == extra_before else "FAIL"
            report["final_native_counts"] = preflight(frappe)["native_counts"]
            report["final_managed_counts"] = {kind: frappe.db.count(kind) for kind in (*KINDS, *POLICY_KINDS)}
            report["tables_empty"] = not any(report["final_managed_counts"].values())
            report["http_requests_by_category"] = NativeReadBoundaryCases.request_counts
            report["http_requests"] = sum(NativeReadBoundaryCases.request_counts.values())
            report["model_permission_checks"] = NativeReadBoundaryCases.model_checks
            report["trusted_internal_share_query"] = NativeReadBoundaryCases.trusted_internal_share_query
            report["real_native_password_session"] = True
            report["administrator_http"] = "NOT_RUN"
            report["limits"] = ("System Manager HTTP and Administrator model only; no Administrator password/session "
                "fabrication, real management activation, schema action, business grant, original-site write or full restore. "
                "Enumerated native storage routes only; arbitrary custom SQL reports and future RPCs not universally audited.")
            print(json.dumps(report, ensure_ascii=False, default=str))
            if (not result.wasSuccessful() or not report["tables_empty"] or report["native_preservation"] != "PASS"
                    or report["report_docshare_preservation"] != "PASS"):
                raise SystemExit(1)
        else:
            print(json.dumps(report, ensure_ascii=False, default=str))
    finally:
        if getattr(frappe.local, "db", None):
            frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
