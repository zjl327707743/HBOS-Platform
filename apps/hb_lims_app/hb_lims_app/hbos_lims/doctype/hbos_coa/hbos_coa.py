# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.guards import guard_content_frozen
from hb_lims_app.hbos_lims.guards import guard_system_fields

COA_STATUS_DRAFT = "草稿"
COA_STATUS_REVIEWED = "已审核"
COA_STATUS_PUBLISHED = "已发布"

# 受控状态：审核后整份 COA 快照冻结，发布后同样（L10-P0-05）
COA_FROZEN_STATUSES = (COA_STATUS_REVIEWED, COA_STATUS_PUBLISHED)
# 快照内容字段（报告头 + 备注）；`report_status` / 签署 / 指纹由系统字段守卫负责
COA_LOCKED_FIELDS = ("sample", "batch_no", "material_code", "material_name",
					 "spec_version", "remarks")
# 项目明细子表：连行序一并冻结（报告书项目排列有语义）
COA_ITEM_TABLE_FIELDS = ("items",)


class HBOSCOA(Document):
	def validate(self):
		guard_system_fields(self, wf.HBOS_COA_SYSTEM_FIELDS)
		self._validate_locked_after_review()

	def _validate_locked_after_review(self):
		"""已审核/已发布后整份 COA 快照冻结（L10-P0-05）。

		含 `items` 每一行内容与**行序**——原实现只比 `len(self.items)`，同长度下
		改检验项目 / 方法 SOP / 标准限度 / 结果 / 判定 / 备注，或仅仅调换行序，
		都能通过。判定依据为**保存前**状态（原实现判当前状态，一旦状态被合法回退
		到草稿，冻结即失效）。
		"""
		guard_content_frozen(self, COA_LOCKED_FIELDS, COA_FROZEN_STATUSES,
							 ordered_table_fields=COA_ITEM_TABLE_FIELDS,
							 status_field="report_status",
							 remedy="走正式作废 / 重新出具流程，不修改原件（L10-P0-05）")
