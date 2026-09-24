# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityFaultTicket(Document):
	def on_trash(self):
		"""仅「待处理」可删（方案 8.3）。"""
		guards.guard_delete(self, "HBOS Stability Fault Ticket", guards.FAULT_DELETABLE_STATUSES)

	def validate(self):
		guards.guard_system_fields(self, guards.FAULT_SYSTEM_FIELDS)
		# 受影响样品为服务专用写入的流水子表（方案 8.6 第 3 张），行不得直接增删改
		guards.guard_child_table_frozen(self, "affected_samples")
