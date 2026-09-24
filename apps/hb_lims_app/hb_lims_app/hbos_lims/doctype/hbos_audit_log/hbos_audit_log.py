# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class HBOSAuditLog(Document):
	def validate(self):
		"""write-once 保护：审计日志创建后不可通过常规保存修改。"""
		if self.is_new() or self.flags.audit_immutable:
			return
		frappe.throw(_("审计日志为只读Write-once记录，不可通过界面修改。"))


	def on_trash(self):
		frappe.throw(_("审计日志不可删除（数据完整性）。"))
