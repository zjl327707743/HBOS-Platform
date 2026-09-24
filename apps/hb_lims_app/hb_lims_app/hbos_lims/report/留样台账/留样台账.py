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
		{"label": _("留样编号"), "fieldname": "name", "fieldtype": "Link",
		 "options": "HBOS Retention Sample", "width": 140},
		{"label": _("样品名称"), "fieldname": "sample_name", "fieldtype": "Data", "width": 130},
		{"label": _("物料编码"), "fieldname": "material_code", "fieldtype": "Data", "width": 100},
		{"label": _("批号"), "fieldname": "batch_no", "fieldtype": "Data", "width": 100},
		{"label": _("容器"), "fieldname": "container_no", "fieldtype": "Int", "width": 60},
		{"label": _("类别"), "fieldname": "category", "fieldtype": "Data", "width": 100},
		{"label": _("留样日期"), "fieldname": "retention_date", "fieldtype": "Date", "width": 100},
		{"label": _("留样量"), "fieldname": "retention_qty", "fieldtype": "Float", "width": 90},
		{"label": _("单位"), "fieldname": "qty_uom", "fieldtype": "Data", "width": 60},
		{"label": _("当前结存"), "fieldname": "current_qty", "fieldtype": "Float", "width": 90},
		{"label": _("预占量"), "fieldname": "reserved_qty", "fieldtype": "Float", "width": 80},
		{"label": _("可用量"), "fieldname": "available_qty", "fieldtype": "Float", "width": 90},
		{"label": _("留样期至"), "fieldname": "retention_due_date", "fieldtype": "Date", "width": 100},
		{"label": _("观察样品"), "fieldname": "observed_flag", "fieldtype": "Check", "width": 80},
		{"label": _("储存位置"), "fieldname": "storage_location", "fieldtype": "Data", "width": 90},
		{"label": _("状态"), "fieldname": "status", "fieldtype": "Data", "width": 80},
		{"label": _("留样人"), "fieldname": "retained_by", "fieldtype": "Link", "options": "User", "width": 110},
		{"label": _("流水对账"), "fieldname": "recon_flag", "fieldtype": "Data", "width": 80},
	]


def _fetch(filters):
	conditions = ["1=1"]
	params = {}
	if filters.get("category"):
		conditions.append("s.category = %(category)s")
		params["category"] = filters["category"]
	if filters.get("status"):
		conditions.append("s.status = %(status)s")
		params["status"] = filters["status"]
	if filters.get("retention_product"):
		conditions.append("s.retention_product = %(retention_product)s")
		params["retention_product"] = filters["retention_product"]
	if filters.get("batch_no"):
		conditions.append("s.batch_no LIKE %(batch_no)s")
		params["batch_no"] = "%{}%".format(filters["batch_no"])
	if filters.get("from_date"):
		conditions.append("s.retention_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("s.retention_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	if filters.get("observed_only"):
		conditions.append("s.observed_flag = 1")
	where = " AND ".join(conditions)
	return frappe.db.sql(f"""
		SELECT s.name, s.sample_name, s.material_code, s.batch_no, s.container_no,
			s.category, s.retention_date, s.retention_qty, s.qty_uom,
			s.current_qty, s.reserved_qty,
			(s.current_qty - s.reserved_qty) AS available_qty,
			s.retention_due_date, s.observed_flag, s.storage_location,
			s.status, s.retained_by
		FROM `tabHBOS Retention Sample` s
		WHERE {where}
		ORDER BY s.retention_date DESC, s.name DESC
	""", params, as_dict=1)
