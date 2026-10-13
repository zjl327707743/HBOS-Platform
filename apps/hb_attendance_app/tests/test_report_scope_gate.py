"""Keep legacy Script Reports closed to department-scoped HR accounts."""
from __future__ import annotations

import sys
import types
import unittest
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


class ReportScopeGateTest(unittest.TestCase):
    def scope(self, visible, total, user="hr@example.com"):
        fake = frappe_stub(visible, total, user)
        with patch.dict(sys.modules, {"frappe": fake}):
            sys.modules.pop("hb_attendance_app.hbos_attendance.report_scope", None)
            from hb_attendance_app.hbos_attendance.report_scope import (
                require_unrestricted_employee_read,
            )
            return require_unrestricted_employee_read()

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

    def test_all_four_raw_reports_have_server_side_guard(self):
        root = Path(__file__).parents[1] / "hb_attendance_app" / "hbos_attendance" / "report"
        reports = (
            "月度考勤汇总",
            "打卡流水",
            "考勤结果",
            "hbos_月度汇总暂存（对账）",
        )
        for name in reports:
            with self.subTest(report=name):
                source = (root / name / f"{name}.py").read_text(encoding="utf-8")
                self.assertIn(
                    "require_unrestricted_employee_read()",
                    source.split("def execute(filters=None):", 1)[1].split("\n", 6)[0:6].__str__(),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
