import unittest
from pathlib import Path

from hb_attendance_app.hbos_attendance import ai_review


class AiBuildPromptTest(unittest.TestCase):
    def test_prompt_contains_employee_rules_anomalies_and_format(self):
        emp = {"name": "张三", "num": "11008018", "dept": "无菌车间"}
        items = [("2026-07-15", "迟到"), ("2026-07-16", "缺勤")]
        checkins = "7/15 08:41 上班机；7/15 20:44 下班机\n7/16 无打卡"
        rule = "行政班 08:30-17:30，08:31 起算迟到；豁免：否"
        p = ai_review.build_prompt(emp, items, checkins, rule)
        for s in ("张三", "11008018", "无菌车间", "行政班", "2026-07-15", "2026-07-16",
                  "属实", "存疑", "非异常", "日期|类型|结论|理由", "迟到", "缺勤"):
            self.assertIn(s, p)

    def test_env_config_returns_keys(self):
        cfg = ai_review.env_config()
        self.assertIn("base_url", cfg)
        self.assertIn("api_key", cfg)
        self.assertIn("model", cfg)
        self.assertIn("timeout", cfg)


class AiParseReviewTest(unittest.TestCase):
    def test_parse_normal_output(self):
        keys = ["2026-07-15", "2026-07-16"]
        text = "2026-07-15|迟到|属实|08:41 打卡超 08:31\n2026-07-16|缺勤|非异常|当天有排班休息记录"
        out = ai_review.parse_review(text, keys)
        self.assertEqual(out["2026-07-15"], "属实：08:41 打卡超 08:31")
        self.assertEqual(out["2026-07-16"], "非异常：当天有排班休息记录")

    def test_parse_skips_malformed_lines_and_truncates(self):
        keys = ["2026-07-15"]
        text = "随便一行没有分隔符\n2026-07-15|迟到|属实|理由\n2026-07-16|缺勤|存疑|多余行"
        out = ai_review.parse_review(text, keys)
        self.assertEqual(list(out.keys()), ["2026-07-15"])  # 只保留 keys 内、跳过多余

    def test_parse_unknown_verdict_falls_back(self):
        keys = ["2026-07-15"]
        text = "2026-07-15|迟到|不知道|理由"
        out = ai_review.parse_review(text, keys)
        self.assertIn("存疑", out["2026-07-15"])


if __name__ == "__main__":
    unittest.main()


APP = Path(__file__).parents[1] / "hb_attendance_app"
REPORT_PY = APP / "hbos_attendance/report/月度考勤汇总/月度考勤汇总.py"
REPORT_JS = APP / "hbos_attendance/report/月度考勤汇总/月度考勤汇总.js"
EXPORT_PY = APP / "hbos_attendance/report/月度考勤汇总/export.py"


class AiMonthlyReportContractTest(unittest.TestCase):
    def test_report_enable_ai_gates_column_and_build(self):
        content = REPORT_PY.read_text()
        self.assertIn('enable_ai', content)
        self.assertIn("def _columns(enable_ai=False)", content)
        self.assertIn('"AI复核"', content)
        self.assertIn("ai_review", content)
        self.assertIn("build_prompt", content)
        self.assertIn("parse_review", content)
        self.assertIn("call_llm", content)
        self.assertIn("ai_review_preview", content)

    def test_report_skips_ai_when_disabled(self):
        content = REPORT_PY.read_text()
        self.assertIn("if enable_ai:", content)

    def test_js_filter_reset_removed_to_not_break_screening(self):
        # 防止 6 个 filter 的 change 复位监听干扰月份/部门筛选的正常提交（曾导致点8月看不到）
        js = REPORT_JS.read_text()
        self.assertNotIn('["month","year","employee","department","from_date","to_date"].forEach(function (fn)', js)
        self.assertNotIn('f.$input.on("change"', js)
        self.assertIn('AI复核', js)

    def test_batch_limit_gates_review(self):
        content = REPORT_PY.read_text()
        # 后端兜底：只复核前 AI_BATCH 人，其余标记未复核（防超代理超时）
        self.assertIn("AI_BATCH", content)
        self.assertIn("all_target[:AI_BATCH]", content)
        self.assertIn("未复核：本批上限", content)
        # preview 返回 batch，前端据此提示分批
        self.assertIn('"batch": AI_BATCH', content)
        js = REPORT_JS.read_text()
        self.assertIn("m.employee_count > m.batch", js)
        self.assertIn("超过单批复核上限", js)

    def test_export_passes_enable_ai(self):
        content = EXPORT_PY.read_text()
        self.assertIn("enable_ai", content)

    def test_date_range_filter_requires_both_and_not_inverted(self):
        """避免「只填开始/结束」或「起止倒置」导致空结果、界面消失。"""
        content = REPORT_PY.read_text()
        self.assertIn("str(from_date) <= str(to_date)", content)
        self.assertIn("if from_date and to_date and", content)
        # 旧逻辑的「单独 from_date」写法应移除：不再无条件 append >= from_date
        self.assertIn("if from_date and to_date and str(from_date) <= str(to_date):", content)

    def test_batch_time_budget_caps_sync_calls(self):
        """串行 20 人 × ≤60s 最坏 1200s 超代理超时：增加单批时间预算，超预算停新调用。"""
        content = REPORT_PY.read_text()
        self.assertIn("AI_BATCH_SECONDS", content)
        self.assertIn("batch_deadline", content)
        self.assertIn("单批时间预算", content)
        ai = APP.joinpath("hbos_attendance/ai_review.py").read_text()
        self.assertIn("AI_BATCH_SECONDS = 100", ai)

    def test_js_has_ai_review_button_and_confirm_and_reset(self):
        content = REPORT_JS.read_text()
        self.assertIn("AI复核", content)
        self.assertIn("ai_review_preview", content)
        self.assertIn("enable_ai", content)
        self.assertIn("confirm", content)


class WeekdayHintTest(unittest.TestCase):
    """把星期写进 prompt —— 修「推理烧光输出预算、正文返回空」。

    实测：缺勤类 prompt 下模型会自己演算「2026-10-07 是星期几」，1200 token
    预算全被 reasoning 吃掉，content 为空 → 复核显示「无有效返回」。
    日期与其星期是给定事实，不该让模型推。
    """

    def test_weekday_cn_formats_known_dates(self):
        from hb_attendance_app.hbos_attendance.ai_review import weekday_cn

        self.assertEqual("2026-10-07（星期三）", weekday_cn("2026-10-07"))
        self.assertEqual("2026-10-05（星期一）", weekday_cn("2026-10-05"))
        self.assertEqual("2026-10-10（星期六）", weekday_cn("2026-10-10"))

    def test_weekday_cn_passes_through_bad_input(self):
        from hb_attendance_app.hbos_attendance.ai_review import weekday_cn

        # 非法输入不能抛错——它是 prompt 构造的一部分，不该让整批复核挂掉
        self.assertEqual("bad", weekday_cn("bad"))
        self.assertEqual("", weekday_cn(""))

    def test_prompt_carries_weekday_for_each_date(self):
        from hb_attendance_app.hbos_attendance.ai_review import build_prompt

        prompt = build_prompt(
            {"name": "测试", "num": "1", "dept": "技术部"},
            [("2026-10-07", "缺勤")], "无打卡记录", "行政班",
        )
        self.assertIn("2026-10-07（星期三）|缺勤", prompt)
        # 也要明确告知不必推算，压住推理
        self.assertIn("无需推算", prompt)


class ParseReviewDateNormalizationTest(unittest.TestCase):
    """模型回抄日期有多种写法，都要能对上 anomaly_keys。

    对不上就是**静默丢结果**（整批被当成「不在待复核集里」），比报错更难查。
    """

    def setUp(self):
        from hb_attendance_app.hbos_attendance.ai_review import parse_review

        self.parse = parse_review
        self.keys = ["2026-10-05", "2026-10-07"]

    def test_accepts_plain_date(self):
        got = self.parse("2026-10-07|缺勤|属实|无打卡", self.keys)
        self.assertEqual("属实：无打卡", got["2026-10-07"])

    def test_accepts_date_with_cn_parens(self):
        # prompt 里给的就是这个形态，模型多半原样回抄
        got = self.parse("2026-10-07（星期三）|缺勤|非异常|周末", self.keys)
        self.assertEqual("非异常：周末", got["2026-10-07"])

    def test_accepts_date_with_ascii_parens(self):
        got = self.parse("2026-10-07(周三)|缺勤|存疑|不确定", self.keys)
        self.assertEqual("存疑：不确定", got["2026-10-07"])

    def test_accepts_month_day_only(self):
        got = self.parse("10-07|缺勤|属实|无打卡", self.keys)
        self.assertEqual("属实：无打卡", got["2026-10-07"])

    def test_unknown_date_still_dropped(self):
        got = self.parse("2026-10-09（星期五）|缺勤|属实|无打卡", self.keys)
        self.assertEqual({}, got)


class MaxTokensBudgetTest(unittest.TestCase):
    """输出预算必须给推理留余量（原为 1200，推理吃满导致正文为空）。"""

    def test_budget_is_generous_enough_for_reasoning(self):
        from hb_attendance_app.hbos_attendance.ai_review import AI_MAX_TOKENS

        self.assertGreater(AI_MAX_TOKENS, 1200)

    def test_call_llm_uses_the_constant(self):
        import pathlib

        src = (pathlib.Path(__file__).resolve().parent.parent
               / "hb_attendance_app" / "hbos_attendance" / "ai_review.py").read_text(encoding="utf-8")
        self.assertIn('"max_tokens": AI_MAX_TOKENS', src)
        self.assertNotIn('"max_tokens": 1200', src)
