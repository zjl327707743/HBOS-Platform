import unittest
from pathlib import Path

SRC = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/sync_rest_leave.py")

# log_error 自身会抛，所以它的调用必须再裹一层。防护层刻意写成不带 as e 的
# 裸形式：定位助手靠回退查找「带 as e 的 except 行」找处理体，带 as e 会让它
# 认错位置。同理，生产代码的注释与字符串里不得出现结构锚点原文。
BARE_GUARD = "except Exception:"


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

    def test_scheduler_pipeline_does_not_throw_business_errors(self):
        """调度编排必须返回摘要，不得因人工 API 的 RBAC 门禁而中断。"""
        start = self.src.index("def sync_rest_leave_pipeline(")
        body = self.src[start:]
        self.assertNotIn("frappe.throw(", body)
        self.assertIn('summary["sync"]', body)
        self.assertIn('summary["parse"]', body)
        self.assertIn('summary["verify"]', body)

    def test_manual_sync_entry_has_server_side_rbac(self):
        """人工触发白名单入口必须执行服务器端权限校验。"""
        start = self.src.index("def sync_rest_leave_from_bitable(")
        end = self.src.index("def parse_pending_rest_leaves(", start)
        body = self.src[start:end]
        self.assertIn("_require_hr_write()", body)

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

    # 每个 log_error 调用点：(用于定位的锚点, 人读的说明)。
    # 锚点必须唯一定位到**那一次**调用：_nested_guard 用 find 取首次出现，
    # 所以同标题出现多次时（`飞书调休同步` 既是拉表失败、也是匹配不到员工）
    # 必须用调用里独有的消息片段当锚点，否则只覆盖到第一处。
    GUARDED_LOG_SITES = (
        ("飞书调休同步", "拉表失败（起始阶段）"),
        ("调休记录匹配不到员工", "匹配不到员工（诊断日志，非错误路径）"),
        ("飞书调休单条处理失败", "逐条整体兜底"),
    )

    def _nested_guard(self, anchor):
        """取出包住该 log_error 调用的裸防护体；没有防护则返回 ""。

        判别点三层，任一层不满足即返回 ""（这样修前这些位置必失败）：
        1. log_error 之前紧邻一个 try:，两者之间除了缩进只剩下被调对象的
           前缀「frappe.」（即该 try 体的第一条语句就是这个日志调用）；
        2. 该 try 对应的 except 是不带 as e 的裸形式（BARE_GUARD）；
        3. 裸 except 体内以 pass 收尾（真吞掉，不是换个方式往上抛）。
        """
        at = self.src.find(anchor)
        if at < 0:
            return ""
        log_at = self.src.rfind("log_error(", 0, at)
        if log_at < 0:
            return ""
        before = self.src[:log_at]
        try_at = before.rfind("try:")
        if try_at < 0:
            return ""
        tail = before[try_at + len("try:"):].strip()
        if tail and tail != "frappe.":
            return ""
        after = self.src[at:]
        guard_at = after.find(BARE_GUARD)
        if guard_at < 0:
            return ""
        # guard_at 必须是**本处**那个 except：若这里写的是带 as e 的 except，
        # 上面的 find 会一路跳到文件后面某个无关的裸 except 上，把别人的防护体
        # 当成本处的（“最近的 except 就是这一个”才成立）。变异验证过：没有这行
        # 时，把本处写成 `except Exception as e:` 的错实现可以蒙混过去。
        if after.find("except") != guard_at:
            return ""
        # pass 必须落在这段防护体的近旁：否则「防护体没吞异常」会被文件后面
        # 某个无关的 pass 蒙混过去。
        pass_at = after.find("pass", guard_at)
        if pass_at < 0 or pass_at - guard_at > 200:
            return ""
        return after[guard_at:pass_at + len("pass")]

    def test_every_handler_log_call_is_shielded_by_nested_guard(self):
        """Review 回修：log_error 自身会抛，本文件每处 log_error 都必须再裹一层。

        理由：frappe.log_error 内部是 get_doc(Error Log) + insert，自己没有兜底。
        最可能的失败场景恰是数据库故障——那条 INSERT 走同一条坏连接再抛一次，
        异常从这里冒出去，逐条兜底就白写了：本批计数、摘要、调度链全丢。
        两处尤其要紧：拉表失败分支里 `summary["error"]` 是调度器区分「跑了没做事」
        与「崩了」的唯一依据；而「匹配不到员工」这条的计数若被日志异常顶到外层
        handler，同一条记录会同时落进 unmatched 与 failed——正是回修要关掉的
        重复计数。判别法见 _nested_guard：修前这几处都没有紧邻的 try:，取不到
        防护体，断言必失败。
        """
        for anchor, what in self.GUARDED_LOG_SITES:
            with self.subTest(anchor=anchor):
                guard = self._nested_guard(anchor)
                self.assertTrue(
                    guard, "%s（%s）的 log_error 没有被裸 try 兜住" % (anchor, what))
                self.assertIn("pass", guard)

    def test_unmatched_count_sits_outside_the_guard(self):
        """重复计数的直接判别器：unmatched 的 +1 不得落进防护层体内。

        计数的归属必须只由业务分支决定。它一旦落在防护层里，日志失败就会
        重复计数：落 `try` 体 → 异常冒到循环体外层 handler，同条再记一次
        `failed`（一条同时进 unmatched 与 failed）；落裸 `except` 体 → 直接
        加两次。断言取防护层整段（`try:` 到 `pass`），只禁止计数在**里面**——
        在防护层之前或之后都合规，因为两者都保证「日志抛了也不改本条归属」。
        """
        anchor = "调休记录匹配不到员工"
        guard = self._nested_guard(anchor)
        self.assertTrue(guard, "缺少裸防护层，无法判断计数位置")
        count_stmt = 'summary["unmatched"] += 1'
        self.assertEqual(
            self.src.count(count_stmt), 1,
            "unmatched 的计数语句应当只有一处，否则本断言无从判断位置")
        at = self.src.find(anchor)
        log_at = self.src.rfind("log_error(", 0, at)
        try_at = self.src.rindex("try:", 0, log_at)
        guard_at = self.src.find(BARE_GUARD, at)
        guard_end = guard_at + len(guard)      # pass 之后
        self.assertNotIn(
            count_stmt, self.src[try_at:guard_end],
            "计数不得落进防护层体内：日志一抛就会把同一条记录重复计数")


if __name__ == "__main__":
    unittest.main()
