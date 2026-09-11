import unittest
from datetime import datetime

from hb_attendance_app.hbos_attendance.pairing import (
    admin_shift_from_gap,
    pair_employee_checkins,
)


class AdminShiftFromGapTest(unittest.TestCase):
    """行政班名单人员判定（Owner 2026-08-21 确认）:
    四车间行政班 08:0x 打卡曾被全局规则表匹配为「早班 08:00 标准」误判迟到。
    名单人员统一 08:31 起算迟到; 20 点后与 0-4 点的跨天卡按晚班不判迟到。
    """

    def test_0803_not_late(self):
        # 杨迪 8/17 08:03 上班: 行政班 8:30 标准, 提前到岗不迟到
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 17, 8, 3)),
                         ("行政班早班", False))

    def test_0830_on_time(self):
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 17, 8, 30)),
                         ("行政班早班", False))

    def test_0831_late(self):
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 17, 8, 31)),
                         ("行政班早班", True))

    def test_2330_night_card_not_late(self):
        # 焦德龙 8/15 23:30 上班机卡: 夜间卡不按早班 8:00 标准判迟到
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 15, 23, 30)),
                         ("晚班", False))

    def test_0003_midnight_card_not_late(self):
        # 焦德龙 8/15 00:03 下班机卡: 凌晨跨天收尾卡不判迟到
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 15, 0, 3)),
                         ("晚班", False))


def _admin_shift_fn(ck_dt, emp_num="", cross_day=False):
    """适配 pair_employee_checkins 的 shift_fn 签名。"""
    return admin_shift_from_gap(ck_dt)


class AdminPairingTest(unittest.TestCase):
    """四车间行政班完整配对: 侯宇晓 8/16 真实卡链 08:08 上班机 → 17:39 下班机。"""

    def _ck(self, day, hour, minute, sn=None):
        d = {"time": datetime(2026, 8, day, hour, minute),
             "employee_name": "侯宇晓", "department": "四车间"}
        if sn:
            d["hbos_terminal_sn"] = sn
        return d

    def test_houyuxiao_0816_not_late(self):
        cks = [self._ck(16, 8, 8, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 17, 39, "13750CS_93C9390B9995FE8C")]
        atts = pair_employee_checkins(cks, "HR-EMP-00033", "11004014",
                                      _admin_shift_fn, terminal_aware=True)
        s = {(a[2], a[3], a[4], a[5], a[7]) for a in atts}
        # 行政班早班 9.52h, 不迟到, 不缺勤
        self.assertIn(("2026-08-16", "Present", "行政班早班", 0, 9.52), s)
        self.assertNotIn(("2026-08-16", "Absent", "", 0, 0), s)

    def test_yangdi_0817_not_late(self):
        cks = [self._ck(17, 8, 3, "13750CS_D7C69C16EC0B2447"),
               self._ck(17, 17, 51, "13750CS_93C9390B9995FE8C")]
        atts = pair_employee_checkins(cks, "HR-EMP-00041", "11004011",
                                      _admin_shift_fn, terminal_aware=True)
        s = {(a[2], a[3], a[4], a[5]) for a in atts}
        self.assertIn(("2026-08-17", "Present", "行政班早班", 0), s)


if __name__ == "__main__":
    unittest.main()
import ast
import re
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from hb_attendance_app.hbos_attendance.shift_rules import match_rule_by_time


API = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/api.py"


def _fn_source(name):
    """取出 api.py 中某个函数的源码（含嵌套 def）。"""
    src = API.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    raise AssertionError("未找到函数 %s" % name)


class AdminListDoesNotOverrideConfigTest(unittest.TestCase):
    """行政班名单短路仅在该人「没有另绑其它班次」时生效（Owner 2026-09-11）。

    事故：卞德志(11004006) 在行政班名单里，但实际绑定「中班 16:00」+「行政班 8:30」，
    原实现把名单短路放在函数最前，使他 15:4x 的上班卡一律按「行政班早班」判定 →
    被判迟到。显式绑定比名单启发式更具体，应优先。
    反向要求：只绑行政班（焦德龙 11004012）或未绑定的名单人员，行为必须不变
    ——他的 23:30 夜班上班卡若被按行政班标准判会误报迟到。
    """

    def test_short_circuit_is_conditional_on_binding(self):
        fn = _fn_source("shift_fn_with_fixed")
        self.assertIn("_admin_bound_other_shift", fn,
                      "名单短路必须带上「是否另绑其它班次」的条件")

    def test_helper_exists_and_documented(self):
        src = API.read_text()
        self.assertIn("def _admin_bound_other_shift(", src)
        self.assertIn("shift_type_by_rule", src)

    def test_night_card_for_admin_only_binding_not_late(self):
        """只绑行政班的人，23:30 的夜班上班卡不得按 08:31 标准判迟到。"""
        from hb_attendance_app.hbos_attendance.pairing import admin_shift_from_gap
        shift, late = admin_shift_from_gap(datetime(2026, 8, 15, 23, 30))
        self.assertEqual(shift, "晚班")
        self.assertFalse(late)

    def test_multi_shift_binding_picks_nearest_not_admin(self):
        """绑定「中班 16:00」+「行政班 8:30」时，15:4x 的卡应判中班且不迟到。"""
        candidates = [
            {"shift_type": "中班", "start_time": timedelta(hours=16),
             "late_after": timedelta(hours=16, minutes=1)},
            {"shift_type": "行政班", "start_time": timedelta(hours=8, minutes=30),
             "late_after": timedelta(hours=8, minutes=31)},
        ]
        for hm in ((15, 34), (15, 42), (15, 53)):
            shift, late = match_rule_by_time(candidates, datetime(2026, 9, 10, *hm), True)
            self.assertEqual(shift, "中班", "%02d:%02d 应判中班" % hm)
            self.assertFalse(late, "%02d:%02d 不应判迟到" % hm)

    def test_morning_card_still_admin(self):
        candidates = [
            {"shift_type": "中班", "start_time": timedelta(hours=16),
             "late_after": timedelta(hours=16, minutes=1)},
            {"shift_type": "行政班", "start_time": timedelta(hours=8, minutes=30),
             "late_after": timedelta(hours=8, minutes=31)},
        ]
        shift, _ = match_rule_by_time(candidates, datetime(2026, 9, 10, 8, 45), False)
        self.assertEqual(shift, "行政班")


if __name__ == "__main__":
    unittest.main()


class SafetyNightShiftTest(unittest.TestCase):
    """安全部晚班 21:00 上班、21:01 起算迟到（Owner 2026-09-11 对齐规则表）。

    事故：原硬编码 20:31 起算迟到，樊祥岩/王翔宇/谷亚超 9/10 的 20:5x 上班卡
    （提前到岗）被误判迟到。
    """

    def _get_shift_and_late(self, h, m):
        # SAFETY_NUMS 分支已抽为 pairing 纯函数（离线可测，api 层直接调用它）
        from hb_attendance_app.hbos_attendance.pairing import safety_shift_from_gap
        return safety_shift_from_gap(datetime(2026, 9, 10, h, m))

    def test_2057_not_late(self):
        shift, late = self._get_shift_and_late(20, 57)
        self.assertEqual(shift, "晚班")
        self.assertFalse(late)

    def test_2101_late(self):
        shift, late = self._get_shift_and_late(21, 1)
        self.assertEqual(shift, "晚班")
        self.assertTrue(late)

    def test_2105_late(self):
        shift, late = self._get_shift_and_late(21, 5)
        self.assertEqual(shift, "晚班")
        self.assertTrue(late)

    def test_morning_0831_still_late(self):
        # 早班 8:31 起算迟到，不变
        shift, late = self._get_shift_and_late(8, 31)
        self.assertEqual(shift, "早班")
        self.assertTrue(late)

    def test_morning_0830_not_late(self):
        shift, late = self._get_shift_and_late(8, 30)
        self.assertEqual(shift, "早班")
        self.assertFalse(late)
