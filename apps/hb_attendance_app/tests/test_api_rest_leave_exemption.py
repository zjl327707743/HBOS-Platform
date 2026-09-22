import re
import unittest
from pathlib import Path

API = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/api.py")


class RestLeaveExemptionContractTest(unittest.TestCase):
    def setUp(self):
        self.src = API.read_text()

    def _fn(self):
        """切出 regenerate_attendance 函数体，避免误判同文件其它函数。"""
        i = self.src.index("def regenerate_attendance(")
        j = self.src.find("\ndef ", i + 10)
        return self.src[i:j if j > 0 else len(self.src)]

    def test_fetches_verified_rest_dates(self):
        self.assertIn("from hb_attendance_app.hbos_attendance.rest_leave_apply import",
                      self.src)
        self.assertIn("verified_rest_dates()", self._fn())

    def test_merges_into_leave_dates(self):
        """必须并入 emp_leave_dates——pairing 只看这一个集合来抑制缺勤。"""
        fn = self._fn()
        self.assertIn("emp_leave_dates", fn)
        self.assertRegex(fn, r"emp_leave_dates\[[^\]]+\]\s*\.update\(|"
                             r"emp_leave_dates\.setdefault\(")

    def test_keeps_separate_rest_leave_set(self):
        """另存一个集合用于区分「调休」与「请假」。"""
        fn = self._fn()
        self.assertIn("emp_rest_leave_dates", fn)

    def test_does_not_reuse_schedule_rest_set(self):
        """不得复用 emp_rest_dates——那是排班休息日，语义相反（不生成记录）。"""
        fn = self._fn()
        self.assertNotRegex(fn, r"emp_rest_dates\s*=\s*verified_rest_dates")

    def test_marks_rest_leave_shift(self):
        """调休日生成的 On Leave 记录，班次列写「调休」。"""
        fn = self._fn()
        self.assertIn('"调休"', fn)

    def test_leave_records_keep_empty_shift(self):
        """请假仍写空班次——不得因为加了调休而把请假也标成调休。"""
        fn = self._fn()
        self.assertRegex(fn, r'"On Leave",\s*(""|shift)')

    def test_does_not_import_from_pairing(self):
        """本阶段靠并入豁免集合实现，不改判定核心。"""
        self.assertNotIn("pair_employee_checkins(", self.src.split("import")[0])

    def test_no_new_sql_for_rest_leave(self):
        """查询收敛在 rest_leave_apply，api.py 不得自建第二份查询。"""
        fn = self._fn()
        self.assertNotIn("tabHBOS Rest Leave Record", fn)


if __name__ == "__main__":
    unittest.main()
