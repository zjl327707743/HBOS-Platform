"""Task 4 契约测试：LLM 解析加班日并落库（结构性 / 契约型断言，不需要 Frappe 站点）。

CI 无 Frappe、无网络，因此这里证明的是「源码结构与顺序」满足设计要求，
不是 LLM 路径的端到端行为验证（那属于 Task 7 的活站验证）。

断言刻意写成「对合理的错误实现会失败」，而不是简单的字符串 grep。
"""
import re
import unittest
from pathlib import Path

BASE = Path(__file__).parents[1]
SRC = BASE / "hb_attendance_app/hbos_attendance/sync_rest_leave.py"
API = BASE / "hb_attendance_app/hbos_attendance/api.py"
PKG = BASE / "hb_attendance_app/hbos_attendance"

# 判定热路径 = hbos_attendance 整包（不是只有 api.py）。排除项：
#   sync_rest_leave.py  同步侧文件，本任务唯一允许调用 LLM 的地方
#   ai_review.py        LLM 通道自身（call_llm 就定义在此）
# report/ 子包另有自己的 LLM 用法且不在本次范围，用非递归 glob 天然排除。
JUDGMENT_EXCLUDE = {"sync_rest_leave.py", "ai_review.py"}
JUDGMENT_MUST_SCAN = ("api.py", "pairing.py", "board_stats.py")

# 只看「赋值」，不看注释里的字样（注释提到 parsed_at 不算）
PARSED_AT_ASSIGN = re.compile(r"\.parsed_at\s*=")

NEUTRAL_SYNC_TITLE = "飞书调休单条处理失败"   # Delta 2：Task 3 处理器中立标题
CALL_FAIL_TITLE = "调休加班日 LLM 调用失败"    # Delta 2：Task 4 调用失败标题
ROW_BODY_TITLE = "调休加班日单条处理失败"      # Important 1：逐条整体兜底标题
SAVE_FAIL_TITLE = "调休加班日写入失败"         # Review 回修：写入失败独立标题

# log_error 自身会抛，所以它的调用必须再裹一层。防护层刻意写成不带 as e 的
# 裸形式：定位助手靠回退查找「带 as e 的 except 行」找处理体，带 as e 会让它
# 认错位置。
BARE_GUARD = "except Exception:"


class ParseStageContractTest(unittest.TestCase):
    """解析段必须：只处理待解析、限时批量、结果落库、失败留痕。"""

    def setUp(self):
        self.src = SRC.read_text()

    # ---------- 基本存在性 ----------

    def test_entry_exists(self):
        self.assertIn("def parse_pending_rest_leaves(", self.src)

    def test_uses_shared_llm_channel(self):
        """复用 ai_review 的通道与配置，不另起一套。"""
        self.assertIn(
            "from hb_attendance_app.hbos_attendance.ai_review import", self.src)
        self.assertIn("call_llm", self.src)
        self.assertIn("env_config", self.src)

    def test_never_called_from_attendance_path(self):
        """判定热路径不得调用 LLM：范围是整个 hbos_attendance 包，不只是 api.py。

        只盯 api.py 会漏掉 pairing / board_stats 等同样在判定链上的模块。
        排除表另配「必须被扫描」的清单，防止将来往排除表里加名字时
        把判定文件本身一起排除掉，让这个测试静默失效。
        """
        scanned = []
        for path in sorted(PKG.glob("*.py")):     # 非递归：report/ 不在范围
            if path.name in JUDGMENT_EXCLUDE:
                continue
            scanned.append(path.name)
            text = path.read_text()
            self.assertNotIn(
                "call_llm", text,
                "%s 属于判定路径，不得调用 LLM" % path.name)
            self.assertNotIn(
                "parse_pending_rest_leaves", text,
                "%s 属于判定路径，不得触发解析批处理" % path.name)
        for must in JUDGMENT_MUST_SCAN:
            self.assertIn(must, scanned, "%s 必须被扫描" % must)
        self.assertIn(API.name, scanned)

    def test_only_pending_records(self):
        """只取 verify_status=待解析 的记录。"""
        filt_at = self.src.index("filters={", self.src.index(
            "def parse_pending_rest_leaves("))
        filt = self.src[filt_at:filt_at + 200]
        self.assertIn("verify_status", filt)
        self.assertIn("PARSE_PENDING", filt)

    def test_failure_marks_parse_failed(self):
        """解析不出日期 → 解析失败（转人工），不是继续留着待解析。"""
        self.assertIn(
            "doc.verify_status = VERIFY_PENDING if dates else VERIFY_PARSE_FAIL",
            self.src)

    def test_records_parsed_at(self):
        self.assertIn("doc.parsed_at", self.src)

    # ---------- DELTA 1：时间预算 ----------

    def test_batch_budget_constant_used(self):
        """必须有一个模块级预算常量，并真的参与 deadline 计算。"""
        self.assertIn("PARSE_BATCH_SECONDS", self.src)
        # 常量定义不能在函数体内（模块级）
        self.assertLess(self.src.index("PARSE_BATCH_SECONDS"),
                        self.src.index("def parse_pending_rest_leaves("))
        self.assertIn("_time.monotonic() + PARSE_BATCH_SECONDS", self.src)
        self.assertIn("batch_deadline", self.src)

    def test_budget_comment_notes_inflight_call(self):
        """预算注释必须写明：在途的那次调用不受预算约束。

        文档性断言（断言的是注释内容，不是行为）：预算是「是否再发起一次调用」
        的截止线，已在途的调用照跑完，所以最坏占用 = 预算 + 单次调用耗时
        （≤ timeout，默认 60s），而不是恰好等于预算。后来者调常数时要看这句。
        """
        decl = self.src.index("PARSE_BATCH_SECONDS = ")
        head = self.src[max(0, decl - 800):decl]
        self.assertIn("在途", head, "注释须说明在途调用不受预算约束")
        self.assertIn("60", head, "注释须给出单次调用的量级（≤60s）")

    def test_deadline_checked_before_each_call(self):
        """deadline 判定必须在 call_llm 之前，且位于 pending 循环内。

        若判定写在调用之后，预算就形同虚设——调用先发生，钱先花了。
        """
        loop_at = self.src.index("for row in pending:")
        deadline_at = self.src.index(
            "if _time.monotonic() > batch_deadline:", loop_at)
        call_at = self.src.index("call_llm(cfg, prompt, contains_pii=True)", loop_at)
        self.assertLess(
            deadline_at, call_at,
            "deadline 判定必须在 call_llm 之前")
        # 判定在循环体内（循环头之后）
        self.assertLess(loop_at, deadline_at)

    def test_budget_skip_is_not_a_failure(self):
        """超预算跳过的记录只是「还没轮到」，不得计入 failed。

        计入 failed 会让运维误判为 LLM 故障，且掩盖真实积压（remaining）。
        """
        deadline_at = self.src.index("if _time.monotonic() > batch_deadline:")
        call_at = self.src.index("call_llm(cfg, prompt, contains_pii=True)", deadline_at)
        chunk = self.src[deadline_at:call_at]
        self.assertNotIn(
            'summary["failed"]', chunk,
            "预算跳过的记录不得计入 failed")
        self.assertIn("break", chunk, "超预算应停止本批调用")

    # ---------- 失败与落库的区分 ----------

    def test_call_failure_does_not_set_parsed_at(self):
        """调用失败 ≠ 已解析：不得写 parsed_at，否则下轮不再重试。

        这是「调用失败（下轮重试）」与「解析出空（转人工，不重试）」的分界。
        """
        loop_at = self.src.index("for row in pending:")
        call_at = self.src.index("call_llm(cfg, prompt, contains_pii=True)", loop_at)
        except_at = self.src.index("except Exception as e:", call_at)
        cont_at = self.src.index("continue", except_at)
        chunk = self.src[except_at:cont_at]
        self.assertIn('summary["failed"] += 1', chunk)
        # 失败分支内不得写 parsed_at（断言是赋值，不是注释里的字样）
        self.assertIsNone(
            PARSED_AT_ASSIGN.search(chunk),
            "调用失败分支不得写 parsed_at")
        # 顺序：循环体内、发起调用之前也不得写（排除「先标已解析再调用」）
        self.assertIsNone(
            PARSED_AT_ASSIGN.search(self.src[loop_at:call_at]),
            "parsed_at 不得在 LLM 调用之前写入")

    def test_summary_keys_identical_on_all_paths(self):
        """所有 return 路径返回同一 summary 变量，键集合恒等。

        少一个键就是调度器里的 KeyError。
        """
        func = self.src[self.src.index("def parse_pending_rest_leaves("):]
        start = func.index("summary = {")
        init = func[start:func.index("}", start)]
        for key in ("parsed", "failed", "remaining", "error"):
            self.assertIn('"%s"' % key, init, "初始化摘要缺键: %s" % key)
        self.assertGreaterEqual(
            func.count("return summary"), 3,
            "配置读取失败 / 未配置 AI / 正常结束 三条路径都要返回同一摘要")
        self.assertNotIn('return {"', func, "不得用字面量 dict 提前返回（易漏键）")

    def test_budget_skipped_rows_are_left_pending(self):
        """超预算跳过 = 保持待解析（下轮继续），不写状态、不写 parsed_at。"""
        deadline_at = self.src.index("if _time.monotonic() > batch_deadline:")
        call_at = self.src.index("call_llm(cfg, prompt, contains_pii=True)", deadline_at)
        chunk = self.src[deadline_at:call_at]
        self.assertNotIn("parsed_at", chunk)
        self.assertNotIn("verify_status", chunk)

    # ---------- 逐条错误兜底（Important 1）与魔法值（Minor 3） ----------

    def test_row_body_is_guarded_end_to_end(self):
        """Important 1：从取年份到 save 的整段逐条处理必须在同一个 try 之内。

        回归场景：get_all 之后这条记录被删 → frappe.get_doc 抛 DoesNotExist。
        修复前 get_doc / parse_overtime_dates 落在循环体唯一的 try（只包着
        call_llm）之外，异常直接冒出函数：本批已落库的计数与 remaining 全丢，
        调度链也断。

        判别法：定位「包含 year = 的那层循环体 try」（8 空格缩进）。
        修复前循环体里唯一的 8 空格 try 是「调用 LLM」那层，它不含 year =，
        断言必失败——这不是字符串 grep，取的是缩进层级所表达的作用域。
        """
        deadline_at = self.src.index("if _time.monotonic() > batch_deadline:")
        get_doc_at = self.src.index("frappe.get_doc(DOCTYPE, row.name)", deadline_at)
        remaining_at = self.src.index('summary["remaining"]', get_doc_at)

        outer_try = self.src.rindex("\n        try:", deadline_at, get_doc_at)
        self.assertIn(
            "year =", self.src[outer_try:get_doc_at],
            "取年份之前就必须进入逐条兜底 try，否则 get_doc 的异常会冒出函数")

        outer_except = self.src.index("\n        except Exception as e:", outer_try)
        self.assertLess(get_doc_at, outer_except, "get_doc 必须落在兜底 try 之内")
        self.assertLess(outer_except, remaining_at, "兜底 except 必须在循环体内")

        handler = self.src[outer_except:remaining_at]
        self.assertIn("summary[\"failed\"] += 1", handler)
        self.assertIn("row.name", handler, "兜底日志要能分辨是哪条")
        self.assertNotIn("raise", handler, "兜底不得再抛，否则等于没兜")

    def test_row_fallback_log_has_neutral_title(self):
        """兜底 handler 的标题要中立：它覆盖的是「整条处理」，不只是写入。"""
        self.assertIn(ROW_BODY_TITLE, self.src)
        chunk = self._except_block(ROW_BODY_TITLE)
        self.assertTrue(chunk, "找不到 %s 对应的 except 处理体" % ROW_BODY_TITLE)
        self.assertIn("row.name", chunk)

    def test_year_fallback_is_named_constant(self):
        """Minor 3：年份兜底不得是裸字面量「2026」，必须是具名常量。"""
        decl = self.src.index("DEFAULT_HINT_YEAR = ")
        self.assertLess(decl, self.src.index("def parse_pending_rest_leaves("))
        self.assertIn('"2026"', self.src[decl:decl + 80], "常量必须定义在模块级")
        self.assertIn("or DEFAULT_HINT_YEAR", self.src, "用点必须真的引常量")
        body = self.src[self.src.index("def parse_pending_rest_leaves("):]
        self.assertNotIn('or "2026"', body, "函数体内不得再出现裸字面量年份")

    # ---------- DELTA 2：日志可分辨、标题不夸大 ----------

    def _log_call(self, title):
        """取出标题为 title 的那次 log_error 调用片段（跨行写法也能取到）。

        从标题往前回退到最近的 `log_error(`，覆盖到标题结尾；这样调用换行
        书写也不影响断言（断言看的是这次调用的消息参数，不是整行）。
        """
        at = self.src.find(title)
        if at < 0:
            return ""
        start = self.src.rfind("log_error(", 0, at)
        if start < 0:
            return ""
        return self.src[start:at + len(title)]

    def _except_block(self, title):
        """取出标题为 title 的那次日志所在的整段 except 处理体。

        用于断言发生在 log_error 之前的语句（例如记录标识的类型守卫）——
        那些语句不在 log_error 调用片段里，_log_call 取不到。
        """
        at = self.src.find(title)
        if at < 0:
            return ""
        start = self.src.rfind("except Exception as e:", 0, at)
        if start < 0:
            return ""
        return self.src[start:at + len(title)]

    def _nested_guard(self, title):
        """取出包住该 log_error 调用的裸防护体；没有防护则返回 ""。

        判别点四层，任一层不满足即返回 ""（这样修前这些位置必失败）：
        1. log_error 之前紧邻一个 try:，两者之间除了缩进只剩下被调对象的
           前缀「frappe.」（即该 try 体的第一条语句就是这个日志调用）；
        2. 该 try 对应的 except 是不带 as e 的裸形式（`except Exception:`）；
        3. 裸 except 体内以 pass 收尾（真吞掉，不是换个方式往上抛）；
        4. 该裸 except 必须是**本处**那一条（最近的 except 就是它），
           否则前向查找会跳到文件后面某个无关的裸 except 上。
        """
        at = self.src.find(title)
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

    def _guard_span(self, marker):
        """取出包住 marker 处调用的整段防护层（行首 try: 到 except 体结束）。

        判别法（结构，不是 grep）：先按缩进确认这次调用落在某个 try **体**里
        ——调用所在行的缩进必须比最近那个 try 行的缩进更深，且两行之间不得
        出现缩进回到 try 同级的语句（那样说明已经走出 try 体）；再向后取同级
        except 的整段体（止于下一个缩进 <= try 的非空行）。修前这两处调用与
        try 平齐、直接写在函数体顶层，返回 ""，断言必失败——这是「对错误的
        实现失败」，不是「源码里有没有 try: 字样」。
        """
        at = self.src.index(marker)
        line_start = self.src.rindex("\n", 0, at) + 1
        indent = len(self.src[line_start:at]) - len(
            self.src[line_start:at].lstrip(" "))
        try_at = self.src.rindex("try:", 0, at)
        tline = self.src[self.src.rindex("\n", 0, try_at) + 1:]
        try_indent = len(tline) - len(tline.lstrip(" "))
        if try_indent >= indent:
            return ""
        head = self.src[self.src.index("\n", try_at) + 1:line_start]
        for line in head.splitlines():
            if line.strip() and len(line) - len(line.lstrip(" ")) <= try_indent:
                return ""
        pos = self.src.index("\n", try_at)
        while True:                       # 同级 except 行
            nxt = self.src.index("\n", pos + 1)
            line = self.src[pos + 1:nxt]
            if (line.strip()
                    and len(line) - len(line.lstrip(" ")) == try_indent
                    and line.lstrip().startswith("except")):
                except_at = pos + 1
                break
            pos = nxt
        pos = self.src.index("\n", except_at)
        while True:                       # except 体结束
            nxt = self.src.index("\n", pos + 1)
            line = self.src[pos + 1:nxt]
            if line.strip() and len(line) - len(line.lstrip(" ")) <= try_indent:
                end_at = pos + 1
                break
            pos = nxt
        return self.src[try_at:end_at]

    def test_pending_list_fetch_and_backlog_count_are_guarded(self):
        """F1：取待解析列表与收尾积压统计都必须在防护层内，失败记 error 不抛。

        回归场景：DB 故障 / 权限 / 连接断。修前这两次调用裸写在
        parse_pending_rest_leaves 的函数体顶层，任一抛异常都直接冒出函数——
        本批已落库的计数与本轮积压数一起丢，调度链也断；而核实段
        verify_pending_rest_leaves 里同形的两处调用都兜住了，形状不一致。
        判别法见 _guard_span（比缩进层级与语句位置）与 _nested_guard
        （日志自身还得再裹一层裸 try）。
        """
        cases = (
            # marker, 日志标题, 是否必须提前返回（读不到列表就无可处理对象）
            ("frappe.db.get_all(", "调休加班日取待解析列表失败", True),
            ("frappe.db.count(", "调休加班日解析积压统计失败", False),
        )
        for marker, title, early in cases:
            with self.subTest(marker=marker):
                span = self._guard_span(marker)
                self.assertTrue(
                    span,
                    "%s 没有落在防护层内：DB 一抛就冒出函数，本批计数与调度链一起丢"
                    % marker)
                self.assertIn(
                    'summary["error"] = str(e)', span,
                    "防护层必须写下 error 摘要（调度器区分「跑了没做事」的唯一依据）")
                self.assertTrue(
                    self._nested_guard(title),
                    "%s 的 log_error 自身没有裸兜底（日志写失败会二次抛出）" % title)
                if early:
                    self.assertIn(
                        "return summary", span,
                        "取列表失败时无可处理对象，必须原样返回摘要")
                else:
                    self.assertNotIn(
                        "return summary", span,
                        "积压统计失败时不得提前返回——循环已跑完、本批计数"
                        "已就绪，只该记 error 后照常返回摘要（与核实段收尾一致）")

    def test_every_handler_log_call_is_shielded_by_nested_guard(self):
        """Review 回修：log_error 自身会抛，Task 3/Task 4 处理体里的每个
        log_error 都必须再裹一层裸 try。

        理由：frappe.log_error 内部是 get_doc(Error Log) + insert，自己没有兜底。
        最可能的失败场景恰是数据库故障——那条 INSERT 走同一条坏连接再抛一次，
        异常从 except 里冒出去，逐条兜底、本批计数、调度链一起丢。
        修前这些位置都只有一个 try:（Task 3 的整条兜底 / Task 4 的逐条兜底），
        它离 log_error 很远，`_nested_guard` 取不到防护体，断言必失败。
        """
        for title in (NEUTRAL_SYNC_TITLE, CALL_FAIL_TITLE,
                      SAVE_FAIL_TITLE, ROW_BODY_TITLE):
            with self.subTest(title=title):
                guard = self._nested_guard(title)
                self.assertTrue(
                    guard, "%s 的 log_error 没有被裸 try 兜住" % title)
                self.assertIn("pass", guard)

    def test_sync_handler_log_identifies_record(self):
        """Task 3 处理器：N 条失败必须能分辨是哪条。"""
        chunk = self._except_block(NEUTRAL_SYNC_TITLE)
        self.assertTrue(chunk, "找不到标题为 %s 的日志调用" % NEUTRAL_SYNC_TITLE)
        self.assertIn("%s: %s", chunk)
        self.assertIn('record.get("id")', chunk)

    def test_sync_handler_tolerates_non_dict_record(self):
        """Important 2：except 里不得对 record 直接 .get——它不是 mapping 时会二次抛错。

        二次抛错发生在 except 内部，会直接冒出 sync_rest_leave_from_bitable，
        把「逐条兜底」本身毁掉（这正是 Delta 2 引入的回归）。判别法：取整段
        except 处理体，断言先做类型守卫才取值——修复前 `.get("id")` 直接写在
        日志参数里，守卫断言必失败。
        """
        chunk = self._except_block(NEUTRAL_SYNC_TITLE)
        self.assertTrue(chunk, "找不到 %s 对应的 except 处理体" % NEUTRAL_SYNC_TITLE)
        self.assertIn(
            'record.get("id") if isinstance(record, dict) else', chunk,
            "取值必须写成带类型守卫的条件表达式")
        log_at = chunk.index("log_error(")
        self.assertNotIn(
            'record.get("id")', chunk[log_at:],
            "日志参数里不得再直接对 record 取值")
        self.assertIn("rid", chunk)

    def test_sync_handler_title_is_neutral(self):
        """Task 3 的 try 覆盖匹配/解析/get_doc，标题不得只写「写入失败」。"""
        self.assertNotIn("飞书调休写入失败", self.src)
        self.assertIn(NEUTRAL_SYNC_TITLE, self.src)

    def test_parse_handler_log_identifies_record(self):
        """Task 4 调用失败处理器同样要带记录标识。"""
        chunk = self._log_call(CALL_FAIL_TITLE)
        self.assertTrue(chunk, "找不到标题为 %s 的日志调用" % CALL_FAIL_TITLE)
        self.assertIn("%s: %s", chunk)
        self.assertIn("row.name", chunk)


if __name__ == "__main__":
    unittest.main()
