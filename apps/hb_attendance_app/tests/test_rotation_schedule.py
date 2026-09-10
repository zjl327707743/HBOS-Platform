import unittest
from datetime import date, timedelta

from hb_attendance_app.hbos_attendance.rotation_schedule import (
    rotation_shift_for,
    ROTATION_GROUPS,
    group_shift_for,
    group_start_date,
    group_member_nums,
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

    def test_生产部_吕玉升_anchor_night(self):
        # 吕玉升 8/15 晚班, 8/16 休息, 8/17 早班
        a = date(2026, 8, 15)
        self.assertEqual(rotation_shift_for("晚班", a, date(2026, 8, 15)), "晚班")
        self.assertEqual(rotation_shift_for("晚班", a, date(2026, 8, 16)), "休息")
        self.assertEqual(rotation_shift_for("晚班", a, date(2026, 8, 17)), "早班")

    def test_生产部_王飞_anchor_rest(self):
        # 王飞 8/15 休息, 8/16 早班, 8/17 晚班
        a = date(2026, 8, 15)
        self.assertEqual(rotation_shift_for("休息", a, date(2026, 8, 15)), "休息")
        self.assertEqual(rotation_shift_for("休息", a, date(2026, 8, 16)), "早班")
        self.assertEqual(rotation_shift_for("休息", a, date(2026, 8, 17)), "晚班")

    def test_生产部_袁式梅_anchor_early(self):
        # 袁式梅 8/15 早班, 8/16 晚班, 8/17 休息
        a = date(2026, 8, 15)
        self.assertEqual(rotation_shift_for("早班", a, date(2026, 8, 15)), "早班")
        self.assertEqual(rotation_shift_for("早班", a, date(2026, 8, 16)), "晚班")
        self.assertEqual(rotation_shift_for("早班", a, date(2026, 8, 17)), "休息")

    def test_cross_cycle(self):
        # 贾正利 8/24 = 8/15 + 9 天, 9 % 3 == 0 → 回到早班
        self.assertEqual(rotation_shift_for("早班", date(2026, 8, 15), date(2026, 8, 24)), "早班")
        # 吕玉升 8/24 = 8/15 + 9 天, 9 % 3 == 0 → 回到晚班
        self.assertEqual(rotation_shift_for("晚班", date(2026, 8, 15), date(2026, 8, 24)), "晚班")

    def test_daily_coverage_设备动力部(self):
        d = date(2026, 8, 20)
        shifts = {
            rotation_shift_for("早班", date(2026, 8, 15), d),
            rotation_shift_for("晚班", date(2026, 8, 15), d),
            rotation_shift_for("休息", date(2026, 8, 15), d),
        }
        self.assertEqual(shifts, {"早班", "晚班", "休息"})

    def test_daily_coverage_生产部(self):
        d = date(2026, 8, 15)
        shifts = {
            rotation_shift_for("早班", date(2026, 8, 15), d),
            rotation_shift_for("晚班", date(2026, 8, 15), d),
            rotation_shift_for("休息", date(2026, 8, 15), d),
        }
        self.assertEqual(shifts, {"早班", "晚班", "休息"})


class PhaseSegmentTest(unittest.TestCase):
    """相位分段：生产部 2026-08-30 起整体前移一天（Owner 2026-09-10 确认）。

    依据: 8/15-8/29 实际轮转吻合段1, 8/30-9/10 吻合段2（吕玉升/王飞 各 12/12）。
    """

    def _pro(self):
        return ROTATION_GROUPS[1]

    def test_group_start_is_earliest_segment(self):
        self.assertEqual(group_start_date(self._pro()), date(2026, 8, 15))

    def test_member_nums_union_across_segments(self):
        self.assertEqual(sorted(group_member_nums(self._pro())),
                         ["10010010", "10010011", "10010013"])

    def test_switch_day_uses_new_segment(self):
        g = self._pro()
        # 8/29 仍按段1（吕玉升 早班），8/30 起按段2（吕玉升 早班 → 8/31 晚班）
        self.assertEqual(group_shift_for(g, "10010011", date(2026, 8, 29)), "早班")
        self.assertEqual(group_shift_for(g, "10010011", date(2026, 8, 30)), "早班")
        self.assertEqual(group_shift_for(g, "10010011", date(2026, 8, 31)), "晚班")
        self.assertEqual(group_shift_for(g, "10010011", date(2026, 9, 1)), "休息")

    def test_segment1_phase_preserved_before_switch(self):
        g = self._pro()
        self.assertEqual(group_shift_for(g, "10010011", date(2026, 8, 15)), "晚班")
        self.assertEqual(group_shift_for(g, "10010011", date(2026, 8, 17)), "早班")
        self.assertEqual(group_shift_for(g, "10010010", date(2026, 8, 16)), "早班")
        self.assertEqual(group_shift_for(g, "10010013", date(2026, 8, 15)), "早班")

    def test_segment2_matches_observed_after_0830(self):
        """8/30 起与生产部实际打卡序列一致（吕玉升: 30早 31晚 1休 2早; 王飞: 30晚 31休 1早）。"""
        g = self._pro()
        expect_lv = {date(2026, 8, 30): "早班", date(2026, 8, 31): "晚班",
                     date(2026, 9, 1): "休息", date(2026, 9, 2): "早班"}
        for d, s in expect_lv.items():
            self.assertEqual(group_shift_for(g, "10010011", d), s, f"吕玉升 {d}")
        expect_wf = {date(2026, 8, 30): "晚班", date(2026, 8, 31): "休息"}
        for d, s in expect_wf.items():
            self.assertEqual(group_shift_for(g, "10010010", d), s, f"王飞 {d}")

    def test_each_day_still_one_early_one_night_one_rest(self):
        """相位分段后仍需保证每天 1 早 1 晚 1 休（12h 倒班覆盖要求）。"""
        g = self._pro()
        d = date(2026, 8, 15)
        while d <= date(2026, 10, 31):
            got = {group_shift_for(g, n, d) for n in group_member_nums(g)}
            self.assertEqual(got, {"早班", "晚班", "休息"}, f"{d} 覆盖异常: {got}")
            d += timedelta(days=1)

    def test_groups_config(self):
        # 两组共 6 人, 无重复工号
        nums = [n for g in ROTATION_GROUPS for n in group_member_nums(g)]
        self.assertEqual(len(nums), len(set(nums)), "两组工号不应重复")
        self.assertEqual(len(nums), 6)
        # 两批起始日均为 2026-08-15 (Owner 2026-09-10 确认)
        for g in ROTATION_GROUPS:
            self.assertEqual(group_start_date(g), date(2026, 8, 15))
        # 生产部: 段1 起 8/15, 段2 起 8/30
        segs = ROTATION_GROUPS[1]["segments"]
        self.assertEqual([s["anchor_date"] for s in segs],
                         [date(2026, 8, 15), date(2026, 8, 30)])
        self.assertEqual(segs[0]["members"]["10010011"], "晚班")
        self.assertEqual(segs[1]["members"]["10010011"], "早班")


if __name__ == "__main__":
    unittest.main()
