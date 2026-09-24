# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityChange(Document):
	def on_trash(self):
		"""草稿、已取消可删（方案 8.3）。"""
		guards.guard_delete(self, "HBOS Stability Change", guards.CHANGE_DELETABLE_STATUSES)

	def validate(self):
		guards.guard_system_fields(self, guards.CHANGE_SYSTEM_FIELDS)
		if not any((self.notice, self.protocol, self.stability_sample)):
			frappe.throw("变更对象至少须指定 通知单 / 方案 / 样品 之一（方案 5.5.1）。")
		self._check_scope_targets()

	def _check_scope_targets(self):
		"""变更落点与变更对象匹配（方案 7.9 落点表）。"""
		required = {
			"涉方案": ("protocol", "方案"),
			"涉通知单": ("notice", "通知单"),
			"涉条件与时间点": ("stability_sample", "样品"),
			"涉样品": ("stability_sample", "样品"),
		}
		field, label = required.get(self.change_scope, (None, None))
		if field and not self.get(field):
			frappe.throw("变更落点「{}」必须指定{}（方案 7.9）。".format(self.change_scope, label))
