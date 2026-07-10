import frappe


LOG_TYPE_LABELS = {
	"IN": "上班打卡",
	"OUT": "下班打卡",
}
SOURCE_LABELS = {
	"HBOS-M1-FIX-B-MONTHLY-DEMO": "考勤机月度导出表适配导入",
	"HBOS-M1-FIX-B-MONTHLY-ADAPTER": "考勤机月度导出表适配导入",
}


def execute(filters=None):
	filters = filters or {}
	conditions = []
	values = {}
	if filters.get("from_date"):
		conditions.append("date(ec.time) >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("date(ec.time) <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("employee"):
		conditions.append("ec.employee = %(employee)s")
		values["employee"] = filters["employee"]
	where = " and ".join(conditions) if conditions else "1 = 1"
	rows = frappe.db.sql(
		f"""
		select
			ec.name,
			ec.employee,
			emp.employee_name,
			emp.employee_number,
			emp.department,
			ec.time,
			ec.log_type,
			ec.shift,
			ec.device_id,
			ec.skip_auto_attendance
		from `tabEmployee Checkin` ec
		left join `tabEmployee` emp on emp.name = ec.employee
		where {where}
		order by ec.time desc
		limit 500
		""",
		values,
		as_dict=True,
	)
	data = []
	for row in rows:
		if row.shift:
			status = LOG_TYPE_LABELS.get(row.log_type, row.log_type or "非排班打卡")
		else:
			status = "未匹配班次"
		data.append(
			{
				"employee": row.employee,
				"employee_name": row.employee_name,
				"employee_number": row.employee_number,
				"department": row.department,
				"time": row.time,
				"log_type": LOG_TYPE_LABELS.get(row.log_type, row.log_type or ""),
				"shift": row.shift,
				"checkin_status": status,
				"source_batch": SOURCE_LABELS.get(row.device_id, row.device_id or "HRMS/既有记录"),
				"duplicate_skipped": "否（已创建记录）",
			}
		)
	return _columns(), data


def _columns():
	return [
		{"label": "员工姓名", "fieldname": "employee_name", "fieldtype": "Data", "width": 120},
		{"label": "工号", "fieldname": "employee_number", "fieldtype": "Data", "width": 110},
		{"label": "部门", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
		{"label": "HRMS Employee ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 130},
		{"label": "打卡时间", "fieldname": "time", "fieldtype": "Datetime", "width": 170},
		{"label": "打卡类型", "fieldname": "log_type", "fieldtype": "Data", "width": 100},
		{"label": "班次", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 170},
		{"label": "打卡状态", "fieldname": "checkin_status", "fieldtype": "Data", "width": 120},
		{"label": "来源批次", "fieldname": "source_batch", "fieldtype": "Data", "width": 210},
		{"label": "是否重复跳过", "fieldname": "duplicate_skipped", "fieldtype": "Data", "width": 130},
	]
