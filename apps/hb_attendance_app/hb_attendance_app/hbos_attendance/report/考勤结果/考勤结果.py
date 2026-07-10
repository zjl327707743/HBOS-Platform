import frappe


STATUS_LABELS = {
	"Present": "正常出勤",
	"Absent": "缺勤",
	"On Leave": "请假",
	"Half Day": "半天",
	"Work From Home": "正常出勤",
}
def execute(filters=None):
	filters = filters or {}
	conditions = ["a.docstatus < 2"]
	values = {}
	if filters.get("from_date"):
		conditions.append("a.attendance_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("a.attendance_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("employee"):
		conditions.append("a.employee = %(employee)s")
		values["employee"] = filters["employee"]
	if filters.get("department"):
		conditions.append("emp.department = %(department)s")
		values["department"] = filters["department"]
	if filters.get("import_log"):
		conditions.append("a.hbos_import_log = %(import_log)s")
		values["import_log"] = filters["import_log"]
	if filters.get("source_type"):
		conditions.append("a.hbos_source_type = %(source_type)s")
		values["source_type"] = filters["source_type"]
	if filters.get("hbos_only"):
		conditions.append("(a.hbos_import_log is not null or a.hbos_source_type is not null or a.hbos_fallback_generated = 1)")
	where = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		select
			a.name,
			a.employee,
			emp.employee_name,
			emp.employee_number,
			emp.department,
			a.attendance_date,
			a.status,
			a.late_entry,
			a.early_exit,
			a.working_hours,
			a.shift,
			a.hbos_source_type as source_type,
			a.hbos_import_log as source_batch
		from `tabAttendance` a
		left join `tabEmployee` emp on emp.name = a.employee
		where {where}
		order by a.attendance_date desc, a.employee asc
		""",
		values,
		as_dict=True,
	)
	data = []
	if not rows and filters.get("import_log") and frappe.db.has_column("Employee Checkin", "hbos_import_log"):
		checkin_count = frappe.db.count("Employee Checkin", {"hbos_import_log": filters.get("import_log")})
		if checkin_count:
			return _columns(), [{
				"employee_name": "已导入打卡，尚未生成考勤结果",
				"status": "待生成",
				"source_batch": filters.get("import_log"),
				"remarks": f"该批次已有 {checkin_count} 条 Employee Checkin；HRMS Auto Attendance 尚未产出 Attendance。",
			}]
	for row in rows:
		status = STATUS_LABELS.get(row.status, row.status or "")
		if row.late_entry:
			status = "迟到"
		source = row.source_type or "HRMS/既有记录"
		if row.early_exit:
			status = f"{status}/早退" if status else "早退"
		data.append(
			{
				"employee": row.employee,
				"employee_name": row.employee_name,
				"employee_number": row.employee_number,
				"department": row.department,
				"attendance_date": row.attendance_date,
				"status": status,
				"late_entry": "是" if row.late_entry else "否",
				"early_exit": "是" if row.early_exit else "否",
				"working_hours": row.working_hours,
				"shift": row.shift,
				"source_batch": source,
				"remarks": row.source_batch or "既有考勤结果",
			}
		)
	return _columns(), data


def _columns():
	return [
		{"label": "员工", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 130},
		{"label": "员工姓名", "fieldname": "employee_name", "fieldtype": "Data", "width": 120},
		{"label": "工号", "fieldname": "employee_number", "fieldtype": "Data", "width": 110},
		{"label": "部门", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
		{"label": "考勤日期", "fieldname": "attendance_date", "fieldtype": "Date", "width": 110},
		{"label": "考勤状态", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "是否迟到", "fieldname": "late_entry", "fieldtype": "Data", "width": 90},
		{"label": "是否早退", "fieldname": "early_exit", "fieldtype": "Data", "width": 90},
		{"label": "工作时长", "fieldname": "working_hours", "fieldtype": "Float", "width": 90},
		{"label": "班次", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 170},
		{"label": "来源批次", "fieldname": "source_batch", "fieldtype": "Data", "width": 210},
		{"label": "备注", "fieldname": "remarks", "fieldtype": "Data", "width": 180},
	]
