# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class HBOSStabilityFaultSample(Document):
	"""流水子表（方案 8.3 流水表特例）：完全由 stability_service 写入，无用户直接填单场景。"""
	pass
