import unittest

from hb_attendance_app.hbos_attendance.board_stats import (
    summarize_rows, group_by_dept, dept_summary,
)


def row(state, kind="shift", tags=None, dept="A", num="1"):
    return {"dept": dept, "state": state, "tags": tags or [], "kind": kind, "num": num}


class SummarizeRowsTest(unittest.TestCase):
    def test_present_and_late(self):
        rows = [row("present"), row("late"), row("fact_present"), row("out_day")]
        s = summarize_rows(rows)
        self.assertEqual(s["expected"], 4)
        self.assertEqual(s["present"], 4)      # 迟到也算已到岗
        self.assertEqual(s["late"], 1)         # state=late 计入迟到
        self.assertEqual(s["noCard"], 0)
        self.assertEqual(s["attendance_rate"], 100.0)

    def test_late_by_tag_counts_in_review_mode(self):
        # 回顾模式：HRMS 迟到以 out_day + tags 呈现，state 不是 late
        rows = [row("out_day", tags=["迟到"])]
        s = summarize_rows(rows)
        self.assertEqual(s["late"], 1)
        self.assertEqual(s["present"], 1)

    def test_before_start_not_counted_as_no_card(self):
        # 晚班 20:00 上班、当前 9 点 → 未到上班时间，不得计入未打卡
        rows = [row("before_start"), row("present")]
        s = summarize_rows(rows)
        self.assertEqual(s["expected"], 2)
        self.assertEqual(s["noCard"], 0)
        self.assertEqual(s["present"], 1)

    def test_no_card_and_absent_are_separate(self):
        rows = [row("absent_expected"), row("fact_none"), row("no_pair"), row("absent_day")]
        s = summarize_rows(rows)
        self.assertEqual(s["expected"], 4)
        self.assertEqual(s["noCard"], 3)       # absent_expected/fact_none/no_pair
        self.assertEqual(s["absent"], 1)       # 仅已定性的缺勤
        self.assertEqual(s["present"], 0)

    def test_identity_holds(self):
        # 恒等仅对已定性的应出勤行成立；before_start（未到上班点）计入 expected
        # 但尚未定性，不属于 present/noCard/absent，故本用例不纳入该状态行。
        rows = [row("present"), row("late"), row("absent_day"), row("fact_none"),
                row("rest", kind="rest"), row("leave", kind="leave"),
                row("exempt", kind="exempt"), row("unknown", kind="unknown")]
        s = summarize_rows(rows)
        self.assertEqual(s["expected"], s["present"] + s["noCard"] + s["absent"])

    def test_non_shift_kinds_excluded_from_denominator(self):
        rows = [row("rest", kind="rest"), row("leave", kind="leave"),
                row("exempt", kind="exempt"), row("unknown", kind="unknown")]
        s = summarize_rows(rows)
        self.assertEqual(s["expected"], 0)
        self.assertIsNone(s["attendance_rate"])
        self.assertEqual(s["rest"], 1)
        self.assertEqual(s["leave"], 1)
        self.assertEqual(s["exempt"], 1)

    def test_out_only_counts_as_no_card(self):
        # 只有下班卡（跨天夜班次日）——未到岗、非 before_start → 未打卡
        rows = [row("out_only")]
        s = summarize_rows(rows)
        self.assertEqual(s["expected"], 1)
        self.assertEqual(s["noCard"], 1)

    def test_empty_rows(self):
        s = summarize_rows([])
        self.assertEqual(s["total"], 0)
        self.assertIsNone(s["attendance_rate"])


class GroupAndDeptSummaryTest(unittest.TestCase):
    def test_group_by_dept_buckets_missing_dept(self):
        g = group_by_dept([row("present", dept="A"), row("present", dept=""), row("present", dept="A")])
        self.assertEqual(len(g["A"]), 2)
        self.assertEqual(len(g["未分组"]), 1)

    def test_dept_summary_sorted_by_problem_first(self):
        rows = [
            row("present", dept="好部门"),
            row("fact_none", dept="差部门"),
            row("fact_none", dept="差部门"),
            row("late", dept="中部门"),
        ]
        out = dept_summary(rows)
        self.assertEqual([d["dept"] for d in out], ["差部门", "中部门", "好部门"])
        self.assertEqual(out[0]["noCard"], 2)
        self.assertEqual(out[0]["expected"], 2)

    def test_dept_summary_fields(self):
        out = dept_summary([row("present", dept="A"), row("absent_day", dept="A"),
                            row("leave", kind="leave", dept="A")])
        self.assertEqual(len(out), 1)
        d = out[0]
        self.assertEqual(d["dept"], "A")
        self.assertEqual(d["total"], 3)
        self.assertEqual(d["expected"], 2)
        self.assertEqual(d["present"], 1)
        self.assertEqual(d["absent"], 1)
        self.assertEqual(d["leave"], 1)
        self.assertEqual(d["noCard"], 0)

    def test_dept_with_no_expected_still_listed_but_filtered_from_message(self):
        # dept_summary 保留该部门（expected=0）；render_report 才过滤（见 Task 4）
        out = dept_summary([row("rest", kind="rest", dept="A")])
        self.assertEqual(out[0]["expected"], 0)
        self.assertEqual(out[0]["total"], 1)


if __name__ == "__main__":
    unittest.main()
