import unittest
from pathlib import Path

SRC = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/sync_rest_leave.py")


class SyncRestLeaveContractTest(unittest.TestCase):
    def setUp(self):
        self.src = SRC.read_text()

    def test_uses_shared_mapping(self):
        self.assertIn("from hb_attendance_app.hbos_attendance.swap_mapping import", self.src)
        self.assertIn("rest_leave_fields", self.src)

    def test_reads_correct_table(self):
        self.assertIn("REST_LEAVE_APP_TOKEN", self.src)
        self.assertIn("REST_LEAVE_TABLE_ID", self.src)

    def test_only_approved_records(self):
        self.assertIn('"已通过"', self.src)

    def test_unique_key_prefix(self):
        self.assertIn("feishu-bitable-restleave-", self.src)

    def test_is_whitelisted_entry(self):
        self.assertIn("@frappe.whitelist()", self.src)
        self.assertIn("def sync_rest_leave_from_bitable(", self.src)

    def test_does_not_touch_attendance_generation(self):
        # 只读登记：不得触发配对/重算
        self.assertNotIn("regenerate_attendance", self.src)
        self.assertNotIn("pair_employee_checkins", self.src)


if __name__ == "__main__":
    unittest.main()
