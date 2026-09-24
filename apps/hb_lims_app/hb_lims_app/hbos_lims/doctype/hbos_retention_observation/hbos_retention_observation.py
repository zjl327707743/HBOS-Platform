# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from hb_lims_app.hbos_lims import retention_contract as rtc


class HBOSRetentionObservation(Document):
	def validate(self):
		self._generate_period_key()
		if self.result == "异常" and not (self.abnormal_note or "").strip():
			frappe_throw("观察结果为异常时必须填写异常描述。")

	def _generate_period_key(self):
		"""观察期业务键 {retention_sample}#{obs_month:03d}（5.7），validate 生成。"""
		self.sample_period_key = rtc.generate_sample_period_key(
			self.retention_sample, self.obs_month or 0)


def frappe_throw(msg):
	import frappe
	frappe.throw(msg)
