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
		{"label": _("修订号"), "fieldname": "revision_name", "fieldtype": "Link", "options": "HBOS Result Revision", "width": 150},
		{"label": _("结果记录"), "fieldname": "result", "fieldtype": "Link", "options": "HBOS Test Result", "width": 150},
		{"label": _("变更字段"), "fieldname": "field_changed", "fieldtype": "Data", "width": 120},
		{"label": _("修改前值"), "fieldname": "old_value", "fieldtype": "Data", "width": 120},
		{"label": _("修改后值"), "fieldname": "new_value", "fieldtype": "Data", "width": 120},
		{"label": _("修改人"), "fieldname": "changed_by", "fieldtype": "Link", "options": "User", "width": 110},
		{"label": _("修改时间"), "fieldname": "changed_at", "fieldtype": "Datetime", "width": 140},
		{"label": _("修改原因"), "fieldname": "change_reason", "fieldtype": "Data", "width": 240},
	]


def _fetch(filters):
	conditions = ["1=1"]
	params = {}
	if filters.get("result"):
		conditions.append("r.result = %(result)s")
		params["result"] = filters["result"]
	if filters.get("changed_by"):
		conditions.append("r.changed_by = %(changed_by)s")
		params["changed_by"] = filters["changed_by"]
	if filters.get("from_date"):
		conditions.append("r.changed_at >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("r.changed_at <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	where = " AND ".join(conditions)
	return frappe.db.sql(f"""
		SELECT r.name AS revision_name, r.result AS result,
			r.field_changed AS field_changed, r.old_value AS old_value,
			r.new_value AS new_value, r.changed_by AS changed_by,
			r.changed_at AS changed_at, r.change_reason AS change_reason
		FROM `tabHBOS Result Revision` r
		WHERE {where}
		ORDER BY r.changed_at DESC
	""", params, as_dict=1)
