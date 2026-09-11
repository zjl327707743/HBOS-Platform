import unittest

from hb_attendance_app.hbos_attendance.swap_mapping import (
    ts_to_date, rest_leave_fields, swap_fields,
)

MS_0901 = 1788192000000   # 2026-09-01 00:00:00 +08（已用 python 反算核对）


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
             "调休人员_调休天数": 1, "说明": "加班换休"}
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
        f = {"调休人员_姓名": "张三", "调休人员_工号": "10001"}
        self.assertIsNone(rest_leave_fields(f))

    def test_end_date_defaults_to_start(self):
        f = {"调休人员_姓名": "张三", "调休人员_工号": "10001",
             "调休人员_开始时间": MS_0901}
        self.assertEqual(rest_leave_fields(f)["end_date"], "2026-09-01")

    def test_days_defaults_zero(self):
        f = {"调休人员_姓名": "张三", "调休人员_工号": "10001",
             "调休人员_开始时间": MS_0901}
        self.assertEqual(rest_leave_fields(f)["rest_days"], 0.0)


class SwapFieldsTest(unittest.TestCase):
    def test_maps_all_columns(self):
        f = {"明细_申请人": "甲", "明细_申请人工号": "10001",
             "明细_替班人": "乙", "明细_替班人工号": "10002",
             "明细_换班日期": MS_0901, "明细_还班日期": MS_0901, "说明": "调班"}
        out = swap_fields(f)
        self.assertEqual(out["applicant_number"], "10001")
        self.assertEqual(out["applicant_name"], "甲")
        self.assertEqual(out["substitute_number"], "10002")
        self.assertEqual(out["substitute_name"], "乙")
        self.assertEqual(out["swap_date"], "2026-09-01")
        self.assertEqual(out["repay_date"], "2026-09-01")
        self.assertEqual(out["remarks"], "调班")

    def test_requires_both_people(self):
        # 缺替班人 → None
        self.assertIsNone(swap_fields({"明细_申请人工号": "10001",
                                       "明细_换班日期": MS_0901}))
        # 缺申请人 → None
        self.assertIsNone(swap_fields({"明细_替班人工号": "10002",
                                       "明细_换班日期": MS_0901}))

    def test_requires_swap_date(self):
        f = {"明细_申请人": "甲", "明细_申请人工号": "10001",
             "明细_替班人": "乙", "明细_替班人工号": "10002"}
        self.assertIsNone(swap_fields(f))

    def test_repay_date_optional(self):
        f = {"明细_申请人": "甲", "明细_申请人工号": "10001",
             "明细_替班人": "乙", "明细_替班人工号": "10002",
             "明细_换班日期": MS_0901}
        self.assertIsNone(swap_fields(f)["repay_date"])
        self.assertEqual(swap_fields(f)["swap_date"], "2026-09-01")


if __name__ == "__main__":
    unittest.main()
