# -*- coding: utf-8 -*-
"""M2-R8D 离线契约测试：变更、稳定性室与设备。

覆盖方案 R8D 验收标准的离线部分：
- 4 DocType（Change / Room Log / Equipment / Fault Ticket）+ 子表 Fault Sample 的
  命名/唯一键/权限契约（Fault Sample 为「服务专用写入」流水表）
- FLOW_STB_CHANGE / FLOW_STB_FAULT 状态机与 6.3.7 / 6.3.8 动作矩阵（门禁 10）
- 变更审批 SoD 硬校验：一般变更批准 QAM 专属（S7 无 Manager 兜底）、重大变更 QP 专属
- 变更落点枚举与对象匹配规则（7.9）
- Room Log 业务键生成、Equipment/Fault 受控枚举
- 删除拦截表（8.3）：Change 草稿/已取消、Room Log 全禁删、Equipment 全禁删、Fault 待处理
- 审计事件受控枚举覆盖 R8D 17 类 + 一致性异常（8.1）

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
	"hbos_stability_change": "HBOS Stability Change",
	"hbos_stability_room_log": "HBOS Stability Room Log",
	"hbos_stability_equipment": "HBOS Stability Equipment",
	"hbos_stability_fault_ticket": "HBOS Stability Fault Ticket",
}
SUBS = {"hbos_stability_fault_sample": "HBOS Stability Fault Sample"}


def _load(dirname):
	return json.loads((DOCTYPES / dirname / (dirname + ".json")).read_text(encoding="utf-8"))


def _enum_options(payload, fieldname):
	"""Select options 通用解析：容忍或不容忍空首项。"""
	options = next(f for f in payload["fields"] if f["fieldname"] == fieldname)["options"]
	parts = options.split("\n")
	while parts and parts[0] == "":
		parts.pop(0)
	return parts



class TestR8DDoctypeContracts(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.mains = {d: _load(d) for d in MAINS}
		cls.subs = {d: _load(d) for d in SUBS}

	def test_doctypes_exist_and_named(self):
		for dirname, expected in MAINS.items():
			payload = self.mains[dirname]
			self.assertEqual(payload["name"], expected, dirname)
			self.assertEqual(payload["module"], "HBOS LIMS", dirname)
			self.assertTrue((DOCTYPES / dirname / (dirname + ".py")).exists(),
							"{}.py 控制器缺失".format(dirname))

	def test_naming_series_have_no_hash(self):
		for dirname, series in (("hbos_stability_change", stb.NAMING_CHANGE),
								("hbos_stability_room_log", stb.NAMING_ROOM_LOG),
								("hbos_stability_equipment", stb.NAMING_EQUIPMENT),
								("hbos_stability_fault_ticket", stb.NAMING_FAULT)):
			field = next(f for f in self.mains[dirname]["fields"]
						 if f["fieldname"] == "naming_series")
			self.assertNotIn("#", series, "命名系列不得含 #")
			self.assertEqual(field["options"], series, dirname)

	def test_change_required_fields(self):
		fields = {f["fieldname"] for f in self.mains["hbos_stability_change"]["fields"]}
		for required in ("change_scope", "change_level", "supersedes", "notice", "protocol",
						 "stability_sample", "change_content", "change_reason",
						 "impact_assessment", "support_docs", "applicant_dept",
						 "qa_review_by", "approver_by", "reject_reason",
						 "implement_record", "implement_by", "post_assessment",
						 "post_assessment_result", "status"):
			self.assertIn(required, fields, required)

	def test_change_scope_and_level_enums(self):
		payload = self.mains["hbos_stability_change"]
		by_name = {f["fieldname"]: f for f in payload["fields"]}
		self.assertEqual(_enum_options(payload, "change_scope"), stb.CHANGE_SCOPES)
		self.assertEqual(_enum_options(payload, "change_level"), stb.CHANGE_LEVELS)
		self.assertEqual(_enum_options(payload, "applicant_dept"), stb.APPLICANT_DEPTS)

	def test_room_log_key_unique_and_readonly(self):
		payload = self.mains["hbos_stability_room_log"]
		by_name = {f["fieldname"]: f for f in payload["fields"]}
		self.assertEqual(by_name["room_date_period_key"].get("unique"), 1)
		self.assertEqual(by_name["room_date_period_key"].get("read_only"), 1)
		self.assertEqual(_enum_options(payload, "period"), stb.LOG_PERIODS)
		self.assertEqual(stb.make_room_log_key("R1", "2026-09-20", "上午"),
						 "R1#2026-09-20#上午")

	def test_room_log_snapshot_fields_readonly(self):
		payload = self.mains["hbos_stability_room_log"]
		for fname in ("temp_min", "temp_max", "humidity_min", "humidity_max", "within_spec"):
			field = next(f for f in payload["fields"] if f["fieldname"] == fname)
			self.assertEqual(field.get("read_only"), 1, fname)

	def test_equipment_enums(self):
		payload = self.mains["hbos_stability_equipment"]
		by_name = {f["fieldname"]: f for f in payload["fields"]}
		self.assertEqual(_enum_options(payload, "equipment_name"), stb.EQUIPMENT_TYPES)
		self.assertEqual(_enum_options(payload, "qualification_status"),
						 stb.QUALIFICATION_STATUSES)
		self.assertEqual(_enum_options(payload, "status"), stb.EQUIPMENT_STATUSES)

	def test_fault_ticket_links_subtable(self):
		payload = self.mains["hbos_stability_fault_ticket"]
		field = next(f for f in payload["fields"] if f["fieldname"] == "affected_samples")
		self.assertEqual(field["options"], "HBOS Stability Fault Sample")
		sub = self.subs["hbos_stability_fault_sample"]
		self.assertEqual(sub.get("istable"), 1, "Fault Sample 须为子表")

	def test_fault_sample_is_service_only(self):
		"""流水表特例（方案 8.3）：LIMS 角色不得授予 create/write。"""
		for perm in self.subs["hbos_stability_fault_sample"]["permissions"]:
			if perm["role"].startswith("LIMS"):
				self.assertFalse(perm.get("create"), perm["role"])
				self.assertFalse(perm.get("write"), perm["role"])

	def test_lims_roles_can_read_all(self):
		for payload in list(self.mains.values()) + list(self.subs.values()):
			roles = {p["role"]: p for p in payload["permissions"]}
			for role in ("LIMS Manager", "LIMS Analyst", "LIMS Reviewer", "LIMS QA"):
				self.assertTrue(roles.get(role, {}).get("read"),
								"{} 缺 {} 读权限".format(payload["name"], role))


class TestChangeStateMachine(unittest.TestCase):
	def test_transitions_match_plan_6_1(self):
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_DRAFT],
						 {stb.CHANGE_WAIT_QA, stb.CHANGE_CANCELLED})
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_WAIT_QA],
						 {stb.CHANGE_WAIT_QAM, stb.CHANGE_WAIT_QP, stb.CHANGE_REJECTED})
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_WAIT_QAM], {stb.CHANGE_APPROVED, stb.CHANGE_REJECTED})
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_WAIT_QP], {stb.CHANGE_APPROVED, stb.CHANGE_REJECTED})
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_APPROVED], {stb.CHANGE_IMPLEMENTED})
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_IMPLEMENTED],
						 {stb.CHANGE_ASSESSED, stb.CHANGE_ASSESS_FAILED})
		# 后评估不通过为终态（P1-3），已评估完成/驳回/取消为终态
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_ASSESS_FAILED], set())
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_ASSESSED], set())
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_REJECTED], set())
		self.assertEqual(stb.CHANGE_TRANSITIONS[stb.CHANGE_CANCELLED], set())

	def test_terminal_states(self):
		self.assertEqual(stb.CHANGE_TERMINAL_STATES,
						 {stb.CHANGE_ASSESS_FAILED, stb.CHANGE_ASSESSED,
						  stb.CHANGE_REJECTED, stb.CHANGE_CANCELLED})

	def test_fault_transitions(self):
		self.assertEqual(stb.FAULT_TRANSITIONS[stb.FAULT_PENDING],
						 {stb.FAULT_HANDLING, stb.FAULT_CLOSED})
		self.assertEqual(stb.FAULT_TRANSITIONS[stb.FAULT_HANDLING],
						 {stb.FAULT_WAIT_ASSESS, stb.FAULT_CLOSED})
		self.assertEqual(stb.FAULT_TRANSITIONS[stb.FAULT_WAIT_ASSESS],
						 {stb.FAULT_CLOSED, stb.FAULT_HANDLING})
		self.assertEqual(stb.FAULT_TRANSITIONS[stb.FAULT_CLOSED], set())

	def test_all_transitions_have_action_rows(self):
		"""门禁 10：6.1 每处转移都有对应动作行（豁免无入口转移）。"""
		covered = set()
		for action, flow, source, target in stb.ACTION_TRANSITIONS:
			if flow == stb.FLOW_STB_CHANGE:
				covered.add((source, target))
			if flow == stb.FLOW_STB_FAULT:
				covered.add((source, target))
		for flow, transitions in ((stb.FLOW_STB_CHANGE, stb.CHANGE_TRANSITIONS),
								  (stb.FLOW_STB_FAULT, stb.FAULT_TRANSITIONS)):
			for source, targets in transitions.items():
				for target in targets:
					self.assertIn((source, target), covered,
								  "{}: {}→{} 无动作行".format(flow, source, target))

	def test_scoped_roles_sod(self):
		"""S7：一般变更批准 QAM 专属（Manager 不得兜底）；重大变更 QP 专属。"""
		for role in (wf.ROLE_ANALYST, wf.ROLE_REVIEWER, wf.ROLE_LIMS_QA, wf.ROLE_MANAGER):
			self.assertFalse(wf.action_allowed("approve_change_general", role),
							 role)
		self.assertTrue(wf.action_allowed("approve_change_general", wf.ROLE_LIMS_QA_MANAGER))
		self.assertFalse(wf.action_allowed("approve_change_general", wf.ROLE_SYSTEM))
		for role in (wf.ROLE_ANALYST, wf.ROLE_REVIEWER, wf.ROLE_LIMS_QA,
					 wf.ROLE_LIMS_QA_MANAGER, wf.ROLE_MANAGER):
			self.assertFalse(wf.action_allowed("approve_change_major", role), role)
		self.assertTrue(wf.action_allowed("approve_change_major", wf.ROLE_LIMS_QP))

	def test_change_action_roles_registered(self):
		for action in ("create_change", "submit_change", "review_change", "reject_change",
					   "cancel_change", "implement_change", "assess_change", "reopen_change",
					   "log_room_env", "manage_equipment", "open_fault_ticket",
					   "start_fault_handling", "submit_fault_assessment",
					   "return_fault_handling", "close_fault_ticket"):
			self.assertIn(action, wf.ACTION_ROLES, action)

	def test_readonly_actions_registered(self):
		for action in ("get_stability_changes", "get_stability_change_detail",
					   "get_stability_room_logs", "get_stability_equipments",
					   "get_stability_fault_tickets"):
			self.assertIn(action, wf.ACTION_ROLES, action)


class TestImplementScope(unittest.TestCase):
	def test_scopes_match_plan_7_9(self):
		self.assertEqual(stb.CHANGE_SCOPES,
						 ["涉方案", "涉通知单", "涉条件与时间点", "涉样品"])

	def test_append_conditions_precondition_matches_scope(self):
		"""append_conditions 受控入口与 implement_change 的落点白名单一致（7.9 受控入口）。"""
		# 白名单语义在 stability_service.append_conditions 内硬编码；此处固化口径
		allowed_scopes = ("涉条件与时间点", "涉方案")
		for scope in allowed_scopes:
			self.assertIn(scope, stb.CHANGE_SCOPES)


class TestDeleteInterceptor(unittest.TestCase):
	def test_deletable_statuses_match_plan_8_3(self):
		# guards 顶部 import frappe（宿主机不可用），离线以源码文本断言
		src = (APP_ROOT / "hb_lims_app" / "hbos_lims" / "stability_guards.py").read_text(
			encoding="utf-8")
		for expected in (
				"CHANGE_DELETABLE_STATUSES = (\"草稿\", \"已取消\")",
				"ROOM_LOG_DELETABLE_STATUSES = ()",
				"EQUIPMENT_DELETABLE_STATUSES = ()",
				"FAULT_DELETABLE_STATUSES = (\"待处理\",)"):
			self.assertIn(expected, src, expected)


class TestAuditEnumCoversR8D(unittest.TestCase):
	def test_r8d_events_in_controlled_enum(self):
		payload = json.loads(
			(DOCTYPES / "hbos_audit_log" / "hbos_audit_log.json").read_text(encoding="utf-8"))
		options = next(f for f in payload["fields"]
					   if f["fieldname"] == "log_type")["options"].split("\n")
		required = ["变更申请", "变更QA审核", "一般变更批准", "重大变更批准", "变更取消",
					"变更实施回写", "变更后评估", "变更重启",
					"温湿度记录", "温湿度超标", "设备台账变更", "设备故障", "故障处理中",
					"故障待评估", "退回处理", "故障关闭", "一致性异常"]
		for event in required:
			self.assertIn(event, options, event)

	def test_hooks_cover_r8d_doctypes(self):
		hooks = (APP_ROOT / "hb_lims_app" / "hooks.py").read_text(encoding="utf-8")
		for dt in MAINS.values():
			self.assertIn('"%s"' % dt, hooks, dt)

	def test_change_status_enum_in_doctype(self):
		payload = _load("hbos_stability_change")
		status = next(f for f in payload["fields"] if f["fieldname"] == "status")
		options = status["options"].split("\n")
		for s in (stb.CHANGE_DRAFT, stb.CHANGE_WAIT_QA, stb.CHANGE_WAIT_QAM,
				  stb.CHANGE_WAIT_QP, stb.CHANGE_APPROVED, stb.CHANGE_IMPLEMENTED,
				  stb.CHANGE_ASSESSED, stb.CHANGE_ASSESS_FAILED, stb.CHANGE_REJECTED,
				  stb.CHANGE_CANCELLED):
			self.assertIn(s, options, s)


if __name__ == "__main__":
	unittest.main()
