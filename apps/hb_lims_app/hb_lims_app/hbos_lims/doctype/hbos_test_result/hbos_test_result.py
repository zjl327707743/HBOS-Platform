# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.guards import guard_system_fields

RESULT_STATUS_DRAFT = "草稿"
RESULT_STATUS_SUBMITTED = "已提交"
RESULT_STATUS_REVIEWED = "已复核"
RESULT_STATUS_APPROVED = "已批准"
RESULT_STATUS_REVISED = "已修订"

# 提交后锁定字段（ALCOA：复核人不可修改原始数据，修改走修订流程生成新版本）
RESULT_LOCKED_FIELDS = ("raw_value", "result_value", "result_text", "calc_input_json",
                        "calculation_used", "limits_type", "lower_limit", "upper_limit",
                        "unit", "significant_digits", "analyst", "verdict", "is_oos_candidate")


class HBOSTestResult(Document):
	def validate(self):
		guard_system_fields(self, wf.HBOS_TEST_RESULT_SYSTEM_FIELDS)
		self._validate_locked_after_submit()

	def _validate_locked_after_submit(self):
		"""已提交及之后，结果 / 限度 / 检验人字段不可直接修改（复核人只读复核，修改必须走修订流程）。

		判定依据为提交前状态（before.result_status）：草稿状态的保存（含草稿 -> 已提交的提交动作）放行；
		提交前已是已提交及以上状态的保存，禁止修改结果相关字段。
		"""
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if not before or before.result_status == RESULT_STATUS_DRAFT:
			return
		for field in RESULT_LOCKED_FIELDS:
			if self.get(field) != before.get(field):
				frappe.throw(
					f"检测记录已提交（状态 {self.result_status}），字段「{self.meta.get_label(field)}」不可直接修改。"
					"如需修改请由 LIMS Manager 执行修订流程（生成修订记录与新版本结果）。"
				)
