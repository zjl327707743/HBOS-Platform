# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class HBOSRetentionProduct(Document):
	def validate(self):
		# 类别与观察规则联动：外售产品 → 每批观察（规程 4.3.1）
		if self.category == "外售产品" and self.obs_rule != "每批观察（外售产品）":
			frappe_throw("外售产品类别必须为「每批观察（外售产品）」观察规则。")
		if self.category != "外售产品" and self.obs_rule == "每批观察（外售产品）":
			frappe_throw("「每批观察（外售产品）」观察规则仅适用于外售产品类别。")
		if not self.is_active:
			return
		# 全检量单位与默认单位可不同（仅影响自动计算闸，见留样登记校验）


def frappe_throw(msg):
	import frappe
	frappe.throw(msg)
