import unittest
from pathlib import Path

SRC = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/sync_rest_leave.py")


class ReparseKeyContractTest(unittest.TestCase):
    """重解析的失效键必须同时覆盖 说明 与 员工。

    只比 remarks：改了工号 → 换了人却不重算 → 用甲的加班给乙换休。
    """

    def setUp(self):
        self.src = SRC.read_text()

    def _sync_fn(self):
        i = self.src.index("def sync_rest_leave_from_bitable(")
        j = self.src.find("\ndef ", i + 10)
        return self.src[i:j if j > 0 else len(self.src)]

    def test_captures_old_employee(self):
        self.assertIn("old_employee", self._sync_fn())

    def test_compares_both_keys(self):
        fn = self._sync_fn()
        self.assertIn("old_remarks", fn)
        self.assertRegex(fn, r"old_employee[^\n]*!=|!=[^\n]*old_employee",
                         "重解析判定必须同时比较 employee")

    def test_old_employee_captured_before_update(self):
        """必须在 doc.update 之前取旧值，否则比较恒为假（第一阶段踩过）。"""
        fn = self._sync_fn()
        cap = fn.index("old_employee")
        upd = fn.index("doc.update(")
        self.assertLess(cap, upd, "old_employee 必须在 doc.update 之前捕获")


if __name__ == "__main__":
    unittest.main()
