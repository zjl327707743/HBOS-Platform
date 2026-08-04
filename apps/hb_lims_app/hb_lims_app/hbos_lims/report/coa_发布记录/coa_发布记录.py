# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	return _columns(), _fetch(filters)


def _columns():
	return [
		{"label": _("COA号"), "fieldname": "coa_name", "fieldtype": "Link", "options": "HBOS COA", "width": 150},
		{"label": _("样品"), "fieldname": "sample", "fieldtype": "Link", "options": "HBOS Sample", "width": 150},
		{"label": _("批号"), "fieldname": "batch_no", "fieldtype": "Data", "width": 110},
		{"label": _("物料名称"), "fieldname": "material_name", "fieldtype": "Data", "width": 130},
		{"label": _("报告状态"), "fieldname": "report_status", "fieldtype": "Data", "width": 90},
		{"label": _("QA审核人"), "fieldname": "qa_reviewer", "fieldtype": "Link", "options": "User", "width": 110},
		{"label": _("审核时间"), "fieldname": "qa_reviewed_at", "fieldtype": "Datetime", "width": 140},
		{"label": _("发布人"), "fieldname": "published_by", "fieldtype": "Link", "options": "User", "width": 110},
		{"label": _("发布时间"), "fieldname": "published_at", "fieldtype": "Datetime", "width": 140},
		{"label": _("PDF报告"), "fieldname": "pdf_attachment", "fieldtype": "Attach", "width": 200},
	]


def _fetch(filters):
	conditions = ["1=1"]
	params = {}
	if filters.get("report_status"):
		conditions.append("c.report_status = %(report_status)s")
		params["report_status"] = filters["report_status"]
	if filters.get("sample"):
		conditions.append("c.sample = %(sample)s")
		params["sample"] = filters["sample"]
	if filters.get("published_by"):
		conditions.append("c.published_by = %(published_by)s")
		params["published_by"] = filters["published_by"]
	where = " AND ".join(conditions)
	return frappe.db.sql(f"""
		SELECT c.name AS coa_name, c.sample AS sample,
			c.batch_no AS batch_no, c.material_name AS material_name,
			c.report_status AS report_status, c.qa_reviewer AS qa_reviewer,
			c.qa_reviewed_at AS qa_reviewed_at, c.published_by AS published_by,
			c.published_at AS published_at, c.pdf_attachment AS pdf_attachment
		FROM `tabHBOS COA` c
		WHERE {where}
		ORDER BY c.creation DESC
	""", params, as_dict=1)
