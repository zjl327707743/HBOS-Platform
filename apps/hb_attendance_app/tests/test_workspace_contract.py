import json
import unittest
from pathlib import Path


APP = Path(__file__).parents[1] / "hb_attendance_app"
WORKSPACE = APP / "hbos_attendance/workspace/海滨考勤工作台/海滨考勤工作台.json"
DESKTOP = APP / "config/desktop.py"
SETUP = APP / "hbos_attendance/setup.py"
IMPORT_PAGE = APP / "hbos_attendance/page/hbos_attendance_import/hbos_attendance_import.js"
CHECKIN_REPORT = APP / "hbos_attendance/report/打卡流水/打卡流水.py"
CHECKIN_REPORT_JS = APP / "hbos_attendance/report/打卡流水/打卡流水.js"
ATTENDANCE_REPORT = APP / "hbos_attendance/report/考勤结果/考勤结果.py"
ATTENDANCE_REPORT_JS = APP / "hbos_attendance/report/考勤结果/考勤结果.js"
MONTHLY_STAGING_REPORT = APP / "hbos_attendance/report/hbos_月度汇总暂存（对账）/hbos_月度汇总暂存（对账）.py"


class WorkspaceContractTest(unittest.TestCase):
	def test_desktop_declares_hbos_attendance_module(self):
		self.assertTrue(DESKTOP.exists(), "海滨考勤必须有版本化桌面 App 入口")
		self.assertIn('"module_name": "HBOS Attendance"', DESKTOP.read_text())

	def test_workspace_renders_authoritative_cards_and_routes(self):
		workspace = json.loads(WORKSPACE.read_text())
		content = workspace["content"]
		self.assertIn("海滨考勤复用 HRMS 的员工、打卡和考勤结果数据", content)
		for card in ("导入与数据", "HBOS 中文报表", "技术核查 / HRMS 原生数据"):
			self.assertIn(f'"card_name":"{card}"', content)
		labels = {link.get("label"): link.get("link_to") for link in workspace["links"]}
		self.assertEqual(labels["导入考勤机导出表"], "hbos-attendance-import")
		self.assertEqual(labels["HBOS 打卡流水（中文）"], "打卡流水")
		self.assertEqual(labels["HBOS 考勤结果（中文）"], "考勤结果")
		self.assertEqual(labels["月度汇总 / 对账暂存"], "HBOS 月度汇总暂存（对账）")
		self.assertEqual(labels["HRMS 原始打卡记录（技术核查用）"], "Employee Checkin")
		self.assertEqual(labels["HRMS 原生考勤结果（技术核查用）"], "Attendance")

	def test_after_migrate_syncs_sidebar_and_desktop_icon_runtime_objects(self):
		content = SETUP.read_text()
		self.assertIn('DESKTOP_LABEL = "海滨考勤"', content)
		self.assertIn('DESKTOP_LOGO_URL = "/assets/hb_attendance_app/hbos-attendance-logo.svg"', content)
		self.assertIn("def _sync_sidebar", content)
		self.assertIn("def _sync_desktop_icon", content)
		self.assertIn("def _hide_stale_workspace_desktop_icon", content)
		for label in ("导入考勤机导出表", "考勤导入日志", "HBOS 打卡流水", "HBOS 考勤结果", "月度汇总 / 对账暂存"):
			self.assertIn(label, content)
		self.assertIn("stale_icon.hidden = 0", content)
		self.assertIn("stale_icon.parent_icon = DESKTOP_LABEL", content)

	def test_import_page_shows_workspace_breadcrumb_and_hbos_buttons(self):
		content = IMPORT_PAGE.read_text()
		self.assertIn("海滨考勤工作台 / 导入考勤机导出表", content)
		self.assertIn("返回海滨考勤工作台", content)
		self.assertIn('data-route="Workspaces/海滨考勤工作台"', content)
		self.assertIn("查看 HBOS 打卡流水", content)
		self.assertIn("查看 HBOS 考勤结果", content)
		self.assertIn("查看考勤导入日志", content)
		self.assertIn("查看月度汇总暂存", content)
		self.assertIn("逐条原始打卡流水才写入 Employee Checkin", content)

	def test_checkin_report_prioritizes_name_number_and_department_before_employee_id(self):
		content = CHECKIN_REPORT.read_text()
		self.assertIn('"HRMS Employee ID"', content)
		self.assertLess(content.index('"员工姓名"'), content.index('"HRMS Employee ID"'))
		self.assertLess(content.index('"工号"'), content.index('"HRMS Employee ID"'))
		self.assertLess(content.index('"部门"'), content.index('"HRMS Employee ID"'))

	def test_reports_have_lineage_filters_without_fixed_500_row_cutoff(self):
		for report in (CHECKIN_REPORT, ATTENDANCE_REPORT):
			content = report.read_text()
			self.assertNotIn("limit 500", content.lower())
			self.assertIn('filters.get("department")', content)
			self.assertIn('filters.get("import_log")', content)
		for report_js in (CHECKIN_REPORT_JS, ATTENDANCE_REPORT_JS):
			content = report_js.read_text()
			self.assertIn('fieldname: "department"', content)
			self.assertIn('fieldname: "import_log"', content)

	def test_monthly_staging_has_dedicated_report(self):
		content = MONTHLY_STAGING_REPORT.read_text()
		self.assertIn("monthly_summary_staging", content)
		self.assertIn("不写入 Employee Checkin，不触发 Auto Attendance", content)


if __name__ == "__main__":
	unittest.main()
