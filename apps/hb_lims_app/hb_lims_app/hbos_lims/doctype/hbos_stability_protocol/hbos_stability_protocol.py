# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityProtocol(Document):
	def on_trash(self):
		"""受控状态禁删（方案 8.3）：仅草稿可删。"""
		guards.guard_delete(self, "HBOS Stability Protocol", guards.PROTOCOL_DELETABLE_STATUSES)

	def validate(self):
		self._check_notice_requires_protocol()
		self._check_batches()
		self._check_items()
		guards.guard_system_fields(self, guards.PROTOCOL_SYSTEM_FIELDS)
		guards.guard_snapshot_frozen(self, stb.SNAPSHOT_FIELDS_PROTOCOL)

	def _notice(self):
		if not self.notice:
			return None
		return frappe.get_doc("HBOS Stability Notice", self.notice)

	def _category(self):
		notice = self._notice()
		if not notice:
			return None
		return frappe.db.get_value("HBOS Stability Product", notice.stability_product, "category")

	def _check_notice_requires_protocol(self):
		"""年度持续稳定性考察类不建方案单（方案 4.2.5）。"""
		category = self._category()
		if category and stb.check_year_long_study_no_protocol(category):
			frappe.throw("年度持续稳定性考察类不建方案单，按通知单执行（方案 4.2.5）。")

	def _check_batches(self):
		category = self._category()
		if not category:
			return
		ok, err = stb.check_batch_count(category, len(self.batches or []))
		if not ok:
			frappe.throw(err)

	def _check_items(self):
		seen = set()
		for row in self.items or []:
			if not row.stability_test_item:
				continue
			if row.stability_test_item in seen:
				frappe.throw("考察项目「{}」重复。".format(row.stability_test_item))
			seen.add(row.stability_test_item)
