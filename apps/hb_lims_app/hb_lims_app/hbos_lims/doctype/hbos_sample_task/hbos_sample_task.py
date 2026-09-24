# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.guards import guard_system_fields


class HBOSSampleTask(Document):
	def validate(self):
		guard_system_fields(self, wf.HBOS_SAMPLE_TASK_SYSTEM_FIELDS)
