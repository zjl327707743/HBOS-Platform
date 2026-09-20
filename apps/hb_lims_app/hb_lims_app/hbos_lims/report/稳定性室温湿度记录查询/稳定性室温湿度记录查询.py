# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt
"""稳定性室温湿度记录查询（方案 5.6 第 5 项）。

含超标筛选；`within_spec=0` 即超标记录，联动异常描述与偏差引用。
"""

import frappe
from frappe import _

ROOM_LOG_DOCTYPE = "HBOS Stability Room Log"


def execute(filters=None):
	filters = filters or {}
	return _columns(), _fetch(filters)


def _columns():
	return [
		{"label": _("记录"), "fieldname": "name", "fieldtype": "Link",
		 "options": ROOM_LOG_DOCTYPE, "width": 150},
		{"label": _("房间"), "fieldname": "room", "fieldtype": "Link",
		 "options": "HBOS Stability Room", "width": 140},
		{"label": _("日期"), "fieldname": "log_date", "fieldtype": "Date", "width": 100},
		{"label": _("班次"), "fieldname": "period", "fieldtype": "Data", "width": 60},
		{"label": _("温度"), "fieldname": "temperature", "fieldtype": "Float", "width": 80},
		{"label": _("温度范围"), "fieldname": "temp_range", "fieldtype": "Data", "width": 100},
		{"label": _("湿度"), "fieldname": "humidity", "fieldtype": "Float", "width": 80},
		{"label": _("湿度范围"), "fieldname": "humidity_range", "fieldtype": "Data", "width": 100},
		{"label": _("在控"), "fieldname": "within_spec", "fieldtype": "Check", "width": 70},
		{"label": _("异常描述"), "fieldname": "exception_desc", "fieldtype": "Data", "width": 160},
		{"label": _("采取措施"), "fieldname": "action_taken", "fieldtype": "Data", "width": 160},
		{"label": _("偏差引用"), "fieldname": "deviation_ref", "fieldtype": "Data", "width": 100},
		{"label": _("检查人"), "fieldname": "checker", "fieldtype": "Link",
		 "options": "User", "width": 100},
	]


def _fetch(filters):
	conditions = ""
	values = {}
	if filters.get("room"):
		conditions += " AND room = %(room)s"
		values["room"] = filters["room"]
	if filters.get("from_date"):
		conditions += " AND log_date >= %(from_date)s"
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions += " AND log_date <= %(to_date)s"
		values["to_date"] = filters["to_date"]
	if filters.get("only_abnormal"):
		conditions += " AND within_spec = 0"
	rows = frappe.db.sql(
		"""
		SELECT name, room, log_date, period, temperature, temp_min, temp_max,
			   humidity, humidity_min, humidity_max, within_spec,
			   exception_desc, action_taken, deviation_ref, checker
		FROM `tabHBOS Stability Room Log`
		WHERE 1=1 {cond}
		ORDER BY log_date DESC, period DESC
		LIMIT 2000
		""".format(cond=conditions),
		values, as_dict=True)
	for r in rows:
		r["temp_range"] = "{} ~ {}".format(r.temp_min, r.temp_max)
		r["humidity_range"] = "{} ~ {}".format(r.humidity_min, r.humidity_max)
	return rows
