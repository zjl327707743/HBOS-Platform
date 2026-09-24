import unittest
from pathlib import Path

APP = Path(__file__).parents[1] / "hb_attendance_app" / "hbos_attendance"
API = APP / "api.py"
EMP = APP / "page" / "hbos_employee_management" / "employee_management_data.py"
SHIFT = APP / "page" / "hbos_shift_management" / "shift_management_data.py"
EXPORT = APP / "report" / "月度考勤汇总" / "export.py"
ROSTER = APP / "roster_export.py"
HOOKS = Path(__file__).parents[1] / "hb_attendance_app" / "hooks.py"
SETUP = APP / "setup.py"


class MergeGovernanceTest(unittest.TestCase):
    def test_regeneration_never_deletes_after_requested_range(self):
        src = API.read_text()
        self.assertNotIn("attendance_date > %s", src)
        self.assertIn("attendance_date BETWEEN %s AND %s", src)

    def test_regeneration_has_no_commit_between_delete_and_rebuild(self):
        src = API.read_text()
        delete_at = src.index("DELETE FROM tabAttendance")
        rebuild_at = src.index("# 对每个员工做贪心配对")
        window = src[delete_at:rebuild_at]
        self.assertNotIn("frappe.db.commit()", window)

    def test_hr_management_endpoints_have_server_side_guards(self):
        emp = EMP.read_text()
        shift = SHIFT.read_text()
        self.assertIn("def _require_hr_read", emp)
        self.assertIn("def _require_hr_write", emp)
        self.assertIn("def _require_hr_read", shift)
        self.assertIn("def _require_hr_write", shift)

    def test_exports_are_private(self):
        for path in (EXPORT, ROSTER):
            src = path.read_text()
            self.assertNotIn('"is_private": 0', src)
            self.assertIn('"is_private": 1', src)
            self.assertIn("def _require_export_permission", src)

    def test_schedule_import_rejects_server_paths(self):
        src = SHIFT.read_text()
        self.assertIn("不允许通过 API 读取服务器任意文件路径", src)

    def test_rest_leave_is_one_ordered_scheduler_job(self):
        src = HOOKS.read_text()
        self.assertIn("sync_rest_leave_pipeline", src)
        self.assertNotIn(
            '"hb_attendance_app.hbos_attendance.sync_rest_leave.parse_pending_rest_leaves"',
            src,
        )
        self.assertNotIn(
            '"hb_attendance_app.hbos_attendance.sync_rest_leave.verify_pending_rest_leaves"',
            src,
        )

    def test_clean_site_declares_runtime_custom_fields(self):
        src = SETUP.read_text()
        for field in (
            "hbos_fixed_shift",
            "hbos_terminal_sn",
            "hbos_delicloud_id",
            "hbos_employee_num",
            "hbos_dept_name",
            "hbos_check_type",
        ):
            self.assertIn(f'"fieldname": "{field}"', src)


if __name__ == "__main__":
    unittest.main()
