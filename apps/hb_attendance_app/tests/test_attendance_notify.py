import unittest

from hb_attendance_app.hbos_attendance.attendance_notify import render_report, build_payload


def d(dept, expected, present, no_card, late=0):
    return {"dept": dept, "total": expected, "expected": expected, "present": present,
            "noCard": no_card, "late": late, "absent": 0, "leave": 0}


class RenderReportTest(unittest.TestCase):
    def test_contains_title_and_all_depts(self):
        text = render_report("2026-09-10", "09:00", [d("无菌车间", 60, 58, 2), d("厂外QC", 55, 53, 2)])
        self.assertIn("【考勤到岗】2026-09-10 09:00", text)
        self.assertIn("无菌车间", text)
        self.assertIn("厂外QC", text)
        self.assertIn("应出勤", text)
        self.assertIn("已到岗", text)
        self.assertIn("未打卡", text)
        self.assertIn("迟到", text)

    def test_no_total_row(self):
        text = render_report("2026-09-10", "09:00", [d("A", 10, 9, 1)])
        # 不含全厂汇总行（Owner 确认只看部门）
        self.assertNotIn("全厂", text)

    def test_dept_with_zero_expected_skipped(self):
        text = render_report("2026-09-10", "09:00", [d("全员休息部", 0, 0, 0), d("A", 10, 9, 1)])
        self.assertNotIn("全员休息部", text)
        self.assertIn("A", text)

    def test_empty_stats_returns_only_title(self):
        text = render_report("2026-09-10", "09:00", [])
        self.assertIn("【考勤到岗】", text)
        self.assertIn("暂无应出勤", text)

    def test_zero_values_render_as_zero(self):
        text = render_report("2026-09-10", "09:00", [d("A", 10, 10, 0, 0)])
        line = [l for l in text.splitlines() if l.startswith("A")][0]
        self.assertIn("0", line)


class BuildPayloadTest(unittest.TestCase):
    def test_payload_shape(self):
        stats = [d("A", 10, 9, 1)]
        p = build_payload("2026-09-10", "2026-09-10 09:00:03", "TEXT", stats)
        self.assertEqual(p["type"], "attendance_daily")
        self.assertEqual(p["date"], "2026-09-10")
        self.assertEqual(p["generated_at"], "2026-09-10 09:00:03")
        self.assertEqual(p["text"], "TEXT")
        self.assertEqual(len(p["dept_stats"]), 1)
        self.assertEqual(p["dept_stats"][0]["dept"], "A")

    def test_payload_dept_stats_has_snake_keys(self):
        # 传输层统一 snake_case，便于 OpenClaw 侧消费
        p = build_payload("2026-09-10", "x", "t", [d("A", 10, 9, 1)])
        self.assertEqual(
            sorted(p["dept_stats"][0].keys()),
            ["absent", "dept", "expected", "late", "leave", "no_card", "not_started",
             "out_only", "present", "total", "unknown_time"],
        )


if __name__ == "__main__":
    unittest.main()


class HeaderAlignmentTest(unittest.TestCase):
    """表头与数据行必须能看出列间隔（中文表头正好填满列宽会连成一片）。"""

    def test_header_labels_separated(self):
        text = render_report("2026-09-10", "09:00", [d("A", 10, 9, 1, 0)])
        header = [l for l in text.splitlines() if l.startswith("部门")][0]
        for label in ("应出勤", "已到岗", "未打卡", "迟到"):
            self.assertIn(label, header)
        # 相邻两个表头标签之间必须至少有一处空格分隔
        self.assertNotIn("应出勤已到岗", header)
        self.assertNotIn("已到岗未打卡", header)
        self.assertNotIn("未打卡迟到", header)

    def test_payload_title_with_bad_generated_at_falls_back(self):
        p = build_payload("2026-09-10", "bad-format", "T", [])
        self.assertEqual(p["title"], "【考勤到岗】2026-09-10")
