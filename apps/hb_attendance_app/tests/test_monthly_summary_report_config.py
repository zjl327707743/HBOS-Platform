import json
import unittest
from pathlib import Path


REPORT_DIR = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/report"
# 全部 HBOS 脚本报表: 都必须可内联运行, 禁止被自动转后台
REPORTS = [
    "月度考勤汇总/月度考勤汇总.json",
    "打卡流水/打卡流水.json",
    "考勤结果/考勤结果.json",
    "hbos_月度汇总暂存（对账）/hbos_月度汇总暂存（对账）.json",
]


class MonthlySummaryReportConfigTest(unittest.TestCase):
    """HBOS 脚本报表必须是可内联运行的报表。

    事故: Frappe 的 execute_script_report 在报表耗时 >15s 时会自动把 Report 的
    prepared_report 置 1(前提 disable_prepared_report_automation 未勾选), 之后每次
    打开都只显示「此报表是后台运行报表, 请…生成新报表」而看不到数据。
    故全部 HBOS 报表固化 prepared_report=0 + disable_prepared_report_automation=1。
    """

    def test_all_hbos_reports_independently_run_inline(self):
        for rel in REPORTS:
            cfg = json.loads((REPORT_DIR / rel).read_text())
            self.assertEqual(cfg["prepared_report"], 0, rel)
            self.assertEqual(cfg["disable_prepared_report_automation"], 1, rel)


if __name__ == "__main__":
    unittest.main()
