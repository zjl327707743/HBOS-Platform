# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityCondition(Document):
	def on_trash(self):
		"""主数据一律禁删（方案 8.3），改用 `is_active=0` 停用。"""
		guards.guard_delete(self, "HBOS Stability Condition", guards.MASTER_DELETABLE_STATUSES)

	def validate(self):
		self._check_range("temp_min", "temp_max", "温度")
		self._check_range("humidity_min", "humidity_max", "湿度")
		self._check_photo_params()

	def _check_range(self, lo, hi, label):
		a, b = self.get(lo), self.get(hi)
		if a is not None and b is not None and float(a) > float(b):
			frappe.throw("{}下限（{}）不得大于上限（{}）。".format(label, a, b))

	def _check_photo_params(self):
		"""强光条件必须给出照度区间与总照度下限（规程 3.3.1）。"""
		if self.condition_type != "影响因素-强光":
			return
		if self.illuminance_lx_min is None or self.illuminance_lx_max is None:
			frappe.throw("强光条件必须填写照度下限与上限。")
		if not self.total_lux_hr_min:
			frappe.throw("强光条件必须填写总照度下限（lux·hr）。")
