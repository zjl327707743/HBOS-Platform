import unittest
from datetime import datetime, date

from hb_attendance_app.hbos_attendance.department_board import (
    resolve_expected, live_state, day_review,
)


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
