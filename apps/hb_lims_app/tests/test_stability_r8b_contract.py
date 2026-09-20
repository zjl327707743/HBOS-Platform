# -*- coding: utf-8 -*-
"""M2-R8B 离线契约测试：样品与时间点（5 DocType + 2 状态机 + 生成/延期算法）。

覆盖方案 R8B 验收标准的离线部分（门禁 5 / 7 / 10 / 12 / 13 / 14 / 18 / 20）：
- 5 个 DocType 的命名/唯一键/子表/权限契约（含「命名系列不含 #」与「不做指向 R8C 的 Link」）
- FLOW_STB_SAMPLE / FLOW_STB_TIMEPOINT / 延期子表状态机
- **门禁 10**：稳定性全部流程的每一处转移都有对应动作、动作不超出转移表
- 时间点生成规则（长期递减、年度按 VD 分档、中间/影响因素）
- 延期上限算法（显式 ROUND_HALF_UP 半值）、日期链全段校验、有效截止日取最新已批准
- **门禁 5 时间边界**：月末（1/31+1月）、闰年（2/29）、影响因素天数
- 0 月免取样豁免判定

本测试不依赖 Frappe，可在宿主机直接运行。
"""

import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import workflow_contract as wf

DOCTYPES = APP_ROOT / "hb_lims_app" / "hbos_lims" / "doctype"

MAINS = {
	"hbos_stability_sample": "HBOS Stability Sample",
	"hbos_stability_timepoint": "HBOS Stability Timepoint",
}

CHILDREN = {
	"hbos_stability_sample_log": "HBOS Stability Sample Log",
	"hbos_stability_timepoint_item": "HBOS Stability Timepoint Item",
	"hbos_stability_timepoint_delay": "HBOS Stability Timepoint Delay",
}

LIMS_READ_ROLES = ["LIMS Manager", "LIMS Analyst", "LIMS Reviewer", "LIMS QA",
				   "LIMS QA Manager", "LIMS QP"]


def _load(dirname):
	return json.loads((DOCTYPES / dirname / (dirname + ".json")).read_text(encoding="utf-8"))


class TestR8BDoctypeContracts(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.mains = {d: _load(d) for d in MAINS}
		cls.children = {d: _load(d) for d in CHILDREN}

	def test_doctypes_exist_and_named(self):
		for dirname, expected in {**MAINS, **CHILDREN}.items():
			payload = self.mains.get(dirname) or self.children[dirname]
			self.assertEqual(payload["name"], expected, dirname)
			self.assertEqual(payload["module"], "HBOS LIMS", dirname)
			self.assertTrue((DOCTYPES / dirname / (dirname + ".py")).exists(),
							"{}.py 控制器缺失".format(dirname))

	def test_naming_series_have_no_hash(self):
		"""命名系列不得含 `#`（Frappe 会无条件追加 `.#####`，见 R8G 修复）。"""
		for dirname, series in (("hbos_stability_sample", stb.NAMING_SAMPLE),
								("hbos_stability_timepoint", stb.NAMING_TIMEPOINT)):
			field = next(f for f in self.mains[dirname]["fields"]
						 if f["fieldname"] == "naming_series")
			self.assertEqual(field["options"], series)
			self.assertNotIn("#", field["options"])

	def test_sample_cond_point_key_unique(self):
		field = next(f for f in self.mains["hbos_stability_timepoint"]["fields"]
					 if f["fieldname"] == "sample_cond_point_key")
		self.assertEqual(field.get("unique"), 1)

	def test_children_are_table(self):
		for dirname in CHILDREN:
			self.assertEqual(self.children[dirname].get("istable"), 1, dirname)

	def test_main_doctypes_lims_roles_read_only(self):
		for dirname, payload in self.mains.items():
			perms = {p["role"]: p for p in payload.get("permissions", [])}
			for role in LIMS_READ_ROLES:
				self.assertIn(role, perms, "{}/{} 缺权限行".format(dirname, role))
				p = perms[role]
				self.assertEqual((p["read"], p["create"], p["write"], p["delete"]), (1, 0, 0, 0),
								 "{}/{} 应只读".format(dirname, role))

	def test_child_tables_have_no_permissions(self):
		"""流水/审批子表属「服务专用写入」（方案 8.6）：不授予任何角色权限。"""
		for dirname, payload in self.children.items():
			self.assertFalse(payload.get("permissions"), "{} 不应有权限行".format(dirname))

	def test_timepoint_item_has_current_result(self):
		"""`current_result` 生效指针（Link → HBOS Stability Result）。

		R8B 时因 Link 目标 DocType 尚未落地而暂缓（避免悬空 Link），R8C 创建 Result 后补建。
		"""
		names = [f["fieldname"] for f in self.children["hbos_stability_timepoint_item"]["fields"]]
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
		for dirname, payload in {**self.mains, **self.children}.items():
			for field in payload.get("fields", []):
				self.assertIn(field.get("fieldtype"), valid,
							  "{}.{} fieldtype 非法".format(dirname, field.get("fieldname")))
				if field.get("fieldtype") == "Link":
					self.assertTrue(field.get("options"),
									"{}.{} 为 Link 但缺 options".format(dirname, field.get("fieldname")))

	def test_sample_has_log_child_table(self):
		names = [f["fieldname"] for f in self.mains["hbos_stability_sample"]["fields"]]
		self.assertIn("logs", names)

	def test_timepoint_has_item_and_delay_tables(self):
		names = [f["fieldname"] for f in self.mains["hbos_stability_timepoint"]["fields"]]
		self.assertIn("test_items", names)
		self.assertIn("delays", names)


class TestR8BStateMachines(unittest.TestCase):
	def test_sample_transitions(self):
		t = stb.SAMPLE_TRANSITIONS
		self.assertEqual(t[stb.SAMPLE_IN_STORAGE],
						 {stb.SAMPLE_IN_STORAGE, stb.SAMPLE_PARTIAL, stb.SAMPLE_DEPLETED,
						  stb.SAMPLE_PENDING_DISPOSAL, stb.SAMPLE_TRANSFERRED})
		self.assertEqual(t[stb.SAMPLE_PARTIAL],
						 {stb.SAMPLE_PARTIAL, stb.SAMPLE_DEPLETED,
						  stb.SAMPLE_PENDING_DISPOSAL, stb.SAMPLE_TRANSFERRED})
		self.assertEqual(t[stb.SAMPLE_DEPLETED], {stb.SAMPLE_PENDING_DISPOSAL, stb.SAMPLE_TRANSFERRED})
		self.assertEqual(t[stb.SAMPLE_PENDING_DISPOSAL],
						 {stb.SAMPLE_DESTROYED, stb.SAMPLE_IN_STORAGE, stb.SAMPLE_PARTIAL,
						  stb.SAMPLE_DEPLETED})
		for terminal in stb.SAMPLE_TERMINAL_STATES:
			self.assertEqual(t[terminal], set(), "{} 应为终态".format(terminal))

	def test_timepoint_transitions(self):
		t = stb.TIMEPOINT_TRANSITIONS
		self.assertEqual(t[stb.TP_WAIT_SAMPLE], {stb.TP_WAIT_TEST, stb.TP_CANCELLED})
		self.assertEqual(t[stb.TP_WAIT_TEST], {stb.TP_TESTING, stb.TP_CANCELLED})
		self.assertEqual(t[stb.TP_TESTING], {stb.TP_DONE, stb.TP_CANCELLED})
		# 「已完成」唯一出口 → 检测中（门禁 20：与终态并存的自相矛盾已消除）
		self.assertEqual(t[stb.TP_DONE], {stb.TP_TESTING})
		self.assertEqual(t[stb.TP_CANCELLED], set())

	def test_delay_transitions(self):
		t = stb.DELAY_TRANSITIONS
		self.assertEqual(t[stb.DELAY_WAIT_APPROVE], {stb.DELAY_APPROVED, stb.DELAY_REJECTED})
		self.assertEqual(t[stb.DELAY_APPROVED], set())
		self.assertEqual(t[stb.DELAY_REJECTED], set())

	def test_merged_into_workflow_contract(self):
		for flow in (stb.FLOW_STB_SAMPLE, stb.FLOW_STB_TIMEPOINT, stb.FLOW_STB_TIMEPOINT_DELAY):
			self.assertIn(flow, wf.FLOW_TRANSITIONS)
		self.assertTrue(wf.can_transition(stb.FLOW_STB_SAMPLE, stb.SAMPLE_IN_STORAGE,
										  stb.SAMPLE_PARTIAL))
		self.assertFalse(wf.can_transition(stb.FLOW_STB_SAMPLE, stb.SAMPLE_DESTROYED,
										   stb.SAMPLE_IN_STORAGE))
		self.assertTrue(wf.can_transition(stb.FLOW_STB_TIMEPOINT, stb.TP_DONE, stb.TP_TESTING))


class TestGate10Coverage(unittest.TestCase):
	"""门禁 10：稳定性**全部**流程的每一处转移都有对应动作，且动作不超出转移表。"""

	def test_every_transition_has_action(self):
		covered = {(flow, src, dst) for _a, flow, src, dst in stb.ACTION_TRANSITIONS}
		for flow, table in stb.STABILITY_FLOW_TRANSITIONS.items():
			for src, targets in table.items():
				for dst in targets:
					self.assertIn((flow, src, dst), covered,
								  "转移缺动作：{} {} -> {}".format(flow, src, dst))

	def test_no_action_outside_transition_table(self):
		for action, flow, src, dst in stb.ACTION_TRANSITIONS:
			self.assertTrue(wf.can_transition(flow, src, dst),
							"动作 {} 的转移 {} {}->{} 不在状态机内".format(action, flow, src, dst))

	def test_all_r8b_actions_registered(self):
		names = {a for a, _f, _s, _d in stb.ACTION_TRANSITIONS}
		names |= set(stb.ACTION_ADMISSION_ONLY)
		for name in names:
			self.assertIn(name, wf.ACTION_ROLES, "动作 {} 未注册角色".format(name))
			self.assertTrue(wf.ACTION_ROLES[name], "动作 {} 角色集为空".format(name))

	def test_system_triggered_actions_registered(self):
		"""门禁 20：系统触发动作角色豁免、但动作名不豁免（仍需登记）。"""
		for name in stb.SYSTEM_TRIGGERED_ACTIONS:
			self.assertIn(name, wf.ACTION_ROLES, "系统动作 {} 未登记".format(name))

	def test_role_sets_match_plan_6_3_3_6_3_4(self):
		A, R, QA, QAM, M, SYS = (wf.ROLE_ANALYST, wf.ROLE_REVIEWER, wf.ROLE_LIMS_QA,
								 wf.ROLE_LIMS_QA_MANAGER, wf.ROLE_MANAGER, wf.ROLE_SYSTEM)
		expected = {
			# 6.3.3 FLOW_STB_SAMPLE
			"register_stability_sample": {A, R, M, SYS},
			"review_sample_storage": {R, QA, M, SYS},
			"record_sampling": {A, M, SYS},
			"return_sample": {A, M, SYS},
			"mark_for_disposal": {R, QA, QAM, M, SYS},
			"cancel_disposal": {R, QA, QAM, M, SYS},
			"dispose_sample": {A, M, SYS},
			# 6.3.4 FLOW_STB_TIMEPOINT
			"generate_timepoints": {A, R, M, SYS},
			"complete_sampling": {A, M, SYS},
			"import_zero_month_result": {A, M, SYS},
			"start_testing": {A, M, SYS},
			"cancel_timepoint": {R, QA, QAM, M, SYS},
			"append_conditions": {R, QAM, M, SYS},
			"apply_delay": {A, M, SYS},
			"approve_delay": {R, QA, QAM, M, SYS},
			"reject_delay": {R, QA, QAM, M, SYS},
			"approve_extra_sampling": {M, SYS},
		}
		for action, roles in expected.items():
			self.assertEqual(wf.ACTION_ROLES[action], roles, "动作 {} 角色不符".format(action))

	def test_adjust_stock_and_transfer_out_shared_with_r7(self):
		"""方案 6.3.3 沿用 R7 同名动作；角色集须一致（Manager + System）。"""
		for action in ("adjust_stock", "transfer_out"):
			self.assertEqual(wf.ACTION_ROLES[action], {wf.ROLE_MANAGER, wf.ROLE_SYSTEM})


class TestTimepointGeneration(unittest.TestCase):
	def test_long_term_series(self):
		self.assertEqual(stb.long_term_months(24), [0, 3, 6, 9, 12, 18, 24])
		self.assertEqual(stb.long_term_months(48), [0, 3, 6, 9, 12, 18, 24, 36, 48])
		# 末点口径：常规序列未落到 VD 上时补上 VD 本身
		self.assertEqual(stb.long_term_months(30), [0, 3, 6, 9, 12, 18, 24, 30])
		self.assertEqual(stb.long_term_months(0), [0])

	def test_yearly_series_by_vd_tier(self):
		self.assertEqual(stb.yearly_study_months(3), [0, 2, 3])       # ⅔效期 ROUND_HALF_UP（3×2/3=2）
		self.assertEqual(stb.yearly_study_months(6), [0, 4, 6])
		self.assertEqual(stb.yearly_study_months(9), [0, 6, 9])
		self.assertEqual(stb.yearly_study_months(12), [0, 6, 12])
		self.assertEqual(stb.yearly_study_months(18), [0, 6, 12, 18])
		self.assertEqual(stb.yearly_study_months(24), [0, 12, 18, 24])
		self.assertEqual(stb.yearly_study_months(36), [0, 12, 24, 36])

	def test_condition_points(self):
		self.assertEqual(stb.condition_points("加速"), [(0, "月"), (3, "月"), (6, "月")])
		self.assertEqual(stb.condition_points("中间"), [(0, "月"), (6, "月"), (9, "月"), (12, "月")])
		self.assertEqual(stb.condition_points("影响因素-高温"),
						 [(0, "天"), (5, "天"), (10, "天"), (30, "天")])
		self.assertEqual(stb.condition_points("影响因素-高湿"), [(5, "天"), (10, "天")])
		self.assertEqual(stb.condition_points("影响因素-强光", 7), [(0, "天"), (7, "天")])

	def test_plan_expands_per_condition_and_marks_full_test(self):
		plan = stb.plan_timepoints("新产品/工艺验证类", 12, [
			{"condition_type": "长期", "condition_code": "LONG"},
			{"condition_type": "加速", "condition_code": "ACC"},
		])
		self.assertEqual(len(plan), len(stb.long_term_months(12)) + 3)
		first = plan[0]
		self.assertEqual((first["value"], first["unit"], first["is_full_test"]), (0, "月", 1))
		self.assertEqual(first["label"], "0月")
		self.assertEqual(first["condition_code"], "LONG")

	def test_zero_month_flag_by_generation(self):
		plan = stb.plan_timepoints("新产品/工艺验证类", 6, [
			{"condition_type": "加速", "condition_code": "ACC"}])
		zero = [p for p in plan if p["unit"] == "月" and p["value"] == 0]
		self.assertEqual(len(zero), 1)


class TestGate5TimeBoundaries(unittest.TestCase):
	"""门禁 5：月末、闰年、影响因素天数、ROUND_HALF_UP 半值。"""

	def test_month_end_overflow(self):
		self.assertEqual(str(stb.add_time_point("2026-01-31", 1, "月")), "2026-02-28")
		self.assertEqual(str(stb.add_time_point("2026-01-31", 3, "月")), "2026-04-30")
		self.assertEqual(str(stb.add_time_point("2026-08-31", 6, "月")), "2027-02-28")

	def test_leap_year(self):
		self.assertEqual(str(stb.add_time_point("2024-02-29", 12, "月")), "2025-02-28")
		self.assertEqual(str(stb.add_time_point("2024-01-31", 1, "月")), "2024-02-29")

	def test_days_unit(self):
		self.assertEqual(str(stb.add_time_point("2026-01-01", 30, "天")), "2026-01-31")

	def test_delay_limit_half_up(self):
		"""影响因素 5 天 × 10% = 0.5 → **1** 天（不得出现 round(0.5)=0）。"""
		self.assertEqual(stb.delay_limit_days(5, "天"), 1)
		self.assertEqual(stb.delay_limit_days(10, "天"), 1)
		self.assertEqual(stb.delay_limit_days(30, "天"), 3)
		self.assertEqual(stb.delay_limit_days(1, "月"), 3)
		self.assertEqual(stb.delay_limit_days(3, "月"), 9)
		self.assertEqual(stb.delay_limit_days(6, "月"), 15)     # 封顶
		self.assertEqual(stb.delay_limit_days(24, "月"), 15)    # 封顶
		self.assertEqual(stb.delay_limit_days(5, "月"), 15)     # 150×10%=15 → 恰好封顶


class TestDelayRules(unittest.TestCase):
	def test_date_chain_apply(self):
		self.assertTrue(stb.check_delay_apply("2026-03-16", "2026-03-20", "2026-03-25")[0])
		# 早于计划日 → 拒
		self.assertFalse(stb.check_delay_apply("2026-03-16", "2026-03-15", "2026-03-25")[0])
		# 超出政策上限 → 拒
		self.assertFalse(stb.check_delay_apply("2026-03-16", "2026-03-26", "2026-03-25")[0])
		# 恰好落在上限 → 允许（区间闭端点）
		self.assertTrue(stb.check_delay_apply("2026-03-16", "2026-03-25", "2026-03-25")[0])

	def test_date_chain_approve(self):
		self.assertTrue(stb.check_delay_approve("2026-03-16", "2026-03-20", "2026-03-22",
												"2026-03-25")[0])
		# 批准早于申请日 → 拒
		self.assertFalse(stb.check_delay_approve("2026-03-16", "2026-03-20", "2026-03-19",
												 "2026-03-25")[0])
		# 批准突破政策上限 → 拒
		self.assertFalse(stb.check_delay_approve("2026-03-16", "2026-03-20", "2026-03-30",
												 "2026-03-25")[0])

	def test_effective_due_takes_latest_approved(self):
		delays = [
			{"delay_type": "取样延期", "status": "已批准",
			 "approve_at": "2026-03-10 09:00:00", "approved_due_date": "2026-03-20"},
			{"delay_type": "取样延期", "status": "已批准",
			 "approve_at": "2026-03-12 08:00:00", "approved_due_date": "2026-03-25"},
			{"delay_type": "检测延期", "status": "已批准",
			 "approve_at": "2026-03-13 08:00:00", "approved_due_date": "2026-04-30"},
			{"delay_type": "取样延期", "status": "已驳回",
			 "approve_at": "2026-03-14 08:00:00", "approved_due_date": "2026-03-28"},
		]
		self.assertEqual(str(stb.effective_due_date(delays, "取样延期", "2026-03-18")), "2026-03-25")
		self.assertEqual(str(stb.effective_due_date(delays, "检测延期", "2026-04-20")), "2026-04-30")
		# 无已批准行 → 回退政策上限
		self.assertEqual(str(stb.effective_due_date([], "取样延期", "2026-03-18")), "2026-03-18")

	def test_approve_not_backwards(self):
		self.assertTrue(stb.check_approve_not_backwards("2026-03-20", "2026-03-10 09:00:00",
														"2026-03-25", "2026-03-12 09:00:00")[0])
		self.assertFalse(stb.check_approve_not_backwards("2026-03-25", "2026-03-12 09:00:00",
														 "2026-03-22", "2026-03-13 09:00:00")[0])
		self.assertFalse(stb.check_approve_not_backwards("2026-03-20", "2026-03-12 09:00:00",
														 "2026-03-25", "2026-03-11 09:00:00")[0])

	def test_sampling_not_late(self):
		self.assertTrue(stb.check_sampling_not_late("2026-03-20", "2026-03-22", "2026-03-25")[0])
		self.assertFalse(stb.check_sampling_not_late("2026-03-26", "2026-03-22", "2026-03-25")[0])

	def test_policy_latest(self):
		# 取样：planned + delay_limit
		self.assertEqual(str(stb.policy_latest_due("2026-03-16", "取样延期", delay_limit=9)),
						 "2026-03-25")
		# 检测：planned + 30 天
		self.assertEqual(str(stb.policy_latest_due("2026-03-16", "检测延期")), "2026-04-15")
		# 委外窗口留空 = 不限制（返回 None）
		self.assertIsNone(stb.policy_latest_due("2026-03-16", "检测延期",
												outsourced_test_window_days=""))


class TestZeroMonthAndTestDates(unittest.TestCase):
	def test_zero_month_exempt(self):
		self.assertTrue(stb.zero_month_exempt(1, "出厂全检"))
		self.assertTrue(stb.zero_month_exempt(1, "委外"))
		self.assertFalse(stb.zero_month_exempt(1, "自检"))
		self.assertFalse(stb.zero_month_exempt(0, "出厂全检"))

	def test_test_dates_normal(self):
		# 正常：实际检测 ≥ 计划 ≥ 实际取样，且未超上限
		self.assertTrue(stb.check_test_dates("2026-03-20", "2026-03-16", "2026-03-16",
											 "2026-04-15", "2026-04-15")[0])
		# 早于计划检测日 → 拒
		self.assertFalse(stb.check_test_dates("2026-03-15", "2026-03-16", "2026-03-16",
											  "2026-04-15", "2026-04-15")[0])
		# 早于实际取样日 → 拒
		self.assertFalse(stb.check_test_dates("2026-03-17", "2026-03-18", "2026-03-16",
											  "2026-04-15", "2026-04-15")[0])
		# 超过政策硬上限 → 拒
		self.assertFalse(stb.check_test_dates("2026-04-16", "2026-03-16", "2026-03-16",
											  "2026-04-15", "2026-04-15")[0])

	def test_test_dates_zero_month_exemption(self):
		"""0 月点豁免 #1/#2（出厂检验日期早于进箱日是正常的）。"""
		self.assertTrue(stb.check_test_dates("2026-03-01", None, "2026-03-16",
											 "2026-04-15", "2026-04-15",
											 exempt_zero_month=True)[0])
		self.assertFalse(stb.check_test_dates("2026-03-01", None, "2026-03-16",
											  "2026-04-15", "2026-04-15",
											  exempt_zero_month=False)[0])


class TestSampleCondPointKey(unittest.TestCase):
	def test_key_format(self):
		self.assertEqual(stb.make_sample_cond_point_key("SMP-1", "LONG", 3, "月"),
						 "SMP-1#LONG#3月")
		self.assertEqual(stb.make_sample_cond_point_key("SMP-1", "HOT", 5, "天"),
						 "SMP-1#HOT#5天")


class TestR8BAuditEvents(unittest.TestCase):
	def test_new_events_registered_in_enum(self):
		payload = json.loads(
			(DOCTYPES / "hbos_audit_log" / "hbos_audit_log.json").read_text(encoding="utf-8"))
		field = next(f for f in payload["fields"] if f["fieldname"] == "log_type")
		allowed = set(field["options"].split("\n"))
		for event in ("入箱登记", "超期进箱评估", "储存复核", "样品进入待处置",
					  "待处置取消（回库）", "取样出库", "返还", "时间点生成",
					  "时间点生成失败", "0 月数据豁免校验", "追加条件/时间点",
					  "检测开始", "检测完成", "时间点取消", "时间点重开",
					  "超方案取样批准", "取样延期申请", "取样延期批准", "取样延期驳回",
					  "检测延期申请", "检测延期批准", "检测延期驳回"):
			self.assertIn(event, allowed, "审计事件 {} 未登记进受控枚举".format(event))

	def test_service_log_types_within_enum(self):
		"""服务埋点的 log_type 必须落在受控枚举内（首参可为字面量或常量名）。"""
		import re
		payload = json.loads(
			(DOCTYPES / "hbos_audit_log" / "hbos_audit_log.json").read_text(encoding="utf-8"))
		field = next(f for f in payload["fields"] if f["fieldname"] == "log_type")
		allowed = set(field["options"].split("\n"))
		src = (APP_ROOT / "hb_lims_app" / "hbos_lims" / "stability_service.py").read_text(encoding="utf-8")
		lits = set(re.findall(r'_audit_(?:on|commit)\(\s*[^,]+,\s*"([^"]+)"', src))
		self.assertGreater(len(lits), 20, "解析到的埋点事件过少，正则可能失效")
		cand = set()
		for l in lits:
			if l == "{}申请":
				cand.update({"取样延期申请", "检测延期申请"})
			elif l == "{}批准":
				cand.update({"取样延期批准", "检测延期批准"})
			elif l == "{}驳回":
				cand.update({"取样延期驳回", "检测延期驳回"})
			elif "{" not in l:
				cand.add(l)
		self.assertEqual(set(), cand - allowed,
						 "审计事件未登记进受控枚举：{}".format(sorted(cand - allowed)))

	def test_r8h_read_interfaces_exported(self):
		"""R8H 前端接入所需的补充只读接口已导出并注册角色。"""
		src = (APP_ROOT / "hb_lims_app" / "hbos_lims" / "stability_service.py").read_text(encoding="utf-8")
		for name in ("get_stability_samples", "get_stability_sample_detail",
					 "get_stability_schedule", "get_stability_timepoint_detail",
					 "get_stability_delays"):
			self.assertIn("def {}(".format(name), src, "缺只读接口 {}".format(name))
		self.assertIn("get_stability_delays", wf.ACTION_ROLES)
		self.assertTrue(wf.ACTION_ROLES["get_stability_delays"])

	def test_schedule_rows_expose_three_layer_dates(self):
		"""计划台账需要三层日期与延期状态：schedule 的投影代码须包含这些键。"""
		src = (APP_ROOT / "hb_lims_app" / "hbos_lims" / "stability_service.py").read_text(encoding="utf-8")
		for key in ("policy_latest_sample_due", "policy_latest_test_due", "delay_state"):
			self.assertIn(key, src, "schedule 缺 {}".format(key))


if __name__ == "__main__":
	unittest.main()
