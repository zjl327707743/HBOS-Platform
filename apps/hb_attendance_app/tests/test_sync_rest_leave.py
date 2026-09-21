import unittest
from pathlib import Path

SRC = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/sync_rest_leave.py")


class SyncRestLeaveContractTest(unittest.TestCase):
    def setUp(self):
        self.src = SRC.read_text()

    def test_uses_pure_module(self):
        self.assertIn("from hb_attendance_app.hbos_attendance.rest_leave import", self.src)
        self.assertIn("rest_leave_fields", self.src)

    def test_writes_rest_leave_doctype(self):
        self.assertIn('"HBOS Rest Leave Record"', self.src)

    def test_reads_correct_table(self):
        self.assertIn("REST_LEAVE_APP_TOKEN", self.src)
        self.assertIn("REST_LEAVE_TABLE_ID", self.src)

    def test_unique_key_prefix(self):
        self.assertIn("ID_PREFIX", self.src)

    def test_is_whitelisted_entry(self):
        self.assertIn("@frappe.whitelist()", self.src)
        self.assertIn("def sync_rest_leave_from_bitable(", self.src)

    def test_no_throw_in_scheduler_path(self):
        """调度任务里抛异常会打断调度链；失败必须记日志并返回摘要。"""
        self.assertNotIn("frappe.throw(", self.src)

    def test_reports_unmatched_instead_of_silent_skip(self):
        self.assertIn("unmatched", self.src)

    def test_status_map_reused_from_api(self):
        self.assertIn("STATUS_MAP", self.src)

    def test_does_not_touch_attendance_generation(self):
        """本阶段不接判定：不得触发配对/重算。"""
        self.assertNotIn("regenerate_attendance", self.src)
        self.assertNotIn("pair_employee_checkins", self.src)


if __name__ == "__main__":
    unittest.main()
