# -*- coding: utf-8 -*-
"""M2-R8J 修复后离线契约测试。

本测试不依赖 Frappe 实例，锁定本轮审查发现的安全边界、库存流水、日期政策
以及前后端接口契约，避免后续重构时缺陷回归。
"""

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "hb_lims_app" / "hbos_lims" / "stability_service.py"
GUARDS = ROOT / "hb_lims_app" / "hbos_lims" / "stability_guards.py"
API = ROOT.parent.parent / "frontend" / "hbos-lims-web" / "src" / "api" / "stability.ts"
OPS = ROOT.parent.parent / "frontend" / "hbos-lims-web" / "src" / "views" / "StabilityOpsView.vue"


def _source(path):
	return path.read_text(encoding="utf-8")


class TestR8JBackendContracts(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.service = _source(SERVICE)
		cls.guards = _source(GUARDS)

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


class TestR8JFrontendContracts(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.api = _source(API)
		cls.ops = _source(OPS)

	def test_schedule_and_trend_types_include_backend_fields(self):
		self.assertIn("test_items?:", self.api)
		self.assertIn("timepoint: string", self.api)
		self.assertIn("result_value?: number | null", self.api)

	def test_change_form_has_extra_condition_input_path(self):
		self.assertIn("extra_conditions?", self.api)
		for marker in ("extraConditionRows", "conditionOptions", "添加条件", "extra_conditions:"):
			self.assertIn(marker, self.ops)


if __name__ == "__main__":
	unittest.main()
