# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityTestItem(Document):
	def on_trash(self):
		"""主数据一律禁删（方案 8.3），改用 `is_active=0` 停用。"""
		guards.guard_delete(self, "HBOS Stability Test Item", guards.MASTER_DELETABLE_STATUSES)

	def validate(self):
		if self.significant_change_rule == "相对变化超阈值":
			if not self.change_threshold or float(self.change_threshold) <= 0:
				frappe.throw("判定规则为「相对变化超阈值」时，必须填写大于 0 的变化阈值。")
		if self.result_type == "数值型" and self.significant_change_rule in (
				"定性不符标准",):
			frappe.throw("数值型项目不适用「定性不符标准」判定规则。")
		seen = set()
		for row in self.dosage_forms or []:
			if not row.dosage_form:
				continue
			if row.dosage_form in seen:
				frappe.throw("适用剂型「{}」重复。".format(row.dosage_form))
			seen.add(row.dosage_form)
