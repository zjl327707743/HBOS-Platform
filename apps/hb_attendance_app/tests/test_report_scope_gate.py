"""Keep legacy Script Reports closed to department-scoped HR accounts."""
from __future__ import annotations

import sys
import types
import unittest
import ast
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


class Denied(Exception):
    pass


def frappe_stub(visible, total, user="hr@example.com"):
    def throw(message, exc=Denied):
        raise Denied(str(message))

    return types.SimpleNamespace(
        session=types.SimpleNamespace(user=user),
        get_list=lambda doctype, **kwargs: list(visible),
        db=types.SimpleNamespace(count=lambda doctype: total),
        PermissionError=Denied,
        throw=throw,
    )


@contextmanager
def scope_environment(visible, total, user="hr@example.com", *, conditions=None,
                      read_types=None, shared_only=(), query_error=None):
    """Model native scope proof separately from the employee row count."""
    fake = frappe_stub(visible, total, user)
    checked = []

    class DatabaseQuery:
        def __init__(self, doctype, user=None):
            self.doctype = doctype
            self.conditions = ["shared rows only"] if doctype in shared_only else []
            self.fields = None

        def check_read_permission(self, doctype):
            checked.append(doctype)
            return (read_types or {}).get(doctype, "read")

        def build_match_conditions(self):
            if query_error:
                raise query_error
            return (conditions or {}).get(self.doctype, "")

    with patch.dict(sys.modules, {
        "frappe": fake,
        "frappe.model.db_query": types.SimpleNamespace(DatabaseQuery=DatabaseQuery),
    }):
        sys.modules.pop("hb_attendance_app.hbos_attendance.report_scope", None)
        from hb_attendance_app.hbos_attendance.report_scope import require_unrestricted_employee_read
        yield require_unrestricted_employee_read, checked
    sys.modules.pop("hb_attendance_app.hbos_attendance.report_scope", None)


class ReportScopeGateTest(unittest.TestCase):
    def scope(self, visible, total, user="hr@example.com"):
        with scope_environment(visible, total, user) as (guard, _):
            return guard()

    def test_unrestricted_hr_can_use_legacy_report(self):
        self.assertIsNone(self.scope(["EMP-A", "EMP-B"], 2))

    def test_department_scoped_hr_is_denied(self):
        with self.assertRaisesRegex(Denied, "部分员工"):
            self.scope(["EMP-A"], 2)

    def test_guest_cannot_run_legacy_report(self):
        with self.assertRaisesRegex(Denied, "登录"):
            self.scope(["EMP-A"], 1, user="Guest")

    def test_invalid_visibility_response_denied(self):
        fake = frappe_stub([], 1)
        fake.get_list = lambda *args, **kwargs: None
        with patch.dict(sys.modules, {"frappe": fake}):
            sys.modules.pop("hb_attendance_app.hbos_attendance.report_scope", None)
            from hb_attendance_app.hbos_attendance.report_scope import (
                require_unrestricted_employee_read,
            )
            with self.assertRaisesRegex(Denied, "无法核实"):
                require_unrestricted_employee_read()

    def test_all_current_employees_visible_is_not_unrestricted_authority(self):
        with scope_environment(["EMP-A"], 1, conditions={"Employee": "department in ('A')"}) as (guard, _):
            with self.assertRaisesRegex(Denied, "部分员工"):
                guard()

    def test_zero_equals_zero_does_not_authorize_scoped_historical_data(self):
        with scope_environment([], 0, conditions={"Employee": "department in ('A')"}) as (guard, _):
            with self.assertRaisesRegex(Denied, "部分员工"):
                guard("HBOS Attendance Import Log")

    def test_genuinely_unrestricted_hr_can_read_history_with_no_employee_rows(self):
        with scope_environment([], 0) as (guard, checked):
            self.assertIsNone(guard("Attendance", "Employee Checkin", "HBOS Attendance Import Log"))
            self.assertIn("Employee", checked)

    def test_actual_report_sources_must_also_be_unscoped(self):
        sources = ("Attendance", "Employee Checkin", "HBOS Leave Record",
                   "HBOS Attendance Import Log", "HBOS Shift Rule")
        for doctype in sources:
            with self.subTest(doctype=doctype), scope_environment(
                ["EMP-A", "EMP-B"], 2, conditions={doctype: "owner = 'restricted-user'"}
            ) as (guard, _):
                with self.assertRaisesRegex(Denied, "部分员工"):
                    guard(doctype)

    def test_select_permission_is_not_permission_to_read_raw_source_rows(self):
        with scope_environment(["EMP-A"], 1, read_types={"Attendance": "select"}) as (guard, _):
            with self.assertRaises(Denied):
                guard("Attendance")

    def test_shared_only_access_does_not_authorize_raw_report(self):
        with scope_environment(["EMP-A"], 1, shared_only=("Attendance",)) as (guard, _):
            with self.assertRaises(Denied):
                guard("Attendance")

    def test_scope_builder_error_fails_closed_without_error_details(self):
        with scope_environment(["EMP-A"], 1, query_error=RuntimeError("secret SQL")) as (guard, _):
            with self.assertRaisesRegex(Denied, "无法核实") as caught:
                guard()
            self.assertNotIn("secret SQL", str(caught.exception))

    def test_invalid_scope_builder_response_fails_closed(self):
        with scope_environment(["EMP-A"], 1, conditions={"Employee": None}) as (guard, _):
            with self.assertRaisesRegex(Denied, "无法核实"):
                guard()

    def test_unrelated_warehouse_scope_does_not_disable_attendance_reports(self):
        with scope_environment(["EMP-A"], 1, conditions={"Warehouse": "name = 'A'"}) as (guard, checked):
            self.assertIsNone(guard("Attendance"))
            self.assertNotIn("Warehouse", checked)

    def test_all_four_raw_reports_have_server_side_guard(self):
        root = Path(__file__).parents[1] / "hb_attendance_app" / "hbos_attendance" / "report"
        reports = {
            "月度考勤汇总": {"Attendance", "Employee Checkin", "HBOS Leave Record"},
            "打卡流水": {"Employee Checkin", "HBOS Shift Rule"},
            "考勤结果": {"Attendance", "Employee Checkin"},
            "hbos_月度汇总暂存（对账）": {"HBOS Attendance Import Log"},
        }
        for name, expected_sources in reports.items():
            with self.subTest(report=name):
                source = (root / name / f"{name}.py").read_text(encoding="utf-8")
                execute = next(node for node in ast.parse(source).body
                               if isinstance(node, ast.FunctionDef) and node.name == "execute")
                first_call = next(node.value for node in execute.body
                                  if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call))
                self.assertEqual(first_call.func.id, "require_unrestricted_employee_read")
                self.assertEqual({ast.literal_eval(arg) for arg in first_call.args}, expected_sources)


if __name__ == "__main__":
    unittest.main(verbosity=2)
