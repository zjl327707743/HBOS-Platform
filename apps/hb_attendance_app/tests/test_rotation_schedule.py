import unittest
from datetime import date

from hb_attendance_app.hbos_attendance.rotation_schedule import (
    rotation_shift_for,
    ROTATION_GROUPS,
)


class RotationShiftTest(unittest.TestCase):
    """12 小时倒班轮转相位（设备动力部 + 生产部，Owner 2026-08-26 确认）。"""

    def test_设备动力部_贾正利_anchor_early(self):
        # 贾正利 8/15 早班, 8/16 晚班, 8/17 休息
        a = date(2026, 8, 15)
        self.assertEqual(rotation_shift_for("早班", a, date(2026, 8, 15)), "早班")
        self.assertEqual(rotation_shift_for("早班", a, date(2026, 8, 16)), "晚班")
        self.assertEqual(rotation_shift_for("早班", a, date(2026, 8, 17)), "休息")

    def test_设备动力部_付全喜_anchor_night(self):
        # 付全喜 8/15 晚班, 8/16 休息, 8/17 早班
        a = date(2026, 8, 15)
        self.assertEqual(rotation_shift_for("晚班", a, date(2026, 8, 15)), "晚班")
        self.assertEqual(rotation_shift_for("晚班", a, date(2026, 8, 16)), "休息")
        self.assertEqual(rotation_shift_for("晚班", a, date(2026, 8, 17)), "早班")

    def test_设备动力部_李双胜_anchor_rest(self):
        # 李双胜 8/15 休息, 8/16 早班, 8/17 晚班
        a = date(2026, 8, 15)
        self.assertEqual(rotation_shift_for("休息", a, date(2026, 8, 15)), "休息")
        self.assertEqual(rotation_shift_for("休息", a, date(2026, 8, 16)), "早班")
        self.assertEqual(rotation_shift_for("休息", a, date(2026, 8, 17)), "晚班")

    def test_生产部_吕玉升_anchor_early(self):
        # 吕玉升 8/26 早班, 8/27 晚班, 8/28 休息
        a = date(2026, 8, 26)
        self.assertEqual(rotation_shift_for("早班", a, date(2026, 8, 26)), "早班")
        self.assertEqual(rotation_shift_for("早班", a, date(2026, 8, 27)), "晚班")
        self.assertEqual(rotation_shift_for("早班", a, date(2026, 8, 28)), "休息")

    def test_生产部_王飞_anchor_night(self):
        # 王飞 8/26 晚班, 8/27 休息, 8/28 早班
        a = date(2026, 8, 26)
        self.assertEqual(rotation_shift_for("晚班", a, date(2026, 8, 26)), "晚班")
        self.assertEqual(rotation_shift_for("晚班", a, date(2026, 8, 27)), "休息")
        self.assertEqual(rotation_shift_for("晚班", a, date(2026, 8, 28)), "早班")

    def test_生产部_袁式梅_anchor_rest(self):
        # 袁式梅 8/26 休息, 8/27 早班, 8/28 晚班
        a = date(2026, 8, 26)
        self.assertEqual(rotation_shift_for("休息", a, date(2026, 8, 26)), "休息")
        self.assertEqual(rotation_shift_for("休息", a, date(2026, 8, 27)), "早班")
        self.assertEqual(rotation_shift_for("休息", a, date(2026, 8, 28)), "晚班")

    def test_cross_cycle(self):
        # 贾正利 8/24 = 8/15 + 9 天, 9 % 3 == 0 → 回到早班
        self.assertEqual(rotation_shift_for("早班", date(2026, 8, 15), date(2026, 8, 24)), "早班")
        # 吕玉升 9/4 = 8/26 + 9 天, 9 % 3 == 0 → 回到早班
        self.assertEqual(rotation_shift_for("早班", date(2026, 8, 26), date(2026, 9, 4)), "早班")

    def test_daily_coverage_设备动力部(self):
        d = date(2026, 8, 20)
        shifts = {
            rotation_shift_for("早班", date(2026, 8, 15), d),
            rotation_shift_for("晚班", date(2026, 8, 15), d),
            rotation_shift_for("休息", date(2026, 8, 15), d),
        }
        self.assertEqual(shifts, {"早班", "晚班", "休息"})

    def test_daily_coverage_生产部(self):
        d = date(2026, 8, 26)
        shifts = {
            rotation_shift_for("早班", date(2026, 8, 26), d),
            rotation_shift_for("晚班", date(2026, 8, 26), d),
            rotation_shift_for("休息", date(2026, 8, 26), d),
        }
        self.assertEqual(shifts, {"早班", "晚班", "休息"})

    def test_groups_config(self):
        # 两组共 6 人, 无重复工号
        nums = [n for g in ROTATION_GROUPS for n in g["members"]]
        self.assertEqual(len(nums), len(set(nums)), "两组工号不应重复")
        self.assertEqual(len(nums), 6)
        # 生产部锚点 = 2026-08-26
        pro = ROTATION_GROUPS[1]
        self.assertEqual(pro["anchor_date"], date(2026, 8, 26))
        self.assertEqual(pro["members"]["10010011"], "早班")
        self.assertEqual(pro["members"]["10010010"], "晚班")
        self.assertEqual(pro["members"]["10010013"], "休息")


if __name__ == "__main__":
    unittest.main()
