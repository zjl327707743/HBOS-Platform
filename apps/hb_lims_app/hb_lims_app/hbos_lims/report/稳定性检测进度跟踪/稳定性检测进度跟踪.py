# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt
"""稳定性检测进度跟踪（方案 5.6 第 3 项）。

检测链进度：取样 → 检测 → 结果 → 趋势评估；含检测逾期与推荐期到期（纯派生，8.4）。
"""

import frappe
from frappe import _

from hb_lims_app.hbos_lims import stability_contract as stb

TIMEPOINT_DOCTYPE = "HBOS Stability Timepoint"
RESULT_DOCTYPE = "HBOS Stability Result"


def execute(filters=None):
	filters = filters or {}
	return _columns(), _fetch(filters)


def _columns():
	return [
		{"label": _("时间点"), "fieldname": "name", "fieldtype": "Link",
		 "options": TIMEPOINT_DOCTYPE, "width": 150},
		{"label": _("产品"), "fieldname": "product_name", "fieldtype": "Data", "width": 140},
		{"label": _("批号"), "fieldname": "batch_no", "fieldtype": "Data", "width": 100},
		{"label": _("条件"), "fieldname": "condition_type", "fieldtype": "Data", "width": 110},
		{"label": _("时间点"), "fieldname": "time_point_label", "fieldtype": "Data", "width": 70},
		{"label": _("状态"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("实际取样日"), "fieldname": "actual_sample_date", "fieldtype": "Date", "width": 100},
		{"label": _("计划检测日"), "fieldname": "plan_test_date", "fieldtype": "Date", "width": 100},
		{"label": _("实际检测日"), "fieldname": "actual_test_date", "fieldtype": "Date", "width": 100},
		{"label": _("检测截止日"), "fieldname": "effective_test_due", "fieldtype": "Date", "width": 110},
		{"label": _("检测逾期"), "fieldname": "test_overdue", "fieldtype": "Check", "width": 80},
		{"label": _("推荐期到期"), "fieldname": "recommend_due", "fieldtype": "Check", "width": 90},
		{"label": _("已批结果数"), "fieldname": "approved_results", "fieldtype": "Int", "width": 90},
		{"label": _("趋势评估"), "fieldname": "eval_conclusion", "fieldtype": "Data", "width": 100},
	]


def _fetch(filters):
	values = {}
	conditions = ""
	if filters.get("status"):
		conditions += " AND t.status = %(status)s"
		values["status"] = filters["status"]
	today = frappe.utils.today()
	rows = frappe.db.sql(
		"""
		SELECT t.name, p.product_name, s.batch_no, t.condition_type, t.time_point_label,
			   t.status, t.actual_sample_date, t.plan_test_date, t.actual_test_date,
			   t.eval_date, t.trend_conclusion,
			   t.time_point_value, t.time_point_unit
		FROM `tabHBOS Stability Timepoint` t
		JOIN `tabHBOS Stability Sample` s ON s.name = t.stability_sample
		JOIN `tabHBOS Stability Product` p ON p.name = s.stability_product
		WHERE t.status IN ('待检测', '检测中', '已完成') {cond}
		ORDER BY t.plan_test_date
		LIMIT 2000
		""".format(cond=conditions),
		values, as_dict=True)
	# 检测截止日为服务层派生（方案 P0-2：已批准延期按顺延日，否则政策窗口）
	from hb_lims_app.hbos_lims.stability_service import _effective_test_due
	result_counts = {}
	for row in frappe.db.sql(
			"""
			SELECT timepoint, COUNT(name) AS n
			FROM `tabHBOS Stability Result`
			WHERE status = %(approved)s
			GROUP BY timepoint
			""", {"approved": stb.RESULT_APPROVED}, as_dict=True):
		result_counts[row.timepoint] = row.n
	for r in rows:
		tp = frappe.get_doc(TIMEPOINT_DOCTYPE, r.name)
		effective, _policy = _effective_test_due(tp)
		r["effective_test_due"] = effective
		r["approved_results"] = result_counts.get(r.name, 0)
		r["test_overdue"] = 1 if (r.status in ("待检测", "检测中") and r.effective_test_due
								  and str(r.effective_test_due) < today) else 0
		days = stb._to_days(r.time_point_value, r.time_point_unit)
		limit = 14 if days <= 30 else 28
		base = r.actual_sample_date
		r["recommend_due"] = 1 if (r.status in ("待检测", "检测中") and base
								   and str(frappe.utils.add_days(base, limit)) < today) else 0
		if filters.get("only_overdue") and not (r.test_overdue or r.recommend_due):
			continue
		r["eval_conclusion"] = r.trend_conclusion or ("已评估" if r.eval_date else "")
	return rows
