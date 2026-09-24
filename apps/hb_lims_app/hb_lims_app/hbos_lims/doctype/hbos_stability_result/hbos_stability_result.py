# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityResult(Document):
	def on_trash(self):
		"""仅「草稿」可删（方案 8.3）；已提交及其后为受控记录。"""
		guards.guard_delete(self, "HBOS Stability Result", guards.RESULT_DELETABLE_STATUSES)

	def validate(self):
		guards.guard_system_fields(self, guards.RESULT_SYSTEM_FIELDS)
		self._check_baseline_mapping()

	def _check_baseline_mapping(self):
		"""基线来源类别与单据类型必须匹配（方案 5.4.1 映射表）。"""
		if not self.baseline_ref and not self.baseline_doctype:
			return
		if not self.baseline_ref:
			frappe.throw("已填写基线来源单据时，必须同时填写基线来源类别（baseline_ref）。")
		allowed = stb.BASELINE_SOURCE_MAP.get(self.baseline_ref)
		if allowed is None:
			frappe.throw("基线来源类别「{}」不在受控枚举内。".format(self.baseline_ref))
		if (self.baseline_doctype or "") not in allowed:
			frappe.throw("基线来源类别「{}」不允许单据类型「{}」（允许：{}）。".format(
				self.baseline_ref, self.baseline_doctype or "空", " / ".join(sorted(allowed))))
		if self.baseline_doctype and not self.baseline_name:
			frappe.throw("已填写基线来源单据类型时，必须填写单据编号（baseline_name）。")
