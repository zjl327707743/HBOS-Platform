import json
import unittest
from pathlib import Path


APP = Path(__file__).parents[1] / "hb_attendance_app"
WORKSPACE = APP / "hbos_attendance/workspace/海滨考勤工作台/海滨考勤工作台.json"
DESKTOP = APP / "config/desktop.py"
CHECKIN_REPORT = APP / "hbos_attendance/report/打卡流水/打卡流水.py"


class WorkspaceContractTest(unittest.TestCase):
	def test_desktop_declares_hbos_attendance_module(self):
		self.assertTrue(DESKTOP.exists(), "海滨考勤必须有版本化桌面 App 入口")
		self.assertIn('"module_name": "HBOS Attendance"', DESKTOP.read_text())

	def test_workspace_renders_authoritative_cards_and_routes(self):
		workspace = json.loads(WORKSPACE.read_text())
		content = workspace["content"]
		for card in ("导入与数据", "HBOS 中文报表", "HRMS 原生数据"):
			self.assertIn(f'"card_name":"{card}"', content)
		labels = {link.get("label"): link.get("link_to") for link in workspace["links"]}
		self.assertEqual(labels["导入考勤机导出表"], "hbos-attendance-import")
		self.assertEqual(labels["HBOS 打卡流水（中文）"], "打卡流水")
		self.assertEqual(labels["HBOS 考勤结果（中文）"], "考勤结果")

	def test_checkin_report_prioritizes_name_number_and_department_before_employee_id(self):
		content = CHECKIN_REPORT.read_text()
		self.assertIn('"HRMS Employee ID"', content)
		self.assertLess(content.index('"员工姓名"'), content.index('"HRMS Employee ID"'))
		self.assertLess(content.index('"工号"'), content.index('"HRMS Employee ID"'))
		self.assertLess(content.index('"部门"'), content.index('"HRMS Employee ID"'))


if __name__ == "__main__":
	unittest.main()
