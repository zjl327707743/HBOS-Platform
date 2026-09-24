# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.guards import guard_system_fields

COA_STATUS_DRAFT = "草稿"
COA_STATUS_REVIEWED = "已审核"
COA_STATUS_PUBLISHED = "已发布"

# 已审核后锁定字段（快照不可改）；已发布后整体锁定
COA_LOCKED_FIELDS = ("sample", "batch_no", "material_code", "material_name", "spec_version")


class HBOSCOA(Document):
	def validate(self):
		guard_system_fields(self, wf.HBOS_COA_SYSTEM_FIELDS)
		self._validate_locked_after_review()

	def _validate_locked_after_review(self):
		"""已审核及之后，报告头与项目明细不可修改（COA 快照不可改，发布后 PDF 归档）。"""
		if self.is_new() or self.report_status == COA_STATUS_DRAFT:
			return
		before = self.get_doc_before_save()
		if not before:
			return
		for field in COA_LOCKED_FIELDS:
			if self.get(field) != before.get(field):
				frappe.throw(f"报告书已进入状态 {self.report_status}，字段「{self.meta.get_label(field)}」不可修改（COA 快照）。")
		if before.report_status != COA_STATUS_DRAFT:
			def item_signature(rows):
				return [
					tuple(str(row.get(k) or "") for k in (
						"test_item", "item_name", "method_sop", "standard",
						"result", "verdict", "remarks",
					))
					for row in (rows or [])
				]
			if item_signature(self.items) != item_signature(before.items):
				frappe.throw(
					"报告书已审核/发布，检验项目明细内容不可增删改；如需更正请走作废/重发流程（COA 快照）。"
				)
