import unittest
from pathlib import Path

SRC = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/report/月度考勤汇总/月度考勤汇总.py")


class RestLeaveCountedAsLeaveTest(unittest.TestCase):
    """调休日必须计入「请假(天)」，不得落进「正常(天)」。

    事故背景：`is_leave` 只从 HBOS Leave Record 构建，而调休记录在
    HBOS Rest Leave Record。故调休日的 Attendance 行（status='On Leave'）
    会落到 else 分支被算成正常出勤 —— 调休在月报里凭空变成正常上班。
    """

    def setUp(self):
        self.src = SRC.read_text()

    def _classify_block(self):
        i = self.src.index("is_leave = ")
        j = self.src.find('"normal_list"]', i)
        self.assertGreater(j, i, "未找到 normal_list 分支，脚本结构可能已变")
        return self.src[i:j + 40]

    def test_is_leave_also_covers_on_leave_status(self):
        """判定必须把 status='On Leave' 也算作请假，而不只看记录集合。"""
        blk = self._classify_block()
        self.assertIn('"On Leave"', blk,
                      "is_leave 必须覆盖 status='On Leave'，否则调休日被算成正常出勤")

    def test_on_leave_precedes_normal_bucket(self):
        """判定顺序：先判请假，再落正常。"""
        blk = self._classify_block()
        self.assertLess(blk.index("On Leave"), blk.index("normal_list"))


if __name__ == "__main__":
    unittest.main()
