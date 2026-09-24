import unittest
from pathlib import Path

from hb_attendance_app.hbos_attendance.roster_classify import classify, LIST_SYSTEMS

APP = Path(__file__).parents[1] / "hb_attendance_app"
ROSTER = APP / "hbos_attendance/roster_export.py"
JS = APP / "hbos_attendance/page/hbos_shift_management/hbos_shift_management.js"


class RosterClassifyTest(unittest.TestCase):
    def setUp(self):
        self.policies = {
            "EXEMPT": {"EMP-EX"},
            "SPECIAL_SHIFT": {"EMP-SP"},
            "FOUR_SHIFT": {"EMP-FOUR"},
            "ADMIN": {"EMP-ADMIN"},
            "SAFETY": {"EMP-SAFE"},
            "FOOD": {"EMP-FOOD"},
        }

    def test_exempt_returns_empty(self):
        self.assertEqual(classify("EMP-EX", policies=self.policies), "")

    def test_bound_shift_type_beats_list(self):
        self.assertEqual(classify("EMP-ADMIN", "早班", self.policies), "早班")

    def test_policy_members_map_to_system(self):
        self.assertEqual(classify("EMP-SP", policies=self.policies), "无菌倒班")
        self.assertEqual(classify("EMP-FOUR", policies=self.policies), "四班次倒班")
        self.assertEqual(classify("EMP-ADMIN", policies=self.policies), "行政班")
        self.assertEqual(classify("EMP-SAFE", policies=self.policies), "安全倒班")
        self.assertEqual(classify("EMP-FOOD", policies=self.policies), "食堂")

    def test_unknown_goes_generic(self):
        self.assertEqual(classify("EMP-GENERIC", policies=self.policies), "通用倒班")

    def test_list_systems_has_five_runtime_policy_groups(self):
        self.assertEqual([label for _, label in LIST_SYSTEMS],
                         ["无菌倒班", "四班次倒班", "行政班", "安全倒班", "食堂"])


class RosterExportContractTest(unittest.TestCase):
    def test_export_module_declares_whitelisted_endpoint(self):
        content = ROSTER.read_text()
        self.assertIn("@frappe.whitelist()", content)
        self.assertIn("def export_shift_roster(", content)
        self.assertIn("openpyxl", content)
        self.assertIn("from hb_attendance_app.hbos_attendance.roster_classify import classify, LIST_SYSTEMS", content)

    def test_export_builds_five_sheets_and_classify_rows(self):
        content = ROSTER.read_text()
        for sheet in ("部门-班次-人员", "豁免人员", "特殊班次", "行政班名单", "说明"):
            self.assertIn(sheet, content)
        self.assertIn("通用倒班", content)
        self.assertIn("{name}({num})", content)

    def test_js_has_export_button(self):
        content = JS.read_text()
        self.assertIn("导出班次人员维护表", content)
        self.assertIn("export_shift_roster", content)

    def test_list_sheets_only_include_active_archived_members(self):
        content = ROSTER.read_text()
        self.assertIn("emp_num_to_name_dept", content)
        self.assertIn("exempt_rows", content)
        self.assertIn("if not name:", content)


if __name__ == "__main__":
    unittest.main()
