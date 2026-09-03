import unittest
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
