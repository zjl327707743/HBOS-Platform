import unittest
from datetime import datetime, date

from hb_attendance_app.hbos_attendance.pairing import (
    dedup_checkins,
    pair_employee_checkins,
    role_from_terminal,
    special_shift_from_gap,
)


class NightOutRestDayTest(unittest.TestCase):
    """夜班下班日次日休息: 下班卡在早4-10点的那天+次日无打卡=休息, 之后连续无打卡算缺勤。"""

    def test_night_out_days_extraction(self):
        from hb_attendance_app.hbos_attendance.pairing import night_out_days_from_roles
        cks = [
            {"time": datetime(2026, 8, 6, 23, 51)},
            {"time": datetime(2026, 8, 7, 8, 10)},
            {"time": datetime(2026, 8, 7, 23, 52)},
            {"time": datetime(2026, 8, 8, 8, 23)},
        ]
        roles = ["in", "out", "in", "out"]
        days = night_out_days_from_roles(cks, roles)
        self.assertEqual(days, {date(2026, 8, 7), date(2026, 8, 8)})

    def test_midnight_out_card_not_night_out_day(self):
        # 凌晨0-4点的下班卡不算「夜班下班日」(那是中班跨天)
        from hb_attendance_app.hbos_attendance.pairing import night_out_days_from_roles
        cks = [{"time": datetime(2026, 8, 3, 0, 30)}]
        roles = ["out"]
        self.assertEqual(night_out_days_from_roles(cks, roles), set())

    def test_early_out_card_before_8am_not_night_out_day(self):
        # 8点前打卡算早退, 不算正常夜班下班日(Owner 2026-08-20 确认)
        from hb_attendance_app.hbos_attendance.pairing import night_out_days_from_roles
        cks = [{"time": datetime(2026, 8, 3, 7, 50)}]
        roles = ["out"]
        self.assertEqual(night_out_days_from_roles(cks, roles), set())

    def test_out_card_8_to_10_is_night_out_day(self):
        from hb_attendance_app.hbos_attendance.pairing import night_out_days_from_roles
        cks = [{"time": datetime(2026, 8, 3, 8, 0)}, {"time": datetime(2026, 8, 3, 9, 59)}]
        roles = ["out", "out"]
        self.assertEqual(night_out_days_from_roles(cks, roles), {date(2026, 8, 3)})

    def test_day_shift_out_card_not_night_out_day(self):
        # 16点的下班卡不算
        from hb_attendance_app.hbos_attendance.pairing import night_out_days_from_roles
        cks = [{"time": datetime(2026, 8, 3, 16, 30)}]
        roles = ["out"]
        self.assertEqual(night_out_days_from_roles(cks, roles), set())


class SpecialShiftTest(unittest.TestCase):
    """无菌/三班独立班次体系: 无菌早/晚(12h) + 早/中/夜班(8h)。"""

    def test_sterile_day_shift_on_time(self):
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 10, 8, 30), 12), ("无菌早", False))

    def test_sterile_day_shift_late(self):
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 10, 8, 31), 12), ("无菌早", True))

    def test_sterile_night_shift_on_time(self):
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 10, 20, 30), 12), ("无菌晚", False))

    def test_sterile_night_shift_late(self):
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 10, 20, 31), 12), ("无菌晚", True))

    def test_day_shift_8h(self):
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 10, 8, 30), 8), ("早班", False))
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 10, 8, 31), 8), ("早班", True))

    def test_middle_shift_8h(self):
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 10, 16, 30), 8), ("中班", False))
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 10, 16, 31), 8), ("中班", True))

    def test_night_shift_8h(self):
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 11, 0, 30), 8), ("夜班", False))
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 11, 0, 31), 8), ("夜班", True))

    def test_pairing_sterile_day(self):
        # 8:30 → 20:31 的 12h 班: 无菌早
        cks = [{"time": datetime(2026, 8, 10, 8, 30), "employee_name": "秦瑀", "department": "无菌车间"},
               {"time": datetime(2026, 8, 10, 20, 31), "employee_name": "秦瑀", "department": "无菌车间"}]
        atts = pair_employee_checkins(cks, "E1", "11008015", fake_shift_fn)
        self.assertIn(("2026-08-10", "Present", "无菌早", 0, 12.02), statuses(atts))

    def test_pairing_sterile_night_cross_day(self):
        # 20:30 → 次日 8:31 的 12h 班: 无菌晚
        cks = [{"time": datetime(2026, 8, 10, 20, 30), "employee_name": "秦瑀", "department": "无菌车间"},
               {"time": datetime(2026, 8, 11, 8, 31), "employee_name": "秦瑀", "department": "无菌车间"}]
        atts = pair_employee_checkins(cks, "E1", "11008015", fake_shift_fn)
        self.assertIn(("2026-08-10", "Present", "无菌晚", 0, 12.02), statuses(atts))


class MultiCardFallbackTest(unittest.TestCase):
    """多次卡兜底: 当天已有完整上下班结构(首末间隔2-18h), 孤立卡视为重复卡不判缺勤。"""

    def _ck(self, day, hour, minute, sn=None):
        d = {"time": datetime(2026, 8, day, hour, minute),
             "employee_name": "测试", "department": "四车间"}
        if sn:
            d["hbos_terminal_sn"] = sn
        return d

    def test_duplicate_after_complete_span_not_absent(self):
        # 7:40 上班机 + 16:10 下班机 = 完整班次 Present
        # 8:00 多余上班机卡 → 当天已有完整上下班结构, 视为重复卡不判缺勤
        # (Owner 2026-08-21 确认, 陈雨欣 8/19 案例同规则)
        cks = [self._ck(16, 7, 40, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 8, 0, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 16, 10, "13750CS_9FB66A86CF3487D7")]
        atts = pair_employee_checkins(cks, "E1", "11004051", fake_shift_fn, terminal_aware=True)
        s = statuses(atts)
        # 完整班次仍正常配对
        self.assertIn(("2026-08-16", "Present", "早班", 0, 8.5), s)
        # 多余的上班机卡不再判缺勤
        self.assertNotIn(("2026-08-16", "Absent", "", 0, 0), s)

    def test_single_card_still_absent(self):
        # 只有一张上班卡无下班卡 → 仍判缺勤
        cks = [self._ck(16, 7, 40, "13750CS_D7C69C16EC0B2447")]
        atts = pair_employee_checkins(cks, "E1", "11004051", fake_shift_fn, terminal_aware=True)
        self.assertIn(("2026-08-16", "Absent", "", 0, 0), statuses(atts))

    def test_span_over_18h_not_fallback(self):
        # 间隔超过18h不配对: 8/16 上班卡向后找不到下班卡(8/17 的下班卡间隔>18h) → 缺勤
        # 8/17 的上班卡与 8/17 下班卡正常配对
        cks = [self._ck(16, 7, 40, "13750CS_D7C69C16EC0B2447"),
               self._ck(17, 7, 40, "13750CS_D7C69C16EC0B2447"),
               self._ck(17, 16, 10, "13750CS_9FB66A86CF3487D7")]
        atts = pair_employee_checkins(cks, "E1", "11004051", fake_shift_fn, terminal_aware=True)
        s = statuses(atts)
        self.assertIn(("2026-08-17", "Present", "早班", 0, 8.5), s)
        self.assertIn(("2026-08-16", "Absent", "", 0, 0), s)


class NightOutMispunchTest(unittest.TestCase):
    """跨天夜班下班误刷上班机(Owner 2026-08-21, 吕玉升/庞冠军 8/16 案例)。"""

    def _ck(self, day, hour, minute, second, sn):
        return {"time": datetime(2026, 8, day, hour, minute, second),
                "employee_name": "测试", "department": "生产部", "hbos_terminal_sn": sn}

    def test_night_out_mispunch_not_absent(self):
        # 8/15 20:24 晚班上班 → 8/16 08:36 下班误刷上班机 + 08:37 正常下班
        cks = [self._ck(15, 20, 24, 31, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 8, 36, 37, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 8, 37, 10, "13750CS_9FB66A86CF3487D7")]
        atts = pair_employee_checkins(cks, "E1", "10010011", fake_shift_fn, terminal_aware=True)
        s = statuses(atts)
        self.assertIn(("2026-08-15", "Present", "晚班", 0, 12.21), s)
        self.assertNotIn(("2026-08-16", "Absent", "", 0, 0), s)

    def test_night_out_early_start_not_absent(self):
        # 庞冠军: 8/15 19:39 晚班提前到岗 → 8/16 08:06 误刷 + 08:07 正常下班
        cks = [self._ck(15, 19, 39, 27, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 8, 6, 15, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 8, 7, 36, "13750CS_9FB66A86CF3487D7")]
        atts = pair_employee_checkins(cks, "E1", "11003028", fake_shift_fn, terminal_aware=True)
        s = statuses(atts)
        self.assertIn(("2026-08-15", "Present", "晚班", 0, 12.47), s)
        self.assertNotIn(("2026-08-16", "Absent", "", 0, 0), s)

    def test_lone_in_card_no_night_before_still_absent(self):
        # 真正缺勤: 早上孤立上班卡, 前一日无夜班卡 → 仍判缺勤
        cks = [self._ck(16, 8, 30, 0, "13750CS_D7C69C16EC0B2447")]
        atts = pair_employee_checkins(cks, "E1", "10010011", fake_shift_fn, terminal_aware=True)
        self.assertIn(("2026-08-16", "Absent", "", 0, 0), statuses(atts))


class SterileOvertimePairTest(unittest.TestCase):
    """无菌倒班加班超 13 小时配对（李明 8/19 案例: 08:17-21:28 = 13.17h）。

    Owner 2026-08-21 确认: 配对上限放宽到 14 小时, 12 小时班 + 加班缓冲;
    冯慧杰 8/15 15.69h 假超长班仍被拦截(>14h)。
    """

    def _ck(self, day, hour, minute, second, sn):
        return {"time": datetime(2026, 8, day, hour, minute, second),
                "employee_name": "李明", "department": "无菌车间",
                "hbos_terminal_sn": sn}

    def test_sterile_13h_overtime_pairs(self):
        # 李明 8/19: 08:17:56 上班机 → 21:28:17 下班机 = 13.17h
        cks = [self._ck(19, 8, 17, 56, "13750CS_D7C69C16EC0B2447"),
               self._ck(19, 21, 28, 17, "13750CS_9FB66A86CF3487D7")]
        atts = pair_employee_checkins(cks, "E1", "11008018", fake_shift_fn, terminal_aware=True)
        s = statuses(atts)
        self.assertIn(("2026-08-19", "Present", "无菌早", 0, 13.17), s)
        self.assertNotIn(("2026-08-19", "Absent", "", 0, 0), s)

    def test_over_16h_still_not_pairs(self):
        # 超过16小时: 漏下班卡导致的假超长班仍不配对
        # (冯慧杰 8/15 15.69h 属真实加班, 16h 上限下正常配对; 16h 以上仍拦截)
        cks = [self._ck(15, 8, 0, 0, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 1, 0, 0, "13750CS_9FB66A86CF3487D7")]
        atts = pair_employee_checkins(cks, "E1", "11008018", fake_shift_fn, terminal_aware=True)
        s = statuses(atts)
        self.assertNotIn(("2026-08-15", "Present", "无菌早", 0, 17.0), s)

    def test_under_16h_pairs(self):
        # 15.7h(冯慧杰 8/15 案例): 16h 上限下正常配对成 Present
        cks = [self._ck(15, 8, 19, 0, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 0, 0, 0, "13750CS_9FB66A86CF3487D7")]
        atts = pair_employee_checkins(cks, "E1", "11008018", fake_shift_fn, terminal_aware=True)
        s = statuses(atts)
        self.assertIn(("2026-08-15", "Present", "无菌早", 0, 15.68), s)

    def test_sterile_night_early_start_not_late(self):
        # 张志兴 8/19: 19:56 上班 13.16h → 无菌晚(20:30标准)提前到岗, 不判迟到
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 19, 19, 56), 13.16), ("无菌晚", False))

    def test_sterile_night_after_2031_late(self):
        # 20:31 起算迟到仍生效
        self.assertEqual(special_shift_from_gap(datetime(2026, 8, 19, 20, 31), 12), ("无菌晚", True))


class TerminalRoleTest(unittest.TestCase):
    def test_in_terminal_sn_maps_to_in(self):
        self.assertEqual(role_from_terminal("13750CS_D7C69C16EC0B2447"), "in")

    def test_out_terminal_sn_maps_to_out(self):
        self.assertEqual(role_from_terminal("13750CS_9FB66A86CF3487D7"), "out")

    def test_unknown_terminal_falls_back_to_none(self):
        self.assertIsNone(role_from_terminal("13750CS_9999999999999999"))
        self.assertIsNone(role_from_terminal(""))
        self.assertIsNone(role_from_terminal(None))

    def test_split_machine_rule_active_from_0815(self):
        # 8/15 及之后: 设备 SN 生效
        self.assertEqual(role_from_terminal("13750CS_D7C69C16EC0B2447", datetime(2026, 8, 15, 8, 0)), "in")
        self.assertEqual(role_from_terminal("13750CS_02281E713F33A9A8", datetime(2026, 8, 18, 16, 0)), "in")
        self.assertEqual(role_from_terminal("13750CS_9FB66A86CF3487D7", datetime(2026, 8, 18, 17, 0)), "out")
        self.assertEqual(role_from_terminal("13750CS_93C9390B9995FE8C", datetime(2026, 8, 18, 8, 0)), "out")

    def test_split_machine_rule_inactive_before_0815(self):
        # 8/15 前: 分机未实施, 设备 SN 不判方向, 回退配对推断
        self.assertIsNone(role_from_terminal("13750CS_D7C69C16EC0B2447", datetime(2026, 8, 14, 23, 59)))
        self.assertIsNone(role_from_terminal("13750CS_9FB66A86CF3487D7", datetime(2026, 8, 14, 17, 0)))


def fake_shift_fn(ck_dt, emp_num, cross_day=False):
    """测试用班次判定：复制 api._get_shift_and_late 的通用倒班分支（不含特殊名单）。"""
    h = ck_dt.hour
    m = ck_dt.minute
    ts = ck_dt.strftime("%H:%M:%S")
    if h >= 20 or h < 4:
        return ("晚班", h < 4 and ts > "00:00:00")
    if 4 <= h < 8:
        return ("早班", False)
    if h == 8:
        return ("早班", m > 0)
    if 9 <= h < 12:
        return ("行政班早班", True)
    if 12 <= h < 16:
        return ("中班", False)
    if 16 <= h < 20:
        if cross_day:
            return ("晚班", False) if h >= 19 else ("中班", False)
        return ("中班", ts > "16:00:00")
    return ("晚班", False)


def ck(day, hour, minute, second=0):
    return {"time": datetime(2026, 8, day, hour, minute, second),
            "employee_name": "刘兴军", "department": "五车间"}


def statuses(atts):
    """返回 {(date_str, status, shift, late, hours)}"""
    return {(a[2], a[3], a[4], a[5], a[7]) for a in atts}


class LiuXingJunCaseTest(unittest.TestCase):
    """刘兴军真实数据回归：零点夜班不再误判缺勤。"""

    def setUp(self):
        # 8/1 23:51 → 8/2 08:00 夜班；8/3 00:47 → 08:00 零点夜班；8/5 早班
        self.cks = [
            ck(1, 23, 51, 2), ck(2, 8, 0, 9),
            ck(3, 0, 47, 7), ck(3, 8, 0, 43),
            ck(5, 7, 54, 28), ck(5, 16, 1, 14),
        ]

    def test_8_3_is_present_night_shift_not_absent(self):
        atts = pair_employee_checkins(self.cks, "HR-EMP-00329", "11005042", fake_shift_fn)
        s = statuses(atts)
        # 8/3: Present 晚班、迟到 1、7.23h（00:47:07 → 08:00:43 = 7.2266h 四舍五入）
        self.assertIn(("2026-08-03", "Present", "晚班", 1, 7.23), s)
        self.assertNotIn(("2026-08-03", "Absent", "", 0, 0), s)

    def test_8_1_night_shift_pairing_unchanged(self):
        atts = pair_employee_checkins(self.cks, "HR-EMP-00329", "11005042", fake_shift_fn)
        s = statuses(atts)
        # 8/1 23:51 → 8/2 08:00 夜班 8.15h 仍正确
        self.assertIn(("2026-08-01", "Present", "晚班", 0, 8.15), s)

    def test_8_5_day_shift_unchanged(self):
        atts = pair_employee_checkins(self.cks, "HR-EMP-00329", "11005042", fake_shift_fn)
        s = statuses(atts)
        self.assertIn(("2026-08-05", "Present", "早班", 0, 8.11), s)


class ZeroShiftBoundaryTest(unittest.TestCase):
    def test_zero_shift_on_time(self):
        atts = pair_employee_checkins([ck(3, 0, 0, 0), ck(3, 8, 0, 0)],
                                      "E1", "10001", fake_shift_fn)
        self.assertIn(("2026-08-03", "Present", "晚班", 0, 8.0), statuses(atts))

    def test_zero_shift_late(self):
        atts = pair_employee_checkins([ck(3, 0, 47, 7), ck(3, 8, 0, 43)],
                                      "E1", "10001", fake_shift_fn)
        self.assertIn(("2026-08-03", "Present", "晚班", 1, 7.23), statuses(atts))

    def test_zero_shift_too_short_is_absent(self):
        # 0:30 → 1:30 不足 2 小时，不配成零点班 → 凌晨孤卡缺勤
        atts = pair_employee_checkins([ck(3, 0, 30), ck(3, 1, 30)],
                                      "E1", "10001", fake_shift_fn)
        self.assertIn(("2026-08-03", "Absent", "", 0, 0), statuses(atts))

    def test_zero_shift_out_after_10am_not_paired(self):
        # 10:00 及之后的卡不算零点班下班卡 → 凌晨孤卡缺勤
        atts = pair_employee_checkins([ck(3, 0, 30), ck(3, 10, 30)],
                                      "E1", "10001", fake_shift_fn)
        self.assertIn(("2026-08-03", "Absent", "", 0, 0), statuses(atts))


class RestDayAfterNightShiftTest(unittest.TestCase):
    """下夜班休息日：当天卡被前一夜班配对消耗，不再补缺勤。"""

    def test_rest_day_after_night_shift_has_no_absent(self):
        # 8/1 23:51 → 8/2 08:00 夜班；8/2 白天休息（无其他卡）
        atts = pair_employee_checkins([ck(1, 23, 51), ck(2, 8, 0)],
                                      "E1", "10001", fake_shift_fn)
        self.assertIn(("2026-08-01", "Present", "晚班", 0, 8.15), statuses(atts))
        # 8/2 不得出现 Absent（休息日）
        self.assertNotIn(("2026-08-02", "Absent", "", 0, 0), statuses(atts))

    def test_night_shift_out_next_morning_then_new_shift(self):
        # 韩百泉真实模式：8/2 15:44 中班上班 → 8/3 00:15 下班；
        # 8/2 08:00 不是中班上班卡，主循环 15:44→00:15 间隔 8.5h 应为中班
        atts = pair_employee_checkins([ck(2, 15, 44), ck(3, 0, 15)],
                                      "E1", "10001", fake_shift_fn)
        s = statuses(atts)
        self.assertIn(("2026-08-02", "Present", "中班", 0, 8.52), s)
        self.assertNotIn(("2026-08-03", "Absent", "", 0, 0), s)


class DedupTest(unittest.TestCase):
    def test_adjacent_under_10min_merged(self):
        out = dedup_checkins([ck(3, 8, 0, 0), ck(3, 8, 5, 0)])
        self.assertEqual(len(out), 1)

    def test_adjacent_over_10min_kept(self):
        out = dedup_checkins([ck(3, 8, 0, 0), ck(3, 8, 11, 0)])
        self.assertEqual(len(out), 2)


class FixedMorningGroupTest(unittest.TestCase):
    """固定早班群体（行政/安全/食堂/豁免）跳过向前配对与零点夜班配对。"""

    def test_zero_shift_not_applied_for_admin_group(self):
        # 行政班名单成员凌晨卡不按零点班配对 → 凌晨孤卡缺勤
        atts = pair_employee_checkins([ck(3, 0, 47), ck(3, 8, 0)],
                                      "E1", "10006001", fake_shift_fn,
                                      is_admin=True, skip_forward=True, skip_night_lock=True)
        self.assertIn(("2026-08-03", "Absent", "", 0, 0), statuses(atts))

    def test_exempt_member_never_absent(self):
        atts = pair_employee_checkins([ck(3, 0, 47)],
                                      "E1", "10006001", fake_shift_fn,
                                      is_exempt=True, skip_forward=True, skip_night_lock=True)
        self.assertNotIn(("2026-08-03", "Absent", "", 0, 0), statuses(atts))


if __name__ == "__main__":
    unittest.main()
