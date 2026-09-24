# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt
"""年度持续稳定性考察覆盖清单（方案 5.6 第 4 项）。

每种规格/包装形式在本年度的考察覆盖情况 + 当年已选批次（年度持续类，规程 4.4）。
"""

import frappe
from frappe import _

PRODUCT_DOCTYPE = "HBOS Stability Product"
SAMPLE_DOCTYPE = "HBOS Stability Sample"
NOTICE_DOCTYPE = "HBOS Stability Notice"


def execute(filters=None):
	filters = filters or {}
	return _columns(), _fetch(filters)


def _columns():
	return [
		{"label": _("产品"), "fieldname": "stability_product", "fieldtype": "Link",
		 "options": PRODUCT_DOCTYPE, "width": 160},
		{"label": _("产品名称"), "fieldname": "product_name", "fieldtype": "Data", "width": 140},
		{"label": _("剂型"), "fieldname": "dosage_form", "fieldtype": "Data", "width": 90},
		{"label": _("包装形式"), "fieldname": "pack_desc", "fieldtype": "Data", "width": 120},
		{"label": _("考察分类"), "fieldname": "category", "fieldtype": "Data", "width": 130},
		{"label": _("年度"), "fieldname": "year", "fieldtype": "Int", "width": 70},
		{"label": _("当年通知单"), "fieldname": "notices", "fieldtype": "Data", "width": 90},
		{"label": _("当年样品批次数"), "fieldname": "batches", "fieldtype": "Int", "width": 110},
		{"label": _("覆盖状态"), "fieldname": "coverage", "fieldtype": "Data", "width": 90},
	]


def _fetch(filters):
	year = int(filters.get("year") or frappe.utils.getdate(frappe.utils.today()).year)
	rows = frappe.get_all(
		PRODUCT_DOCTYPE, filters={"is_active": 1},
		fields=["name", "product_name", "dosage_form", "pack_desc", "category"],
		limit_page_length=0)
	out = []
	for p in rows:
		notice_names = frappe.get_all(
			NOTICE_DOCTYPE,
			filters={"stability_product": p.name,
					 "creation": ["like", "{}%".format(year)]},
			pluck="name", limit_page_length=0)
		batch_count = frappe.db.count(
			SAMPLE_DOCTYPE,
			{"stability_product": p.name, "in_date": ["like", "{}%".format(year)]})
		coverage = "已覆盖" if (notice_names or batch_count) else "未覆盖"
		if filters.get("only_uncovered") and coverage != "未覆盖":
			continue
		out.append({
			"stability_product": p.name, "product_name": p.product_name,
			"dosage_form": p.dosage_form, "pack_desc": p.pack_desc,
			"category": p.category, "year": year,
			"notices": len(notice_names), "batches": batch_count,
			"coverage": coverage,
		})
	return out
