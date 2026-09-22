# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

import frappe
from frappe import _

# 任务状态中文映射（与 workflow_contract 一致）
TASK_STATUS_LABELS = {
	"待分配": "待分配",
	"已分配": "已分配",
	"检验中": "检验中",
	"已提交": "已提交",
	"已复核": "已复核",
	"已批准": "已批准",
	"OOS候选": "OOS候选",
	"OOS锁定": "OOS锁定",
}

PRIORITY_LABELS = {"常规": "常规", "加急": "加急", "特急": "特急"}


def execute(filters=None):
	filters = filters or {}
	columns = _columns()
	rows = _fetch(filters)
	return columns, rows


def _columns():
	return [
		{"label": _("任务号"), "fieldname": "task_name", "fieldtype": "Link", "options": "HBOS Sample Task", "width": 150},
		{"label": _("样品"), "fieldname": "sample", "fieldtype": "Link", "options": "HBOS Sample", "width": 150},
		{"label": _("物料"), "fieldname": "material_name", "fieldtype": "Data", "width": 120},
		{"label": _("批号"), "fieldname": "batch_no", "fieldtype": "Data", "width": 110},
		{"label": _("检验项目"), "fieldname": "item_name", "fieldtype": "Data", "width": 120},
		{"label": _("检验组"), "fieldname": "lab_department", "fieldtype": "Link", "options": "HBOS Lab Department", "width": 110},
		{"label": _("检验员"), "fieldname": "assignee", "fieldtype": "Link", "options": "User", "width": 110},
		{"label": _("优先级"), "fieldname": "priority", "fieldtype": "Data", "width": 80},
		{"label": _("分配时间"), "fieldname": "assigned_date", "fieldtype": "Datetime", "width": 140},
		{"label": _("应完成日期"), "fieldname": "due_date", "fieldtype": "Date", "width": 110},
		{"label": _("状态"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("超时"), "fieldname": "overdue", "fieldtype": "Data", "width": 70},
	]


def _fetch(filters):
	filters = dict(filters or {})
	if filters.get("scope") == "mine":
		from hb_lims_app.hbos_lims.todo_service import get_my_testing_task_names
		filters["task_names"] = get_my_testing_task_names()
		filters.pop("assignee", None)
	conditions = ["1=1"]
	params = {}

	if filters.get("lab_department"):
		conditions.append("t.lab_department = %(lab_department)s")
		params["lab_department"] = filters["lab_department"]
	if filters.get("status"):
		conditions.append("t.status = %(status)s")
		params["status"] = filters["status"]
	if filters.get("assignee"):
		conditions.append("t.assignee = %(assignee)s")
		params["assignee"] = filters["assignee"]
	if filters.get("task_names") is not None:
		task_names = tuple(filters["task_names"] or ("__NO_CURRENT_TODO__",))
		conditions.append("t.name IN %(task_names)s")
		params["task_names"] = task_names
	if filters.get("priority"):
		conditions.append("t.priority = %(priority)s")
		params["priority"] = filters["priority"]

	where = " AND ".join(conditions)
	rows = frappe.db.sql(f"""
		SELECT
			t.name AS task_name,
			t.sample AS sample,
			s.material_name AS material_name,
			s.batch_no AS batch_no,
			t.item_name AS item_name,
			t.lab_department AS lab_department,
			t.assignee AS assignee,
			t.priority AS priority,
			t.assigned_date AS assigned_date,
			t.due_date AS due_date,
			t.status AS status
		FROM `tabHBOS Sample Task` t
		LEFT JOIN `tabHBOS Sample` s ON s.name = t.sample
		LEFT JOIN `tabHBOS COA` c ON c.sample = s.name
		WHERE {where}
		-- 样品已生成 COA 时，其已批准任务视为已完成报告阶段，不再作为待检任务展示
		AND NOT (t.status = '已批准' AND c.name IS NOT NULL)
		GROUP BY t.name
		ORDER BY t.creation DESC
	""", params, as_dict=1)

	today = frappe.utils.today()
	for row in rows:
		row.status = TASK_STATUS_LABELS.get(row.status, row.status)
		row.priority = PRIORITY_LABELS.get(row.priority, row.priority)
		overdue = False
		if row.due_date and row.status not in ("已批准",):
			# due_date 为 date 类型，today 为 str，统一转 date 再比较
			overdue = frappe.utils.getdate(row.due_date) < frappe.utils.getdate(today)
		row.overdue = "是" if overdue else ""
	return rows
