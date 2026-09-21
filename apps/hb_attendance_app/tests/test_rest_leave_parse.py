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

# 只看「赋值」，不看注释里的字样（注释提到 parsed_at 不算）
PARSED_AT_ASSIGN = re.compile(r"\.parsed_at\s*=")

NEUTRAL_SYNC_TITLE = "飞书调休单条处理失败"   # Delta 2：Task 3 处理器中立标题
CALL_FAIL_TITLE = "调休加班日 LLM 调用失败"    # Delta 2：Task 4 调用失败标题


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
        """判定热路径（api.py）不得调用 LLM。"""
        api = API.read_text()
        self.assertNotIn("parse_pending_rest_leaves", api)
        self.assertNotIn("call_llm", api)

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
            "VERIFY_PENDING if dates else VERIFY_PARSE_FAIL", self.src)

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

    def test_deadline_checked_before_each_call(self):
        """deadline 判定必须在 call_llm 之前，且位于 pending 循环内。

        若判定写在调用之后，预算就形同虚设——调用先发生，钱先花了。
        """
        loop_at = self.src.index("for row in pending:")
        deadline_at = self.src.index(
            "if _time.monotonic() > batch_deadline:", loop_at)
        call_at = self.src.index("call_llm(cfg, prompt)", loop_at)
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
        call_at = self.src.index("call_llm(cfg, prompt)", deadline_at)
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
        call_at = self.src.index("call_llm(cfg, prompt)", loop_at)
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
        call_at = self.src.index("call_llm(cfg, prompt)", deadline_at)
        chunk = self.src[deadline_at:call_at]
        self.assertNotIn("parsed_at", chunk)
        self.assertNotIn("verify_status", chunk)

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

    def test_sync_handler_log_identifies_record(self):
        """Task 3 处理器：N 条失败必须能分辨是哪条。"""
        chunk = self._log_call(NEUTRAL_SYNC_TITLE)
        self.assertTrue(chunk, "找不到标题为 %s 的日志调用" % NEUTRAL_SYNC_TITLE)
        self.assertIn("%s: %s", chunk)
        self.assertIn('record.get("id")', chunk)

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
