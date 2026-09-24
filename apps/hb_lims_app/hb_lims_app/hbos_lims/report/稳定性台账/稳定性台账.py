# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt
"""稳定性台账（方案 5.6 第 1 项）。

全量稳定性样品 + 时间点汇总视图：产品 / 批号 / 条件 / 时间点 / 状态 / 结存。
只读投影，逾期为纯派生（方案 8.4）。
"""

import frappe
from frappe import _

SAMPLE_DOCTYPE = "HBOS Stability Sample"
TIMEPOINT_DOCTYPE = "HBOS Stability Timepoint"


def execute(filters=None):
	filters = filters or {}
	return _columns(), _fetch(filters)


def _columns():
	return [
		{"label": _("样品"), "fieldname": "stability_sample", "fieldtype": "Link",
		 "options": SAMPLE_DOCTYPE, "width": 150},
		{"label": _("产品"), "fieldname": "product_name", "fieldtype": "Data", "width": 140},
		{"label": _("批号"), "fieldname": "batch_no", "fieldtype": "Data", "width": 100},
		{"label": _("样品状态"), "fieldname": "sample_status", "fieldtype": "Data", "width": 90},
		{"label": _("条件"), "fieldname": "condition_type", "fieldtype": "Data", "width": 110},
		{"label": _("时间点"), "fieldname": "time_point_label", "fieldtype": "Data", "width": 70},
		{"label": _("时间点状态"), "fieldname": "tp_status", "fieldtype": "Data", "width": 90},
		{"label": _("入箱日期"), "fieldname": "in_date", "fieldtype": "Date", "width": 100},
		{"label": _("计划取样日"), "fieldname": "plan_sample_date", "fieldtype": "Date", "width": 100},
		{"label": _("有效截止日"), "fieldname": "effective_sample_due", "fieldtype": "Date", "width": 110},
		{"label": _("当前结存"), "fieldname": "current_qty", "fieldtype": "Float", "width": 90},
	]


def _fetch(filters):
	conditions = ""
	values = {}
	if filters.get("stability_product"):
		conditions += " AND s.stability_product = %(stability_product)s"
		values["stability_product"] = filters["stability_product"]
	if filters.get("batch_no"):
		conditions += " AND s.batch_no LIKE %(batch_no)s"
		values["batch_no"] = "%" + filters["batch_no"] + "%"
	if filters.get("status"):
		conditions += " AND t.status = %(status)s"
		values["status"] = filters["status"]
	rows = frappe.db.sql(
		"""
		SELECT s.name AS stability_sample, p.product_name, s.batch_no, s.status AS sample_status,
			   t.condition_type, t.time_point_label, t.status AS tp_status,
			   s.in_date, t.plan_sample_date, s.current_qty, t.name AS tp_name
		FROM `tabHBOS Stability Timepoint` t
		JOIN `tabHBOS Stability Sample` s ON s.name = t.stability_sample
		JOIN `tabHBOS Stability Product` p ON p.name = s.stability_product
		WHERE 1=1 {cond}
		ORDER BY s.name, t.plan_sample_date, t.time_point_value
		LIMIT 2000
		""".format(cond=conditions),
		values, as_dict=True)
	# 有效截止日为服务层派生（已有已批准延期按顺延日，否则政策硬上限，方案 P0-2）
	from hb_lims_app.hbos_lims.stability_service import _effective_sample_due
	for r in rows:
		tp = frappe.get_doc(TIMEPOINT_DOCTYPE, r.tp_name)
		effective, _policy = _effective_sample_due(tp)
		r["effective_sample_due"] = effective
	return rows
