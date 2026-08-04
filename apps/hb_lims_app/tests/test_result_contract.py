# -*- coding: utf-8 -*-
"""M2-R2 判定引擎离线单测：judge_result / round_significant / apply_formula / verdict_to_label。"""

import unittest

from hb_lims_app.hbos_lims import result_contract as rc


class TestJudgeResult(unittest.TestCase):
    def test_range_pass_within_limits(self):
        self.assertEqual(rc.judge_result(98.5, rc.LIMITS_RANGE, 95.0, 105.0), rc.VERDICT_PASS)

    def test_range_pass_at_lower_boundary(self):
        self.assertEqual(rc.judge_result(95.0, rc.LIMITS_RANGE, 95.0, 105.0), rc.VERDICT_PASS)

    def test_range_pass_at_upper_boundary(self):
        self.assertEqual(rc.judge_result(105.0, rc.LIMITS_RANGE, 95.0, 105.0), rc.VERDICT_PASS)

    def test_range_fail_above_upper(self):
        self.assertEqual(rc.judge_result(105.1, rc.LIMITS_RANGE, 95.0, 105.0), rc.VERDICT_FAIL)

    def test_range_fail_below_lower(self):
        self.assertEqual(rc.judge_result(94.9, rc.LIMITS_RANGE, 95.0, 105.0), rc.VERDICT_FAIL)

    def test_upper_only_pass(self):
        self.assertEqual(rc.judge_result(0.32, rc.LIMITS_UP, upper=0.5), rc.VERDICT_PASS)

    def test_upper_only_fail(self):
        self.assertEqual(rc.judge_result(0.51, rc.LIMITS_UP, upper=0.5), rc.VERDICT_FAIL)

    def test_lower_only_pass(self):
        self.assertEqual(rc.judge_result(99.5, rc.LIMITS_DOWN, lower=99.0), rc.VERDICT_PASS)

    def test_lower_only_fail(self):
        self.assertEqual(rc.judge_result(98.9, rc.LIMITS_DOWN, lower=99.0), rc.VERDICT_FAIL)

    def test_record_type_not_applicable(self):
        self.assertEqual(rc.judge_result("符合规定", rc.LIMITS_RECORD), rc.VERDICT_NA)

    def test_empty_value_undetermined(self):
        self.assertEqual(rc.judge_result(None, rc.LIMITS_RANGE, 95.0, 105.0), rc.VERDICT_UNDETERMINED)
        self.assertEqual(rc.judge_result("", rc.LIMITS_UP, upper=0.5), rc.VERDICT_UNDETERMINED)

    def test_string_value_accepted(self):
        self.assertEqual(rc.judge_result("98.5", rc.LIMITS_RANGE, 95.0, 105.0), rc.VERDICT_PASS)

    def test_unknown_limits_type_raises(self):
        with self.assertRaises(ValueError):
            rc.judge_result(1.0, "未知模式")


class TestRoundSignificant(unittest.TestCase):
    def test_half_to_even_down(self):
        self.assertEqual(rc.round_significant(0.125, 2), 0.12)

    def test_half_to_even_up(self):
        self.assertEqual(rc.round_significant(0.135, 2), 0.14)

    def test_half_to_even_1_245(self):
        self.assertEqual(rc.round_significant(1.245, 2), 1.24)

    def test_half_to_even_1_235(self):
        self.assertEqual(rc.round_significant(1.235, 2), 1.24)

    def test_plain_round(self):
        self.assertEqual(rc.round_significant(98.456, 2), 98.46)

    def test_integer_digits(self):
        self.assertEqual(rc.round_significant(98.5, 0), 98.0)


class TestApplyFormula(unittest.TestCase):
    def test_content_percent_normal(self):
        # A样=1000, C对=0.10 mg/ml, D=1, A对=1000, W样=0.10 g
        # 1000 * 0.10 * 1 / (1000 * 0.10) * 100 = 100.0（含量 100%）
        params = {"a_sample": 1000.0, "c_standard": 0.10, "dilution": 1.0,
                  "a_standard": 1000.0, "w_sample": 0.10}
        self.assertAlmostEqual(rc.apply_formula(params, rc.FORMULA_CONTENT_PERCENT), 100.0, places=6)

    def test_content_percent_zero_denominator(self):
        params = {"a_sample": 1200.0, "c_standard": 0.10, "dilution": 100.0,
                  "a_standard": 0.0, "w_sample": 0.1200}
        with self.assertRaises(rc.FormulaError):
            rc.apply_formula(params, rc.FORMULA_CONTENT_PERCENT)

    def test_content_percent_missing_param(self):
        params = {"a_sample": 1200.0, "c_standard": 0.10, "dilution": 100.0, "a_standard": 1000.0}
        with self.assertRaises(rc.FormulaError):
            rc.apply_formula(params, rc.FORMULA_CONTENT_PERCENT)

    def test_unknown_formula_type_raises(self):
        with self.assertRaises(ValueError):
            rc.apply_formula({}, "自定义表达式")


class TestVerdictLabels(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(rc.verdict_to_label(rc.VERDICT_PASS), "合格")
        self.assertEqual(rc.verdict_to_label(rc.VERDICT_FAIL), "不合格")
        self.assertEqual(rc.verdict_to_label(rc.VERDICT_OOS), "OOS候选")
        self.assertEqual(rc.verdict_to_label(rc.VERDICT_NA), "不适用")
        self.assertEqual(rc.verdict_to_label(rc.VERDICT_UNDETERMINED), "无法判定")


if __name__ == "__main__":
    unittest.main()
