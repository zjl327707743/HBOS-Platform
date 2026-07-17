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
	has_import_log = frappe.db.has_column("Employee Checkin", "hbos_import_log")
	has_source_type = frappe.db.has_column("Employee Checkin", "hbos_source_type")
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
	if filters.get("department"):
		conditions.append("emp.department = %(department)s")
		values["department"] = filters["department"]
	if filters.get("source_device"):
		conditions.append("ec.device_id = %(source_device)s")
		values["source_device"] = filters["source_device"]
	if filters.get("import_log") and has_import_log:
		conditions.append("ec.hbos_import_log = %(import_log)s")
		values["import_log"] = filters["import_log"]
	if filters.get("hbos_only"):
		source_conditions = ["ec.device_id like 'HBOS-%'", "ec.device_id like '%MONTHLY%'"]
		if has_import_log:
			source_conditions.append("ec.hbos_import_log is not null")
		conditions.append("(" + " or ".join(source_conditions) + ")")
	where = " and ".join(conditions) if conditions else "1 = 1"
	import_log_field = "ec.hbos_import_log" if has_import_log else "null"
	source_type_field = "ec.hbos_source_type" if has_source_type else "null"
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
			{import_log_field} as hbos_import_log,
			{source_type_field} as hbos_source_type,
			ec.skip_auto_attendance
		from `tabEmployee Checkin` ec
		left join `tabEmployee` emp on emp.name = ec.employee
		where {where}
		order by ec.time desc
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
				"source_batch": row.hbos_import_log or SOURCE_LABELS.get(row.device_id, row.device_id or "HRMS/既有记录"),
				"source_type": row.hbos_source_type or SOURCE_LABELS.get(row.device_id, "HRMS/既有记录"),
				"source_device": row.device_id or "",
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
		{"label": "来源类型", "fieldname": "source_type", "fieldtype": "Data", "width": 190},
		{"label": "来源设备", "fieldname": "source_device", "fieldtype": "Data", "width": 190},
		{"label": "是否重复跳过", "fieldname": "duplicate_skipped", "fieldtype": "Data", "width": 130},
	]
