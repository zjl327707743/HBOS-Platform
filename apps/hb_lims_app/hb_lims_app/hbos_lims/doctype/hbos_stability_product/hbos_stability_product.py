# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityProduct(Document):
	def on_trash(self):
		"""主数据一律禁删（方案 8.3），改用 `is_active=0` 停用。"""
		guards.guard_delete(self, "HBOS Stability Product", guards.MASTER_DELETABLE_STATUSES)

	def validate(self):
		ok, err = stb.check_product_code(self.product_code)
		if not ok:
			frappe.throw(err)
		if self.qty_factor is not None and float(self.qty_factor) <= 0:
			frappe.throw("默认用量倍数必须大于 0。")
		if self.vd_months is not None and int(self.vd_months) < 0:
			frappe.throw("有效期（月）不得为负。")
		for field, label in (("storage_cond_long", "长期条件"),
							 ("storage_cond_acc", "加速条件"),
							 ("storage_cond_inter", "中间条件")):
			cond = self.get(field)
			if cond and not frappe.db.get_value("HBOS Stability Condition", cond, "is_active"):
				frappe.throw("{}「{}」未启用或不存在，请先维护条件主数据。".format(label, cond))
