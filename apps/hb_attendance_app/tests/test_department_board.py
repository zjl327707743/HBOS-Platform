import unittest
from datetime import datetime, date
from pathlib import Path

from hb_attendance_app.hbos_attendance.department_board import (
    resolve_expected, live_state, day_review,
)

DATA_PY = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/department_board_data.py"


def profile(**kw):
    base = {
        "num": "1", "exempt": False, "admin_list": False, "food": False,
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


class DayReviewTest(unittest.TestCase):
    def test_no_attendance_shift_without_events_no_pair(self):
        p = profile(schedule={"kind": "shift", "shift_type": "行政班",
                              "start_time": "08:30", "late_after": "08:31", "leave_type": None})
        e = resolve_expected(p, weekday=1)
        st = day_review(e, p, [], datetime(2026, 9, 8, 23, 59))
        self.assertEqual(st["state"], "no_pair")
        self.assertFalse(st["tags"])  # 不判缺勤


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
