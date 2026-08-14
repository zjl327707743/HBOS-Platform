import frappe


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
		source_conditions = ["ec.device_id like \"HBOS-%%\"", "ec.device_id like \"%%MONTHLY%%\""]
		if has_import_log:
			source_conditions.append("ec.hbos_import_log is not null")
		conditions.append("(" + " or ".join(source_conditions) + ")")
	# 豁免名单过滤: 经理以上人员不计入异常考勤
	from hb_attendance_app.hbos_attendance.api import EXEMPT_NUMS
	if EXEMPT_NUMS:
		quoted = ",".join("'%s'" % v.replace("'", "") for v in sorted(EXEMPT_NUMS))
		conditions.append("emp.employee_number NOT IN (%s)" % quoted)
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
		shift = row.shift or ""
		status = "已匹配" if shift else "未匹配班次"
		data.append(
			{
				"employee": row.employee,
				"employee_name": row.employee_name,
				"employee_number": row.employee_number,
				"department": row.department,
				"time": row.time,
				"shift": shift,
				"checkin_status": status,
				"source_batch": row.hbos_import_log or (row.device_id or "HRMS/既有记录"),
				"source_type": row.hbos_source_type or (row.device_id or "HRMS/既有记录"),
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
		{"label": "打卡状态", "fieldname": "checkin_status", "fieldtype": "Data", "width": 120},
		{"label": "班次", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 170},
		{"label": "来源批次", "fieldname": "source_batch", "fieldtype": "Data", "width": 210},
		{"label": "来源类型", "fieldname": "source_type", "fieldtype": "Data", "width": 190},
		{"label": "来源设备", "fieldname": "source_device", "fieldtype": "Data", "width": 190},
		{"label": "是否重复跳过", "fieldname": "duplicate_skipped", "fieldtype": "Data", "width": 130},
	]
