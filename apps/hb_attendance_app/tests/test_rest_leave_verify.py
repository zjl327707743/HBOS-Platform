"""Task 5 契约测试：核实加班日（只写结论，不接豁免）。

CI 无 Frappe 站点、无网络，所以这里证明的是两类东西：

1. 结构性断言——源码的形状/顺序满足设计要求，且刻意写成「对合理的错误实现
   会失败」，不是只认字样的 grep。
2. 行为性断言——用 ``sys.modules`` 打桩的假 frappe 真调用 ``verify_pending_rest_leaves``
   （被测模块的 import 链 ai_review/api/pairing/rule_lists 在假 frappe 下可导入），
   真的走一遍控制流，覆盖「只取待核实 / 逐条异常不外泄 / 摘要键恒等」这些
   光看源码字符串证明不了的的性质；判定用的 ``verify_status_for`` 是真模块。

**证明不了的**：``_present_dates`` 的 SQL 在真库上跑得对（列名、参数展开、
日期类型）。这里只能钉住「两个判据都在 SQL 里」。真库行为属于 Task 7 的活站验证。
"""
import importlib
import re
import sys
import types
import unittest
import warnings
from pathlib import Path
from unittest import mock

BASE = Path(__file__).parents[1]
SRC = BASE / "hb_attendance_app/hbos_attendance/sync_rest_leave.py"
MODULE_NAME = "hb_attendance_app.hbos_attendance.sync_rest_leave"

VERIFY_ENTRY = "def verify_pending_rest_leaves("
PRESENT_DATES_ENTRY = "def _present_dates("

# 日志标题：整条兜底与写入失败必须分开，且都带记录标识
ROW_BODY_TITLE = "调休加班核实单条处理失败"
SAVE_FAIL_TITLE = "调休加班核实写入失败"
LIST_FAIL_TITLE = "调休加班核实取待核列表失败"
COUNT_FAIL_TITLE = "调休加班核实积压统计失败"
NO_EMPLOYEE_TITLE = "调休加班核实缺员工"
NO_DATES_TITLE = "调休加班核实缺加班日"
# 负面结论的判据日志：写明缺哪几天（Minor 3）
MISSING_PAIR_TITLE = "调休加班核实缺少配对"

# log_error 自身会抛，所以它的调用必须再裹一层。防护层刻意写成不带 as e 的
# 裸形式：测试的定位助手靠回退查找「带 as e 的 except 行」找处理体，带 as e
# 会让它认错位置。
BARE_GUARD = "except Exception:"

SUMMARY_KEYS = {"verified", "failed", "skipped", "remaining", "error"}

NOW = "2026-09-21 10:00:00"

IMPORT_ANCHOR = "from hb_attendance_app.hbos_attendance.rest_leave import"


def _import_block(src):
    """取出从 rest_leave 的 import 到括号收尾的那段，用来断言真的导入了常量。"""
    at = src.index(IMPORT_ANCHOR)
    return src[at:src.index(")", at)]


class VerifyStageContractTest(unittest.TestCase):
    """源码结构 / 顺序契约。"""

    def setUp(self):
        self.src = SRC.read_text()

    def _func(self, entry=VERIFY_ENTRY):
        if entry not in self.src:
            self.fail("源码里没有 %s（核实阶段入口不存在）" % entry)
        return self.src[self.src.index(entry):]

    def _sql_literal(self):
        """取出 _present_dates 里那次 frappe.db.sql 的 SQL 字面量。"""
        body = self._func(PRESENT_DATES_ENTRY)
        if "frappe.db.sql(" not in body:
            self.fail("_present_dates 没有走 frappe.db.sql 查 tabAttendance")
        at = body.index("frappe.db.sql(")
        start = body.index('"""', at)
        end = body.index('"""', start + 3)
        return body[start:end]

    def _log_call(self, title):
        at = self.src.find(title)
        if at < 0:
            return ""
        start = self.src.rfind("log_error(", 0, at)
        if start < 0:
            return ""
        return self.src[start:at + len(title)]

    def _except_block(self, title):
        at = self.src.find(title)
        if at < 0:
            return ""
        start = self.src.rfind("except Exception as e:", 0, at)
        if start < 0:
            return ""
        return self.src[start:at + len(title)]

    def _nested_guard(self, title):
        """取出包住该 log_error 调用的裸防护体；没有防护则返回 ""。

        判别点三层，任一层不满足即返回 ""（这样修前必失败）：
        1. log_error 之前紧邻一个 try:，两者之间除了缩进只剩下被调对象的
           前缀「frappe.」（即该 try 体的第一条语句就是这个日志调用）；
        2. 该 try 对应的 except 是不带 as e 的裸形式（`except Exception:`）；
        3. 裸 except 体内以 pass 收尾（真吞掉，不是换个方式往上抛）。
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
        pass_at = after.find("pass", guard_at)
        if pass_at < 0:
            return ""
        return after[guard_at:pass_at + len("pass")]

    def _log_title_in(self, chunk):
        """从一段源码里取出 log_error 的标题实参（调用里最后一个字符串字面量）。

        读的是**源码里实际写下的字面量**，不是本文件的常量——对常量断言只有在
        有人改测试时才可能失败，等于没测。
        正则用 `"([^"]*)"?`：_except_block 的切片止于标题的收尾引号之前，
        模式必须容忍最后一个字面量没有右引号。
        """
        at = chunk.index("log_error(")
        quoted = re.findall(r'"([^"]*)"?', chunk[at:])
        return quoted[-1] if quoted else ""

    # ---------- 存在性与判据复用 ----------

    def test_entry_exists(self):
        self.assertIn(VERIFY_ENTRY, self.src)

    def test_reuses_system_pairing_result_not_own_algorithm(self):
        """核实判据 = 系统已生成的完整配对结果，不另写一套配对定义。

        「完整上下班配对」在本系统里由 pairing.py 落进 tabAttendance：
        非豁免的 Present 一定带真实配对间隔（working_hours），所以查
        status='Present' 且 working_hours >= 2 就是在复用系统算好的结论。
        两处判据必须同源，否则迟早漂移。
        """
        sql = self._sql_literal()
        self.assertIn("`tabAttendance`", sql)
        self.assertIn("status = 'Present'", sql)
        self.assertIn("working_hours >= 2", sql)
        self.assertIn("attendance_date", sql)

    def test_query_is_scoped_to_the_one_employee(self):
        """必须按员工收窄：漏掉 employee 条件会把别人的出勤算成本人的。"""
        self.assertIn("employee = %s", self._sql_literal())

    def test_does_not_reimplement_pairing_from_checkins(self):
        """不得在调休模块里从打卡流水重推配对（那正是两套定义漂移的开端）。"""
        sql = self._sql_literal()
        body = self._func(PRESENT_DATES_ENTRY)
        self.assertNotIn("Employee Checkin", sql)
        self.assertNotIn("log_type", body)
        self.assertNotIn("pair_employee_checkins", self.src)

    def test_present_dates_short_circuits_without_employee_or_dates(self):
        """缺员工或缺日期必须在查询之前短路——否则会把 None 拼进查询。"""
        body = self._func(PRESENT_DATES_ENTRY)
        guard_at = body.index("if not dates or not employee:")
        sql_at = body.index("frappe.db.sql(")
        self.assertLess(guard_at, sql_at, "短路守卫必须在查询之前")
        self.assertIn("return set()", body[guard_at:sql_at])

    # ---------- 只碰待核实 ----------

    def test_only_pending_records_selected(self):
        """只取 verify_status=待核实；不得把已核实/待解析的再捞一遍。"""
        func = self._func()
        filt_at = func.index("filters={")
        filt = func[filt_at:filt_at + 120]
        self.assertIn("verify_status", filt)
        self.assertIn("VERIFY_PENDING", filt)
        self.assertNotIn("VERIFY_OK", filt)
        self.assertNotIn("PARSE_PENDING", filt)
        self.assertIn("VERIFY_PENDING", _import_block(self.src))

    def test_verdict_comes_from_pure_module(self):
        """结论只由 rest_leave.verify_status_for 产生，本文件不自行判定。"""
        self.assertIn("verify_status_for(dates, paired)", self.src)
        self.assertIn("VERIFY_OK", self.src)
        block = _import_block(self.src)
        self.assertIn("verify_status_for", block)
        self.assertIn("VERIFY_OK", block)
        self.assertIn("VERIFY_PENDING", block)

    def test_records_verify_time(self):
        self.assertIn("doc.verify_time = frappe.utils.now_datetime()", self.src)

    def test_does_not_clobber_parse_result(self):
        """核实阶段只写结论，不得覆写解析阶段的产物。"""
        func = self._func()
        self.assertNotIn(".parsed_at", func)
        self.assertNotIn(".overtime_dates =", func)
        # remarks 存着飞书原说明：Task 4 的重新解析靠比较它来发现说明被改过，
        # 从核实阶段覆写会静默毁掉那条路径。负面结论的判据写进日志，不写这里。
        # （此断言是前向护栏：修前源码同样满足，它不构成 RED 判别。）
        self.assertNotIn(".remarks", func)

    # ---------- 不接豁免、不打断调度 ----------

    def test_does_not_hook_into_attendance_generation(self):
        """本阶段只写结论：不得触发重算，也不得进入判定。"""
        self.assertNotIn("regenerate_attendance", self.src)
        self.assertNotIn("pair_employee_checkins", self.src)
        self.assertNotIn("frappe.throw(", self.src)

    # ---------- 逐条兜底（DELTA 1） ----------

    def test_row_body_is_guarded_end_to_end(self):
        """从切日期到 save 的整段逐条处理必须在同一个 try 之内。

        回归场景：get_all 之后这条记录被删 → frappe.get_doc 抛 DoesNotExist。
        修复前 get_doc 落在循环体唯一的 try 之外，异常直接冒出函数：本批已落库
        的计数与 remaining 全丢，调度链也断（与 Task 3/Task 4 同一种失效模式）。

        判别法：定位「包含切日期那行的那层循环体 try」（8 空格缩进）。
        修复前循环体里唯一的 8 空格 try 只包着 _present_dates，它不含切日期，
        断言必失败——取的是缩进层级所表达的作用域，不是字样。
        """
        func = self._func()
        get_doc_at = func.index("frappe.get_doc(DOCTYPE, row.name)")
        count_at = func.index('summary["remaining"]')

        outer_try = func.rindex("\n        try:", 0, get_doc_at)
        self.assertIn(
            "for d in str(row.overtime_dates", func[outer_try:get_doc_at],
            "切日期之前就必须进入逐条兜底 try")
        self.assertIn(
            "_present_dates(", func[outer_try:get_doc_at],
            "查考勤也必须在兜底 try 之内")

        outer_except = func.index("\n        except Exception as e:", outer_try)
        self.assertLess(get_doc_at, outer_except, "get_doc 必须落在兜底 try 之内")
        self.assertLess(outer_except, count_at, "兜底 except 必须在循环体内")

        handler = func[outer_except:count_at]
        self.assertIn('summary["failed"] += 1', handler)
        self.assertIn("row.name", handler, "兜底日志要能分辨是哪条")
        self.assertNotIn("raise", handler, "兜底不得再抛，否则等于没兜")

    def test_loop_head_is_cheap(self):
        """循环头与循环外只放不能抛的便宜操作：取列带必须留在 try 内。

        修复前的写法把 get_all 之后的一切裸放在循环体里；这里断言循环体第一层
        可执行语句就是 try（8 空格），中间不得夹带未受保护的调用。
        """
        func = self._func()
        loop_at = func.index("for row in pending:")
        body = func[loop_at:]
        first = body.index("\n        ")
        self.assertEqual(
            body[first:first + 13], "\n        try:",
            "循环体第一层必须是兜底 try，不得先裸跑语句")

    # ---------- 摘要键（DELTA 4） ----------

    def test_summary_keys_identical_on_all_paths(self):
        """所有返回路径返回同一 summary 变量，键集合恒等。

        至少要有两条返回路径（起始阶段失败 / 正常结束），否则「所有路径一致」
        是句空话；且不得用字面量 dict 提前返回（极易漏键 → 调度器 KeyError）。
        """
        func = self._func()
        start = func.index("summary = {")
        init = func[start:func.index("}", start)]
        for key in sorted(SUMMARY_KEYS):
            self.assertIn('"%s"' % key, init, "初始化摘要缺键: %s" % key)
        self.assertGreaterEqual(
            func.count("return summary"), 2,
            "起始阶段失败与正常结束都要返回同一摘要")
        self.assertNotIn('return {"', func, "不得用字面量 dict 提前返回（易漏键）")

    # ---------- 日志（DELTA 3） ----------

    def test_row_fallback_log_title_is_neutral_and_identifies_record(self):
        """整条兜底的标题要中立：它覆盖的是「整条处理」，不只是写入。

        断言读的是**源码里实际写下的标题实参**（不是本文件自己的常量）：
        对常量断言只有在有人改测试时才可能失败，等于没测。
        """
        chunk = self._except_block(ROW_BODY_TITLE)
        self.assertTrue(chunk, "找不到 %s 对应的 except 处理体" % ROW_BODY_TITLE)
        self.assertIn("%s: %s", chunk)
        self.assertIn("row.name", chunk)
        actual = self._log_title_in(chunk)
        self.assertTrue(actual, "处理体里找不到 log_error 的标题实参")
        self.assertNotIn("写入", actual, "整条兜底的标题不得写成「写入失败」")
        self.assertNotEqual(
            actual, self._log_title_in(self._except_block(SAVE_FAIL_TITLE)),
            "整条兜底与写入失败必须是两条分得开的日志标题")

    def test_every_handler_log_call_is_shielded_by_nested_guard(self):
        """log_error 自身会抛，处理体里的每个 log_error 都必须再裹一层裸 try。

        理由：frappe.log_error 内部是 get_doc(Error Log) + insert，自己没有兜底。
        最可能的失败场景恰是数据库故障——那条 INSERT 走同一条坏连接再抛一次，
        异常从 except 里冒出去，逐条兜底、本批计数、调度链一起丢。
        判别法见 _nested_guard：要求 log_error 之前紧邻一个 try:，对应的 except
        是不带 as e 的裸形式、体内以 pass 收尾。修前这些位置都没有紧邻的 try:，
        每个标题都取不到防护体，断言必失败。
        """
        for title in (ROW_BODY_TITLE, SAVE_FAIL_TITLE, LIST_FAIL_TITLE,
                      COUNT_FAIL_TITLE, NO_EMPLOYEE_TITLE, NO_DATES_TITLE,
                      MISSING_PAIR_TITLE):
            with self.subTest(title=title):
                guard = self._nested_guard(title)
                self.assertTrue(
                    guard, "%s 的 log_error 没有被裸 try 兜住" % title)
                self.assertIn("pass", guard)

    def test_save_failure_log_identifies_record(self):
        chunk = self._except_block(SAVE_FAIL_TITLE)
        self.assertTrue(chunk, "找不到 %s 对应的 except 处理体" % SAVE_FAIL_TITLE)
        self.assertIn("%s: %s", chunk)
        self.assertIn("row.name", chunk)

    def test_startup_failure_log_is_accurate(self):
        """起始阶段（读待核列表 / 统计积压）失败的标题要写明是哪一步。"""
        self.assertIn(LIST_FAIL_TITLE, self.src)
        self.assertIn(COUNT_FAIL_TITLE, self.src)
        self.assertTrue(self._except_block(LIST_FAIL_TITLE))
        self.assertTrue(self._except_block(COUNT_FAIL_TITLE))
        # 起始阶段失败必须写进 error 键，调用方据此判断「本轮没处理任何记录」
        self.assertIn('summary["error"] = str(e)', self._except_block(LIST_FAIL_TITLE))

    def test_skip_reasons_are_distinguishable(self):
        """两类「没法核」的跳过必须能分辨：缺员工 vs 缺加班日（DELTA 2）。"""
        for title in (NO_EMPLOYEE_TITLE, NO_DATES_TITLE):
            chunk = self._log_call(title)
            self.assertTrue(chunk, "找不到标题为 %s 的日志调用" % title)
            self.assertIn("row.name", chunk)


# ---------------------------------------------------------------------------
# 行为性测试：假的 frappe + 真的被测函数
# ---------------------------------------------------------------------------

_STUB = None
_MOD = None


def setUpModule():
    """注入假 frappe 再导入被测模块（CI 无 Frappe 站点）。

    假 frappe 只在这里注入一次——模块级 import 会把它捕获成模块全局——所以
    各用例改的是它内部的属性（db / get_doc / log_error），而不是换掉 sys.modules
    里那个对象：换掉对象的话，被测模块手里那个引用不会跟着变。
    """
    global _STUB, _MOD
    _STUB = types.SimpleNamespace(
        whitelist=lambda *a, **k: (lambda fn: fn),
        db=types.SimpleNamespace(),
        utils=types.SimpleNamespace(now_datetime=lambda: NOW),
        log_error=lambda *a, **k: None,
        get_doc=lambda *a, **k: None,
    )
    with mock.patch.dict(sys.modules, {"frappe": _STUB}):
        sys.modules.pop(MODULE_NAME, None)
        # 被测模块的 import 链会拉进 api.py 的 `import requests` → urllib3 v2，
        # 后者在导入时就对 macOS 系统 Python 的 LibreSSL 发 NotOpenSSLWarning。
        # 那是环境噪声、与本任务无关，但会污染测试输出（契约要求输出干净），
        # 所以在**只包住这次导入**的局部范围里按消息前缀静音，不外溢到全局。
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="urllib3 v2 only supports OpenSSL")
            _MOD = importlib.import_module(MODULE_NAME)


def _row(name, employee="EMP-1", overtime_dates="2026-08-01"):
    return types.SimpleNamespace(
        name=name, employee=employee, overtime_dates=overtime_dates)


class _FakeDoc:
    def __init__(self, name, fail_save=False):
        self.name = name
        self.verify_status = None
        self.verify_time = None
        self.parsed_at = "保留原值"
        self.overtime_dates = "保留原值"
        self.saves = 0
        self.fail_save = fail_save

    def save(self, ignore_permissions=False):
        if self.fail_save:
            raise RuntimeError("save 失败")
        self.saves += 1


class _FakeDB:
    def __init__(self, pending=(), present_dates=(), remaining=0,
                 get_all_error=None, sql_error=None, count_error=None):
        self.pending = list(pending)
        self.present_dates = list(present_dates)
        self.remaining = remaining
        self.get_all_error = get_all_error
        self.sql_error = sql_error
        self.count_error = count_error
        self.sql_calls = []
        self.commits = 0
        self.get_all_kw = None
        self.count_filters = None

    def get_all(self, doctype, **kw):
        self.get_all_kw = kw
        if self.get_all_error:
            raise RuntimeError(self.get_all_error)
        return list(self.pending)

    def sql(self, query, params=None, as_dict=False):
        self.sql_calls.append((query, params))
        if self.sql_error:
            raise RuntimeError(self.sql_error)
        return [{"attendance_date": d} for d in self.present_dates]

    def count(self, doctype, filters=None):
        self.count_filters = filters
        if self.count_error:
            raise RuntimeError(self.count_error)
        return self.remaining

    def commit(self):
        self.commits += 1


class _BehaviourBase(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.docs = {}
        self.fail_get_doc = set()
        self.fail_save = set()
        self.db = _FakeDB()
        self._install(self.db)

    def _install(self, db):
        self.db = db
        _STUB.db = db
        self.fail_get_doc = set()
        self.fail_save = set()
        self.logs = []
        _STUB.log_error = lambda msg=None, title=None: self.logs.append(
            (str(msg), str(title)))
        _STUB.get_doc = self._get_doc

    def _get_doc(self, doctype, name):
        if name in self.fail_get_doc:
            raise RuntimeError("DoesNotExist: %s" % name)
        doc = _FakeDoc(name, fail_save=name in self.fail_save)
        self.docs[name] = doc
        return doc

    def _titles(self):
        return [t for _, t in self.logs]

    def run_verify(self, **kw):
        return _MOD.verify_pending_rest_leaves(**kw)


class VerifyBehaviourTest(_BehaviourBase):
    """真的调用函数：选择、判定、兜底、摘要。"""

    def test_verified_when_every_overtime_date_is_on_record(self):
        db = _FakeDB(
            pending=[_row("RL-1", overtime_dates="2026-08-01,2026-08-02")],
            present_dates=["2026-08-01", "2026-08-02"], remaining=0)
        self._install(db)

        summary = self.run_verify()

        self.assertEqual(summary["verified"], 1)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["skipped"], 0)
        self.assertEqual(summary["error"], "")
        self.assertEqual(self.docs["RL-1"].verify_status, "已核实")
        self.assertEqual(self.docs["RL-1"].verify_time, NOW)
        self.assertEqual(self.docs["RL-1"].saves, 1)
        self.assertEqual(db.commits, 1)
        # 加班日真的被绑进了查询（漏了就变成「查全部出勤」）
        self.assertIn("2026-08-01", str(db.sql_calls[0][1]))
        self.assertIn("2026-08-02", str(db.sql_calls[0][1]))
        self.assertIn("EMP-1", str(db.sql_calls[0][1]))

    def test_one_missing_overtime_date_fails_verification(self):
        """哪怕只有一天没配对，整条也不通过（宁可漏判不可错判）。"""
        db = _FakeDB(
            pending=[_row("RL-1", overtime_dates="2026-08-01,2026-08-02")],
            present_dates=["2026-08-01"])
        self._install(db)

        summary = self.run_verify()

        self.assertEqual(summary["verified"], 0)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(self.docs["RL-1"].verify_status, "核实不通过")
        self.assertEqual(self.docs["RL-1"].verify_time, NOW)
        # 负面结论要留下判据：写清缺的是哪一天、是哪条记录，人工才查得下去
        # （DELTA 3 的延伸；证据走日志，绝不覆写 remarks 里的飞书原说明）
        self.assertIn(MISSING_PAIR_TITLE, self._titles())
        evidence = str(self.logs[0][0])
        self.assertIn("RL-1", evidence)
        self.assertIn("2026-08-02", evidence, "要点名缺配对的那一天")
        self.assertNotIn("2026-08-01", evidence, "已配对的那天不该被列进来")

    def test_selects_only_verify_pending(self):
        db = _FakeDB(remaining=4)
        self._install(db)
        from hb_attendance_app.hbos_attendance.rest_leave import VERIFY_PENDING

        summary = self.run_verify(limit=7)

        self.assertEqual(VERIFY_PENDING, "待核实")
        self.assertEqual(db.get_all_kw["filters"], {"verify_status": VERIFY_PENDING})
        self.assertEqual(db.get_all_kw["limit_page_length"], 7)
        self.assertTrue(
            {"name", "employee", "overtime_dates"} <= set(db.get_all_kw["fields"]),
            "取列必须够用：name/employee/overtime_dates")
        self.assertEqual(db.count_filters, {"verify_status": VERIFY_PENDING})
        self.assertEqual(summary["remaining"], 4)

    def test_records_without_overtime_dates_are_skipped_not_verified(self):
        db = _FakeDB(
            pending=[_row("RL-1", overtime_dates="  ,  ")], remaining=1)
        self._install(db)

        summary = self.run_verify()

        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["verified"], 0)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(db.sql_calls, [])
        self.assertEqual(self.docs, {})
        self.assertIn(NO_DATES_TITLE, self._titles())

    def test_missing_employee_is_not_verified_and_stays_pending(self):
        """DELTA 2：缺员工 = 「没法核」而不是「核实不通过」。

        状态字段没有「无法核实」这一档，写「核实不通过」等于断言一个我们从未
        做过的判断；此路保持待核实（仍在待核队列里可见）并单独记日志，
        绝不产生假「已核实」。
        """
        db = _FakeDB(pending=[_row("RL-1", employee=None)], remaining=1)
        self._install(db)

        summary = self.run_verify()

        self.assertEqual(summary["verified"], 0, "缺员工绝不能核实通过")
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(db.sql_calls, [], "缺员工不得发起考勤查询")
        self.assertEqual(self.docs, {}, "缺员工不得写回任何结论")
        self.assertIn(NO_EMPLOYEE_TITLE, self._titles())
        self.assertIn("RL-1", str(self.logs[0][0]), "日志要能分辨是哪条")

    def test_row_exception_does_not_escape_and_later_rows_still_run(self):
        """DELTA 1：单条抛异常不得冒出函数，后续记录照常处理。"""
        db = _FakeDB(
            pending=[_row("RL-1"), _row("RL-2", overtime_dates="2026-08-05")],
            present_dates=["2026-08-05"], remaining=0)
        self._install(db)
        self.fail_get_doc = {"RL-1"}

        summary = self.run_verify()

        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["verified"], 1, "RL-1 的异常不得吃掉 RL-2")
        self.assertEqual(self.docs["RL-2"].verify_status, "已核实")
        self.assertIn(ROW_BODY_TITLE, self._titles())
        self.assertIn("RL-1", str(self.logs[0][0]))
        self.assertIn("remaining", summary)

    def test_query_exception_is_contained(self):
        """查考勤失败也要逐条兜住（DB 抖动不该中断整批）。"""
        db = _FakeDB(
            pending=[_row("RL-1"), _row("RL-2")], sql_error="DB 抖动")
        self._install(db)

        summary = self.run_verify()

        self.assertEqual(summary["failed"], 2)
        self.assertEqual(summary["verified"], 0)
        self.assertEqual(self.docs, {})
        self.assertIn(ROW_BODY_TITLE, self._titles())

    def test_save_failure_is_counted_separately(self):
        db = _FakeDB(pending=[_row("RL-1")], present_dates=["2026-08-01"])
        self._install(db)
        self.fail_save = {"RL-1"}

        summary = self.run_verify()

        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["verified"], 0)
        self.assertIn(SAVE_FAIL_TITLE, self._titles())
        self.assertIn("RL-1", str(self.logs[0][0]))

    def test_summary_keys_identical_when_list_read_fails(self):
        """起始阶段失败：不抛异常、error 有值、键集合与正常路径完全相同。"""
        db = _FakeDB(get_all_error="表不存在")
        self._install(db)

        summary = self.run_verify()

        self.assertEqual(set(summary), SUMMARY_KEYS)
        self.assertNotEqual(summary["error"], "")
        self.assertEqual(summary["verified"], 0)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["skipped"], 0)
        self.assertEqual(summary["remaining"], 0)
        self.assertIn(LIST_FAIL_TITLE, self._titles())

    def test_summary_keys_identical_on_normal_path(self):
        db = _FakeDB(pending=[_row("RL-1")], present_dates=["2026-08-01"])
        self._install(db)

        summary = self.run_verify()

        self.assertEqual(set(summary), SUMMARY_KEYS)

    def test_count_failure_does_not_escape(self):
        """统计积压失败不得把已处理的计数一起丢掉。"""
        db = _FakeDB(
            pending=[_row("RL-1")], present_dates=["2026-08-01"],
            count_error="count 失败")
        self._install(db)

        summary = self.run_verify()

        self.assertEqual(set(summary), SUMMARY_KEYS)
        self.assertEqual(summary["verified"], 1, "已落库的计数不能丢")
        self.assertNotEqual(summary["error"], "")
        self.assertIn(COUNT_FAIL_TITLE, self._titles())

    def test_log_failure_does_not_escape_or_double_count(self):
        """写日志失败（多半是 DB 故障）不得冒泡、不得把同一条重复计数。

        修前：skipped 分支先在摘要上加计数、再写日志；log_error 一抛，异常被
        外层 per-row 兜底接住，同一条于是同时进了 skipped 和 failed，日志标题
        也认错了归属。更糟的是这条异常正是「逐条兜底声称要防的事」本身，
        它能把这批已落库的计数、摘要和调度链一起带走。
        这里让每次 log_error 都抛，断言：函数照常返回完整摘要、每条记录恰好
        计数一次、后续记录照常处理。
        """
        db = _FakeDB(
            pending=[_row("RL-1", overtime_dates="  "),        # 缺加班日 → skipped
                     _row("RL-2", overtime_dates="2026-08-05"),  # 正常 → verified
                     _row("RL-3", employee=None)],               # 缺员工 → skipped
            present_dates=["2026-08-05"], remaining=3)
        self._install(db)

        def _boom(*a, **k):
            raise RuntimeError("Error Log 表写不进去")

        _STUB.log_error = _boom

        summary = self.run_verify()

        self.assertEqual(set(summary), SUMMARY_KEYS)
        self.assertEqual(summary["skipped"], 2, "两条没法核的各计一次，不多不少")
        self.assertEqual(summary["failed"], 0, "日志失败不得被误记成 failed")
        self.assertEqual(summary["verified"], 1, "日志失败不得吃掉正常记录")
        self.assertEqual(self.docs["RL-2"].verify_status, "已核实")
        self.assertEqual(summary["remaining"], 3)

    def test_missing_pair_evidence_log_failure_still_counts_once(self):
        """负面结论的判据日志：先尝试留痕，失败也仍只计一次 failed。

        修前根本没有这条判据日志（徒有「核实不通过」，人工得自己重算缺哪天），
        故 `attempts` 为空、断言必失败——本用例同时是 Minor 3 的判别。
        """
        db = _FakeDB(
            pending=[_row("RL-1", overtime_dates="2026-08-01")],
            present_dates=[], remaining=1)
        self._install(db)
        attempts = []

        def _boom(msg=None, title=None):
            attempts.append(title)
            raise RuntimeError("Error Log 表写不进去")

        _STUB.log_error = _boom

        summary = self.run_verify()

        self.assertIn(MISSING_PAIR_TITLE, attempts, "必须尝试留下缺配对的判据日志")
        self.assertEqual(set(summary), SUMMARY_KEYS)
        self.assertEqual(summary["failed"], 1, "日志失败不得让本条重复计数")
        self.assertEqual(summary["verified"], 0)
        self.assertEqual(self.docs["RL-1"].verify_status, "核实不通过")


if __name__ == "__main__":
    unittest.main()
