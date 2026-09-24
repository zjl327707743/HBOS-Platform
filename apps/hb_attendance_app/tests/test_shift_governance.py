import json
import unittest
from pathlib import Path

BASE = Path(__file__).parents[1] / "hb_attendance_app" / "hbos_attendance"
SHIFT_RULE_JSON = BASE / "doctype/hbos_shift_rule/hbos_shift_rule.json"
EMP_SHIFT_JSON = BASE / "doctype/hbos_employee_shift/hbos_employee_shift.json"
SCHEDULE_JSON = BASE / "doctype/hbos_employee_schedule/hbos_employee_schedule.json"
SHIFT_DATA = BASE / "page/hbos_shift_management/shift_management_data.py"
SHIFT_JS = BASE / "page/hbos_shift_management/hbos_shift_management.js"
ROTATION = BASE / "rotation_schedule.py"
API = BASE / "api.py"
SETUP = BASE / "setup.py"


class ShiftGovernanceContractTest(unittest.TestCase):
    def test_shift_rule_has_stable_identity_and_lineage(self):
        doc = json.loads(SHIFT_RULE_JSON.read_text())
        fields = {f["fieldname"]: f for f in doc["fields"]}
        self.assertIn("rule_code", fields)
        self.assertTrue(fields["rule_code"].get("read_only"))
        self.assertIn("supersedes", fields)
        self.assertEqual(fields["supersedes"].get("options"), "HBOS Shift Rule")

    def test_employee_binding_has_stable_rule_code(self):
        doc = json.loads(EMP_SHIFT_JSON.read_text())
        fields = {f["fieldname"]: f for f in doc["fields"]}
        self.assertIn("rule_code", fields)
        self.assertIn("shift_rule", fields)
        self.assertTrue(fields["shift_rule"].get("read_only"))
        self.assertFalse(bool(fields["shift_rule"].get("reqd")))

    def test_one_save_creates_one_version(self):
        api = SHIFT_DATA.read_text()
        self.assertIn("def update_shift_rule(rule_name, updates=None", api)
        self.assertIn("旧版逐字段保存接口已停用", api)
        js = SHIFT_JS.read_text()
        start = js.index("function saveShiftRow(")
        end = js.index("// 新建规则", start)
        body = js[start:end]
        self.assertEqual(body.count("frappe.call({"), 1)
        self.assertIn("updates: JSON.stringify(updates)", body)

    def test_runtime_resolves_rule_family_by_business_date(self):
        src = API.read_text()
        self.assertIn("def _rule_for_day(rule_code, day)", src)
        self.assertIn('fields=["employee", "rule_code", "shift_rule"]', src)
        self.assertIn("hbos_fixed_shift_code", src)
        self.assertNotIn("if v.name == rule_name", src)

    def test_setup_backfills_legacy_shift_bindings(self):
        src = SETUP.read_text()
        self.assertIn("def _backfill_shift_rule_identity", src)
        self.assertIn("hbos_fixed_shift_code", src)
        self.assertIn('"rule_code"', src)


class ScheduleOwnershipContractTest(unittest.TestCase):
    def test_schedule_tracks_source(self):
        doc = json.loads(SCHEDULE_JSON.read_text())
        fields = {f["fieldname"]: f for f in doc["fields"]}
        self.assertIn("source_type", fields)
        self.assertIn("source_ref", fields)
        options = fields["source_type"]["options"].splitlines()
        for value in ("LEGACY", "ROTATION", "IMPORT", "MANUAL", "SWAP"):
            self.assertIn(value, options)

    def test_rotation_only_replaces_owned_rows_and_never_commits(self):
        src = ROTATION.read_text()
        self.assertIn('"source_type": "ROTATION"', src)
        self.assertIn('"source_ref": group["name"]', src)
        self.assertIn('"source_type": "ROTATION"', src)
        self.assertNotIn("frappe.db.commit()", src)

    def test_import_only_replaces_import_or_rotation(self):
        src = SHIFT_DATA.read_text()
        start = src.index("def import_schedule_file(")
        end = src.index("def get_conflicts(", start)
        body = src[start:end]
        self.assertIn('["IMPORT", "ROTATION"]', body)
        self.assertIn('"source_type": "IMPORT"', body)
        self.assertIn("protected", body)

    def test_schedule_controller_enforces_employee_day_uniqueness(self):
        controller = (BASE / "doctype/hbos_employee_schedule/hbos_employee_schedule.py").read_text()
        self.assertIn('"employee": self.employee', controller)
        self.assertIn('"schedule_date": self.schedule_date', controller)
        self.assertIn("同一员工同一天只能保留一条权威排班", controller)


if __name__ == "__main__":
    unittest.main()
