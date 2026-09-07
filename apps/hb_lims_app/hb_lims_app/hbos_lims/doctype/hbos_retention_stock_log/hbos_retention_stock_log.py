# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class HBOSRetentionStockLog(Document):
	def validate(self):
		# 手动调整原因必填（方案 5.2 Stock Log 规则）
		if self.transaction_type == "手动调整" and not self.remarks:
			frappe_throw("手动调整必须填写原因。")


def frappe_throw(msg):
	import frappe
	frappe.throw(msg)
