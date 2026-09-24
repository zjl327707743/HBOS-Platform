import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from hb_attendance_app.hbos_attendance.rotation_schedule import (
    _assignment_for_day,
    _versions_by_employee,
    rotation_shift_for,
)


class RotationShiftTest(unittest.TestCase):
    def test_three_day_cycle(self):
        anchor = date(2026, 1, 1)
        self.assertEqual(rotation_shift_for("早班", anchor, anchor), "早班")
        self.assertEqual(rotation_shift_for("早班", anchor, date(2026, 1, 2)), "晚班")
        self.assertEqual(rotation_shift_for("早班", anchor, date(2026, 1, 3)), "休息")
        self.assertEqual(rotation_shift_for("早班", anchor, date(2026, 1, 4)), "早班")

    def test_each_anchor_phase_rotates(self):
        anchor = date(2026, 1, 1)
        expected = {
            "早班": ("早班", "晚班", "休息"),
            "晚班": ("晚班", "休息", "早班"),
            "休息": ("休息", "早班", "晚班"),
        }
        for initial, shifts in expected.items():
            got = tuple(
                rotation_shift_for(initial, anchor, date(2026, 1, 1 + offset))
                for offset in range(3)
            )
            self.assertEqual(got, shifts)


class RotationAssignmentVersionTest(unittest.TestCase):
    def _row(self, name, employee, start, shift, end=None):
        return SimpleNamespace(
            name=name,
            employee=employee,
            employee_number="TEST-" + employee,
            group_name="TEST",
            anchor_shift=shift,
            effective_from=start,
            effective_to=end,
        )

    def test_versions_are_grouped_without_real_identity_data(self):
        rows = [
            self._row("A1", "EMP-A", "2026-01-01", "早班"),
            self._row("A2", "EMP-A", "2026-02-01", "晚班"),
            self._row("B1", "EMP-B", "2026-01-01", "休息"),
        ]
        grouped = _versions_by_employee(rows)
        self.assertEqual(set(grouped), {"EMP-A", "EMP-B"})
        self.assertEqual([r.name for r in grouped["EMP-A"]], ["A1", "A2"])

    def test_latest_effective_assignment_wins(self):
        versions = [
            self._row("V1", "EMP-A", "2026-01-01", "早班"),
            self._row("V2", "EMP-A", "2026-02-01", "晚班"),
        ]
        self.assertEqual(_assignment_for_day(versions, date(2026, 1, 31)).name, "V1")
        self.assertEqual(_assignment_for_day(versions, date(2026, 2, 1)).name, "V2")

    def test_source_contains_no_production_employee_ids(self):
        src = (
            Path(__file__).parents[1]
            / "hb_attendance_app/hbos_attendance/rotation_schedule.py"
        ).read_text()
        import re
        self.assertIsNone(re.search(r"\b\d{8}\b", src))
        self.assertIn("get_rotation_assignments", src)
        self.assertIn('"source_type": "ROTATION"', src)


if __name__ == "__main__":
    unittest.main()
