# -*- coding: utf-8 -*-
"""M2-R8C 离线契约测试：结果与报告（2 DocType + 2 状态机 + 判定/趋势/外推算法）。

覆盖方案 R8C 验收标准的离线部分：
- `HBOS Stability Result` / `HBOS Stability Report` 的命名/唯一键/权限契约
- `HBOS Stability Timepoint Item.current_result` 补建（R8B 暂缓项）
- FLOW_STB_RESULT / FLOW_STB_REPORT 状态机与**同名动作的作用域授权**（SCOPED_ACTION_ROLES）
- 显著变化判定六条规则（7.4）
- 趋势线最小二乘拟合（7.5；**不含统计控制限**）
- ICH Q1E 外推五分支 + 冷藏特例（7.6）
- 业务键生成与分隔符安全、Customer 编码规范、报告范围映射、工作日

本测试不依赖 Frappe，可在宿主机直接运行。
"""

import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from hb_lims_app.hbos_lims import result_contract as rc
from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import workflow_contract as wf

DOCTYPES = APP_ROOT / "hb_lims_app" / "hbos_lims" / "doctype"

MAINS = {
	"hbos_stability_result": "HBOS Stability Result",
	"hbos_stability_report": "HBOS Stability Report",
}
LIMS_READ_ROLES = ["LIMS Manager", "LIMS Analyst", "LIMS Reviewer", "LIMS QA",
				   "LIMS QA Manager", "LIMS QP"]


def _load(dirname):
	return json.loads((DOCTYPES / dirname / (dirname + ".json")).read_text(encoding="utf-8"))


class TestR8CDoctypeContracts(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.mains = {d: _load(d) for d in MAINS}

	def test_doctypes_exist_and_named(self):
		for dirname, expected in MAINS.items():
			payload = self.mains[dirname]
			self.assertEqual(payload["name"], expected, dirname)
			self.assertEqual(payload["module"], "HBOS LIMS", dirname)
			self.assertTrue((DOCTYPES / dirname / (dirname + ".py")).exists(),
							"{}.py 控制器缺失".format(dirname))

	def test_naming_series_have_no_hash(self):
		for dirname, series in (("hbos_stability_result", stb.NAMING_RESULT),
								("hbos_stability_report", stb.NAMING_REPORT)):
			field = next(f for f in self.mains[dirname]["fields"]
						 if f["fieldname"] == "naming_series")
			self.assertEqual(field["options"], series)
			self.assertNotIn("#", field["options"])

	def test_unique_business_keys(self):
		for dirname, key in (("hbos_stability_result", "result_version_key"),
							 ("hbos_stability_report", "report_period_key")):
			field = next(f for f in self.mains[dirname]["fields"] if f["fieldname"] == key)
			self.assertEqual(field.get("unique"), 1, "{} 唯一键未声明".format(dirname))

	def test_result_status_options_match_contract(self):
		field = next(f for f in self.mains["hbos_stability_result"]["fields"]
					 if f["fieldname"] == "status")
		self.assertEqual(set(field["options"].split("\n")), set(stb.RESULT_TRANSITIONS.keys()))

	def test_report_status_options_match_contract(self):
		field = next(f for f in self.mains["hbos_stability_report"]["fields"]
					 if f["fieldname"] == "status")
		self.assertEqual(set(field["options"].split("\n")), set(stb.REPORT_TRANSITIONS.keys()))

	def test_lims_roles_read_only(self):
		for dirname, payload in self.mains.items():
			perms = {p["role"]: p for p in payload.get("permissions", [])}
			for role in LIMS_READ_ROLES:
				self.assertIn(role, perms, "{}/{} 缺权限行".format(dirname, role))
				p = perms[role]
				self.assertEqual((p["read"], p["create"], p["write"], p["delete"]), (1, 0, 0, 0),
								 "{}/{} 应只读".format(dirname, role))

	def test_timepoint_item_has_current_result(self):
		"""R8B 因 Link 目标不存在而暂缓，R8C 补建 `current_result` 生效指针。"""
		payload = _load("hbos_stability_timepoint_item")
		names = [f["fieldname"] for f in payload["fields"]]
		self.assertIn("current_result", names)

	def test_all_fieldtypes_valid(self):
		valid = {
			"Data", "Link", "Dynamic Link", "Select", "Small Text", "Long Text", "Text",
			"Text Editor", "Int", "Float", "Currency", "Percent", "Check", "Date", "Datetime",
			"Time", "Duration", "Password", "Read Only", "Attach", "Attach Image", "Table",
			"Table MultiSelect", "Section Break", "Column Break", "Tab Break", "HTML",
			"Heading", "Button", "Image", "Geolocation", "Barcode", "Color", "Icon", "Rating",
			"Signature", "JSON", "Fold", "Autocomplete", "Long Int", "Code",
		}
		for dirname, payload in self.mains.items():
			for field in payload.get("fields", []):
				self.assertIn(field.get("fieldtype"), valid,
							  "{}.{} fieldtype 非法".format(dirname, field.get("fieldname")))
				if field.get("fieldtype") in ("Link", "Dynamic Link"):
					self.assertTrue(field.get("options"),
									"{}.{} 为 Link 但缺 options".format(dirname, field.get("fieldname")))


class TestR8CStateMachines(unittest.TestCase):
	def test_result_transitions(self):
		t = stb.RESULT_TRANSITIONS
		self.assertEqual(t[stb.RESULT_DRAFT], {stb.RESULT_SUBMITTED, stb.RESULT_VOIDED})
		self.assertEqual(t[stb.RESULT_SUBMITTED],
						 {stb.RESULT_REVIEWED, stb.RESULT_DRAFT, stb.RESULT_VOIDED})
		self.assertEqual(t[stb.RESULT_REVIEWED],
						 {stb.RESULT_APPROVED, stb.RESULT_SUBMITTED, stb.RESULT_VOIDED})
		self.assertEqual(t[stb.RESULT_APPROVED], {stb.RESULT_REVISED, stb.RESULT_VOIDED})
		for terminal in stb.RESULT_TERMINAL_STATES:
			self.assertEqual(t[terminal], set(), "{} 应为终态".format(terminal))

	def test_report_transitions(self):
		t = stb.REPORT_TRANSITIONS
		self.assertEqual(t[stb.REPORT_DRAFT], {stb.REPORT_WAIT_QA, stb.REPORT_VOIDED})
		self.assertEqual(t[stb.REPORT_WAIT_QA], {stb.REPORT_APPROVED, stb.REPORT_REJECTED})
		self.assertEqual(t[stb.REPORT_APPROVED], {stb.REPORT_VOIDED})
		for terminal in stb.REPORT_TERMINAL_STATES:
			self.assertEqual(t[terminal], set(), "{} 应为终态".format(terminal))

	def test_merged_into_workflow_contract(self):
		for flow in (stb.FLOW_STB_RESULT, stb.FLOW_STB_REPORT):
			self.assertIn(flow, wf.FLOW_TRANSITIONS)

	def test_mark_superseded_is_system_triggered(self):
		self.assertIn("mark_superseded", stb.SYSTEM_TRIGGERED_ACTIONS)


class TestScopedActionRoles(unittest.TestCase):
	"""同名动作按 DocType 作用域授权（防 R3 检验流程与 R8C 稳定性结果互相放宽权限）。"""

	def test_colliding_actions_declared_scoped(self):
		for action in ("submit_result", "review_result", "approve_result", "revise_result"):
			self.assertIn(("HBOS Stability Result", action), wf.SCOPED_ACTION_ROLES,
						  "{} 未声明作用域角色".format(action))

	def test_scoped_roles_match_plan_6_3_5(self):
		A, R, QA, QAM, M, SYS = (wf.ROLE_ANALYST, wf.ROLE_REVIEWER, wf.ROLE_LIMS_QA,
								 wf.ROLE_LIMS_QA_MANAGER, wf.ROLE_MANAGER, wf.ROLE_SYSTEM)
		expected = {
			"submit_result": {A, M, SYS},
			"review_result": {R, QA, QAM, M, SYS},
			"approve_result": {QA, QAM, M, SYS},
			"revise_result": {A, M, SYS},
		}
		for action, roles in expected.items():
			self.assertEqual(wf.SCOPED_ACTION_ROLES[("HBOS Stability Result", action)], roles,
							 "{} 作用域角色不符".format(action))

	def test_scope_override_does_not_widen_r3(self):
		"""稳定性结果的角色集不得泄漏到 R3 检验流程（反之亦然）。"""
		self.assertFalse(wf.action_allowed("approve_result", wf.ROLE_REVIEWER,
										   scope="HBOS Stability Result"))
		self.assertTrue(wf.action_allowed("approve_result", wf.ROLE_LIMS_QA,
										  scope="HBOS Stability Result"))
		# 无 scope 时回到全局（R3）口径
		self.assertTrue(wf.action_allowed("approve_result", wf.ROLE_REVIEWER))
		self.assertFalse(wf.action_allowed("approve_result", wf.ROLE_LIMS_QA))

	def test_report_and_new_action_roles(self):
		QA, QAM, M, QP, SYS = (wf.ROLE_LIMS_QA, wf.ROLE_LIMS_QA_MANAGER,
							   wf.ROLE_MANAGER, wf.ROLE_LIMS_QP, wf.ROLE_SYSTEM)
		expected = {
			"record_result": {wf.ROLE_ANALYST, M, SYS},
			"return_result": {wf.ROLE_REVIEWER, QA, QAM, M, SYS},
			"void_result": {QA, QAM, M, SYS},
			"eval_trend": {wf.ROLE_ANALYST, wf.ROLE_REVIEWER, M, SYS},
			"create_stability_report": {wf.ROLE_ANALYST, wf.ROLE_REVIEWER, M, SYS},
			"submit_report": {wf.ROLE_ANALYST, wf.ROLE_REVIEWER, M, SYS},
			"review_report": {wf.ROLE_REVIEWER, QA, QAM, M, SYS},
			"approve_report": {QA, QAM, M, SYS},
			"reject_report": {QA, QAM, M, SYS},
			"void_report": {QP, M, SYS},
		}
		for action, roles in expected.items():
			self.assertEqual(wf.ACTION_ROLES[action], roles, "动作 {} 角色不符".format(action))


class TestBusinessKeys(unittest.TestCase):
	def test_result_version_key(self):
		self.assertEqual(stb.make_result_version_key("TPT-1", "ITEM-A", 1), "TPT-1#ITEM-A#01")
		self.assertEqual(stb.make_result_version_key("TPT-1", "ITEM-A", 12), "TPT-1#ITEM-A#12")

	def test_report_period_key_regular_and_special(self):
		self.assertEqual(
			stb.make_report_period_key("PROD-A", 2026, "年度趋势分析报告"),
			"PROD-A#2026#年度趋势分析报告#-#-")
		self.assertEqual(
			stb.make_report_period_key("PROD-A", 2026, stb.REPORT_TYPE_SPECIAL,
									   "HBOS Stability Protocol", "PRO-1", "CUST-A", 2),
			"PROD-A#2026#专项（客户要求）#HBOS Stability Protocol#PRO-1#CUST-A#02")

	def test_key_parts_reject_hash(self):
		self.assertFalse(stb.check_report_key_parts("PROD#A", None, None)[0])
		self.assertFalse(stb.check_report_key_parts("PROD-A", "PRO#1", None)[0])
		self.assertFalse(stb.check_report_key_parts("PROD-A", None, "CUST#A")[0])
		self.assertTrue(stb.check_report_key_parts("PROD-A", "PRO-1", "CUST-A")[0])

	def test_customer_code_rules(self):
		self.assertTrue(stb.check_customer_code("CUST-A_1")[0])
		self.assertFalse(stb.check_customer_code("客户甲")[0])
		self.assertFalse(stb.check_customer_code("cust-a")[0])       # 必须大写
		self.assertFalse(stb.check_customer_code("CUST#A")[0])
		self.assertFalse(stb.check_customer_code("A" * 41)[0])

	def test_report_scope_mapping(self):
		# 工艺验证类只允许 Protocol 来源
		self.assertTrue(stb.check_report_scope("工艺验证稳定性报告", "HBOS Stability Protocol",
											   None, None, None)[0])
		self.assertFalse(stb.check_report_scope("工艺验证稳定性报告", "HBOS Stability Notice",
												None, None, None)[0])
		# 年度趋势类只允许 Notice
		self.assertTrue(stb.check_report_scope("年度趋势分析报告", "HBOS Stability Notice",
											   None, None, None)[0])
		# APQR 不绑定来源
		self.assertTrue(stb.check_report_scope("APQR 年度稳定性汇总", None, None, None, None)[0])
		# 专项必须带客户与序号
		self.assertFalse(stb.check_report_scope(stb.REPORT_TYPE_SPECIAL, None, None, None, None)[0])
		self.assertFalse(stb.check_report_scope(stb.REPORT_TYPE_SPECIAL, None, "CUST-A",
												"CUST-A", None)[0])
		self.assertTrue(stb.check_report_scope(stb.REPORT_TYPE_SPECIAL, None, "CUST-A",
											   "CUST-A", 1)[0])
		# 非专项不得带客户三字段
		self.assertFalse(stb.check_report_scope("年度趋势分析报告", "HBOS Stability Notice",
												"CUST-A", "CUST-A", 1)[0])


class TestSignificantChange(unittest.TestCase):
	"""方案 7.4 六条规则。"""

	def test_skip_rule(self):
		ok, basis = stb.check_significant_change(stb.SIG_SKIP, 123)
		self.assertFalse(ok)
		self.assertIn("不参与判定", basis)

	def test_missing_value(self):
		ok, basis = stb.check_significant_change(stb.SIG_RELATIVE, None, 100)
		self.assertFalse(ok)
		self.assertIn("缺失", basis)

	def test_relative_change(self):
		ok, basis = stb.check_significant_change(stb.SIG_RELATIVE, 105.3, baseline=100.0,
												 threshold=5)
		self.assertTrue(ok)
		self.assertIn("5.3%", basis)
		self.assertFalse(stb.check_significant_change(stb.SIG_RELATIVE, 103.0,
													  baseline=100.0, threshold=5)[0])
		# 恰好等于阈值 → 显著（≥）
		self.assertTrue(stb.check_significant_change(stb.SIG_RELATIVE, 105.0,
													 baseline=100.0, threshold=5)[0])

	def test_relative_change_zero_baseline_guard(self):
		ok, basis = stb.check_significant_change(stb.SIG_RELATIVE, 5, baseline=0)
		self.assertFalse(ok)
		self.assertIn("除零保护", basis)

	def test_relative_change_non_numeric(self):
		ok, basis = stb.check_significant_change(stb.SIG_RELATIVE, "符合规定", baseline=100,
												 result_type="定性型")
		self.assertFalse(ok)
		self.assertIn("非数值", basis)

	def test_over_limit_uses_judge_engine(self):
		ok, basis = stb.check_significant_change(stb.SIG_OVER_LIMIT, 105.0,
												 limits_type=rc.LIMITS_UP, upper=100.0)
		self.assertTrue(ok)
		self.assertIn("超出规格限度", basis)
		self.assertFalse(stb.check_significant_change(stb.SIG_OVER_LIMIT, 95.0,
													  limits_type=rc.LIMITS_UP, upper=100.0)[0])
		ok, basis = stb.check_significant_change(stb.SIG_OVER_LIMIT, 4.0,
												 limits_type=rc.LIMITS_RANGE, lower=5.0, upper=7.0)
		self.assertTrue(ok)

	def test_qualitative(self):
		self.assertFalse(stb.check_significant_change(stb.SIG_QUALITATIVE, "符合规定")[0])
		ok, basis = stb.check_significant_change(stb.SIG_QUALITATIVE, "不符合规定")
		self.assertTrue(ok)
		self.assertIn("不符标准", basis)


class TestTrendLine(unittest.TestCase):
	def test_perfect_line(self):
		fit = stb.fit_trend_line([(0, 100), (3, 101), (6, 102), (9, 103)])
		self.assertAlmostEqual(fit["slope"], 1 / 3, places=4)
		self.assertAlmostEqual(fit["r2"], 1.0, places=3)
		self.assertEqual(fit["n"], 4)

	def test_insufficient_points(self):
		self.assertIsNone(stb.fit_trend_line([(0, 100)]))
		self.assertIsNone(stb.fit_trend_line([]))
		self.assertIsNone(stb.fit_trend_line(None))

	def test_skips_missing_values(self):
		fit = stb.fit_trend_line([(0, 100), (3, None), (6, 102), (9, "")])
		self.assertEqual(fit["n"], 2)

	def test_no_control_limits_exposed(self):
		"""方案 7.5：不计算统计控制限（口径待 QA 确认前不展示）。"""
		fit = stb.fit_trend_line([(0, 1), (1, 2)])
		self.assertEqual(set(fit.keys()), {"slope", "intercept", "r2", "n"})


class TestValidityAdvice(unittest.TestCase):
	"""方案 7.6 ICH Q1E 外推五分支 + 冷藏特例。"""

	def test_no_data(self):
		months, branch, _ = stb.advise_validity(0)
		self.assertIsNone(months)
		self.assertEqual(branch, "数据不足")

	def test_three_month_significant_change_blocks(self):
		months, branch, _ = stb.advise_validity(12, sig_change_3m=True)
		self.assertIsNone(months)
		self.assertIn("3 月", branch)

	def test_long_term_sufficient(self):
		months, branch, _ = stb.advise_validity(12, long_term_sufficient=True)
		self.assertEqual(months, 24)          # min(2×12, 12+12)
		self.assertIn("长期数据充分", branch)

	def test_long_term_sufficient_refrigerated(self):
		months, branch, _ = stb.advise_validity(12, long_term_sufficient=True, refrigerated=True)
		self.assertEqual(months, 18)          # min(1.5×12, 12+6)
		self.assertIn("冷藏", branch)

	def test_correlated(self):
		months, branch, _ = stb.advise_validity(9, correlated=True)
		self.assertEqual(months, 12)          # min(9+3, 18)
		self.assertIn("相关性", branch)

	def test_six_month_significant_needs_intermediate(self):
		months, branch, _ = stb.advise_validity(12, sig_change_6m=True, intermediate_ok=False)
		self.assertIsNone(months)
		months, branch, _ = stb.advise_validity(12, sig_change_6m=True, intermediate_ok=True)
		self.assertEqual(months, 18)          # min(1.5×12, 12+6)
		self.assertIn("中间条件", branch)

	def test_minor_change_default_branch(self):
		months, branch, _ = stb.advise_validity(6)
		self.assertEqual(months, 9)           # min(1.5×6, 6+6)
		self.assertIn("微小变化", branch)

	def test_prefix_shorter_than_x_plus_n(self):
		"""较短覆盖期：1.5X 分支应小于 X+6（确认取 min 而非固定加数）。"""
		months, _branch, _ = stb.advise_validity(8)
		self.assertEqual(months, 12)          # min(12, 14)


class TestWorkingDays(unittest.TestCase):
	def test_add_working_days_skips_weekend(self):
		# 2026-09-18 是周五 → +5 个工作日 = 09-25（周五）
		self.assertEqual(str(stb.add_working_days("2026-09-18", 5)), "2026-09-25")

	def test_add_working_days_with_holiday(self):
		import datetime
		holidays = {datetime.date(2026, 9, 21)}
		self.assertEqual(str(stb.add_working_days("2026-09-18", 5, holidays)), "2026-09-28")


if __name__ == "__main__":
	unittest.main()
