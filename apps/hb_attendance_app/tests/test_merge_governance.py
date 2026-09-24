import re
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
RULE_LISTS = APP / "rule_lists.py"
PAIRING = APP / "pairing.py"
ROTATION = APP / "rotation_schedule.py"
REST_LEAVE = APP / "rest_leave.py"
AI_REVIEW = APP / "ai_review.py"
REPO = Path(__file__).parents[3]
ENV_EXAMPLE = REPO / ".env.example"


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

    def test_runtime_sources_do_not_embed_employee_policy_memberships(self):
        for path in (RULE_LISTS, PAIRING, ROTATION, API, ROSTER):
            src = path.read_text()
            self.assertIsNone(
                re.search(r"\b(?:100|110)\d{5}\b", src),
                f"{path.name} must not embed production employee numbers",
            )
            self.assertIsNone(
                re.search(r"HB-[\u4e00-\u9fff]{2,}", src),
                f"{path.name} must not embed employee names",
            )

    def test_external_resource_ids_are_configuration_not_source_literals(self):
        for path in (API, REST_LEAVE):
            src = path.read_text()
            self.assertIsNone(re.search(r'["\']tbl[A-Za-z0-9]{8,}["\']', src))
            self.assertIsNone(re.search(r'["\'][A-Za-z0-9]{20,}["\']', src))
        env = ENV_EXAMPLE.read_text()
        for key in (
            "HBOS_FEISHU_LEAVE_APP_TOKEN",
            "HBOS_FEISHU_OVERTIME_APP_TOKEN",
            "HBOS_FEISHU_REST_LEAVE_APP_TOKEN",
            "HBOS_FEISHU_EXCEPTION_APP_TOKEN",
        ):
            self.assertIn(key, env)

    def test_external_writes_and_ai_are_default_off(self):
        env = ENV_EXAMPLE.read_text()
        self.assertIn("HBOS_FEISHU_SYNC_ENABLED=0", env)
        self.assertIn("HBOS_DELICLOUD_SYNC_ENABLED=0", env)
        self.assertIn("HBOS_AI_ENABLED=0", env)
        self.assertIn("HBOS_AI_ALLOW_PII=0", env)
        ai = AI_REVIEW.read_text()
        self.assertIn('"enabled": _env_flag("HBOS_AI_ENABLED")', ai)
        self.assertIn('"allow_pii": _env_flag("HBOS_AI_ALLOW_PII")', ai)

    def test_legacy_duplicate_engines_are_absent(self):
        for name in (
            "daily_feishu_sync.py",
            "pair_checkins.py",
            "shift_matcher.py",
            "generate_attendance.py",
        ):
            self.assertFalse((APP / name).exists(), name)

    def test_delicloud_cursor_advances_only_after_successful_writes(self):
        src = API.read_text()
        self.assertIn("if all_recs and write_failed == 0:", src)
        self.assertIn('"cursor_advanced": cursor_advanced', src)

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
