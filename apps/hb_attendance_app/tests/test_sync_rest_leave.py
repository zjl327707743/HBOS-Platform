import unittest
from pathlib import Path

SRC = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/sync_rest_leave.py")


class SyncRestLeaveContractTest(unittest.TestCase):
    def setUp(self):
        self.src = SRC.read_text()

    def test_uses_pure_module(self):
        self.assertIn("from hb_attendance_app.hbos_attendance.rest_leave import", self.src)
        self.assertIn("rest_leave_fields", self.src)

    def test_writes_rest_leave_doctype(self):
        self.assertIn('"HBOS Rest Leave Record"', self.src)

    def test_reads_correct_table(self):
        self.assertIn("REST_LEAVE_APP_TOKEN", self.src)
        self.assertIn("REST_LEAVE_TABLE_ID", self.src)

    def test_unique_key_prefix(self):
        self.assertIn("ID_PREFIX", self.src)

    def test_is_whitelisted_entry(self):
        self.assertIn("@frappe.whitelist()", self.src)
        self.assertIn("def sync_rest_leave_from_bitable(", self.src)

    def test_no_throw_in_scheduler_path(self):
        """调度任务里抛异常会打断调度链；失败必须记日志并返回摘要。"""
        self.assertNotIn("frappe.throw(", self.src)

    def test_reports_unmatched_instead_of_silent_skip(self):
        self.assertIn("unmatched", self.src)

    def test_status_map_reused_from_api(self):
        self.assertIn("STATUS_MAP", self.src)

    def test_does_not_touch_attendance_generation(self):
        """本阶段不接判定：不得触发配对/重算。"""
        self.assertNotIn("regenerate_attendance", self.src)
        self.assertNotIn("pair_employee_checkins", self.src)

    # ---------- 以下为 Review 回修新增：断言必须能区分修前/修后 ----------

    def test_captures_old_remarks_before_overwrite(self):
        """说明被改过要重新解析：必须先暂存旧值再 update。

        `doc.update({... "remarks": ...})` 会就地改写 doc.remarks；
        若在 update 之后再比较，`doc.remarks != mapped["remarks"]` 恒为假，
        「说明被改过 → 重新解析」的分支永远不触发，加班日会永久留旧值。
        """
        self.assertIn("old_remarks", self.src)
        capture_at = self.src.index("old_remarks = ")
        update_at = self.src.index("doc.update({")
        self.assertLess(
            capture_at, update_at,
            "旧说明必须在 doc.update(...) 之前暂存，否则比较恒为假")
        self.assertNotIn(
            "doc.remarks != mapped", self.src,
            "不得在 update 之后比较 doc.remarks（已被覆盖，恒等）")

    def test_per_record_failure_is_contained(self):
        """单条记录异常不得中断整批：循环体处理必须整体包在 try 里。

        修前只有 doc.save() 被 try 包住；员工匹配、exists、get_doc、
        doc.update 裸奔，任一抛异常都会冒泡出函数、丢掉摘要并打断调度链。
        """
        loop_at = self.src.index("for record in records:")
        body = self.src[loop_at:]
        try_at = body.index("try:")
        match_at = body.index("_match_employee(mapped")
        self.assertLess(
            try_at, match_at,
            "员工匹配必须在循环体 try 之内，否则单条异常会中断整批")
        self.assertIn('"failed"', body)

    def test_save_failure_reported_separately(self):
        """写入失败要与「脏行 / 缺字段」区分开：failed 独立成键且初始化即存在。"""
        start = self.src.index("summary = {")
        init = self.src[start:self.src.index("}", start)]
        for key in ("total", "created", "updated", "skipped",
                    "unmatched", "failed", "error"):
            self.assertIn('"%s"' % key, init, "初始化摘要缺键: %s" % key)
        self.assertIn('summary["failed"] += 1', self.src)


if __name__ == "__main__":
    unittest.main()
