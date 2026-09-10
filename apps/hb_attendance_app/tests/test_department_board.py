import unittest
from datetime import datetime, date
from pathlib import Path

from hb_attendance_app.hbos_attendance.department_board import (
    resolve_expected, live_state, day_review, bound_times, pick_bound_rule,
)

DATA_PY = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/department_board_data.py"
WS_JSON = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/workspace/海滨考勤工作台/海滨考勤工作台.json"


def profile(**kw):
    base = {
        "num": "1", "exempt": False, "late_exempt": False, "admin_list": False, "food": False,
        "safety": False, "rotate_label": None,
        "bound": False, "bound_shift_type": None, "bound_start": None, "bound_late": None,
        "schedule": None, "leave_record": False, "leave_record_type": None,
    }
    base.update(kw)
    return base


class ResolveExpectedTest(unittest.TestCase):
    def test_schedule_rest_wins(self):
        p = profile(schedule={"kind": "rest", "shift_type": "休息",
                              "start_time": None, "late_after": None, "leave_type": None})
        e = resolve_expected(p, weekday=0)
        self.assertEqual(e["kind"], "rest")
        self.assertEqual(e["label"], "休息")

    def test_schedule_leave(self):
        p = profile(schedule={"kind": "leave", "shift_type": None,
                              "start_time": None, "late_after": None, "leave_type": "年假"})
        e = resolve_expected(p, weekday=0)
        self.assertEqual(e["kind"], "leave")

    def test_schedule_shift_beats_bound(self):
        p = profile(
            schedule={"kind": "shift", "shift_type": "行政班",
                      "start_time": "08:30", "late_after": "08:31", "leave_type": None},
            bound=True, bound_shift_type="早班", bound_start="08:00", bound_late="08:01",
        )
        e = resolve_expected(p, weekday=0)
        self.assertEqual(e["kind"], "shift")
        self.assertEqual(e["shift_type"], "行政班")
        self.assertEqual(e["start_time"], "08:30")
        self.assertEqual(e["late_after"], "08:31")

    def test_exempt_priority(self):
        p = profile(exempt=True,
                    schedule={"kind": "shift", "shift_type": "早班",
                              "start_time": "08:00", "late_after": "08:01", "leave_type": None})
        e = resolve_expected(p, weekday=0)
        self.assertEqual(e["kind"], "exempt")

    def test_bound_fallback(self):
        e = resolve_expected(profile(bound=True, bound_shift_type="早班",
                                     bound_start="08:00", bound_late="08:01"), weekday=3)
        self.assertEqual(e["kind"], "shift")
        self.assertEqual(e["shift_type"], "早班")
        self.assertEqual(e["start_time"], "08:00")

    def test_admin_weekday_vs_weekend(self):
        e = resolve_expected(profile(admin_list=True), weekday=3)
        self.assertEqual(e["kind"], "shift")
        self.assertEqual(e["start_time"], "08:30")
        self.assertEqual(e["late_after"], "08:31")
        e_we = resolve_expected(profile(admin_list=True), weekday=6)
        self.assertEqual(e_we["kind"], "rest")

    def test_food_fact_only(self):
        e = resolve_expected(profile(food=True), weekday=2)
        self.assertEqual(e["kind"], "shift")
        self.assertIsNone(e["start_time"])
        self.assertEqual(e["label"], "食堂")

    def test_safety_and_rotate_undetermined(self):
        e = resolve_expected(profile(safety=True), weekday=1)
        self.assertIsNone(e["start_time"])
        self.assertEqual(e["label"], "安全倒班")
        e2 = resolve_expected(profile(rotate_label="四班次倒班"), weekday=1)
        self.assertIsNone(e2["start_time"])
        self.assertEqual(e2["label"], "四班次倒班")

    def test_unknown(self):
        e = resolve_expected(profile(), weekday=0)
        self.assertEqual(e["kind"], "unknown")
        self.assertEqual(e["label"], "在册待确认")

    def test_general_rotate_label_fact_only(self):
        """数据层兜底：无排班/绑定/名单命中者 rotate_label=通用倒班 →
        kind=shift、无起算点 → 只报打卡事实、计入应出勤。"""
        e = resolve_expected(profile(rotate_label="通用倒班"), weekday=1)
        self.assertEqual(e["kind"], "shift")
        self.assertIsNone(e["start_time"])
        self.assertIsNone(e["late_after"])
        self.assertEqual(e["label"], "通用倒班")


class BoundRulePickTest(unittest.TestCase):
    """倒班人员绑定多条规则：按当天首卡时间挑班次；坏 late_after 不得误判迟到。

    案例（陈飞 10007015 环保部，2026-09-10）：绑定「早班 08:00-16:00」+「两班倒中班
    13:00-20:00」，当天 12:48 打卡。原实现只取一条绑定、且该中班规则的 late_after
    误填 08:31（早于上班时间），导致 12:48 被判迟到。
    """

    def test_bad_late_after_falls_back_to_start_plus_one(self):
        self.assertEqual(bound_times("13:00", "08:31"), ("13:00", "13:01"))
        self.assertEqual(bound_times("13:00", None), ("13:00", "13:01"))
        self.assertEqual(bound_times("08:00", "08:01"), ("08:00", "08:01"))  # 正常不动

    def test_pick_nearest_start_by_reference_time(self):
        rules = [
            {"shift_type": "早班", "start_hm": "08:00", "late_hm": "08:01"},
            {"shift_type": "行政班", "start_hm": "13:00", "late_hm": "08:31"},
        ]
        self.assertEqual(pick_bound_rule(rules, "12:48")[0], "行政班")   # 接近 13:00
        self.assertEqual(pick_bound_rule(rules, "07:54")[0], "早班")     # 接近 08:00

    def test_pick_without_reference_uses_first(self):
        rules = [
            {"shift_type": "早班", "start_hm": "08:00", "late_hm": "08:01"},
            {"shift_type": "行政班", "start_hm": "13:00", "late_hm": "08:31"},
        ]
        self.assertEqual(pick_bound_rule(rules, None)[0], "早班")

    def test_pick_empty_returns_none(self):
        self.assertIsNone(pick_bound_rule([], "09:00"))
        self.assertIsNone(pick_bound_rule(None, "09:00"))

    def test_chen_fei_1248_not_late(self):
        """端到端（纯函数）：12:48 到岗、选中 13:00 中班 → 不判迟到。"""
        rules = [
            {"shift_type": "早班", "start_hm": "08:00", "late_hm": "08:01"},
            {"shift_type": "行政班", "start_hm": "13:00", "late_hm": "08:31"},
        ]
        picked = pick_bound_rule(rules, "12:48")
        start_hm, late_hm = bound_times(picked[1], picked[2])
        p = profile(bound=True, bound_shift_type=picked[0],
                    bound_start=start_hm, bound_late=late_hm)
        e = resolve_expected(p, weekday=3)      # 2026-09-10 是周四
        self.assertEqual(e["kind"], "shift")
        self.assertEqual(e["start_time"], "13:00")
        st = live_state(e, p, [datetime(2026, 9, 10, 12, 48)],
                        datetime(2026, 9, 10, 14, 0))
        self.assertEqual(st["state"], "present")
        self.assertNotIn("迟到", st["tags"])


class OutCardNotArrivalTest(unittest.TestCase):
    """下班机卡不得当作到岗卡（吕玉升 2026-09-10：08:01 下班卡被误标早班迟到）。"""

    def _d(self, h, m=0):
        return datetime(2026, 9, 10, h, m)

    def _morning_shift(self):
        return {"kind": "shift", "shift_type": "早班", "start_time": "08:00",
                "late_after": "08:01", "label": "早班"}

    def test_out_only_card_is_not_late(self):
        ev = [self._d(8, 1)]                      # 当天只有一张下班机卡
        st = live_state(self._morning_shift(), profile(), ev, self._d(14), out_events=ev)
        self.assertNotIn("迟到", st["tags"])       # 关键：不得判迟到
        self.assertEqual(st["state"], "out_only")
        self.assertEqual(st["out_hm"], "08:01")

    def test_out_card_not_picked_as_first_arrival(self):
        # 凌晨 00:05 是前夜班的尾巴（下班机卡），真正的上班卡是 07:55 → 到岗取 07:55
        outs = [self._d(0, 5)]
        ev = [self._d(0, 5), self._d(7, 55)]
        st = live_state(self._morning_shift(), profile(), ev, self._d(9), out_events=outs)
        self.assertEqual(st["state"], "present")
        self.assertEqual(st["first_hm"], "07:55")

    def test_night_shift_worker_before_start_not_present(self):
        # 晚班 20:00 上班、现在 13:59：早上那张是前夜下班卡 → 还没上班，不是「已到岗」
        e = {"kind": "shift", "shift_type": "晚班", "start_time": "20:00",
             "late_after": "20:01", "label": "晚班"}
        outs = [self._d(8, 8)]
        st = live_state(e, profile(), outs, self._d(13, 59), out_events=outs)
        self.assertEqual(st["state"], "before_start")
        self.assertNotIn("迟到", st["tags"])

    def test_night_shift_worker_after_start_shows_out_only(self):
        # 同一人到了 21:00 仍未打上班卡 → 只报「仅下班卡」，不判迟到/缺勤
        e = {"kind": "shift", "shift_type": "晚班", "start_time": "20:00",
             "late_after": "20:01", "label": "晚班"}
        outs = [self._d(8, 8)]
        st = live_state(e, profile(), outs, self._d(21), out_events=outs)
        self.assertEqual(st["state"], "out_only")
        self.assertNotIn("迟到", st["tags"])

    def test_direction_unknown_keeps_time_based_judgement(self):
        # 分机实施前 / GPS / 未登记设备：无方向信息，仍按时间判定（不回归）
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        st = live_state(e, profile(), [self._d(8, 45)], self._d(9), out_events=[])
        self.assertEqual(st["state"], "late")

    def test_review_mode_out_only(self):
        st = day_review(self._morning_shift(), profile(), [self._d(8, 1)], self._d(23),
                        out_events=[self._d(8, 1)])
        self.assertEqual(st["state"], "out_only")
        self.assertNotIn("迟到", st["tags"])


class OutPunchTest(unittest.TestCase):
    """「已下班」判定：仅当有可信下班卡（下班机 + 与首次到岗间隔 >=2h）时给出 out_hm。"""

    def _shift(self):
        return {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
                "late_after": "08:31", "label": "行政班"}

    def _d(self, h, m=0):
        return datetime(2026, 9, 8, h, m)

    def test_finished_shift_reports_out_hm(self):
        st = live_state(self._shift(), profile(),
                        [self._d(8, 20), self._d(17, 2)],
                        self._d(18), out_events=[self._d(17, 2)])
        self.assertEqual(st["state"], "present")
        self.assertEqual(st["first_hm"], "08:20")
        self.assertEqual(st["out_hm"], "17:02")     # 上完一整班 → 标出已下班

    def test_still_on_duty_has_no_out_hm(self):
        # 只打了上班卡（还没下班）→ 不显示已下班
        st = live_state(self._shift(), profile(), [self._d(8, 20)],
                        self._d(12), out_events=[])
        self.assertEqual(st["state"], "present")
        self.assertIsNone(st["out_hm"])

    def test_short_gap_out_ignored(self):
        # 上班后 15 分钟就出现下班机卡（误刷/连刷，不足最短班次 2h）→ 不算已下班
        st = live_state(self._shift(), profile(),
                        [self._d(8, 20), self._d(8, 35)],
                        self._d(12), out_events=[self._d(8, 35)])
        self.assertIsNone(st["out_hm"])

    def test_last_qualified_out_wins(self):
        # 下班后折返又刷一次 → 取最后一次
        st = live_state(self._shift(), profile(),
                        [self._d(8, 20), self._d(17, 2), self._d(19, 30)],
                        self._d(20), out_events=[self._d(17, 2), self._d(19, 30)])
        self.assertEqual(st["out_hm"], "19:30")

    def test_fact_only_shift_also_reports_out_hm(self):
        # 班次起算点未定（通用倒班）也应能看出已下班
        e = {"kind": "shift", "shift_type": None, "start_time": None,
             "late_after": None, "label": "通用倒班"}
        st = live_state(e, profile(), [self._d(7, 45), self._d(17, 20)],
                        self._d(18), out_events=[self._d(17, 20)])
        self.assertEqual(st["state"], "fact_present")
        self.assertEqual(st["out_hm"], "17:20")

    def test_review_mode_day_param_wins_over_now(self):
        """回顾模式：now 是今天、目标是历史日，day 必须显式传入，否则 out_hm 会因
        日期不匹配而丢失（now.date() != 目标日）。"""
        e = resolve_expected(profile(), weekday=1)
        st = day_review(e, profile(), [self._d(8, 20), self._d(17, 2)], self._d(23),
                        attendance={"status": "Present", "late_entry": False,
                                    "early_exit": False},
                        out_events=[self._d(17, 2)], day=datetime(2026, 9, 8).date())
        self.assertEqual(st["out_hm"], "17:02")

    def test_review_mode_reports_out_hm_and_first_card(self):
        e = resolve_expected(profile(), weekday=1)
        st = day_review(e, profile(), [self._d(8, 20), self._d(17, 2)], self._d(23),
                        attendance={"status": "Present", "late_entry": False,
                                    "early_exit": False},
                        out_events=[self._d(17, 2)])
        self.assertEqual(st["state"], "out_day")
        self.assertEqual(st["first_hm"], "08:20")   # 回顾模式首卡不再是空
        self.assertEqual(st["out_hm"], "17:02")

    def test_absent_row_has_no_out_hm(self):
        e = resolve_expected(profile(), weekday=1)
        st = day_review(e, profile(), [], self._d(23),
                        attendance={"status": "Absent", "late_entry": False,
                                    "early_exit": False},
                        out_events=[self._d(8, 35)])
        self.assertEqual(st["state"], "absent_day")
        self.assertIsNone(st["out_hm"])


class LiveStateTest(unittest.TestCase):
    def _day(self):
        return datetime(2026, 9, 8)  # 周二

    def test_leave_record_no_card(self):
        p = profile(leave_record=True, leave_record_type="事假",
                    schedule={"kind": "shift", "shift_type": "行政班",
                              "start_time": "08:30", "late_after": "08:31", "leave_type": None})
        e = resolve_expected(p, weekday=1)
        st = live_state(e, p, [], datetime(2026, 9, 8, 10, 0))
        self.assertEqual(st["state"], "leave")
        self.assertIn("事假", st["label"])

    def test_leave_record_but_clocked_is_present(self):
        p = profile(leave_record=True, leave_record_type="病假",
                    schedule={"kind": "shift", "shift_type": "行政班",
                              "start_time": "08:30", "late_after": "08:31", "leave_type": None})
        e = resolve_expected(p, weekday=1)
        # 8:25 在入窗点(04:30)之后、迟到点(08:31)之前 → 出勤非迟到
        ev = [datetime(2026, 9, 8, 8, 25)]
        st = live_state(e, p, ev, datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "present")
        self.assertEqual(st["first_hm"], "08:25")

    def test_before_start(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        st = live_state(e, profile(), [], datetime(2026, 9, 8, 7, 0))
        self.assertEqual(st["state"], "before_start")

    def test_pending_between_start_and_late(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        # 08:30:30 在上班点(08:30)之后、迟到点(08:31)之前 → 未打卡待判定
        st = live_state(e, profile(), [], datetime(2026, 9, 8, 8, 30, 30))
        self.assertEqual(st["state"], "pending")

    def test_absent_expected_after_late(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        st = live_state(e, profile(), [], datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "absent_expected")
        self.assertTrue(st["note"])

    def test_present_not_late(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        st = live_state(e, profile(), [datetime(2026, 9, 8, 8, 20)], datetime(2026, 9, 8, 9, 0))
        self.assertEqual(st["state"], "present")
        self.assertEqual(st["tags"], [])

    def test_late(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        st = live_state(e, profile(), [datetime(2026, 9, 8, 8, 45)], datetime(2026, 9, 8, 9, 0))
        self.assertEqual(st["state"], "late")
        self.assertIn("迟到", st["tags"])

    def test_offwindow_card_not_absent(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        # 只有 00:30 一张卡（入窗点 04:30 之前），不应判「未打卡」
        st = live_state(e, profile(), [datetime(2026, 9, 8, 0, 30)], datetime(2026, 9, 8, 9, 0))
        self.assertIn(st["state"], ("present_offwindow",))
        self.assertFalse(st["tags"])

    def test_fact_only(self):
        e = {"kind": "shift", "shift_type": None, "start_time": None, "late_after": None,
             "label": "食堂"}
        st = live_state(e, profile(food=True), [datetime(2026, 9, 8, 10, 0)],
                        datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "fact_present")
        st2 = live_state(e, profile(food=True), [], datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st2["state"], "fact_none")

    def test_rest_leave_exempt_unknown(self):
        self.assertEqual(live_state({"kind": "rest", "label": "休息"}, profile(),
                                    [], datetime(2026, 9, 8, 12, 0))["state"], "rest")
        self.assertEqual(live_state({"kind": "exempt", "label": "豁免"}, profile(),
                                    [], datetime(2026, 9, 8, 12, 0))["state"], "exempt")
        self.assertEqual(live_state({"kind": "unknown", "label": "在册待确认"}, profile(),
                                    [], datetime(2026, 9, 8, 12, 0))["state"], "unknown")

    def test_unknown_with_leave_record_is_leave(self):
        """无排班/绑定/名单命中（kind=unknown）但有已通过请假记录 →
        不得被 unknown 短路，显示请假并带请假类型。"""
        p = profile(leave_record=True, leave_record_type="病假")
        e = resolve_expected(p, weekday=1)
        self.assertEqual(e["kind"], "unknown")
        st = live_state(e, p, [], datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "leave")
        self.assertIn("病假", st["label"])

    def test_rest_still_beats_leave_record(self):
        """豁免/休息优先级保留：排班休息 + 有请假记录 → 仍显示休息。"""
        p = profile(leave_record=True, leave_record_type="事假",
                    schedule={"kind": "rest", "shift_type": "休息",
                              "start_time": None, "late_after": None, "leave_type": None})
        e = resolve_expected(p, weekday=1)
        self.assertEqual(e["kind"], "rest")
        st = live_state(e, p, [], datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "rest")
        self.assertNotEqual(st["state"], "leave")


class DayReviewTest(unittest.TestCase):
    def test_no_attendance_shift_without_events_no_pair(self):
        p = profile(schedule={"kind": "shift", "shift_type": "行政班",
                              "start_time": "08:30", "late_after": "08:31", "leave_type": None})
        e = resolve_expected(p, weekday=1)
        st = day_review(e, p, [], datetime(2026, 9, 8, 23, 59))
        self.assertEqual(st["state"], "no_pair")
        self.assertFalse(st["tags"])  # 不判缺勤

    def test_unknown_with_leave_record_is_leave(self):
        """回顾模式同构：kind=unknown + 已通过请假记录 → 显示请假（含类型）。"""
        p = profile(leave_record=True, leave_record_type="病假")
        e = resolve_expected(p, weekday=1)
        self.assertEqual(e["kind"], "unknown")
        st = day_review(e, p, [], datetime(2026, 9, 8, 23, 59))
        self.assertEqual(st["state"], "leave")
        self.assertIn("病假", st["label"])

    def test_rest_still_beats_leave_record(self):
        """回顾模式：排班休息 + 有请假记录 → 仍显示休息。"""
        p = profile(leave_record=True, leave_record_type="事假",
                    schedule={"kind": "rest", "shift_type": "休息",
                              "start_time": None, "late_after": None, "leave_type": None})
        e = resolve_expected(p, weekday=1)
        self.assertEqual(e["kind"], "rest")
        st = day_review(e, p, [], datetime(2026, 9, 8, 23, 59))
        self.assertEqual(st["state"], "rest")


class DataLayerContractTest(unittest.TestCase):
    """数据层 get_data 依赖 frappe 运行态，测试按仓库惯例用文件内容校验契约。"""

    def test_data_module_whitelists_get_data(self):
        content = DATA_PY.read_text()
        self.assertIn("@frappe.whitelist()", content)
        self.assertIn("def get_data(department=None, date_str=None)", content)
        self.assertIn('frappe.throw("不能查看未来日期")', content)
        # 复用名单/班次常量，不内联复制
        self.assertIn("from hb_attendance_app.hbos_attendance.rule_lists import", content)
        self.assertIn("from hb_attendance_app.hbos_attendance.shift_rules import BUILTIN_SHIFTS", content)
        self.assertIn("live_state", content)
        self.assertIn("day_review", content)
        self.assertIn("resolve_expected", content)

    def test_aggregate_rate_and_contract(self):
        content = DATA_PY.read_text()
        self.assertIn('"kind": exp["kind"]', content)
        # 统计口径已上移到 board_stats 纯模块（单一来源）；
        # 数据层不再自带 _PRESENT_STATES 这类重复定义
        self.assertIn("summarize_rows(rows)", content)
        self.assertNotIn("_PRESENT_STATES", content)
        self.assertIn("attendance=attendance.get", content)
        self.assertIn("ORDER BY employee, time", content)
        self.assertIn("FOUR_SHIFT_NUMS, SPECIAL_SHIFT_NUMS", content)

    def test_role_gate_tz_plus8_and_general_rotate_fallback(self):
        """整分支审查拍板：API 角色门禁、时区 +8、通用倒班兜底入应出勤。"""
        content = DATA_PY.read_text()
        # get_data 与 live_sync 两处均需门禁
        self.assertGreaterEqual(content.count("frappe.only_for"), 2)
        self.assertIn("TZ_PLUS8", content)
        self.assertIn('timezone(timedelta(hours=8))', content)
        # 通用倒班兜底：非名单命中的无排班员工计入应出勤分母
        self.assertIn("通用倒班", content)
        self.assertIn('_rotating_label(ROTATE_SYSTEM, num) or "通用倒班"', content)

    def test_data_layer_uses_shared_board_stats(self):
        content = DATA_PY.read_text()
        self.assertIn("from hb_attendance_app.hbos_attendance.board_stats import", content)
        self.assertIn("summarize_rows", content)
        self.assertIn("dept_summary", content)
        self.assertIn('"dept_stats"', content)
        # 旧的自有聚合实现必须移除，口径只能有一处
        self.assertNotIn("def _aggregate(", content)
        self.assertNotIn("def _empty_stats(", content)


class LiveSyncContractTest(unittest.TestCase):
    """live_sync 手动同步端点契约：frappe 运行态函数，测试用文件内容校验。"""

    def test_live_sync_throttle_present(self):
        content = DATA_PY.read_text()
        self.assertIn("def live_sync()", content)
        self.assertIn("sync_delicloud_checkin", content)
        self.assertIn("120", content)  # 节流秒数


class FrontendContractTest(unittest.TestCase):
    """前端 Page JS/JSON 与工作台 workspace 契约：仅文件文本断言，不 import 运行态模块。"""

    def test_page_js_has_controls_and_endpoints(self):
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        self.assertIn('frappe.pages["hbos-department-board"]', js)
        self.assertIn("db-dept", js)
        self.assertIn("db-date", js)
        self.assertIn("db-autorefresh", js)
        self.assertIn("db-only-attention", js)
        self.assertIn("db-sync", js)
        self.assertIn("get_data", js)
        self.assertIn("live_sync", js)
        self.assertIn("visibilityState", js)

    def test_page_js_overview_first_layout(self):
        """整洁化改版：概览优先 + 展开式明细，取代「每部门一张卡片堆叠」。"""
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        self.assertIn("db-dept-row", js)          # 部门汇总行（可点击展开）
        self.assertIn("db-detail", js)            # 内联展开的人员明细
        self.assertIn("tabular-nums", js)         # 数字列对齐可读
        self.assertNotIn("db-dept-card", js)      # 旧的多卡片堆叠已移除
        # 轮询静默刷新：自动刷新不再整屏 spinner，且保留展开状态
        self.assertIn("openDepts", js)
        self.assertIn("silent", js)

    def test_kpi_splits_absent_from_no_record(self):
        """缺勤（已定性）与未打卡（未知）必须是两张分开的卡片，不得混在一张里。

        口径已上移到后端 stats：前端只渲染 s.absent / s.noCard，不再自行判定。"""
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        self.assertNotIn("未打卡/无考勤", js)
        self.assertIn('"未打卡"', js)
        self.assertIn('"缺勤"', js)
        self.assertIn("s.absent", js)             # 缺勤独立计数
        self.assertIn("s.noCard", js)             # 未打卡独立计数
        self.assertNotIn('r.state === "absent_day"', js)   # 定性逻辑不再留在前端

    def test_frontend_uses_server_stats(self):
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        self.assertIn("data.stats", js)
        self.assertIn("data.dept_stats", js)
        # 前端不得再自带汇总实现（口径只能在后端一处）
        self.assertNotIn("function summarize(", js)

    def test_page_json_and_folder_named(self):
        folder = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board"
        self.assertTrue((folder / "hbos_department_board.json").exists())
        self.assertTrue((folder / "department_board_data.py").exists())
        content = (folder / "hbos_department_board.json").read_text()
        self.assertIn('"name": "hbos-department-board"', content)

    def test_workspace_json_link_and_shortcut(self):
        content = WS_JSON.read_text()
        self.assertIn('"label": "部门看板"', content)
        self.assertIn('"link_to": "hbos-department-board"', content)

    def test_color_for_review_fix(self):
        """配色：红=late/absent_day（确凿）；绿=present/out_day/fact_present；
        absent_expected（未打卡不定性）落琥珀默认，不得进红分支。"""
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        red_line = next(l for l in js.splitlines() if 'return "s-red"' in l)
        self.assertIn('"late"', red_line)
        self.assertIn('"absent_day"', red_line)
        self.assertNotIn("absent_expected", red_line)
        green_line = next(l for l in js.splitlines() if 'return "s-green"' in l)
        self.assertIn('"present"', green_line)
        self.assertIn('"out_day"', green_line)


class LateExemptBoardTest(unittest.TestCase):
    """看板侧：暂不记迟到名单只清迟到标记，到岗事实照常显示。"""

    def _shift(self):
        return {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
                "late_after": "08:31", "label": "行政班 08:30"}

    def test_late_exempt_hides_late_tag(self):
        ev = [datetime(2026, 9, 10, 12, 56)]
        st = live_state(self._shift(), profile(late_exempt=True), ev,
                        datetime(2026, 9, 10, 14, 0))
        self.assertEqual(st["state"], "present")
        self.assertNotIn("迟到", st["tags"])
        self.assertEqual(st["first_hm"], "12:56")     # 到岗时间照常显示

    def test_without_exempt_still_late(self):
        ev = [datetime(2026, 9, 10, 12, 56)]
        st = live_state(self._shift(), profile(), ev, datetime(2026, 9, 10, 14, 0))
        self.assertEqual(st["state"], "late")
        self.assertIn("迟到", st["tags"])
