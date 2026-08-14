import json

import frappe
from frappe.utils import getdate


def execute(filters=None):
	filters = filters or {}
	log_filters = {"monthly_summary_staging": ("is", "set")}
	if filters.get("import_log"):
		log_filters["name"] = filters["import_log"]

	# 豁免名单: 经理以上人员不计入异常考勤
	from hb_attendance_app.hbos_attendance.api import EXEMPT_NUMS

	logs = frappe.get_all(
		"HBOS Attendance Import Log",
		filters=log_filters,
		fields=["name", "import_type", "import_status", "period_start", "period_end", "monthly_summary_staging"],
		order_by="period_end desc, creation desc",
	)
	data = []
	for log in logs:
		for record in _records(log):
			if not _matches_filters(record, log, filters):
				continue
			if record.get("employee_number") in EXEMPT_NUMS:
				continue
			data.append(
				{
					"import_log": log.name,
					"import_type": log.import_type,
					"period_start": log.period_start,
					"period_end": log.period_end,
					"employee_name": record.get("employee_name"),
					"employee_number": record.get("employee_number"),
					"department": record.get("department"),
					"expected_days": record.get("expected_days"),
					"actual_days": record.get("actual_days"),
					"leave_hours": record.get("leave_hours"),
					"pay_hours": record.get("pay_hours"),
					"late_count": record.get("late_count"),
					"early_count": record.get("early_count"),
					"absent_days": record.get("absent_days"),
					"storage_note": "月度汇总暂存；不写入 Employee Checkin，不触发 Auto Attendance。",
				}
			)
	return _columns(), data


def _records(log):
	try:
		payload = json.loads(log.monthly_summary_staging or "{}")
	except json.JSONDecodeError:
		return []
	return payload.get("records") or []


def _matches_filters(record, log, filters):
	if filters.get("from_date") and log.period_end and getdate(log.period_end) < getdate(filters["from_date"]):
		return False
	if filters.get("to_date") and log.period_start and getdate(log.period_start) > getdate(filters["to_date"]):
		return False
	if filters.get("department") and filters["department"] not in (record.get("department") or ""):
		return False
	if filters.get("employee_number") and filters["employee_number"] != (record.get("employee_number") or ""):
		return False
	return True


def _columns():
	return [
		{"label": "HBOS 导入批次", "fieldname": "import_log", "fieldtype": "Link", "options": "HBOS Attendance Import Log", "width": 190},
		{"label": "导入类型", "fieldname": "import_type", "fieldtype": "Data", "width": 140},
		{"label": "开始日期", "fieldname": "period_start", "fieldtype": "Date", "width": 100},
		{"label": "结束日期", "fieldname": "period_end", "fieldtype": "Date", "width": 100},
		{"label": "员工姓名", "fieldname": "employee_name", "fieldtype": "Data", "width": 120},
		{"label": "工号", "fieldname": "employee_number", "fieldtype": "Data", "width": 110},
		{"label": "部门", "fieldname": "department", "fieldtype": "Data", "width": 150},
		{"label": "应出勤天数", "fieldname": "expected_days", "fieldtype": "Float", "width": 110},
		{"label": "实际出勤天数", "fieldname": "actual_days", "fieldtype": "Float", "width": 120},
		{"label": "请假时长", "fieldname": "leave_hours", "fieldtype": "Float", "width": 100},
		{"label": "计薪时长", "fieldname": "pay_hours", "fieldtype": "Float", "width": 100},
		{"label": "迟到次数", "fieldname": "late_count", "fieldtype": "Float", "width": 90},
		{"label": "早退次数", "fieldname": "early_count", "fieldtype": "Float", "width": 90},
		{"label": "旷工天数", "fieldname": "absent_days", "fieldtype": "Float", "width": 90},
		{"label": "暂存说明", "fieldname": "storage_note", "fieldtype": "Data", "width": 280},
	]
