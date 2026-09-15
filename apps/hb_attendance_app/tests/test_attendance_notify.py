import os
import sys
import types
import unittest
from datetime import datetime
from unittest import mock

from hb_attendance_app.hbos_attendance import attendance_notify, board_stats
from hb_attendance_app.hbos_attendance.attendance_notify import (
    render_report, build_feishu_payload, feishu_result, collect_exceptions,
    render_card, EMPTY_HINT, NO_CARD_HINT,
)


def d(dept, expected, present, no_card, late=0):
    return {"dept": dept, "total": expected, "expected": expected, "present": present,
            "noCard": no_card, "late": late, "absent": 0, "leave": 0}


def row(dept, num, name, state, kind="shift", tags=None, anomaly_hidden=False):
    """明细行（get_data()['rows'] 的元素）测试构造器。"""
    return {"dept": dept, "num": num, "name": name, "state": state, "kind": kind,
            "tags": tags or [], "anomaly_hidden": anomaly_hidden}


class RenderReportTest(unittest.TestCase):
    def test_contains_title_and_all_depts(self):
        text = render_report("2026-09-10", "09:00", [d("无菌车间", 60, 58, 2), d("厂外QC", 55, 53, 2)])
        self.assertIn("【考勤到岗】2026-09-10 09:00", text)
        self.assertIn("无菌车间", text)
        self.assertIn("厂外QC", text)
        self.assertIn("应出勤", text)
        self.assertIn("已到岗", text)
        self.assertIn("未打卡", text)
        self.assertIn("迟到", text)

    def test_no_total_row(self):
        text = render_report("2026-09-10", "09:00", [d("A", 10, 9, 1)])
        # 不含全厂汇总行（Owner 确认只看部门）
        self.assertNotIn("全厂", text)

    def test_dept_with_zero_expected_skipped(self):
        text = render_report("2026-09-10", "09:00", [d("全员休息部", 0, 0, 0), d("A", 10, 9, 1)])
        self.assertNotIn("全员休息部", text)
        self.assertIn("A", text)

    def test_empty_stats_returns_only_title(self):
        text = render_report("2026-09-10", "09:00", [])
        self.assertIn("【考勤到岗】", text)
        self.assertIn("暂无应出勤", text)

    def test_zero_values_render_as_zero(self):
        text = render_report("2026-09-10", "09:00", [d("A", 10, 10, 0, 0)])
        line = [l for l in text.splitlines() if l.startswith("A")][0]
        self.assertIn("0", line)


class FeishuPayloadTest(unittest.TestCase):
    """飞书自定义机器人要求的报文格式（Owner 2026-09-11 选定路线 B）。"""

    def test_text_message_shape(self):
        from hb_attendance_app.hbos_attendance.attendance_notify import build_feishu_payload
        p = build_feishu_payload("【考勤到岗】2026-09-10 09:00\n部门 ...")
        self.assertEqual(p, {"msg_type": "text",
                             "content": {"text": "【考勤到岗】2026-09-10 09:00\n部门 ..."}})

    def test_payload_has_only_expected_keys(self):
        from hb_attendance_app.hbos_attendance.attendance_notify import build_feishu_payload
        p = build_feishu_payload("x")
        self.assertEqual(sorted(p.keys()), ["content", "msg_type"])


class FeishuResultTest(unittest.TestCase):
    """飞书即使失败也可能返回 HTTP 200，错误在 body 的 code 里 —— 不能只看状态码。"""

    def setUp(self):
        from hb_attendance_app.hbos_attendance.attendance_notify import feishu_result
        self.f = feishu_result

    def test_success_code_zero(self):
        ok, msg = self.f(200, '{"code":0,"msg":"success","data":{}}')
        self.assertTrue(ok)
        self.assertIn("200", msg)

    def test_http_200_but_error_code_is_failure(self):
        # 典型：token 错误 / 签名不匹配 / 被限流，飞书给 200 + 非零 code
        ok, msg = self.f(200, '{"code":19021,"msg":"sign match fail"}')
        self.assertFalse(ok)
        self.assertIn("19021", msg)

    def test_legacy_status_code_field(self):
        ok, _ = self.f(200, '{"StatusCode":0,"StatusMessage":"success"}')
        self.assertTrue(ok)
        ok2, _ = self.f(200, '{"StatusCode":9499,"StatusMessage":"Bad Request"}')
        self.assertFalse(ok2)

    def test_non_2xx_is_failure(self):
        ok, msg = self.f(500, "oops")
        self.assertFalse(ok)
        self.assertIn("500", msg)

    def test_unparseable_body_with_2xx_treated_as_success(self):
        # 兼容非飞书端点（如自建网关返回纯文本）
        ok, _ = self.f(200, "OK")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()


class HeaderAlignmentTest(unittest.TestCase):
    """表头与数据行必须能看出列间隔（中文表头正好填满列宽会连成一片）。"""

    def test_header_labels_separated(self):
        text = render_report("2026-09-10", "09:00", [d("A", 10, 9, 1, 0)])
        header = [l for l in text.splitlines() if l.startswith("部门")][0]
        for label in ("应出勤", "已到岗", "未打卡", "迟到"):
            self.assertIn(label, header)
        # 相邻两个表头标签之间必须至少有一处空格分隔
        self.assertNotIn("应出勤已到岗", header)
        self.assertNotIn("已到岗未打卡", header)
        self.assertNotIn("未打卡迟到", header)

    def test_feishu_payload_carries_rendered_title(self):
        text = render_report("2026-09-10", "09:00", [])
        from hb_attendance_app.hbos_attendance.attendance_notify import build_feishu_payload
        p = build_feishu_payload(text)
        self.assertIn("【考勤到岗】2026-09-10 09:00", p["content"]["text"])


class ShouldSendNowTest(unittest.TestCase):
    def test_only_nine_am_beijing(self):
        from datetime import datetime
        from hb_attendance_app.hbos_attendance.attendance_notify import should_send_now
        self.assertTrue(should_send_now(datetime(2026, 9, 10, 9, 0)))
        self.assertTrue(should_send_now(datetime(2026, 9, 10, 9, 59)))
        self.assertFalse(should_send_now(datetime(2026, 9, 10, 8, 59)))
        self.assertFalse(should_send_now(datetime(2026, 9, 10, 10, 0)))
        self.assertFalse(should_send_now(datetime(2026, 9, 10, 17, 0)))  # 容器 UTC 误触发


class ModuleContractTest(unittest.TestCase):
    def test_exposes_scheduler_entry_and_endpoint(self):
        from pathlib import Path
        src = (Path(__file__).parents[1]
               / "hb_attendance_app/hbos_attendance/attendance_notify.py").read_text()
        self.assertIn("def send_daily_report(", src)
        self.assertIn("def post_to_webhook(", src)
        self.assertIn("HBOS_NOTIFY_WEBHOOK_URL", src)
        self.assertIn("HBOS_NOTIFY_TOKEN", src)
        self.assertIn("HBOS_NOTIFY_DRY_RUN", src)
        self.assertIn("hbos_notify_sent:", src)

    def test_hooks_registers_nine_am_cron(self):
        from pathlib import Path
        src = (Path(__file__).parents[1] / "hb_attendance_app/hooks.py").read_text()
        self.assertIn("attendance_notify.send_daily_report", src)
        self.assertIn('"0 9 * * *"', src)          # 北京时间 09:00
        # 同一方法只能挂一条：Scheduled Job Type 以 method 为唯一键，
        # 挂多条会互相覆盖，可能被覆盖成非 9 点而导致守卫拒发
        self.assertEqual(src.count("attendance_notify.send_daily_report"), 1)


_DATA_MOD = ("hb_attendance_app.hbos_attendance.page."
             "hbos_department_board.department_board_data")


class _FakeCache:
    """假 frappe.cache：足够支撑 get_value/set_value 的内存实现。"""

    def __init__(self, store):
        self.store = store

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value):
        self.store[key] = value


class SendDailyReportDispatchTest(unittest.TestCase):
    """send_daily_report 的调度/发送行为：force 绕过双守卫、干跑不出网、异常不外抛。

    全部打桩（假 frappe + 假取数模块），绝不发真实网络请求。
    桩通过 mock.patch.dict(sys.modules, ...) 注入，tearDown 自动还原，
    不会污染其它测试文件。
    """

    def setUp(self):
        self.cache_store = {}
        self.log_calls = []
        self.get_data_calls = []
        self.bj_now = datetime(2026, 9, 10, 17, 30)      # 非 9 点：force 才应放行
        self.get_data_impl = self._default_get_data
        self._patches = []
        # 假 frappe + 假取数模块（send_daily_report 内部 import frappe / get_data）
        self._install(mock.patch.dict(sys.modules, {
            "frappe": types.SimpleNamespace(
                cache=_FakeCache(self.cache_store),
                log_error=lambda *a, **k: self.log_calls.append(a),
            ),
            _DATA_MOD: types.SimpleNamespace(
                get_data=lambda **kw: self.get_data_impl(**kw)),
        }))
        self._install(mock.patch.object(attendance_notify, "_bj_now", lambda: self.bj_now))

    def _install(self, patcher):
        patcher.start()
        self._patches.append(patcher)

    def tearDown(self):
        for patcher in reversed(self._patches):
            patcher.stop()

    def _default_get_data(self, department=None, date_str=None):
        self.get_data_calls.append((department, date_str))
        return {"dept_stats": [d("无菌车间", 60, 58, 2)]}

    def test_force_bypasses_both_guards(self):
        # 幂等位已落 + 当前非 9 点：非 force 会被双守卫挡住，force 必须绕过并取数
        self.cache_store[attendance_notify._sent_key("2026-09-10")] = "1"
        with mock.patch.dict(os.environ, {
                "HBOS_NOTIFY_DRY_RUN": "", "HBOS_NOTIFY_WEBHOOK_URL": ""}, clear=False):
            blocked = attendance_notify.send_daily_report()
            forced = attendance_notify.send_daily_report(force=True)
        self.assertIn("skipped", blocked)
        self.assertNotIn("skipped", forced)
        self.assertTrue(self.get_data_calls)             # 确实走了取数流程

    def test_dry_run_skips_network_but_marks_sent(self):
        with mock.patch.dict(os.environ, {
                "HBOS_NOTIFY_DRY_RUN": "1",
                "HBOS_NOTIFY_WEBHOOK_URL": "https://example.invalid/hook"}, clear=False), \
                mock.patch.object(attendance_notify, "post_to_webhook") as post, \
                mock.patch.object(attendance_notify, "mark_sent") as mark:
            result = attendance_notify.send_daily_report(force=True)
        post.assert_not_called()                          # 干跑不出网
        mark.assert_called_once_with("2026-09-10")        # 幂等位已落
        self.assertEqual(result["reason"], "dry_run")

    def test_exception_is_swallowed_and_logged(self):
        def boom(**kwargs):
            raise RuntimeError("boom-from-get-data")
        self.get_data_impl = boom
        with mock.patch.dict(os.environ, {
                "HBOS_NOTIFY_DRY_RUN": "", "HBOS_NOTIFY_WEBHOOK_URL": ""}, clear=False):
            result = attendance_notify.send_daily_report(force=True)  # 不得抛
        self.assertFalse(result["sent"])
        self.assertIn("boom-from-get-data", result["reason"])
        self.assertTrue(self.log_calls)                   # frappe.log_error 被调用


class CollectExceptionsTest(unittest.TestCase):
    """异常名录的取数与 board_stats 同一口径（不重写判定规则）。"""

    def test_no_card_and_late_split_by_type(self):
        rows = [
            row("六车间", "0002", "李四", "absent_expected"),
            row("六车间", "0001", "张三", "absent_expected"),
            row("六车间", "0003", "王五", "late"),
        ]
        out = collect_exceptions(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["dept"], "六车间")
        self.assertEqual([p["name"] for p in out[0]["noCard"]], ["张三", "李四"])  # 按工号升序
        self.assertEqual([p["name"] for p in out[0]["late"]], ["王五"])

    def test_skips_non_alert_states(self):
        rows = [row("A", "1", "甲", "present"), row("A", "2", "乙", "rest"),
                row("A", "3", "丙", "leave"), row("A", "4", "丁", "exempt"),
                row("A", "5", "戊", "unknown"), row("A", "6", "己", "before_start"),
                row("A", "7", "庚", "out_only"), row("A", "8", "辛", "fact_none")]
        self.assertEqual(collect_exceptions(rows), [])

    def test_skips_anomaly_hidden_and_non_shift(self):
        rows = [row("A", "1", "甲", "absent_expected", anomaly_hidden=True),
                row("A", "2", "乙", "absent_expected", kind="holiday")]
        self.assertEqual(collect_exceptions(rows), [])

    def test_late_via_tag_is_caught(self):
        # 回顾模式：HRMS 打「迟到」标签而 state 非 late
        rows = [row("A", "1", "甲", "present", tags=["迟到"])]
        out = collect_exceptions(rows)
        self.assertEqual([p["name"] for p in out[0]["late"]], ["甲"])

    def test_late_tag_on_non_expected_row_is_ignored(self):
        # 关键回归：非应出勤行（休假/休息/豁免/无排班/非班次）即使带「迟到」标签也不算异常——
        # summarize_rows 不计它，卡片若计入就会与看板数字漂移。
        # 注：fact_none 不属于「非应出勤」——board_stats 对 kind="shift" 的 fact_none 仍计入
        # expected，其「迟到」标签也计入 late（见 test_matches_summarize_rows_over_all_states），
        # 故此处只列真正的非应出勤行。
        rows = [row("A", "1", "甲", "leave", tags=["迟到"]),
                row("A", "2", "乙", "rest", tags=["迟到"]),
                row("A", "3", "丙", "exempt", tags=["迟到"]),
                row("A", "4", "丁", "unknown", tags=["迟到"]),
                row("A", "6", "己", "present", tags=["迟到"], kind="holiday")]
        self.assertEqual(collect_exceptions(rows), [])

    def test_matches_summarize_rows_over_all_states(self):
        # 逐 state × kind × 迟到标签 全枚举，断言卡片名单与统计口径逐项一致
        states = ["present", "late", "fact_present", "present_offwindow", "out_day",
                  "out_offwindow", "out_only", "fact_none", "before_start",
                  "absent_expected", "no_pair", "pending", "absent_day",
                  "leave", "rest", "exempt", "unknown", "unexpected_state"]
        for st in states:
            for kind in ("shift", "holiday"):
                for tags in ([], ["迟到"]):
                    r = row("D", "1", "甲", st, kind=kind, tags=tags)
                    s = board_stats.summarize_rows([r])
                    out = collect_exceptions([r])
                    got_nc = bool(out and out[0]["noCard"])
                    got_lt = bool(out and out[0]["late"])
                    self.assertEqual(got_nc, bool(s["noCard"]), "%s/%s/%s" % (st, kind, tags))
                    self.assertEqual(got_lt, bool(s["late"]), "%s/%s/%s" % (st, kind, tags))
                    if not s["expected"]:
                        self.assertEqual(out, [], "%s/%s" % (st, kind))

    def test_anomaly_hidden_never_listed(self):
        rows = [row("A", "1", "甲", "absent_expected", anomaly_hidden=True),
                row("A", "2", "乙", "late", anomaly_hidden=True)]
        self.assertEqual(collect_exceptions(rows), [])

    def test_counts_match_summarize_rows(self):
        rows = [row("六车间", "1", "甲", "absent_expected"),
                row("六车间", "2", "乙", "no_pair"),
                row("六车间", "3", "丙", "late"),
                row("仓储部", "4", "丁", "pending"),
                row("仓储部", "5", "戊", "present")]
        out = {e["dept"]: e for e in collect_exceptions(rows)}
        for dept in ("六车间", "仓储部"):
            s = board_stats.summarize_rows([r for r in rows if r["dept"] == dept])
            self.assertEqual(len(out[dept]["noCard"]), s["noCard"], dept)
            self.assertEqual(len(out[dept]["late"]), s["late"], dept)

    def test_dept_order_matches_dept_summary(self):
        rows = [row("A", "1", "甲", "absent_expected"),
                row("B", "2", "乙", "absent_expected"),
                row("B", "3", "丙", "absent_expected")]
        out = [e["dept"] for e in collect_exceptions(rows)]
        ordered = [d_["dept"] for d_ in board_stats.dept_summary(rows) if d_["dept"] in out]
        self.assertEqual(out, ordered)
        self.assertEqual(out, ["B", "A"])          # 异常多的部门在前

    def test_depts_without_exception_omitted(self):
        rows = [row("正常部", "1", "甲", "present"),
                row("异常部", "2", "乙", "absent_expected")]
        self.assertEqual([e["dept"] for e in collect_exceptions(rows)], ["异常部"])

    def test_empty_rows(self):
        self.assertEqual(collect_exceptions([]), [])


def card_text(card):
    """把卡片里所有文本元素拍平，便于断言（分隔线等无文本元素自动跳过）。"""
    parts = []
    for el in card["elements"]:
        t = (el.get("text") or {}).get("content")
        if t:
            parts.append(t)
    return "\n".join(parts)


class RenderCardTest(unittest.TestCase):
    STATS = {"expected": 696, "present": 651, "noCard": 12, "late": 3,
             "notStarted": 40, "outOnly": 8, "unknownTime": 5}

    def _card(self, exceptions, dept_stats=None, stats=None):
        return render_card("2026-09-11", "09:00", stats or self.STATS,
                           dept_stats if dept_stats is not None else [d("六车间", 40, 36, 3)],
                           exceptions)

    def test_header_orange_when_alert(self):
        card = self._card([{"dept": "六车间", "noCard": [{"name": "张三", "num": "1"}], "late": []}])
        self.assertEqual(card["header"]["template"], "orange")
        self.assertEqual(card["header"]["title"]["content"], "考勤到岗 · 2026-09-11 09:00")

    def test_header_green_and_hint_when_no_alert(self):
        card = self._card([], dept_stats=[d("六车间", 40, 36, 0)],
                          stats=dict(self.STATS, noCard=0, late=0))
        self.assertEqual(card["header"]["template"], "green")
        self.assertIn("全部正常", card_text(card))

    def test_factory_line_shows_expected_and_present_always(self):
        card = self._card([], dept_stats=[d("六车间", 40, 36, 0)],
                          stats=dict(self.STATS, noCard=0, late=0))
        txt = card_text(card)
        self.assertIn("应出勤 696", txt)
        self.assertIn("已到岗 651", txt)

    def test_factory_line_omits_zero_fields(self):
        card = self._card([], dept_stats=[d("六车间", 40, 36, 0)],
                          stats=dict(self.STATS, noCard=0, late=0))
        txt = card_text(card)
        self.assertNotIn("未打卡 0", txt)
        self.assertNotIn("迟到 0", txt)

    def test_dept_line_shows_only_nonzero_counts(self):
        card = self._card([{"dept": "仓储部", "noCard": [{"name": "赵六", "num": "1"}], "late": []}],
                          dept_stats=[d("仓储部", 17, 15, 1)])
        txt = card_text(card)
        self.assertIn("未打卡 1", txt)
        self.assertNotIn("迟到 0", txt)

    def test_single_type_omits_name_label(self):
        txt = card_text(self._card(
            [{"dept": "六车间", "noCard": [{"name": "张三", "num": "1"}], "late": []}]))
        self.assertIn("张三", txt)
        self.assertNotIn("未打卡：张三", txt)

    def test_both_types_get_labels(self):
        txt = card_text(self._card(
            [{"dept": "六车间", "noCard": [{"name": "张三", "num": "1"}],
              "late": [{"name": "李四", "num": "2"}]}],
            dept_stats=[d("六车间", 40, 36, 1, 1)]))
        self.assertIn("未打卡：张三", txt)
        self.assertIn("迟到：李四", txt)

    def test_names_truncated_at_six(self):
        people = [{"name": "人%d" % i, "num": "%03d" % i} for i in range(1, 10)]   # 9 人
        txt = card_text(self._card([{"dept": "六车间", "noCard": people, "late": []}],
                                   dept_stats=[d("六车间", 40, 36, 9)]))
        self.assertIn("等 3 人", txt)
        self.assertNotIn("人9", txt)

    def test_depts_truncated_at_ten(self):
        dept_stats = [d("D%02d" % i, 10, 9, 1) for i in range(1, 13)]             # 12 个部门
        exc = [{"dept": "D%02d" % i, "noCard": [{"name": "张三", "num": "1"}], "late": []}
               for i in range(1, 13)]
        txt = card_text(self._card(exc, dept_stats=dept_stats))
        self.assertIn("另有 2 个部门存在异常", txt)
        self.assertNotIn("D11", txt)
        self.assertNotIn("D12", txt)

    def test_normal_dept_count(self):
        dept_stats = [d("A", 10, 9, 1), d("B", 10, 10, 0), d("C", 10, 10, 0)]
        txt = card_text(self._card(
            [{"dept": "A", "noCard": [{"name": "张三", "num": "1"}], "late": []}],
            dept_stats=dept_stats))
        self.assertIn("其余 2 个部门全部正常", txt)

    def test_no_normal_dept_line_when_all_alert(self):
        dept_stats = [d("A", 10, 9, 1)]
        txt = card_text(self._card(
            [{"dept": "A", "noCard": [{"name": "张三", "num": "1"}], "late": []}],
            dept_stats=dept_stats))
        self.assertIn("⚠ 需处理（1 个部门）", txt)
        self.assertNotIn("其余", txt)

    def test_zero_expected_dept_not_counted_as_normal(self):
        dept_stats = [d("A", 10, 9, 1), d("全员休息", 0, 0, 0)]
        txt = card_text(self._card(
            [{"dept": "A", "noCard": [{"name": "张三", "num": "1"}], "late": []}],
            dept_stats=dept_stats))
        self.assertNotIn("其余 1 个部门全部正常", txt)

    def test_note_present_when_not_started_group_exists(self):
        txt = card_text(self._card([], dept_stats=[d("A", 10, 9, 0)],
                                   stats=dict(self.STATS, noCard=0, late=0)))
        self.assertIn(NO_CARD_HINT, txt)

    def test_note_absent_when_no_not_started_group(self):
        txt = card_text(self._card([], dept_stats=[d("A", 10, 9, 0)],
                                   stats=dict(self.STATS, noCard=0, late=0,
                                              notStarted=0, outOnly=0, unknownTime=0)))
        self.assertNotIn(NO_CARD_HINT, txt)

    def test_no_expected_dept_shows_empty_hint_only(self):
        card = render_card("2026-09-11", "09:00",
                           dict(self.STATS, expected=0, present=0, noCard=0, late=0), [], [])
        self.assertEqual(card["header"]["template"], "green")
        txt = card_text(card)
        self.assertIn(EMPTY_HINT, txt)
        self.assertNotIn(NO_CARD_HINT, txt)

    def test_serializable(self):
        import json
        card = self._card([{"dept": "六车间", "noCard": [{"name": "张三", "num": "1"}], "late": []}])
        self.assertIsInstance(json.dumps(card, ensure_ascii=False), str)

    def test_every_element_is_renderable(self):
        # 卡片元素只允许 div / hr（最小能力集，避免依赖表格组件的版本兼容性）
        card = self._card([{"dept": "六车间", "noCard": [{"name": "张三", "num": "1"}], "late": []}])
        self.assertEqual(card["config"], {"wide_screen_mode": True})
        self.assertIn("header", card)
        for el in card["elements"]:
            self.assertIn(el["tag"], ("div", "hr"))
