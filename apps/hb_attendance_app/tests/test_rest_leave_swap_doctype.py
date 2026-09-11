import json
import unittest
from pathlib import Path

DT = (Path(__file__).parents[1]
      / "hb_attendance_app/hbos_attendance/doctype")


def load(name):
    return json.loads((DT / name / (name + ".json")).read_text())


class DocTypeExistsTest(unittest.TestCase):
    def test_rest_leave_doctype(self):
        d = load("hbos_rest_leave_record")
        self.assertEqual(d["name"], "HBOS Rest Leave Record")
        self.assertEqual(d["autoname"], "field:feishu_approval_id")
        self.assertEqual(d["module"], "HBOS Attendance")
        fields = [f["fieldname"] for f in d["fields"]]
        for f in ("employee", "start_date", "end_date", "rest_days",
                  "approval_status", "feishu_approval_id", "feishu_sync_time", "remarks"):
            self.assertIn(f, fields)

    def test_shift_swap_doctype(self):
        d = load("hbos_shift_swap_record")
        self.assertEqual(d["name"], "HBOS Shift Swap Record")
        self.assertEqual(d["autoname"], "field:feishu_approval_id")
        fields = [f["fieldname"] for f in d["fields"]]
        for f in ("applicant", "substitute", "swap_date", "repay_date",
                  "approval_status", "feishu_approval_id", "feishu_sync_time", "remarks"):
            self.assertIn(f, fields)

    def test_both_have_three_role_permissions(self):
        for name in ("hbos_rest_leave_record", "hbos_shift_swap_record"):
            roles = sorted(p["role"] for p in load(name)["permissions"])
            self.assertEqual(roles, ["HR Manager", "HR User", "System Manager"])

    def test_feishu_id_unique(self):
        for name in ("hbos_rest_leave_record", "hbos_shift_swap_record"):
            f = [x for x in load(name)["fields"] if x["fieldname"] == "feishu_approval_id"][0]
            self.assertEqual(f.get("unique"), 1)


if __name__ == "__main__":
    unittest.main()
