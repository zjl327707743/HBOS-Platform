# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityEquipment(Document):
	def on_trash(self):
		"""设备台账全状态禁删，用「停用」代替删除（方案 8.3）。"""
		guards.guard_delete(self, "HBOS Stability Equipment", guards.EQUIPMENT_DELETABLE_STATUSES)

	def validate(self):
		guards.guard_system_fields(self, guards.EQUIPMENT_SYSTEM_FIELDS)
