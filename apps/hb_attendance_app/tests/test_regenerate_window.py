"""守住定时重算的窗口边界（不连数据库、不起 Frappe）。

## 为什么需要这个测试

2026-09-02 引入的「删除 range_end 之后」那条语句 + 原窗口「本月 1 日 → 昨天」
造成了一个**只在月末发作**的缺陷：每个月最后一天会在次日被删掉，而次日已跨月、
窗口从 1 日起，重建范围覆盖不到它 → **永久丢失**。

实测证据：9/30 整日为 0 行；而 7/31、8/31 幸存，因为那时还没有那条 DELETE。

这类缺陷的共同特征是「平时看着没问题」——所以必须用**断言窗口**的测试守住，
而不是靠跑一遍全量逻辑去看。
"""
from __future__ import annotations

import ast
import pathlib
import unittest
from datetime import datetime, timedelta

APP = pathlib.Path(__file__).resolve().parent.parent / "hb_attendance_app" / "hbos_attendance"
API = APP / "api.py"


def _module_constant(name):
    """从 api.py 里取模块级常量（不导入，避免拉起 frappe）。"""
    tree = ast.parse(API.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    return None


def _window(now: datetime, lookback_days: int):
    """复刻 regenerate 调用处算窗口的那两行。"""
    yesterday = now - timedelta(days=1)
    start = yesterday - timedelta(days=lookback_days)
    return start.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")


class RegenerateWindowTest(unittest.TestCase):
    def setUp(self):
        self.lookback = _module_constant("REGENERATE_LOOKBACK_DAYS")
        self.assertIsNotNone(self.lookback, "REGENERATE_LOOKBACK_DAYS 必须存在")

    def test_lookback_covers_a_whole_month(self):
        # 必须 > 31：否则「上个月最后一天」仍会掉进跨月空洞
        self.assertGreater(self.lookback, 31)

    def test_month_end_day_is_covered_on_the_next_day(self):
        # 核心回归：9/30 必须在 10/01 的窗口内
        start, end = _window(datetime(2026, 10, 1, 8, 0), self.lookback)
        self.assertLessEqual(start, "2026-09-30", "上个月最后一天必须落在窗口起点之后")
        self.assertGreaterEqual(end, "2026-09-30")

    def test_every_month_end_is_covered_the_next_day(self):
        # 逐月扫一遍，不挑特例
        for year in (2026, 2027):
            for month in range(1, 13):
                last_day = (datetime(year + (month == 12), month % 12 + 1, 1)
                            - timedelta(days=1))
                nxt = last_day + timedelta(days=1)
                with self.subTest(month_end=last_day.strftime("%Y-%m-%d")):
                    start, _ = _window(nxt, self.lookback)
                    self.assertLessEqual(
                        start, last_day.strftime("%Y-%m-%d"),
                        "月末那天必须落在次日重算的窗口内",
                    )

    def test_window_is_never_inverted(self):
        # 原实现在跨月首日会算出 month_start(10-01) > yesterday(09-30) 的倒置区间，
        # 导致 in_range 恒为假、一条都不重建。滚动窗口下 start 永远 <= end。
        for day in (datetime(2026, 1, 1), datetime(2026, 3, 1),
                    datetime(2026, 10, 1), datetime(2027, 1, 1)):
            with self.subTest(day=day.strftime("%Y-%m-%d")):
                start, end = _window(day, self.lookback)
                self.assertLess(start, end, "窗口不得倒置")

    def test_window_ends_yesterday_not_today(self):
        # 今天数据不完整（下班卡/夜班卡未打），算进来会全员假缺勤 —— 这条不能破
        start, end = _window(datetime(2026, 10, 9, 8, 0), self.lookback)
        self.assertEqual("2026-10-08", end)


class CallSiteTest(unittest.TestCase):
    """源码级断言：调用处真的用了滚动窗口，而不是又回到「本月 1 日」。"""

    def setUp(self):
        self.src = API.read_text(encoding="utf-8")

    def test_does_not_use_month_start_any_more(self):
        i = self.src.index("regenerate_attendance(gen_start")
        head = self.src[:i]
        tail_start = head.rindex("# ===== HBOS 考勤生成")
        block = self.src[tail_start:i + 60]
        self.assertNotIn("replace(day=1)", block,
                         "调用处不得再按「本月 1 日」开窗——月末那天会掉进空洞")
        self.assertIn("REGENERATE_LOOKBACK_DAYS", block)

    def test_lookback_constant_is_documented(self):
        # 常量旁必须写明为什么是 35（> 31 才有意义），否则后人会随手改小
        i = self.src.index("REGENERATE_LOOKBACK_DAYS =")
        block = self.src[max(0, i - 400):i + 120]
        self.assertIn("31", block)


if __name__ == "__main__":
    unittest.main()
