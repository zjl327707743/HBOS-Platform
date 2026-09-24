import json
import unittest
from pathlib import Path

DT = (Path(__file__).parents[1]
      / "hb_attendance_app/hbos_attendance/doctype/hbos_rest_leave_record")


def load():
    return json.loads((DT / "hbos_rest_leave_record.json").read_text())


class RestLeaveDocTypeTest(unittest.TestCase):
    def test_identity(self):
        d = load()
        self.assertEqual(d["name"], "HBOS Rest Leave Record")
        self.assertEqual(d["module"], "HBOS Attendance")
        self.assertEqual(d["autoname"], "field:feishu_approval_id")

    def test_leave_template_fields(self):
        """模板与请假一致：这些字段一个都不能少。"""
        fields = [f["fieldname"] for f in load()["fields"]]
        for f in ("employee", "employee_name", "employee_number", "department",
                  "start_date", "end_date", "rest_days", "feishu_approval_id",
                  "approval_status", "feishu_sync_time", "remarks"):
            self.assertIn(f, fields, f"缺少模板字段 {f}")

    def test_own_fields(self):
        fields = [f["fieldname"] for f in load()["fields"]]
        for f in ("overtime_dates", "parsed_at", "verify_status", "verify_time"):
            self.assertIn(f, fields, f"缺少自有字段 {f}")

    def test_verify_status_options_match_pure_module(self):
        """Select 选项必须与 rest_leave.py 的常量逐字一致，否则落库会报错。"""
        from hb_attendance_app.hbos_attendance.rest_leave import ALL_STATUSES
        f = [x for x in load()["fields"] if x["fieldname"] == "verify_status"][0]
        self.assertEqual(f["fieldtype"], "Select")
        self.assertEqual(set(f["options"].split("\n")), set(ALL_STATUSES))

    def test_default_status_is_parse_pending(self):
        f = [x for x in load()["fields"] if x["fieldname"] == "verify_status"][0]
        self.assertEqual(f["default"], "待解析")

    def test_feishu_id_unique(self):
        f = [x for x in load()["fields"] if x["fieldname"] == "feishu_approval_id"][0]
        self.assertEqual(f.get("unique"), 1)

    def test_three_role_permissions(self):
        roles = sorted(p["role"] for p in load()["permissions"])
        self.assertEqual(roles, ["HR Manager", "HR User", "System Manager"])


if __name__ == "__main__":
    unittest.main()
