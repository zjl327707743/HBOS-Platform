# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt
"""设备与校准到期清单（方案 5.6 第 6 项）。

确认 / 校准 / 维护任一到期日距今 ≤ 30 天即列入（方案 8.4）。
"""

import frappe
from frappe import _

from hb_lims_app.hbos_lims import stability_contract as stb

EQUIPMENT_DOCTYPE = "HBOS Stability Equipment"
DUE_WINDOW_DAYS = 30


def execute(filters=None):
	filters = filters or {}
	return _columns(), _fetch(filters)


def _columns():
	return [
		{"label": _("设备"), "fieldname": "name", "fieldtype": "Link",
		 "options": EQUIPMENT_DOCTYPE, "width": 150},
		{"label": _("设备名称"), "fieldname": "equipment_name", "fieldtype": "Data", "width": 120},
		{"label": _("房间"), "fieldname": "room", "fieldtype": "Link",
		 "options": "HBOS Stability Room", "width": 130},
		{"label": _("位置"), "fieldname": "location", "fieldtype": "Data", "width": 90},
		{"label": _("对应条件"), "fieldname": "storage_cond", "fieldtype": "Link",
		 "options": "HBOS Stability Condition", "width": 120},
		{"label": _("确认状态"), "fieldname": "qualification_status", "fieldtype": "Data", "width": 90},
		{"label": _("确认到期"), "fieldname": "qualification_due", "fieldtype": "Date", "width": 100},
		{"label": _("校准到期"), "fieldname": "calibration_due", "fieldtype": "Date", "width": 100},
		{"label": _("维护到期"), "fieldname": "maintenance_due", "fieldtype": "Date", "width": 100},
		{"label": _("最近故障"), "fieldname": "last_fault_date", "fieldtype": "Date", "width": 100},
		{"label": _("状态"), "fieldname": "status", "fieldtype": "Data", "width": 80},
		{"label": _("最早到期项"), "fieldname": "due_field", "fieldtype": "Data", "width": 100},
		{"label": _("最早到期日"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
	]


def _fetch(filters):
	today = stb._as_date(frappe.utils.today())
	window_end = stb._add_days(today, DUE_WINDOW_DAYS)
	rows = frappe.get_all(
		EQUIPMENT_DOCTYPE,
		fields=["name", "equipment_name", "room", "location", "storage_cond",
				"qualification_status", "qualification_due", "calibration_due",
				"maintenance_due", "last_fault_date", "status"],
		order_by="calibration_due asc", limit_page_length=0)
	out = []
	labels = {"qualification_due": "确认", "calibration_due": "校准",
			  "maintenance_due": "维护"}
	for eq in rows:
		due_items = []
		for field, label in labels.items():
			due = stb._as_date(eq.get(field))
			if due and due <= window_end:
				due_items.append((field, due, label))
		if not due_items and not filters.get("include_all"):
			continue
		due_items.sort(key=lambda x: x[1])
		first_field, first_due, _label = due_items[0] if due_items else (None, None, None)
		out.append({
			**eq,
			"due_field": labels.get(first_field, ""),
			"due_date": str(first_due) if first_due else None,
		})
	return out
