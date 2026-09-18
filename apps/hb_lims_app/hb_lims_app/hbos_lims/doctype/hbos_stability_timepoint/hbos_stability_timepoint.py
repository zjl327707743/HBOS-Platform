# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityTimepoint(Document):
	def on_trash(self):
		"""仅「待取样」且无取样/延期记录时可删（方案 8.3）。

		有任何取样流水（Sample Log 指向本时间点）或延期记录即禁删。
		"""
		allowed = guards.TIMEPOINT_DELETABLE_STATUSES
		if self.delays or frappe.db.exists("HBOS Stability Sample Log",
										   {"source_timepoint": self.name}):
			allowed = ()
		guards.guard_delete(self, "HBOS Stability Timepoint", allowed)

	def validate(self):
		guards.guard_system_fields(self, guards.TIMEPOINT_SYSTEM_FIELDS)
		self._check_items_unique()
		self._check_zero_month()

	def _check_items_unique(self):
		"""父单级项目防重复（方案 5.3.2 P1-6）。"""
		seen = set()
		for row in self.test_items or []:
			if not row.stability_test_item:
				continue
			if row.stability_test_item in seen:
				frappe.throw("检测项目「{}」重复（方案 5.3.2）。".format(row.stability_test_item))
			seen.add(row.stability_test_item)

	def _check_zero_month(self):
		"""0 月点只允许标记在「月」单位的 0 值时间点上（方案 7.3 / P1-1）。"""
		if not self.is_zero_month:
			return
		if self.time_point_unit != "月" or int(self.time_point_value or 0) != 0:
			frappe.throw("只有 0 月时间点可标记为「0 月点」（方案 7.3）。")
