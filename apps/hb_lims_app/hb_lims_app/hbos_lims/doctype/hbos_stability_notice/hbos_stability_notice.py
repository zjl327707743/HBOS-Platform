# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import stability_guards as guards


class HBOSStabilityNotice(Document):
	def on_trash(self):
		"""受控状态禁删（方案 8.3）：仅草稿 / 已驳回 / 已取消可删。"""
		guards.guard_delete(self, "HBOS Stability Notice", guards.NOTICE_DELETABLE_STATUSES)

	def validate(self):
		self._compute_conditions_count()
		self._check_conditions_match_category()
		self._check_batches()
		guards.guard_system_fields(self, guards.NOTICE_SYSTEM_FIELDS)
		guards.guard_snapshot_frozen(self, stb.SNAPSHOT_FIELDS_NOTICE)

	def _compute_conditions_count(self):
		"""条件数量为派生只读值（方案 5.2.1）。"""
		self.conditions_count = len(self.study_conditions or [])

	def _category(self):
		if not self.stability_product:
			return None
		return frappe.db.get_value("HBOS Stability Product", self.stability_product, "category")

	def _check_conditions_match_category(self):
		"""该分类「至少包含条件」校验（方案 4.1）。"""
		category = self._category()
		if not category:
			return
		rows = [{"condition_type": r.condition_type} for r in (self.study_conditions or [])]
		ok, err = stb.check_notice_conditions(category, rows)
		if not ok:
			frappe.throw(err)

	def _check_batches(self):
		"""批次数量按分类下限校验（方案 4.1）。"""
		category = self._category()
		if not category:
			return
		ok, err = stb.check_batch_count(category, len(self.batches or []))
		if not ok:
			frappe.throw(err)
