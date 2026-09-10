import json
import unittest
from pathlib import Path


REPORT_JSON = (
    Path(__file__).parents[1]
    / "hb_attendance_app/hbos_attendance/report/月度考勤汇总/月度考勤汇总.json"
)


class MonthlySummaryReportConfigTest(unittest.TestCase):
    """月度考勤汇总必须是可内联运行的报表。

    事故: Frappe 的 execute_script_report 在报表耗时 >15s 时会自动把 Report 的
    prepared_report 置 1(前提 disable_prepared_report_automation 未勾选), 之后每次
    打开都只显示「此报表是后台运行报表, 请…生成新报表」而看不到数据。
    故固化 prepared_report=0 + disable_prepared_report_automation=1。
    """

    def test_prepared_report_disabled(self):
        cfg = json.loads(REPORT_JSON.read_text())
        self.assertEqual(cfg["prepared_report"], 0)

    def test_automation_disabled(self):
        cfg = json.loads(REPORT_JSON.read_text())
        self.assertEqual(cfg["disable_prepared_report_automation"], 1)


if __name__ == "__main__":
    unittest.main()
