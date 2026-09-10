import unittest
from datetime import datetime, time, timedelta

from hb_attendance_app.hbos_attendance.shift_rules import (
    _to_secs,
    _effective_late_secs,
    match_rule_by_time,
)


class ToSecsTest(unittest.TestCase):
    """Time 值解析：必须兼容 frappe 从库中读出的 timedelta。

    事故：早期版本只对字符串 split，timedelta 抛异常被吞成 0，
    所有规则被当成「0 点上班」的夜班跳过 → 规则表从未生效（102 名有绑定员工全走硬编码兜底）。
    """

    def test_timedelta(self):
        self.assertEqual(_to_secs(timedelta(hours=13)), 46800)
        self.assertEqual(_to_secs(timedelta(hours=8, minutes=31)), 30660)
        self.assertEqual(_to_secs(timedelta(0)), 0)

    def test_string(self):
        self.assertEqual(_to_secs("13:00:00"), 46800)
        self.assertEqual(_to_secs("8:31"), 30660)
        self.assertEqual(_to_secs("08:31:00"), 30660)

    def test_time_object_and_empty(self):
        self.assertEqual(_to_secs(time(13, 0)), 46800)
        self.assertEqual(_to_secs(None), 0)
        self.assertEqual(_to_secs(""), 0)


class EffectiveLateTest(unittest.TestCase):
    """迟到起算点：数据异常（早于/等于上班时间）时回落上班 +1 分钟，不改原始数据。"""

    def test_normal_rule_unchanged(self):
        r = {"shift_type": "早班", "late_after": timedelta(hours=8, minutes=1)}
        self.assertEqual(_effective_late_secs(r, _to_secs("08:00")), _to_secs("08:01"))

    def test_broken_late_after_falls_back(self):
        # 环保部 13:00-20:00 规则 late_after 误填 08:31
        r = {"shift_type": "行政班", "late_after": timedelta(hours=8, minutes=31)}
        self.assertEqual(_effective_late_secs(r, _to_secs("13:00")), _to_secs("13:01"))

    def test_missing_late_after_uses_builtin(self):
        r = {"shift_type": "行政班", "late_after": None}
        self.assertEqual(_effective_late_secs(r, _to_secs("08:30")), _to_secs("08:31"))


class MatchRuleTest(unittest.TestCase):
    """规则匹配：修好解析后规则表真正生效（含倒班多规则按时间选班）。"""

    def setUp(self):
        # 环保部 陈飞/戚素敏：早班 08:00 + 两班倒中班 13:00（late_after 误填 08:31）
        self.rules = [
            {"shift_type": "早班", "start_time": timedelta(hours=8),
             "late_after": timedelta(hours=8, minutes=1)},
            {"shift_type": "行政班", "start_time": timedelta(hours=13),
             "late_after": timedelta(hours=8, minutes=31)},
        ]

    def test_picks_nearest_shift(self):
        self.assertEqual(match_rule_by_time(self.rules, datetime(2026, 9, 10, 12, 48))[0], "行政班")
        self.assertEqual(match_rule_by_time(self.rules, datetime(2026, 9, 10, 7, 54))[0], "早班")

    def test_broken_late_after_does_not_flag_late(self):
        # 12:46 到 13:00 班：属提前到岗，不得判迟到
        shift, late = match_rule_by_time(self.rules, datetime(2026, 9, 10, 12, 46))
        self.assertEqual(shift, "行政班")
        self.assertFalse(late)

    def test_early_morning_uses_dedicated_branch(self):
        # 0-4 点：优先匹配 00:00 上班的夜班规则
        rules = [
            {"shift_type": "早班", "start_time": timedelta(hours=8),
             "late_after": timedelta(hours=8, minutes=1)},
            {"shift_type": "夜班", "start_time": timedelta(0),
             "late_after": timedelta(minutes=1)},
        ]
        shift, late = match_rule_by_time(rules, datetime(2026, 9, 10, 0, 47))
        self.assertEqual(shift, "夜班")
        self.assertTrue(late)     # 0:47 > 0:01

    def test_safety_night_2100_not_late_at_2053(self):
        # 安全部倒班夜班规则 21:00-8:30（late_after 误填 20:01）→ 20:53 属提前到岗
        rules = [{"shift_type": "晚班", "start_time": timedelta(hours=21),
                  "late_after": timedelta(hours=20, minutes=1)}]
        shift, late = match_rule_by_time(rules, datetime(2026, 9, 8, 20, 53))
        self.assertEqual(shift, "晚班")
        self.assertFalse(late)


if __name__ == "__main__":
    unittest.main()
