import unittest

from hb_attendance_app.hbos_attendance.rest_leave import (
    VERIFY_FAIL, VERIFY_OK, VERIFY_PARSE_FAIL,
    build_overtime_prompt, expand_dates, parse_overtime_dates,
    rest_leave_fields, ts_to_date, verify_status_for,
)

MS_0901 = 1788192000000  # 2026-09-01 00:00:00 +08，与 test_swap_mapping 同源常量


class TsToDateTest(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(ts_to_date(MS_0901), "2026-09-01")

    def test_empty_and_zero(self):
        self.assertIsNone(ts_to_date(0))
        self.assertIsNone(ts_to_date(None))
        self.assertIsNone(ts_to_date(""))

    def test_bad_value(self):
        self.assertIsNone(ts_to_date("not-a-ts"))


class RestLeaveFieldsTest(unittest.TestCase):
    def test_maps_all_columns(self):
        f = {"调休人员_姓名": "张三", "调休人员_工号": "10001",
             "调休人员_开始时间": MS_0901, "调休人员_结束时间": MS_0901,
             "调休人员_调休天数": "1", "说明": "加班换休"}
        out = rest_leave_fields(f)
        self.assertEqual(out["employee_number"], "10001")
        self.assertEqual(out["employee_name"], "张三")
        self.assertEqual(out["start_date"], "2026-09-01")
        self.assertEqual(out["end_date"], "2026-09-01")
        self.assertEqual(out["rest_days"], 1.0)
        self.assertEqual(out["remarks"], "加班换休")

    def test_missing_person_returns_none(self):
        self.assertIsNone(rest_leave_fields({"调休人员_开始时间": MS_0901}))
        self.assertIsNone(rest_leave_fields({"调休人员_工号": "1"}))

    def test_missing_dates_returns_none(self):
        self.assertIsNone(rest_leave_fields(
            {"调休人员_姓名": "张三", "调休人员_工号": "10001"}))

    def test_end_date_defaults_to_start(self):
        f = {"调休人员_姓名": "张三", "调休人员_工号": "10001",
             "调休人员_开始时间": MS_0901}
        self.assertEqual(rest_leave_fields(f)["end_date"], "2026-09-01")

    def test_days_dirty_value_falls_back_to_zero(self):
        """调休天数是 Text 字段，脏值不得抛异常（否则整次同步中断）。"""
        for bad in ("abc", "", None, " ", "一小时"):
            with self.subTest(bad=bad):
                f = {"调休人员_姓名": "张三", "调休人员_工号": "10001",
                     "调休人员_开始时间": MS_0901, "调休人员_调休天数": bad}
                self.assertEqual(rest_leave_fields(f)["rest_days"], 0.0)

    def test_phone_not_leaked(self):
        """联系电话与考勤无关，不得进入产出字段。"""
        f = {"调休人员_姓名": "张三", "调休人员_工号": "10001",
             "调休人员_开始时间": MS_0901, "调休人员_联系电话": "13800000000"}
        out = rest_leave_fields(f)
        self.assertNotIn("13800000000", str(out))


class ExpandDatesTest(unittest.TestCase):
    def test_single_day(self):
        self.assertEqual(expand_dates("2026-08-18", "2026-08-18"), ["2026-08-18"])

    def test_multi_day_inclusive(self):
        self.assertEqual(expand_dates("2026-08-13", "2026-08-14"),
                         ["2026-08-13", "2026-08-14"])

    def test_span_overrides_day_count(self):
        """09-06→09-11 跨 6 天只申报 1 天：仍按区间展开 6 天。"""
        out = expand_dates("2026-09-06", "2026-09-11")
        self.assertEqual(len(out), 6)
        self.assertEqual(out[0], "2026-09-06")
        self.assertEqual(out[-1], "2026-09-11")

    def test_end_defaults_to_start(self):
        self.assertEqual(expand_dates("2026-08-18", None), ["2026-08-18"])

    def test_bad_input_returns_empty(self):
        self.assertEqual(expand_dates(None, None), [])
        self.assertEqual(expand_dates("不是日期", "2026-08-18"), [])


class ParseOvertimeDatesTest(unittest.TestCase):
    def test_iso_format(self):
        self.assertEqual(parse_overtime_dates("2026-08-02\n2026-08-16", "2026"),
                         ["2026-08-02", "2026-08-16"])

    def test_chinese_format_uses_year_hint(self):
        self.assertEqual(parse_overtime_dates("8月2日", "2026"), ["2026-08-02"])

    def test_dedupes(self):
        self.assertEqual(parse_overtime_dates("2026-08-02\n2026-08-02", "2026"),
                         ["2026-08-02"])

    def test_no_date_returns_empty(self):
        self.assertEqual(parse_overtime_dates("无", "2026"), [])
        self.assertEqual(parse_overtime_dates("", "2026"), [])
        self.assertEqual(parse_overtime_dates(None, "2026"), [])


class BuildPromptTest(unittest.TestCase):
    def test_includes_identity_and_remarks(self):
        p = build_overtime_prompt("张三", "10001", "8月2日加班，调休到8月3日", "2026")
        self.assertIn("张三", p)
        self.assertIn("10001", p)
        self.assertIn("8月2日加班，调休到8月3日", p)
        self.assertIn("2026", p)


class VerifyStatusTest(unittest.TestCase):
    def test_all_paired_is_ok(self):
        self.assertEqual(verify_status_for(["2026-08-02"], {"2026-08-02"}), VERIFY_OK)

    def test_missing_pair_fails(self):
        self.assertEqual(verify_status_for(["2026-08-02"], set()), VERIFY_FAIL)

    def test_partial_fails(self):
        self.assertEqual(
            verify_status_for(["2026-08-02", "2026-08-16"], {"2026-08-02"}),
            VERIFY_FAIL)

    def test_no_overtime_dates_is_parse_failure(self):
        self.assertEqual(verify_status_for([], {"2026-08-02"}), VERIFY_PARSE_FAIL)


if __name__ == "__main__":
    unittest.main()
