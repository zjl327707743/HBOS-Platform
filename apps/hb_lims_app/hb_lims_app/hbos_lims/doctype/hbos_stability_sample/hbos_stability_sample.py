# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilitySample(Document):
	def on_trash(self):
		"""全生命周期禁删（方案 8.3）：样品为受控记录，终止走「已销毁 / 已转出」。"""
		guards.guard_delete(self, "HBOS Stability Sample", guards.SAMPLE_DELETABLE_STATUSES)

	def validate(self):
		guards.guard_system_fields(self, guards.SAMPLE_SYSTEM_FIELDS)
		self._check_evaluation()
		self._check_qty()

	def _check_evaluation(self):
		"""进箱超生产 1 个月 → 强制评估四件套（方案 5.3.1 / 门禁 14）。

		`need_evaluation` 为系统字段（服务写入）；此处保证「置了就必须填齐」。
		"""
		if not self.need_evaluation:
			return
		if not (self.evaluation_conclusion or "").strip():
			frappe.throw("进箱超过生产日期 1 个月时，必须填写评估结论（方案 5.3.1）。")
		if not self.evaluated_by or not self.evaluation_date:
			frappe.throw("进箱超过生产日期 1 个月时，必须填写评估人与评估日期（方案 5.3.1）。")

	def _check_qty(self):
		for field, label in (("init_qty", "初始量"), ("current_qty", "当前结存")):
			value = self.get(field)
			if value is not None and float(value) < 0:
				frappe.throw("{}不得为负。".format(label))
