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
        self.assertEqual(s["late"], 1)
        self.assertEqual(s["noCard"], 0)
        self.assertEqual(s["attendance_rate"], 100.0)

    def test_late_by_tag_counts_in_review_mode(self):
        # 回顾模式：HRMS 迟到以 out_day + tags 呈现，state 不是 late
        s = summarize_rows([row("out_day", tags=["迟到"])])
        self.assertEqual(s["late"], 1)
        self.assertEqual(s["present"], 1)

    def test_not_started_is_own_bucket_not_no_card(self):
        # 晚班 20:00 上班、9 点时未到上班时间 → 未开始，绝不计入未打卡
        s = summarize_rows([row("before_start"), row("present")])
        self.assertEqual(s["expected"], 2)
        self.assertEqual(s["notStarted"], 1)
        self.assertEqual(s["noCard"], 0)

    def test_out_only_and_unknown_time_are_own_buckets(self):
        # 夜班收工只刷到下班机 / 无排班无绑定导致班次未定
        s = summarize_rows([row("out_only"), row("fact_none")])
        self.assertEqual(s["expected"], 2)
        self.assertEqual(s["outOnly"], 1)
        self.assertEqual(s["unknownTime"], 1)
        self.assertEqual(s["noCard"], 0)        # 两者都不得计入未打卡

    def test_no_card_is_overdue_only(self):
        # 班次已开始却无到岗卡 → 真预警
        s = summarize_rows([row("absent_expected"), row("no_pair"), row("pending")])
        self.assertEqual(s["expected"], 3)
        self.assertEqual(s["noCard"], 3)

    def test_absent_is_separate_from_no_card(self):
        # 已定性缺勤（absent_day）与真预警未打卡（absent_expected）分属两桶
        s = summarize_rows([row("absent_day"), row("absent_expected")])
        self.assertEqual(s["absent"], 1)
        self.assertEqual(s["noCard"], 1)

    def test_identity_holds_exactly(self):
        # 恒等: 每个 state 恰好归入一处（含 before_start）
        rows = [row("present"), row("late"), row("absent_day"), row("absent_expected"),
                row("no_pair"), row("pending"), row("out_only"), row("fact_none"),
                row("before_start"), row("fact_present"), row("present_offwindow"),
                row("out_day"), row("out_offwindow"),
                row("rest", kind="rest"), row("leave", kind="leave"),
                row("exempt", kind="exempt"), row("unknown", kind="unknown")]
        s = summarize_rows(rows)
        self.assertEqual(
            s["expected"],
            s["present"] + s["noCard"] + s["outOnly"] + s["unknownTime"]
            + s["notStarted"] + s["absent"],
        )
        # 并逐桶核对，防某一桶被重复计入
        self.assertEqual(s["present"], 6)
        self.assertEqual(s["noCard"], 3)
        self.assertEqual(s["outOnly"], 1)
        self.assertEqual(s["unknownTime"], 1)
        self.assertEqual(s["notStarted"], 1)
        self.assertEqual(s["absent"], 1)
        self.assertEqual(s["expected"], 13)

    def test_non_shift_kinds_excluded_from_denominator(self):
        s = summarize_rows([row("rest", kind="rest"), row("leave", kind="leave"),
                            row("exempt", kind="exempt"), row("unknown", kind="unknown")])
        self.assertEqual(s["expected"], 0)
        self.assertIsNone(s["attendance_rate"])
        self.assertEqual(s["rest"], 1)
        self.assertEqual(s["leave"], 1)
        self.assertEqual(s["exempt"], 1)

    def test_empty_rows(self):
        s = summarize_rows([])
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["expected"], 0)
        self.assertIsNone(s["attendance_rate"])


class GroupAndDeptSummaryTest(unittest.TestCase):
    def test_group_by_dept_buckets_missing_dept(self):
        g = group_by_dept([row("present", dept="A"), row("present", dept=""), row("present", dept="A")])
        self.assertEqual(len(g["A"]), 2)
        self.assertEqual(len(g["未分组"]), 1)

    def test_dept_summary_sorted_by_problem_first(self):
        rows = [row("present", dept="好部门"), row("absent_expected", dept="差部门"),
                row("absent_expected", dept="差部门"), row("late", dept="中部门")]
        out = dept_summary(rows)
        self.assertEqual([d["dept"] for d in out], ["差部门", "中部门", "好部门"])
        self.assertEqual(out[0]["noCard"], 2)
        self.assertEqual(out[0]["expected"], 2)

    def test_dept_summary_fields(self):
        out = dept_summary([row("present", dept="A"), row("absent_day", dept="A"),
                            row("leave", kind="leave", dept="A"), row("out_only", dept="A")])
        d = out[0]
        self.assertEqual(d["dept"], "A")
        self.assertEqual(d["total"], 4)
        self.assertEqual(d["expected"], 3)
        self.assertEqual(d["present"], 1)
        self.assertEqual(d["absent"], 1)
        self.assertEqual(d["outOnly"], 1)
        self.assertEqual(d["noCard"], 0)
        self.assertEqual(d["leave"], 1)

    def test_dept_with_no_expected_still_listed(self):
        # dept_summary 保留该部门（expected=0）；render_report 才过滤（见 Task 4）
        out = dept_summary([row("rest", kind="rest", dept="A")])
        self.assertEqual(out[0]["expected"], 0)
        self.assertEqual(out[0]["total"], 1)


if __name__ == "__main__":
    unittest.main()


class AnomalyHiddenTest(unittest.TestCase):
    """看板不显示异常的行：仍出现在明细里，但不参与任何统计（Owner 2026-09-11）。"""

    def _r(self, state, hidden=False, kind="shift"):
        return {"dept": "设备动力部", "state": state, "tags": ["迟到"] if state == "late" else [],
                "kind": kind, "anomaly_hidden": hidden}

    def test_hidden_rows_excluded_from_all_buckets(self):
        rows = [self._r("present"), self._r("late", hidden=True),
                self._r("absent_expected", hidden=True), self._r("absent_day", hidden=True)]
        s = summarize_rows(rows)
        self.assertEqual(s["total"], 4)      # 仍在明细里
        self.assertEqual(s["expected"], 1)   # 只算未隐藏的那条
        self.assertEqual(s["late"], 0)
        self.assertEqual(s["noCard"], 0)
        self.assertEqual(s["absent"], 0)
        self.assertEqual(s["present"], 1)

    def test_identity_holds_with_hidden_rows(self):
        rows = [self._r("present"), self._r("late"), self._r("out_only"),
                self._r("fact_none"), self._r("before_start"), self._r("absent_day"),
                self._r("absent_expected", hidden=True), self._r("late", hidden=True)]
        s = summarize_rows(rows)
        self.assertEqual(
            s["expected"],
            s["present"] + s["noCard"] + s["outOnly"] + s["unknownTime"]
            + s["notStarted"] + s["absent"],
        )

    def test_dept_summary_excludes_hidden_from_anomaly_counts(self):
        rows = [self._r("present"), self._r("late", hidden=True)]
        out = dept_summary(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["total"], 2)
        self.assertEqual(out[0]["late"], 0)


class AnomalyHiddenFrontendTest(unittest.TestCase):
    """前端：不显示异常的人用中性色、无迟到标记、不进「只看异常」。"""

    def test_frontend_neutralizes_anomaly_hidden(self):
        from pathlib import Path
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        self.assertIn("anomaly_hidden", js)
        self.assertIn("rowTags", js)
        # needsAttention 必须排除隐藏行，否则「只看异常」仍会列出他们
        self.assertIn("!r.anomaly_hidden && (isLate(r)", js)


class AnomalyHiddenPolicyTest(unittest.TestCase):
    """Anomaly-hidden membership is business data rather than a source literal."""

    def test_list_is_database_backed_policy_set(self):
        from hb_attendance_app.hbos_attendance.policy_registry import PolicySet
        from hb_attendance_app.hbos_attendance.rule_lists import (
            ANOMALY_HIDDEN_NUMS, LATE_EXEMPT_NUMS,
        )
        self.assertIsInstance(ANOMALY_HIDDEN_NUMS, PolicySet)
        self.assertIsInstance(LATE_EXEMPT_NUMS, PolicySet)

