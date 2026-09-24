import unittest
from pathlib import Path

BOARD = (Path(__file__).parents[1]
         / "hb_attendance_app/hbos_attendance/page/hbos_department_board/department_board_data.py")
PURE = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/department_board.py")


def _func_body(src, name):
    """按函数名切出源码片段（到下一个顶层 def 为止）。"""
    i = src.index("def %s(" % name)
    j = src.find("\ndef ", i + 10)
    return src[i:j if j > 0 else len(src)]


def _branch_body(src, marker):
    """从含 marker 的行起，收集其后缩进更深的所有行（含注解行）。

    遇到第一行「非空且已回到 if 同级或更外层」的代码即停，
    避免把后续分支误并进来。
    """
    lines = src.splitlines()
    start = next(k for k, ln in enumerate(lines) if marker in ln)
    out = [lines[start]]
    for ln in lines[start + 1:]:
        if ln.strip() and not ln.startswith("            "):
            break
        out.append(ln)
    return "\n".join(out)


class BoardRestLeaveContractTest(unittest.TestCase):
    def setUp(self):
        self.src = BOARD.read_text()

    def test_loads_verified_rest_dates(self):
        self.assertIn("verified_rest_dates", self.src)

    def test_uses_shared_entry_not_own_query(self):
        """不得在看板里自建第二份「已通过 + 已核实」查询。"""
        body = _func_body(self.src, "_load_leave_records")
        self.assertNotIn("tabHBOS Rest Leave Record", body)
        self.assertNotIn("verify_status", body)

    def test_labels_rest_leave_distinctly(self):
        self.assertIn("调休", self.src)

    def test_still_reads_native_leave_records(self):
        """原有的 HBOS Leave Record 来源不得被替换掉。"""
        self.assertIn('"HBOS Leave Record"', self.src)


class ReviewModeRestLeaveLabelTest(unittest.TestCase):
    """回顾模式（过去日期）走 Attendance 记录，是第二条标签路径。

    调休日由考勤引擎在 Attendance.shift 写入「调休」，请假日留空。
    该路径必须读 shift 才能把两者显示成不同的标签。
    """

    def setUp(self):
        self.data_src = BOARD.read_text()
        self.pure_src = PURE.read_text()

    def test_load_attendance_selects_shift_field(self):
        """_load_attendance 必须把 shift 查出来，否则回顾模式拿不到区分依据。"""
        body = _func_body(self.data_src, "_load_attendance")
        i = body.index("fields=[")
        j = body.index("]", i)
        self.assertIn("shift", body[i:j + 1])

    def test_load_attendance_returns_shift_key(self):
        """查出来还要放进返回 dict，下游 a.get("shift") 才有值。"""
        body = _func_body(self.data_src, "_load_attendance")
        self.assertIn('"shift":', body)

    def test_on_leave_branch_uses_shift_for_label(self):
        """On Leave / Half Day 分支必须用 shift 构造标签，不能写死「请假」。"""
        branch = _branch_body(self.pure_src, 'if status in ("On Leave", "Half Day"):')
        self.assertIn("shift", branch)

    def test_on_leave_branch_label_not_hardcoded(self):
        """退化守卫：有人把标签改回写死的 "请假" 时必须变红。"""
        branch = _branch_body(self.pure_src, 'if status in ("On Leave", "Half Day"):')
        self.assertNotIn('"label": "请假"', branch)

    def test_present_branch_untouched(self):
        """调休区分不得挪进 Present 分支：出勤行照旧只看出勤。"""
        branch = _branch_body(self.pure_src, 'if status == "Present":')
        self.assertNotIn("调休", branch)
        self.assertNotIn("shift", branch)


if __name__ == "__main__":
    unittest.main()
