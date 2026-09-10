import os
import sys
import types
import unittest
from datetime import datetime
from unittest import mock

from hb_attendance_app.hbos_attendance import attendance_notify
from hb_attendance_app.hbos_attendance.attendance_notify import render_report, build_payload


def d(dept, expected, present, no_card, late=0):
    return {"dept": dept, "total": expected, "expected": expected, "present": present,
            "noCard": no_card, "late": late, "absent": 0, "leave": 0}


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


class BuildPayloadTest(unittest.TestCase):
    def test_payload_shape(self):
        stats = [d("A", 10, 9, 1)]
        p = build_payload("2026-09-10", "2026-09-10 09:00:03", "TEXT", stats)
        self.assertEqual(p["type"], "attendance_daily")
        self.assertEqual(p["date"], "2026-09-10")
        self.assertEqual(p["generated_at"], "2026-09-10 09:00:03")
        self.assertEqual(p["text"], "TEXT")
        self.assertEqual(len(p["dept_stats"]), 1)
        self.assertEqual(p["dept_stats"][0]["dept"], "A")

    def test_payload_dept_stats_has_snake_keys(self):
        # 传输层统一 snake_case，便于 OpenClaw 侧消费
        p = build_payload("2026-09-10", "x", "t", [d("A", 10, 9, 1)])
        self.assertEqual(
            sorted(p["dept_stats"][0].keys()),
            ["absent", "dept", "expected", "late", "leave", "no_card", "not_started",
             "out_only", "present", "total", "unknown_time"],
        )


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

    def test_payload_title_with_bad_generated_at_falls_back(self):
        p = build_payload("2026-09-10", "bad-format", "T", [])
        self.assertEqual(p["title"], "【考勤到岗】2026-09-10")


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
