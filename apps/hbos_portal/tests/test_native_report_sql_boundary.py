"""Stored Query Report SQL must not hide the eight protected IAM tables.

These are synthetic request-classification contracts, not live Site acceptance.
Trusted Script Report code, database views/functions and arbitrary server SQL
remain outside this targeted guard; they require separate source/runtime review.
"""
from types import SimpleNamespace
import unittest

from hbos_portal.organization.native_read_boundary import (
    before_request, is_protected_request, protected_doctypes,
)


class Denied(Exception):
    pass


class NativeReportSQLBoundaryTests(unittest.TestCase):
    path = "/api/method/frappe.desk.query_report.run"
    params = {"report_name": "synthetic-public-label"}

    @staticmethod
    def report(query, **overrides):
        return {"ref_doctype": "Employee", "report_type": "Query Report",
                "query": query, **overrides}

    def test_public_ref_doctype_cannot_hide_any_protected_table_in_saved_sql(self):
        for kind in protected_doctypes():
            with self.subTest(doctype=kind):
                report = self.report(f"SELECT name FROM `tab{kind}`")
                self.assertTrue(is_protected_request(self.path, self.params, lambda _: report))

    def test_table_reference_check_is_case_insensitive(self):
        for name in ("tabHBOS Position", "TABHBOS POSITION", "tabhbos position"):
            with self.subTest(name=name):
                report = self.report(f"SELECT name FROM `{name}`")
                self.assertTrue(is_protected_request(self.path, self.params, lambda _: report))

    def test_protected_reference_in_join_cte_or_subquery_is_denied(self):
        queries = (
            "SELECT e.name FROM tabEmployee e JOIN `tabHBOS Position` p ON 1=1",
            "WITH p AS (SELECT name FROM `tabHBOS Position`) SELECT * FROM p",
            "SELECT name FROM tabEmployee WHERE EXISTS (SELECT 1 FROM `tabHBOS Position`)",
        )
        for query in queries:
            with self.subTest(query=query):
                self.assertTrue(is_protected_request(self.path, self.params,
                                                     lambda _: self.report(query)))

    def test_custom_reference_chain_checks_the_terminal_saved_query(self):
        reports = {
            "synthetic-public-label": {"ref_doctype": "User", "report_type": "Custom Report",
                                       "reference_report": "synthetic-query"},
            "synthetic-query": self.report("SELECT name FROM `tabHBOS Organization Management Policy`"),
        }
        self.assertTrue(is_protected_request(self.path, self.params, reports.get))

    def test_client_query_cannot_replace_saved_sql_for_authorization(self):
        params = {**self.params, "doctype": "Employee", "query": "SELECT 1"}
        report = self.report("SELECT name FROM `tabHBOS Position`")
        self.assertTrue(is_protected_request(self.path, params, lambda _: report))

    def test_native_report_entry_variants_share_the_same_guard(self):
        report = self.report("SELECT name FROM `tabHBOS Personnel Assignment`")
        for prefix in ("/api/method/", "/api/v1/method/", "/api/v2/method/"):
            for method in ("run", "get_script"):
                with self.subTest(prefix=prefix, method=method):
                    self.assertTrue(is_protected_request(
                        prefix + "frappe.desk.query_report." + method, self.params, lambda _: report))
        self.assertTrue(is_protected_request("/", {**self.params, "cmd": "frappe.desk.query_report.run"},
                                             lambda _: report))

    def test_before_request_fetches_saved_query_without_executing_it(self):
        statements = []
        def metadata_sql(statement, values, as_dict=False):
            statements.append((statement, values))
            result = {"ref_doctype": "Employee", "report_type": "Query Report",
                      "reference_report": None}
            if "`query`" in statement:
                result["query"] = "SELECT name FROM `tabHBOS Position`"
            return [result]
        native = SimpleNamespace(
            PermissionError=Denied,
            local=SimpleNamespace(request=SimpleNamespace(path=self.path)),
            form_dict=dict(self.params), db=SimpleNamespace(sql=metadata_sql),
        )
        with self.assertRaises(Denied):
            before_request(native=native)
        self.assertEqual(len(statements), 1)
        self.assertIn("FROM `tabReport` WHERE name=%s", statements[0][0])
        self.assertIn("`query`", statements[0][0])
        self.assertEqual(statements[0][1], ("synthetic-public-label",))

    def test_ordinary_employee_query_is_not_blocked(self):
        report = self.report("SELECT name FROM tabEmployee WHERE status = %(status)s")
        self.assertFalse(is_protected_request(self.path, self.params, lambda _: report))

    def test_unrelated_script_and_builder_reports_are_not_taken_over(self):
        for kind in ("Script Report", "Report Builder"):
            with self.subTest(report_type=kind):
                report = {"ref_doctype": "Employee", "report_type": kind}
                self.assertFalse(is_protected_request(self.path, self.params, lambda _: report))

    def test_malformed_saved_query_fails_closed(self):
        for query in ([], {}, 42, False):
            with self.subTest(query=query):
                self.assertTrue(is_protected_request(self.path, self.params,
                                                     lambda _: self.report(query)))

    def test_oversized_saved_query_fails_closed(self):
        report = self.report("SELECT 1 /*" + "x" * 65536 + "*/")
        self.assertTrue(is_protected_request(self.path, self.params, lambda _: report))

    def test_protected_name_in_sql_literal_is_conservatively_denied(self):
        # Intentionally not a SQL sandbox/parser: false positives are preferred
        # to silently permitting this protected-table marker through native SQL.
        report = self.report("SELECT 'tabHBOS Position' AS label")
        self.assertTrue(is_protected_request(self.path, self.params, lambda _: report))


if __name__ == "__main__":
    unittest.main()
