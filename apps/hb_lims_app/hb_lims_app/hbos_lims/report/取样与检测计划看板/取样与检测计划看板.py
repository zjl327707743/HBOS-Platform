# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt
"""取样与检测计划看板（方案 5.6 第 2 项；R8B 唯一交付轮）。

当月应取样 / 应检测 + 计划/实际日期 + **逾期派生**（方案 8.4：逾期为纯派生标识，
不进 `status` 枚举、不改单据状态）。

逾期判定用 `effective_due_date`（已有已批准延期则按顺延日，否则政策硬上限）。

说明：Frappe Script Report 原生不支持按行着色，故逾期以 `exec_state`（含「取样逾期 /
检测逾期」取值）与 `sample_overdue` / `test_overdue` 两列表达，未引入自定义报表 JS。
"""

import frappe
from frappe import _

from hb_lims_app.hbos_lims import stability_contract as stb

SAMPLE_DOCTYPE = "HBOS Stability Sample"
TIMEPOINT_DOCTYPE = "HBOS Stability Timepoint"


def execute(filters=None):
	filters = filters or {}
	return _columns(), _fetch(filters)


def _columns():
	return [
		{"label": _("时间点"), "fieldname": "name", "fieldtype": "Link",
		 "options": TIMEPOINT_DOCTYPE, "width": 150},
		{"label": _("产品"), "fieldname": "product_name", "fieldtype": "Data", "width": 140},
		{"label": _("批号"), "fieldname": "batch_no", "fieldtype": "Data", "width": 100},
		{"label": _("样品"), "fieldname": "stability_sample", "fieldtype": "Link",
		 "options": SAMPLE_DOCTYPE, "width": 150},
		{"label": _("条件"), "fieldname": "condition_type", "fieldtype": "Data", "width": 110},
		{"label": _("时间点"), "fieldname": "time_point_label", "fieldtype": "Data", "width": 70},
		{"label": _("全项"), "fieldname": "is_full_test", "fieldtype": "Check", "width": 60},
		{"label": _("计划取样日"), "fieldname": "plan_sample_date", "fieldtype": "Date", "width": 100},
		{"label": _("实际取样日"), "fieldname": "actual_sample_date", "fieldtype": "Date", "width": 100},
		{"label": _("取样有效截止"), "fieldname": "effective_sample_due", "fieldtype": "Date", "width": 110},
		{"label": _("计划检测日"), "fieldname": "plan_test_date", "fieldtype": "Date", "width": 100},
		{"label": _("实际检测日"), "fieldname": "actual_test_date", "fieldtype": "Date", "width": 100},
		{"label": _("检测有效截止"), "fieldname": "effective_test_due", "fieldtype": "Date", "width": 110},
		{"label": _("延期状态"), "fieldname": "delay_state", "fieldtype": "Data", "width": 130},
		{"label": _("执行状态"), "fieldname": "exec_state", "fieldtype": "Data", "width": 100},
		{"label": _("取样逾期"), "fieldname": "sample_overdue", "fieldtype": "Check", "width": 80},
		{"label": _("检测逾期"), "fieldname": "test_overdue", "fieldtype": "Check", "width": 80},
		{"label": _("状态"), "fieldname": "status", "fieldtype": "Data", "width": 90},
	]


def _fetch(filters):
	rows = frappe.get_all(
		TIMEPOINT_DOCTYPE,
		filters=_tp_filters(filters),
		fields=["name", "stability_sample", "condition_type", "storage_cond",
				"time_point_label", "time_point_value", "time_point_unit", "is_full_test",
				"plan_sample_date", "actual_sample_date", "plan_test_date", "actual_test_date",
				"delay_limit_days", "status"],
		order_by="plan_sample_date asc, time_point_value asc",
		limit_page_length=2000)
	rows = _enrich(rows, filters)
	return rows


def _tp_filters(filters):
	out = {}
	if filters.get("condition"):
		out["condition_type"] = filters["condition"]
	return out


def _enrich(rows, filters):
	today = frappe.utils.getdate(frappe.utils.today())
	month = (filters.get("month") or "").strip()
	keyword = (filters.get("keyword") or "").strip().lower()
	exec_filter = filters.get("exec_status")

	sample_names = sorted({r["stability_sample"] for r in rows if r.get("stability_sample")})
	samples, products = {}, {}
	if sample_names:
		for s in frappe.get_all(SAMPLE_DOCTYPE, filters={"name": ["in", sample_names]},
								fields=["name", "batch_no", "stability_product"],
								limit_page_length=0):
			samples[s.name] = s
		prod_names = sorted({s["stability_product"] for s in samples.values()
							 if s.get("stability_product")})
		if prod_names:
			products = dict(frappe.get_all("HBOS Stability Product",
										   filters={"name": ["in", prod_names]},
										   fields=["name", "product_name"], as_list=True))

	# 延期：按时间点批量取已批准行（算有效截止日）
	delay_map = {}
	tp_names = [r["name"] for r in rows]
	if tp_names:
		for d in frappe.get_all(
				"HBOS Stability Timepoint Delay",
				filters={"parent": ["in", tp_names], "parenttype": TIMEPOINT_DOCTYPE},
				fields=["parent", "delay_type", "status", "approve_at", "approved_due_date",
						"requested_due_date"],
				limit_page_length=0):
			delay_map.setdefault(d.parent, []).append(d)

	out = []
	for r in rows:
		s = samples.get(r["stability_sample"]) or {}
		r["batch_no"] = s.get("batch_no")
		r["product_name"] = products.get(s.get("stability_product"))
		delays = delay_map.get(r["name"], [])

		policy_sample = stb._add_days(r["plan_sample_date"], r["delay_limit_days"] or 0)
		policy_test = stb._add_days(r["plan_test_date"], stb.TEST_WINDOW_DAYS)
		eff_sample = stb.effective_due_date(delays, "取样延期", policy_sample)
		eff_test = stb.effective_due_date(delays, "检测延期", policy_test)
		r["effective_sample_due"] = eff_sample
		r["effective_test_due"] = eff_test

		inflight = [d for d in delays if d.status == stb.DELAY_WAIT_APPROVE]
		approved = [d for d in delays if d.status == stb.DELAY_APPROVED]
		if inflight:
			r["delay_state"] = "{}（待批准）".format(inflight[-1].delay_type)
		elif approved:
			latest = sorted(approved, key=lambda d: str(d.approve_at or ""))[-1]
			r["delay_state"] = "{} 延至 {}".format(latest.delay_type, latest.approved_due_date)
		else:
			r["delay_state"] = ""

		r["sample_overdue"] = 0
		r["test_overdue"] = 0
		r["exec_state"] = r["status"]
		if r["status"] == stb.TP_WAIT_SAMPLE and eff_sample and today > eff_sample:
			r["sample_overdue"] = 1
			r["exec_state"] = "取样逾期"
		if r["status"] in (stb.TP_WAIT_TEST, stb.TP_TESTING) and eff_test and today > eff_test:
			r["test_overdue"] = 1
			r["exec_state"] = "检测逾期"

		if month and not str(r["plan_sample_date"] or "").startswith(month):
			continue
		if exec_filter and r["exec_state"] != exec_filter and r["status"] != exec_filter:
			continue
		if keyword and keyword not in "{} {} {}".format(
				r["name"], r["batch_no"] or "", (r["product_name"] or "")).lower():
			continue
		out.append(r)
	return out
