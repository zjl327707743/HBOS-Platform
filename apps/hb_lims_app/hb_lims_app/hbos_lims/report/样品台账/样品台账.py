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
		{"label": _("样品号"), "fieldname": "sample_name", "fieldtype": "Link", "options": "HBOS Sample", "width": 150},
		{"label": _("样品类型"), "fieldname": "sample_type", "fieldtype": "Link", "options": "HBOS Sample Type", "width": 110},
		{"label": _("物料"), "fieldname": "material_name", "fieldtype": "Data", "width": 130},
		{"label": _("批号"), "fieldname": "batch_no", "fieldtype": "Data", "width": 110},
		{"label": _("标准版本"), "fieldname": "spec_version", "fieldtype": "Data", "width": 90},
		{"label": _("优先级"), "fieldname": "priority", "fieldtype": "Data", "width": 70},
		{"label": _("状态"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("请验人"), "fieldname": "requestor", "fieldtype": "Link", "options": "User", "width": 110},
		{"label": _("接收人"), "fieldname": "received_by", "fieldtype": "Link", "options": "User", "width": 110},
		{"label": _("检验时限截止"), "fieldname": "test_due_date", "fieldtype": "Date", "width": 110},
	]


def _fetch(filters):
	conditions = ["1=1"]
	params = {}
	if filters.get("sample_type"):
		conditions.append("s.sample_type = %(sample_type)s")
		params["sample_type"] = filters["sample_type"]
	if filters.get("status"):
		conditions.append("s.status = %(status)s")
		params["status"] = filters["status"]
	if filters.get("material_code"):
		conditions.append("s.material_code = %(material_code)s")
		params["material_code"] = filters["material_code"]
	if filters.get("from_date"):
		conditions.append("s.creation >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("s.creation <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	where = " AND ".join(conditions)
	return frappe.db.sql(f"""
		SELECT s.name AS sample_name, s.sample_type AS sample_type,
			s.material_name AS material_name, s.batch_no AS batch_no,
			s.spec_version AS spec_version, s.priority AS priority,
			s.status AS status, s.requestor AS requestor,
			s.received_by AS received_by, s.test_due_date AS test_due_date
		FROM `tabHBOS Sample` s
		WHERE {where}
		ORDER BY s.creation DESC
	""", params, as_dict=1)
