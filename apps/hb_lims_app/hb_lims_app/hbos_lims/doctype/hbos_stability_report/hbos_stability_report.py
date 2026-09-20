# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityReport(Document):
	def on_trash(self):
		"""仅「草稿」可删（方案 8.3）。"""
		guards.guard_delete(self, "HBOS Stability Report", guards.REPORT_DELETABLE_STATUSES)

	def validate(self):
		guards.guard_system_fields(self, guards.REPORT_SYSTEM_FIELDS)
		self._sync_customer()
		self._check_scope()
		self._check_key_parts()

	def _sync_customer(self):
		"""客户编码/名称由 `customer` Link **只读派生**（方案 5.4.2 P1 rev14/rev15）。

		`client_code` 唯一来源为 Customer **文档名**（受控编码），`client` 取 `customer_name`。
		若传入的 `client_code` 与派生值不一致 —— 视为试图手工改写，**拒绝保存**。
		"""
		if not self.customer:
			self.client_code = None
			self.client = None
			return
		derived_code = self.customer
		derived_name = frappe.db.get_value("Customer", self.customer, "customer_name") or ""
		if self.client_code and self.client_code != derived_code:
			frappe.throw("客户编码与所选客户不一致（该字段为只读派生，不得手工修改）；"
						 "如需更正请改选客户，或作废后重录。")
		self.client_code = derived_code
		self.client = derived_name
		ok, err = stb.check_customer_code(derived_code)
		if not ok:
			frappe.throw(err)

	def _check_scope(self):
		"""报告类型 ↔ 来源单据类型映射 + 专项/非专项字段口径（方案 5.4.2）。"""
		ok, err = stb.check_report_scope(
			self.report_type, self.source_doctype, self.customer, self.client_code, self.seq)
		if not ok:
			frappe.throw(err)

	def _check_key_parts(self):
		"""入键成分禁 `#` 且长度受限（方案 P2 rev14）。"""
		ok, err = stb.check_report_key_parts(
			frappe.db.get_value("HBOS Stability Product", self.stability_product, "product_code")
			if self.stability_product else None,
			self.source_name, self.client_code)
		if not ok:
			frappe.throw(err)
