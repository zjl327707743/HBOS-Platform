# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.guards import guard_system_fields


class HBOSRetentionUsageApply(Document):
	def validate(self):
		"""审批单据状态/签署字段守卫（方案 6.1 / 7.7，与 R7 其它状态单据同口径）。

		只有业务服务（retention_service，带 `allow_system_fields` 标记）与内建
		Administrator 可以推进状态或写入签署留痕；表单直改、
		`frappe.client.set_value`、`PUT /api/resource/...` 等原生写路径一律拦截，
		否则 System Manager 可以伪造「已批准」而完全绕过规定的审批/签署链和业务服务校验。
		"""
		guard_system_fields(self, wf.HBOS_RETENTION_USAGE_SYSTEM_FIELDS)
