import unittest

from hb_attendance_app.hbos_attendance.rest_leave import expand_verified_records


class ExpandVerifiedRecordsTest(unittest.TestCase):
    def test_single_day(self):
        rows = [{"employee": "E1", "start_date": "2026-08-18", "end_date": "2026-08-18"}]
        self.assertEqual(expand_verified_records(rows), {"E1": {"2026-08-18"}})

    def test_multi_day_inclusive(self):
        rows = [{"employee": "E1", "start_date": "2026-08-13", "end_date": "2026-08-14"}]
        self.assertEqual(expand_verified_records(rows),
                         {"E1": {"2026-08-13", "2026-08-14"}})

    def test_end_none_falls_back_to_start(self):
        rows = [{"employee": "E1", "start_date": "2026-09-01", "end_date": None}]
        self.assertEqual(expand_verified_records(rows), {"E1": {"2026-09-01"}})

    def test_same_employee_multiple_records_merge(self):
        rows = [
            {"employee": "E1", "start_date": "2026-08-18", "end_date": "2026-08-18"},
            {"employee": "E1", "start_date": "2026-08-20", "end_date": "2026-08-20"},
        ]
        self.assertEqual(expand_verified_records(rows),
                         {"E1": {"2026-08-18", "2026-08-20"}})

    def test_reverse_range_still_expands(self):
        rows = [{"employee": "E1", "start_date": "2026-08-18", "end_date": "2026-08-16"}]
        got = expand_verified_records(rows)["E1"]
        self.assertEqual(len(got), 3)

    def test_bad_rows_are_skipped_not_raised(self):
        rows = [
            {"employee": "E1", "start_date": "不是日期", "end_date": "2026-08-18"},
            {"employee": "", "start_date": "2026-08-18", "end_date": "2026-08-18"},
            {"employee": "E2", "start_date": None, "end_date": None},
            {"employee": "E3", "start_date": "2026-08-18", "end_date": "2026-08-18"},
        ]
        self.assertEqual(expand_verified_records(rows), {"E3": {"2026-08-18"}})

    def test_empty_input(self):
        self.assertEqual(expand_verified_records([]), {})
        self.assertEqual(expand_verified_records(None), {})

    def test_missing_keys_do_not_raise(self):
        self.assertEqual(expand_verified_records([{"employee": "E1"}]), {})


if __name__ == "__main__":
    unittest.main()
