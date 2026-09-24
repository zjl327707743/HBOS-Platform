import unittest
from pathlib import Path

SRC = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/page/hbos_department_board/department_board_data.py")


class BoardRestLeaveContractTest(unittest.TestCase):
    def setUp(self):
        self.src = SRC.read_text()

    def test_loads_verified_rest_dates(self):
        self.assertIn("verified_rest_dates", self.src)

    def test_uses_shared_entry_not_own_query(self):
        """不得在看板里自建第二份「已通过 + 已核实」查询。"""
        i = self.src.index("def _load_leave_records(")
        j = self.src.find("\ndef ", i + 10)
        body = self.src[i:j if j > 0 else len(self.src)]
        self.assertNotIn("tabHBOS Rest Leave Record", body)
        self.assertNotIn("verify_status", body)

    def test_labels_rest_leave_distinctly(self):
        self.assertIn("调休", self.src)

    def test_still_reads_native_leave_records(self):
        """原有的 HBOS Leave Record 来源不得被替换掉。"""
        self.assertIn('"HBOS Leave Record"', self.src)


if __name__ == "__main__":
    unittest.main()
