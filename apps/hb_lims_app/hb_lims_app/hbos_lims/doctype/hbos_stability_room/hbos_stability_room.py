# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityRoom(Document):
	def on_trash(self):
		"""主数据一律禁删（方案 8.3），改用 `is_active=0` 停用。"""
		guards.guard_delete(self, "HBOS Stability Room", guards.MASTER_DELETABLE_STATUSES)

	def validate(self):
		for lo, hi, label in (("temp_min", "temp_max", "温度"),
							  ("humidity_min", "humidity_max", "湿度")):
			a, b = self.get(lo), self.get(hi)
			if a is not None and b is not None and float(a) > float(b):
				frappe.throw("房间{}下限（{}）不得大于上限（{}）。".format(label, a, b))
