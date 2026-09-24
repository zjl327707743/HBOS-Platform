# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.guards import guard_system_fields

SAMPLE_STATUS_DRAFT = "草稿"
SAMPLE_STATUS_REGISTERED = "已登记"
SAMPLE_STATUS_TESTING = "检验中"
SAMPLE_STATUS_TESTED = "检验完成"
SAMPLE_STATUS_RELEASED = "已放行"
SAMPLE_STATUS_REJECTED = "已拒绝"
SAMPLE_STATUS_OOS = "OOS锁定"

SAMPLE_ITEM_LOCKED_FIELDS = ("specification", "sample_type", "material_code", "material_name", "batch_no",
							"sample_source", "stability_timepoint")


class HBOSSample(Document):
	def validate(self):
		guard_system_fields(self, wf.HBOS_SAMPLE_SYSTEM_FIELDS)
		self._validate_spec_active()
		self._validate_locked_after_register()

	def _validate_spec_active(self):
		"""质量标准必须已生效（草稿 / 已废止不可引用）。"""
		if not self.specification:
			return
		from hb_lims_app.hbos_lims.doctype.hbos_specification.hbos_specification import is_spec_active
		if not is_spec_active(self.specification):
			frappe.throw(f"质量标准 {self.specification} 未生效（草稿或已废止），样品登记只能引用已生效标准。")

	def _validate_locked_after_register(self):
		"""登记后关键字段锁定（ALCOA：登记信息不可随意变更）。"""
		if self.is_new() or self.status in (SAMPLE_STATUS_DRAFT,):
			return
		before = self.get_doc_before_save()
		if not before:
			return
		for field in SAMPLE_ITEM_LOCKED_FIELDS:
			if self.get(field) != before.get(field):
				frappe.throw(f"样品登记后字段「{self.meta.get_label(field)}」不可修改，如需变更请走修订流程。")
