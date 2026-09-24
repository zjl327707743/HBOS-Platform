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

    def test_days_non_finite_falls_back_to_zero(self):
        """float() 接受 nan/inf，非有限值不得写进 Float 字段与 JSON。"""
        for bad in ("nan", "NaN", "inf", "-inf", float("nan"), float("inf")):
            with self.subTest(bad=bad):
                f = {"调休人员_姓名": "张三", "调休人员_工号": "10001",
                     "调休人员_开始时间": MS_0901, "调休人员_调休天数": bad}
                self.assertEqual(rest_leave_fields(f)["rest_days"], 0.0)


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

    def test_reverse_range_is_swapped(self):
        """起止写反（08-18 → 08-13）时按区间展开，不返回空。"""
        self.assertEqual(expand_dates("2026-08-18", "2026-08-13"),
                         ["2026-08-13", "2026-08-14", "2026-08-15",
                          "2026-08-16", "2026-08-17", "2026-08-18"])

    def test_bad_input_returns_empty(self):
        self.assertEqual(expand_dates(None, None), [])
        self.assertEqual(expand_dates("不是日期", "2026-08-18"), [])


class ParseOvertimeDatesTest(unittest.TestCase):
    def test_iso_format(self):
        self.assertEqual(parse_overtime_dates("2026-08-02\n2026-08-16", "2026"),
                         ["2026-08-02", "2026-08-16"])

    def test_chinese_format_uses_year_hint(self):
        self.assertEqual(parse_overtime_dates("8月2日", "2026"), ["2026-08-02"])

    def test_chinese_hao_form(self):
        """真实 104 条说明里「月+号」71 条、「月+日」13 条；号是主要写法，必须都认。"""
        self.assertEqual(parse_overtime_dates("8月2号加的班", "2026"),
                         ["2026-08-02"])
        self.assertEqual(parse_overtime_dates("8月2号", "2026"),
                         parse_overtime_dates("8月2日", "2026"))
        self.assertEqual(parse_overtime_dates("8月2号、8月16号", "2026"),
                         ["2026-08-02", "2026-08-16"])

    def test_time_span_not_read_as_date(self):
        """「9月20号晚上17:30-21:30」里的时间不得被当成日期产出。"""
        self.assertEqual(
            parse_overtime_dates("9月20号晚上17:30-21:30加的班", "2026"),
            ["2026-09-20"])
        # 冒号写成点号（17.30-21.30）时也不得产出 17 月 30 日之类的伪日期
        self.assertEqual(parse_overtime_dates("8月2号加班 17.30-21.30", "2026"),
                         ["2026-08-02"])

    def test_multiple_chinese_dates_all_extracted_no_range_expansion(self):
        """多条中文日期一律提取，且不做区间展开（保持单日逐个产出）。

        说明同时提到加班日与调休日时会多提一个休息日，这是**有意**的保守行为：
        多提只会让核实更严格（核实不通过 → 转人工），漏提才会把真实加班误判成解析失败。
        """
        self.assertEqual(
            parse_overtime_dates("9月6号加班，调休9月11号休息", "2026"),
            ["2026-09-06", "2026-09-11"])

    def test_dotted_pair_extracted(self):
        """「08.09加的班，调休到08.19」两个短式日期都要提取。"""
        self.assertEqual(parse_overtime_dates("08.09加的班，调休到08.19", "2026"),
                         ["2026-08-09", "2026-08-19"])

    def test_chinese_with_explicit_year_beats_hint(self):
        """「2026年8月2号」自带年份，不依赖【申请年】；年份冲突时以原文为准。"""
        self.assertEqual(parse_overtime_dates("2026年8月2号加班", "2026"),
                         ["2026-08-02"])
        self.assertEqual(parse_overtime_dates("2026年8月2号加班", None),
                         ["2026-08-02"])
        self.assertEqual(parse_overtime_dates("2026年8月2号加班", "2025"),
                         ["2026-08-02"])

    def test_dedupes(self):
        self.assertEqual(parse_overtime_dates("2026-08-02\n2026-08-02", "2026"),
                         ["2026-08-02"])

    def test_no_date_returns_empty(self):
        self.assertEqual(parse_overtime_dates("无", "2026"), [])
        self.assertEqual(parse_overtime_dates("", "2026"), [])
        self.assertEqual(parse_overtime_dates(None, "2026"), [])

    def test_missing_year_hint_returns_empty_not_raise(self):
        """申请年取不到时不得抛异常：说明原文会被整批中断的失败模式不能重现。"""
        self.assertEqual(parse_overtime_dates("8月2日", None), [])
        self.assertEqual(parse_overtime_dates("8月2日", ""), [])
        self.assertEqual(parse_overtime_dates("8月2日", "abc"), [])
        # 非四位年份不是可用年份：宁可解析失败，也不要编出 "0026-08-02"
        self.assertEqual(parse_overtime_dates("8月2日", "26"), [])
        self.assertEqual(parse_overtime_dates("8月2日", 0), [])
        # 自带年份的完整日期不依赖申请年，仍应解析出来
        self.assertEqual(parse_overtime_dates("2026-08-02\n8月2日", None),
                         ["2026-08-02"])

    def test_impossible_calendar_date_not_emitted(self):
        """正则只约束数字形状，非法日历日不得当成日期产出。"""
        self.assertEqual(parse_overtime_dates("2026-13-45", "2026"), [])
        self.assertEqual(parse_overtime_dates("13月45日", "2026"), [])
        self.assertEqual(parse_overtime_dates("2026-02-30", "2026"), [])

    def test_iso_and_chinese_forms_merge(self):
        """两种写法混排时不得因命中 ISO 就丢掉后面的中文式日期。"""
        self.assertEqual(parse_overtime_dates("2026-08-02 and 7月5日", "2026"),
                         ["2026-08-02", "2026-07-05"])

    def test_dotted_and_slashed_forms(self):
        """prompt 告知模型输入可能是「08.02」「8/2」，模型原样回显时也要能解析。"""
        self.assertEqual(parse_overtime_dates("08.02", "2026"), ["2026-08-02"])
        self.assertEqual(parse_overtime_dates("8/2", "2026"), ["2026-08-02"])
        self.assertEqual(parse_overtime_dates("2026.08.02", "2026"), ["2026-08-02"])
        self.assertEqual(parse_overtime_dates("2026/8/2", "2026"), ["2026-08-02"])


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
