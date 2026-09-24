# -*- coding: utf-8 -*-
"""M2-R8A 离线契约测试：10 个 DocType JSON 约定 + 稳定性契约 + 动作矩阵覆盖。

覆盖方案 R8A 验收标准的离线部分：
- DocType 存在 / 命名 / 模块 / 控制器 / 唯一键 / 权限（LIMS 角色只读）
- 子表 istable 声明
- FLOW_STB_NOTICE / FLOW_STB_PROTOCOL 状态机（含终态）
- **门禁 10**：6.1 的每一处状态转移都有对应动作、且动作不超出转移表
- 动作角色与方案 6.3.1 / 6.3.2 逐行一致（6 角色列 A/R/QA/QAM/M/QP）
- 契约纯函数：产品编码分隔符安全、分类批次下限、必备条件、多条件复核、冻结快照、版本

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

MASTERS = {
	"hbos_stability_product": "HBOS Stability Product",
	"hbos_stability_condition": "HBOS Stability Condition",
	"hbos_stability_room": "HBOS Stability Room",
	"hbos_stability_test_item": "HBOS Stability Test Item",
	"hbos_stability_notice": "HBOS Stability Notice",
	"hbos_stability_protocol": "HBOS Stability Protocol",
}

CHILDREN = {
	"hbos_stability_test_item_form": "HBOS Stability Test Item Form",
	"hbos_stability_batch": "HBOS Stability Batch",
	"hbos_stability_study_condition": "HBOS Stability Study Condition",
	"hbos_stability_protocol_item": "HBOS Stability Protocol Item",
}

# LIMS 业务角色（DocType 层一律只读，写路径全部走服务方法——方案 8.6）
LIMS_READ_ROLES = ["LIMS Manager", "LIMS Analyst", "LIMS Reviewer", "LIMS QA",
				   "LIMS QA Manager", "LIMS QP"]


def _load(dirname):
	json_path = DOCTYPES / dirname / f"{dirname}.json"
	payload = json.loads(json_path.read_text(encoding="utf-8"))
	payload["_json_path"] = json_path
	return payload


class TestStabilityDoctypeContracts(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.masters = {d: _load(d) for d in MASTERS}
		cls.children = {d: _load(d) for d in CHILDREN}

	def test_doctypes_exist_and_named(self):
		for dirname, expected in {**MASTERS, **CHILDREN}.items():
			payload = self.masters.get(dirname) or self.children[dirname]
			self.assertEqual(payload["name"], expected, dirname)
			self.assertEqual(payload["module"], "HBOS LIMS", dirname)
			self.assertTrue((DOCTYPES / dirname / f"{dirname}.py").exists(),
							"{}.py 控制器缺失".format(dirname))

	def test_master_naming_and_unique_keys(self):
		expected_autoname = {
			"hbos_stability_product": ("field:product_code", "product_code"),
			"hbos_stability_condition": ("field:condition_code", "condition_code"),
			"hbos_stability_room": ("field:room_code", "room_code"),
			"hbos_stability_test_item": ("field:item_code", "item_code"),
		}
		for dirname, (autoname, key) in expected_autoname.items():
			payload = self.masters[dirname]
			self.assertEqual(payload["autoname"], autoname, dirname)
			field = next(f for f in payload["fields"] if f["fieldname"] == key)
			self.assertEqual(field.get("unique"), 1, "{} 唯一键未声明".format(dirname))

	def test_transactional_naming_series(self):
		self.assertEqual(self.masters["hbos_stability_notice"]["autoname"], "naming_series:")
		self.assertEqual(self.masters["hbos_stability_protocol"]["autoname"], "naming_series:")
		notice_series = next(f for f in self.masters["hbos_stability_notice"]["fields"]
							 if f["fieldname"] == "naming_series")
		self.assertEqual(notice_series["options"], stb.NAMING_NOTICE)
		proto_series = next(f for f in self.masters["hbos_stability_protocol"]["fields"]
							if f["fieldname"] == "naming_series")
		self.assertEqual(proto_series["options"], stb.NAMING_PROTOCOL)

	def test_children_are_table(self):
		for dirname in CHILDREN:
			self.assertEqual(self.children[dirname].get("istable"), 1, dirname)

	def test_lims_roles_read_only(self):
		"""8.6：DocType 层 LIMS 角色只读，写路径唯一为业务服务。"""
		for dirname, payload in {**self.masters, **self.children}.items():
			perms = {p["role"]: p for p in payload.get("permissions", [])}
			for role in LIMS_READ_ROLES:
				if dirname in CHILDREN:
					continue  # 子表无独立权限
				self.assertIn(role, perms, "{}/{} 缺权限行".format(dirname, role))
				p = perms[role]
				self.assertEqual(p["read"], 1, "{}/{} 应可读".format(dirname, role))
				self.assertEqual(p["create"], 0, "{}/{} 不应可建".format(dirname, role))
				self.assertEqual(p["write"], 0, "{}/{} 不应可写".format(dirname, role))
				self.assertEqual(p["delete"], 0, "{}/{} 不应可删".format(dirname, role))

	def test_notice_status_options_match_contract(self):
		status_field = next(f for f in self.masters["hbos_stability_notice"]["fields"]
							if f["fieldname"] == "status")
		self.assertEqual(set(status_field["options"].split("\n")),
						 set(stb.NOTICE_TRANSITIONS.keys()))

	def test_protocol_status_options_match_contract(self):
		status_field = next(f for f in self.masters["hbos_stability_protocol"]["fields"]
							if f["fieldname"] == "status")
		self.assertEqual(set(status_field["options"].split("\n")),
						 set(stb.PROTOCOL_TRANSITIONS.keys()))

	def test_room_defers_equipment_link(self):
		"""R8A 不建 strictest_equipment（Equipment 属 R8D），避免 Link 指向不存在的 DocType。"""
		names = [f["fieldname"] for f in self.masters["hbos_stability_room"]["fields"]]
		self.assertNotIn("strictest_equipment", names)

	def test_snapshot_fields_exist_on_doctypes(self):
		"""契约声明的冻结快照字段必须真实存在于对应 DocType。

		曾发生 Protocol 漏建 `snapshot_frozen` 致该单的快照守卫恒不生效（方案 7.7）。
		"""
		for dirname, fields in (
			("hbos_stability_notice", stb.SNAPSHOT_FIELDS_NOTICE),
			("hbos_stability_protocol", stb.SNAPSHOT_FIELDS_PROTOCOL),
		):
			names = {f["fieldname"] for f in self.masters[dirname]["fields"]}
			self.assertIn("snapshot_frozen", names, "{} 缺冻结标记字段".format(dirname))
			for field in fields:
				self.assertIn(field, names, "{} 缺契约声明的快照字段 {}".format(dirname, field))

	def test_naming_series_has_no_hash_placeholder(self):
		"""命名系列不得含 `#`。

		Frappe 的 `set_name_by_naming_series` 会无条件追加 `.#####`
		（frappe/model/naming.py），系列自带 `#` 会生成
		`HBOS-STB-NOT-2026-####00009` 这类畸形单号（R8G 修复）。
		"""
		for dirname in ("hbos_stability_notice", "hbos_stability_protocol"):
			field = next(f for f in self.masters[dirname]["fields"]
						 if f["fieldname"] == "naming_series")
			self.assertNotIn("#", field["options"],
							 "{} 命名系列 {} 不应含 `#`".format(dirname, field["options"]))

	def test_all_fieldtypes_are_valid(self):
		"""字段定义不能出现非法 fieldtype（曾发生 fieldtype/label 写反致非法值落库）。"""
		valid = {
			"Data", "Link", "Dynamic Link", "Select", "Small Text", "Long Text", "Text",
			"Text Editor", "Markdown Editor", "Int", "Float", "Currency", "Percent", "Check",
			"Date", "Datetime", "Time", "Duration", "Password", "Read Only", "Attach",
			"Attach Image", "Table", "Table MultiSelect", "Section Break", "Column Break",
			"Tab Break", "HTML", "Heading", "Button", "Image", "Geolocation", "Barcode",
			"Color", "Icon", "Rating", "Signature", "JSON", "Fold", "Autocomplete",
			"Long Int", "Code",
		}
		for dirname, payload in {**self.masters, **self.children}.items():
			for field in payload.get("fields", []):
				self.assertIn(field.get("fieldtype"), valid,
							  "{}.{} 的 fieldtype 非法：{!r}".format(
								  dirname, field.get("fieldname"), field.get("fieldtype")))
				if field.get("fieldtype") == "Link":
					self.assertTrue(field.get("options"),
									"{}.{} 为 Link 但缺 options".format(dirname, field.get("fieldname")))


class TestStabilityStateMachines(unittest.TestCase):
	def test_notice_transitions(self):
		table = stb.NOTICE_TRANSITIONS
		self.assertEqual(table[stb.NOTICE_DRAFT], {stb.NOTICE_WAIT_QC, stb.NOTICE_CANCELLED})
		self.assertEqual(table[stb.NOTICE_WAIT_QC], {stb.NOTICE_WAIT_APPROVE, stb.NOTICE_REJECTED})
		self.assertEqual(table[stb.NOTICE_WAIT_APPROVE], {stb.NOTICE_APPROVED, stb.NOTICE_REJECTED})
		self.assertEqual(table[stb.NOTICE_APPROVED], {stb.NOTICE_CLOSED})
		for terminal in (stb.NOTICE_REJECTED, stb.NOTICE_CLOSED, stb.NOTICE_CANCELLED):
			self.assertEqual(table[terminal], set(), "{} 应为终态".format(terminal))

	def test_protocol_transitions(self):
		table = stb.PROTOCOL_TRANSITIONS
		self.assertEqual(table[stb.PROTOCOL_DRAFT], {stb.PROTOCOL_WAIT_QA, stb.PROTOCOL_VOIDED})
		self.assertEqual(table[stb.PROTOCOL_WAIT_QA], {stb.PROTOCOL_APPROVED, stb.PROTOCOL_REJECTED})
		self.assertEqual(table[stb.PROTOCOL_APPROVED], {stb.PROTOCOL_VOIDED})
		for terminal in (stb.PROTOCOL_REJECTED, stb.PROTOCOL_VOIDED):
			self.assertEqual(table[terminal], set(), "{} 应为终态".format(terminal))

	def test_yearly_category_has_no_protocol(self):
		self.assertTrue(stb.check_year_long_study_no_protocol("年度持续稳定性考察类"))
		self.assertFalse(stb.check_year_long_study_no_protocol("新产品/工艺验证类"))

	def test_merged_into_workflow_contract(self):
		"""稳定性流程并入 workflow_contract 的统一转移表，且可直接用 can_transition。"""
		self.assertIn(stb.FLOW_STB_NOTICE, wf.FLOW_TRANSITIONS)
		self.assertIn(stb.FLOW_STB_PROTOCOL, wf.FLOW_TRANSITIONS)
		self.assertTrue(wf.can_transition(stb.FLOW_STB_NOTICE, stb.NOTICE_DRAFT, stb.NOTICE_WAIT_QC))
		self.assertFalse(wf.can_transition(stb.FLOW_STB_NOTICE, stb.NOTICE_DRAFT, stb.NOTICE_APPROVED))
		self.assertTrue(wf.can_transition(stb.FLOW_STB_PROTOCOL, stb.PROTOCOL_APPROVED, stb.PROTOCOL_VOIDED))


class TestActionMatrixCoverage(unittest.TestCase):
	"""门禁 10：6.1 每一处转移都有对应动作，且矩阵动作不超出转移表。"""

	def test_every_transition_has_action(self):
		covered = {(flow, src, dst) for _a, flow, src, dst in stb.ACTION_TRANSITIONS}
		for flow in (stb.FLOW_STB_NOTICE, stb.FLOW_STB_PROTOCOL):
			table = stb.STABILITY_FLOW_TRANSITIONS[flow]
			for src, targets in table.items():
				for dst in targets:
					self.assertIn((flow, src, dst), covered,
								  "转移缺动作：{} {} -> {}".format(flow, src, dst))

	def test_no_action_outside_transition_table(self):
		for action, flow, src, dst in stb.ACTION_TRANSITIONS:
			self.assertTrue(wf.can_transition(flow, src, dst),
							"动作 {} 的转移 {} {}->{} 不在状态机内".format(action, flow, src, dst))

	def test_all_actions_registered_with_roles(self):
		names = {a for a, _f, _s, _d in stb.ACTION_TRANSITIONS}
		names |= set(stb.ACTION_ADMISSION_ONLY)
		names |= {"create_notice", "review_protocol", "get_stability_dashboard", "get_stability_notices",
				  "get_stability_notice_detail", "get_stability_master", "get_stability_products",
				  "get_stability_protocols", "get_stability_audit"}
		for name in names:
			self.assertIn(name, wf.ACTION_ROLES, "动作 {} 未注册角色".format(name))
			self.assertTrue(wf.ACTION_ROLES[name], "动作 {} 角色集为空".format(name))

	def test_role_sets_match_plan_6_3(self):
		"""逐行核对方案 6.3.1 / 6.3.2 的角色列。"""
		A, R, QA, QAM, M, QP, SYS = (
			wf.ROLE_ANALYST, wf.ROLE_REVIEWER, wf.ROLE_LIMS_QA,
			wf.ROLE_LIMS_QA_MANAGER, wf.ROLE_MANAGER, wf.ROLE_LIMS_QP, wf.ROLE_SYSTEM)
		expected = {
			# 6.3.1 FLOW_STB_NOTICE
			"register_review": {QA, QAM, M, SYS},
			"submit_notice": {QA, QAM, M, SYS},
			"confirm_notice_qc": {R, M, SYS},
			"approve_notice": {QA, QAM, M, SYS},
			"reject_notice": {R, QA, QAM, M, SYS},
			"cancel_notice": {QA, QAM, M, SYS},
			"close_notice": {QA, QAM, M, SYS},
			# 6.3.2 FLOW_STB_PROTOCOL
			"submit_protocol": {A, R, M, SYS},
			"approve_protocol": {QA, QAM, M, SYS},
			"reject_protocol": {QA, QAM, M, SYS},
			"void_protocol": {QP, M, SYS},
		}
		for action, roles in expected.items():
			self.assertEqual(wf.ACTION_ROLES[action], roles, "动作 {} 角色不符".format(action))

	def test_new_roles_defined(self):
		"""Owner 2026-09-16：新增 LIMS QA Manager 与 LIMS QP，且二者与既有角色不重合。"""
		self.assertEqual(wf.ROLE_LIMS_QA_MANAGER, "LIMS QA Manager")
		self.assertEqual(wf.ROLE_LIMS_QP, "LIMS QP")
		self.assertNotEqual(wf.ROLE_LIMS_QP, wf.ROLE_MANAGER)
		self.assertNotEqual(wf.ROLE_LIMS_QA_MANAGER, wf.ROLE_LIMS_QA)

	def test_void_protocol_requires_qp_or_manager(self):
		"""方案 6.3.2：方案作废限 QP / Manager，不含普通 QA 与 Analyst。"""
		roles = wf.ACTION_ROLES["void_protocol"]
		self.assertIn(wf.ROLE_LIMS_QP, roles)
		self.assertIn(wf.ROLE_MANAGER, roles)
		self.assertNotIn(wf.ROLE_LIMS_QA, roles)
		self.assertNotIn(wf.ROLE_ANALYST, roles)


class TestAuditEventEnums(unittest.TestCase):
	"""方案 8.1：业务埋点的审计事件必须落在 `HBOS Audit Log.log_type` 受控枚举内。"""

	def test_service_log_types_within_enum(self):
		import re

		audit_json = APP_ROOT / "hb_lims_app" / "hbos_lims" / "doctype" / "hbos_audit_log" / "hbos_audit_log.json"
		payload = json.loads(audit_json.read_text(encoding="utf-8"))
		log_type = next(f for f in payload["fields"] if f["fieldname"] == "log_type")
		allowed = set(log_type["options"].split("\n"))

		src = (APP_ROOT / "hb_lims_app" / "hbos_lims" / "stability_service.py").read_text(encoding="utf-8")
		# 首参可以是字面量或常量名（如 SAMPLE_DOCTYPE）
		used = set(re.findall(r'_audit_(?:on|commit)\(\s*[^,]+,\s*"([^"]+)"', src))
		used = {u for u in used if "{" not in u}
		self.assertTrue(used, "未从 stability_service 解析到任何审计事件")
		self.assertEqual(set(), used - allowed,
						 "审计事件未登记进 HBOS Audit Log.log_type 受控枚举：{}".format(sorted(used - allowed)))


class TestStabilityReadInterfaces(unittest.TestCase):
	"""前端接入所需的只读接口已导出并注册角色（静态扫描源码，不导入 Frappe）。"""

	READ_METHODS = [
		"get_stability_dashboard", "get_stability_notices", "get_stability_notice_detail",
		"get_stability_master", "get_stability_products",
		"get_stability_protocols", "get_stability_protocol_detail", "get_stability_audit",
	]

	def test_service_exports_read_methods(self):
		src = (APP_ROOT / "hb_lims_app" / "hbos_lims" / "stability_service.py").read_text(encoding="utf-8")
		for name in self.READ_METHODS:
			self.assertIn("def {}(".format(name), src,
						  "stability_service 缺少只读接口 {}".format(name))

	def test_new_read_actions_registered(self):
		for action in ("get_stability_master", "get_stability_products",
					   "get_stability_protocols", "get_stability_audit"):
			self.assertIn(action, wf.ACTION_ROLES, "只读动作 {} 未注册角色".format(action))
			self.assertTrue(wf.ACTION_ROLES[action])
			self.assertIn(wf.ROLE_ANALYST, wf.ACTION_ROLES[action])


class TestStabilityContractRules(unittest.TestCase):
	def test_product_code_rejects_hash(self):
		ok, err = stb.check_product_code("TEST-STB-TAB-A")
		self.assertTrue(ok, err)
		ok, err = stb.check_product_code("BAD#CODE")
		self.assertFalse(ok)
		self.assertIn("#", err)
		ok, err = stb.check_product_code("")
		self.assertFalse(ok)
		ok, err = stb.check_product_code("X" * 41)
		self.assertFalse(ok)

	def test_batch_count_by_category(self):
		ok, _ = stb.check_batch_count("新产品/工艺验证类", 3)
		self.assertTrue(ok)
		ok, err = stb.check_batch_count("新产品/工艺验证类", 2)
		self.assertFalse(ok)
		self.assertIn("3", err)
		# 变更类 / 年度类 / 其它类 不设 3 批硬下限
		self.assertTrue(stb.check_batch_count("变更类", 1)[0])
		self.assertTrue(stb.check_batch_count("年度持续稳定性考察类", 1)[0])
		self.assertTrue(stb.check_batch_count("其它类", 1)[0])

	def test_required_condition_types(self):
		ok, _ = stb.check_notice_conditions("新产品/工艺验证类",
										   [{"condition_type": "长期"}, {"condition_type": "加速"}])
		self.assertTrue(ok)
		ok, err = stb.check_notice_conditions("新产品/工艺验证类",
											 [{"condition_type": "长期"}])
		self.assertFalse(ok)
		self.assertIn("加速", err)
		ok, err = stb.check_notice_conditions("新产品/工艺验证类", [])
		self.assertFalse(ok)

	def test_multi_condition_review(self):
		# 2 个条件：无需补充原因与复核
		self.assertTrue(stb.check_multi_condition_review(2, "", None)[0])
		# 3 个条件：必须补充原因
		ok, err = stb.check_multi_condition_review(3, "", None)
		self.assertFalse(ok)
		self.assertIn("补充原因", err)
		# 有原因但无复核人
		ok, err = stb.check_multi_condition_review(3, "法规新增条件", None)
		self.assertFalse(ok)
		self.assertIn("注册人员复核", err)
		# 齐备
		self.assertTrue(stb.check_multi_condition_review(3, "法规新增条件", "qa@example.com")[0])

	def test_snapshot_frozen_blocks_change(self):
		before = {"snapshot_frozen": 1, "spec_version": "V1"}
		ok, _err, _f = stb.check_snapshot_frozen(before, {"spec_version": "V1"})
		self.assertTrue(ok)
		ok, err, field = stb.check_snapshot_frozen(before, {"spec_version": "V2"})
		self.assertFalse(ok)
		self.assertEqual(field, "spec_version")
		self.assertIn("冻结", err)

	def test_snapshot_not_frozen_allows_change(self):
		before = {"snapshot_frozen": 0, "spec_version": "V1"}
		self.assertTrue(stb.check_snapshot_frozen(before, {"spec_version": "V2"})[0])
		self.assertTrue(stb.check_snapshot_frozen(None, {"spec_version": "V2"})[0])

	def test_next_version(self):
		self.assertEqual(stb.next_version(None), 1)
		self.assertEqual(stb.next_version(1), 2)

	def test_enumerations_present(self):
		self.assertIn("其它", stb.DOSAGE_FORMS)
		self.assertIn("影响因素-强光", stb.CONDITION_TYPES)
		self.assertIn("年度持续稳定性考察类", stb.CATEGORIES)
		self.assertEqual(stb.UOM_OPTIONS[:3], ["g", "kg", "mg"])
		self.assertEqual(stb.MULTI_CONDITION_THRESHOLD, 2)


if __name__ == "__main__":
	unittest.main()
