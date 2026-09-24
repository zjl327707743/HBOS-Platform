# -*- coding: utf-8 -*-
"""M2-R8J 修复后离线契约测试。

本测试不依赖 Frappe 实例，锁定本轮审查发现的安全边界、库存流水、日期政策
以及前后端接口契约，避免后续重构时缺陷回归。
"""

import ast
import json
import unittest
from pathlib import Path

from hb_lims_app.hbos_lims import stability_contract as stb


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "hb_lims_app" / "hbos_lims" / "stability_service.py"
GUARDS = ROOT / "hb_lims_app" / "hbos_lims" / "stability_guards.py"
LIMS_SERVICE = ROOT / "hb_lims_app" / "hbos_lims" / "lims_service.py"
SAMPLE_DOCTYPE = ROOT / "hb_lims_app" / "hbos_lims" / "doctype" / "hbos_sample" / "hbos_sample.json"
STABILITY_RESULT_DOCTYPE = ROOT / "hb_lims_app" / "hbos_lims" / "doctype" / "hbos_stability_result" / "hbos_stability_result.json"
API = ROOT.parent.parent / "frontend" / "hbos-lims-web" / "src" / "api" / "stability.ts"
LIMS_API = ROOT.parent.parent / "frontend" / "hbos-lims-web" / "src" / "api" / "lims.ts"
SAMPLE_VIEW = ROOT.parent.parent / "frontend" / "hbos-lims-web" / "src" / "views" / "SampleView.vue"
OPS = ROOT.parent.parent / "frontend" / "hbos-lims-web" / "src" / "views" / "StabilityOpsView.vue"
RESULT_VIEW = ROOT.parent.parent / "frontend" / "hbos-lims-web" / "src" / "views" / "StabilityResultView.vue"
STABILITY_SCSS = ROOT.parent.parent / "frontend" / "hbos-lims-web" / "src" / "styles" / "stability.scss"


def _source(path):
	return path.read_text(encoding="utf-8")


def _json(path):
	return json.loads(_source(path))


class TestR8JBackendContracts(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.service = _source(SERVICE)
		cls.guards = _source(GUARDS)
		cls.lims_service = _source(LIMS_SERVICE)
		cls.api = _source(API)
		cls.sample_view = _source(SAMPLE_VIEW)
		cls.lims_api = _source(LIMS_API)

	def test_python_sources_parse(self):
		ast.parse(self.service, filename=str(SERVICE))
		ast.parse(self.guards, filename=str(GUARDS))

	def test_new_insert_system_fields_are_guarded(self):
		self.assertIn("if not before:", self.guards)
		self.assertIn("禁止通过直接新建写入", self.guards)
		self.assertIn("meta.get_field(field)", self.guards)
		# 合法服务建档必须显式声明系统字段写入授权。
		for marker in (
			"doc.flags.allow_system_fields = True\n\t\tdoc.insert(ignore_permissions=True)",
			"doc.flags.allow_system_fields = True\n\t\tnew.insert(ignore_permissions=True)",
		):
			self.assertIn(marker.split("\n")[0], self.service)

	def test_sample_registration_checks_notice_protocol_product_chain(self):
		for marker in (
			"notice_doc.stability_product != stability_product",
			"protocol_doc.notice != notice",
			"protocol_product != stability_product",
		):
			self.assertIn(marker, self.service)

	def test_transfer_out_writes_negative_remaining_quantity(self):
		self.assertIn('"受托转出", qty_delta=-remaining, remaining_qty=0', self.service)

	def test_actual_sampling_date_uses_one_policy_guard(self):
		self.assertIn("def _validate_actual_sample_date", self.service)
		self.assertGreaterEqual(self.service.count("_validate_actual_sample_date("), 3)
		self.assertIn("实际取样日期（{}）晚于计划日期（{}）", self.service)
		self.assertIn("policy", self.service[self.service.index("def _validate_actual_sample_date"):])

	def test_schedule_filters_before_paging_and_projects_test_items(self):
		block = self.service[self.service.index("def get_stability_schedule"):self.service.index("def _enrich_schedule")]
		self.assertIn('filters["plan_sample_date"] = ["like", month_key[:7] + "%"]', block)
		self.assertIn('"HBOS Stability Timepoint Item"', block)
		self.assertIn('row["test_items"] = item_map.get(row["name"], [])', block)

	def test_trend_projection_matches_frontend_contract(self):
		block = self.service[self.service.index("def get_stability_trend"):self.service.index("def _to_float")]
		for marker in ('"timepoint"', '"result_value"', '"status"', '"is_current"'):
			self.assertIn(marker, block)

	def test_change_sod_and_extra_conditions_are_server_enforced(self):
		for marker in (
			"变更 QA 审核人不得为申请人",
			"变更批准人不得为申请人",
			"变更批准人不得为 QA 审核人",
			"def _normalize_change_conditions",
			"extra_conditions=None",
			"study_conditions = [r.as_dict() for r in (old.study_conditions or [])]",
		):
			self.assertIn(marker, self.service)

	def test_stability_source_alias_and_binding_contract(self):
		self.assertEqual(stb.normalize_sample_source("稳定性取样"), "稳定性")
		self.assertTrue(stb.is_stability_sample_source("稳定性"))
		self.assertEqual(stb.validate_stability_binding("稳定性", None)[0], False)
		self.assertEqual(stb.validate_stability_binding("稳定性", "TP-001")[0], True)
		self.assertEqual(stb.validate_stability_binding("生产取样", "TP-001")[0], False)

	def test_business_sample_and_stability_result_have_explicit_links(self):
		sample_fields = {field["fieldname"]: field for field in _json(SAMPLE_DOCTYPE)["fields"]}
		result_fields = {field["fieldname"]: field for field in _json(STABILITY_RESULT_DOCTYPE)["fields"]}
		self.assertEqual(sample_fields["stability_timepoint"]["options"], "HBOS Stability Timepoint")
		self.assertEqual(result_fields["source_test_result"]["options"], "HBOS Test Result")
		self.assertEqual(result_fields["source_test_result"].get("read_only"), 1)
		self.assertEqual(result_fields["source_test_result"].get("unique"), 1)

	def test_standard_result_flow_calls_stability_projection_sync(self):
		self.assertIn("stability_timepoint", self.lims_service)
		self.assertGreaterEqual(self.lims_service.count("sync_standard_test_result"), 4)
		self.assertIn("source_test_result", self.service)
		self.assertIn("sync_standard_test_result", self.service)

	def test_sync_preflight_protects_scope_sod_and_cancelled_timepoints(self):
		for marker in (
			"def validate_standard_test_result_sync",
			"_SYNCABLE_TIMEPOINT_STATES",
			"scope=RESULT_DOCTYPE",
			"standard.reviewer == approver",
			"audit=False",
		):
			self.assertIn(marker, self.service, marker)
		# 稳定性批准前置校验必须发生在业务结果落库前。
		preflight = self.lims_service.index(
			'validate_standard_test_result_sync(result.name, target_status="已批准"')
		write = self.lims_service.index('result.result_status = "已批准"')
		self.assertLess(preflight, write)

	def test_revision_approval_reloads_superseded_projection(self):
		approval = self.service[self.service.index("elif target == stb.RESULT_APPROVED:"):]
		self.assertIn("mark_superseded(old.name)", approval)
		self.assertIn("old = _load(RESULT_DOCTYPE, old.name)", approval)

	def test_stability_master_mapping_has_manager_write_path(self):
		for marker in (
			"def update_stability_test_item_mapping",
			'_check_action("manage_stability_master"',
			'"base_test_item"',
			"updateStabilityTestItemMapping",
		):
			combined = self.service + self.api + self.sample_view
			self.assertIn(marker, combined, marker)

	def test_manual_result_guard_is_project_granular(self):
		for marker in (
			"def _business_stability_items_for_timepoint",
			"stability_test_item in covered_items",
			"业务检验样品已覆盖项目",
		):
			self.assertIn(marker, self.service, marker)

	def test_stability_sample_binding_locks_timepoint_before_duplicate_check(self):
		block = self.lims_service[
			self.lims_service.index("def _validate_stability_sample_binding"):
			self.lims_service.index("\n\n@frappe.whitelist()\ndef register_sample")
		]
		self.assertIn('for_update=True', block)
		self.assertLess(block.index('for_update=True'), block.index('stability_timepoint": stability_timepoint'))


	def test_review_preflight_prevents_approver_deadlock(self):
		# 业务与稳定性两侧批准角色的交集（排除 System Manager）是全流程唯一批准线：
		# 复核人若占满该角色，复核后无人可批，且业务状态机不允许 已复核 -> 已提交，
		# 修订逃生口同样不通 —— 记录会永久卡死。故复核准入须前置拒绝。
		for marker in (
			"def _assert_independent_approver_exists",
			"target == stb.RESULT_REVIEWED",
			'wf.SCOPED_ACTION_ROLES.get((RESULT_DOCTYPE, "approve_result")',
			"reviewer or standard.reviewer or _user()",
		):
			self.assertIn(marker, self.service, marker)
		# 复核准入校验必须发生在业务结果落库前，并显式传入本次复核人。
		preflight = self.lims_service.index(
			'validate_standard_test_result_sync(result.name, target_status="已复核", reviewer=_user())')
		write = self.lims_service.index("result.reviewer = _user()")
		self.assertLess(preflight, write)


class TestR8JFrontendContracts(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.api = _source(API)
		cls.ops = _source(OPS)
		cls.lims_api = _source(LIMS_API)
		cls.sample_view = _source(SAMPLE_VIEW)
		cls.study = _source(ROOT.parent.parent / "frontend" / "hbos-lims-web" / "src" / "views" / "StabilityStudyView.vue")
		cls.result_view = _source(RESULT_VIEW)
		cls.stability_scss = _source(STABILITY_SCSS)

	def test_schedule_and_trend_types_include_backend_fields(self):
		self.assertIn("test_items?:", self.api)
		self.assertIn("timepoint: string", self.api)
		self.assertIn("result_value?: number | null", self.api)

	def test_change_form_has_extra_condition_input_path(self):
		self.assertIn("extra_conditions?", self.api)
		for marker in ("extraConditionRows", "conditionOptions", "添加条件", "extra_conditions:"):
			self.assertIn(marker, self.ops)

	def test_sample_registration_exposes_stability_timepoint_binding(self):
		for marker in ("stability_timepoint", "schedule(", "稳定性取样", "稳定性时间点"):
			self.assertIn(marker, self.sample_view)
		self.assertIn("stability_timepoint?: string", self.lims_api)

	def test_result_api_exposes_business_source_link(self):
		self.assertIn("source_test_result?: string", self.api)

	def test_stability_master_ui_exposes_mapping_maintenance(self):
		for marker in (
			"manage_stability_master",
			"base_test_item",
			"mappingOptions",
			"updateStabilityTestItemMapping",
		):
			self.assertIn(marker, self.study)

	def test_trend_summary_controls_stay_within_panel_width(self):
		self.assertIn('class="stb-result-col trend"', self.result_view)
		self.assertIn(
			"grid-template-columns: repeat(2, minmax(0, 1fr));",
			self.stability_scss,
		)
		self.assertIn(".stb-form-field {\n  min-width: 0;", self.stability_scss)
		self.assertIn(
			".stb-result-col.trend .ant-select {\n  min-width: 0;\n  max-width: 100%;",
			self.stability_scss,
		)
		self.assertIn(
			"grid-template-columns: minmax(0, 1fr);",
			self.stability_scss,
		)


if __name__ == "__main__":
	unittest.main()
