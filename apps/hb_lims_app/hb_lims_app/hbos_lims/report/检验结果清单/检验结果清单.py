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
		{"label": _("结果号"), "fieldname": "result_name", "fieldtype": "Link", "options": "HBOS Test Result", "width": 150},
		{"label": _("样品"), "fieldname": "sample", "fieldtype": "Link", "options": "HBOS Sample", "width": 150},
		{"label": _("批号"), "fieldname": "batch_no", "fieldtype": "Data", "width": 110},
		{"label": _("检验项目"), "fieldname": "item_name", "fieldtype": "Data", "width": 120},
		{"label": _("结果值"), "fieldname": "result_value", "fieldtype": "Float", "width": 100},
		{"label": _("单位"), "fieldname": "unit", "fieldtype": "Data", "width": 60},
		{"label": _("判定"), "fieldname": "verdict", "fieldtype": "Data", "width": 90},
		{"label": _("检验人"), "fieldname": "analyst", "fieldtype": "Link", "options": "User", "width": 110},
		{"label": _("复核人"), "fieldname": "reviewer", "fieldtype": "Link", "options": "User", "width": 110},
		{"label": _("记录状态"), "fieldname": "result_status", "fieldtype": "Data", "width": 90},
	]


def _fetch(filters):
	conditions = ["1=1"]
	params = {}
	if filters.get("sample"):
		conditions.append("r.sample = %(sample)s")
		params["sample"] = filters["sample"]
	if filters.get("verdict"):
		conditions.append("r.verdict = %(verdict)s")
		params["verdict"] = filters["verdict"]
	if filters.get("result_status"):
		conditions.append("r.result_status = %(result_status)s")
		params["result_status"] = filters["result_status"]
	if filters.get("from_date"):
		conditions.append("r.submitted_at >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("r.submitted_at <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	where = " AND ".join(conditions)
	return frappe.db.sql(f"""
		SELECT
			r.name AS result_name, r.sample AS sample,
			s.batch_no AS batch_no, r.item_name AS item_name,
			r.result_value AS result_value, r.unit AS unit,
			r.verdict AS verdict, r.analyst AS analyst,
			r.reviewer AS reviewer, r.result_status AS result_status
		FROM `tabHBOS Test Result` r
		LEFT JOIN `tabHBOS Sample` s ON s.name = r.sample
		WHERE {where}
		ORDER BY r.creation DESC
	""", params, as_dict=1)
