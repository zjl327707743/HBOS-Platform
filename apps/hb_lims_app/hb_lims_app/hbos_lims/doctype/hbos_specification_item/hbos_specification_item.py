# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HBOSSpecificationItem(Document):
	def validate(self):
		"""独立子单会避开父单冻结；合法父单保存直接调用 child.db_insert/db_update。"""
		frappe.throw("检验项目只能通过质量标准父单编辑，禁止独立新增或修改。", frappe.PermissionError)

	def on_trash(self):
		"""REST 可直达子文档删除，必须在父单冻结之外拦截。"""
		frappe.throw("检验项目只能通过质量标准父单移除，禁止独立删除。", frappe.PermissionError)
