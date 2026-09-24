# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.guards import guard_system_fields

SPEC_STATUS_DRAFT = "草稿"
SPEC_STATUS_ACTIVE = "已生效"
SPEC_STATUS_OBSOLETE = "已废止"


def is_spec_active(spec_name):
	"""质量标准是否已生效（草稿 / 已废止不可被样品引用）。"""
	doc = frappe.get_cached_doc("HBOS Specification", spec_name)
	return doc.status == SPEC_STATUS_ACTIVE


def get_active_specifications():
	"""全部已生效质量标准（供样品登记选择）。"""
	return frappe.get_all(
		"HBOS Specification",
		filters={"status": SPEC_STATUS_ACTIVE},
		fields=["name", "spec_code", "spec_name", "material_code", "material_name", "version"],
		order_by="spec_code asc",
	)


class HBOSSpecification(Document):
	def validate(self):
		guard_system_fields(self, wf.HBOS_SPECIFICATION_SYSTEM_FIELDS)
		self._validate_immutable_after_activation()
		self._validate_unique_version()
		self._validate_limits()

	def _validate_immutable_after_activation(self):
		"""已生效/已废止版本是质量标准快照，不允许原地改业务内容。"""
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if not before or before.status == SPEC_STATUS_DRAFT:
			return
		locked = (
			"spec_code", "spec_name", "material_code", "material_name", "version",
			"standard_source", "effective_date", "storage_condition",
			"retain_sample_qty", "remarks",
		)
		for field in locked:
			if str(self.get(field) or "") != str(before.get(field) or ""):
				frappe.throw(
					f"质量标准 {self.name} 已进入 {before.status}，业务内容不可原地修改；请复制生成新版本。"
				)
		def sig(rows):
			return [
				tuple(str(row.get(k) or "") for k in (
					"item", "item_name", "method_sop", "limits_type", "lower_limit",
					"upper_limit", "unit", "significant_digits"
				))
				for row in (rows or [])
			]
		if sig(self.items) != sig(before.items):
			frappe.throw(
				f"质量标准 {self.name} 已进入 {before.status}，检验项目/限度不可原地修改；请复制生成新版本。"
			)

	def _validate_unique_version(self):
		"""同规格 ID + 同版本号禁止重复（版本控制为复制新版本人工流程）。"""
		existing = frappe.db.get_value(
			"HBOS Specification",
			{"spec_code": self.spec_code, "version": self.version, "name": ["!=", self.name]},
			"name",
		)
		if existing:
			frappe.throw(
				f"规格 {self.spec_code} 版本 {self.version} 已存在（{existing}），"
				"同一版本号不允许重复，请复制为新版本。"
			)

	def _validate_limits(self):
		"""限度一致性：区间必须同时有下限和上限，且下限小于等于上限。"""
		for row in self.items:
			if row.limits_type == "区间":
				if row.lower_limit is None or row.upper_limit is None:
					frappe.throw(
						f"检验项目 {row.item_name or row.item} 的限度模式为区间，"
						"必须同时填写限度下限和限度上限。"
					)
				if float(row.lower_limit) > float(row.upper_limit):
					frappe.throw(
						f"检验项目 {row.item_name or row.item} 的限度下限大于上限，请检查。"
					)
			elif row.limits_type == "上限":
				if row.upper_limit is None:
					frappe.throw(f"检验项目 {row.item_name or row.item} 的限度模式为上限，必须填写限度上限。")
			elif row.limits_type == "下限":
				if row.lower_limit is None:
					frappe.throw(f"检验项目 {row.item_name or row.item} 的限度模式为下限，必须填写限度下限。")
