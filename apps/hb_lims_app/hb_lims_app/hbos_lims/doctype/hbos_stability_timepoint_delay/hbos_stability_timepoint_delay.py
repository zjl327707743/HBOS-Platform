# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HBOSStabilityTimepointDelay(Document):
	def validate(self):
		"""阻止独立子文档写入；合法父单保存使用 child.db_insert/db_update。"""
		frappe.throw("延期记录只能通过时间点的延期申请、批准或驳回操作写入，禁止独立新增或修改。",
			frappe.PermissionError)

	def on_trash(self):
		"""REST 删除可直达子文档，不经过父单 validate，故在此独立拦截。"""
		frappe.throw("延期审批历史禁止直接删除。", frappe.PermissionError)
