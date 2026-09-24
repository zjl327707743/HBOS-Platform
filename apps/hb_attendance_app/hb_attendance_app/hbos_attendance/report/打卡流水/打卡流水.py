import frappe


def _role_map_for_rows(rows):
    """用配对算法推断每张卡的上下班方向（与考勤判定口径一致）。

    返回 {(employee, checkin_name): "in"|"out"}。
    配对上下文覆盖查询范围前后各 2 天（覆盖跨天夜班与早晨卡向前配对），
    方向只回填给查询范围内的卡。
    """
    from collections import defaultdict
    from datetime import timedelta
    from hb_attendance_app.hbos_attendance.api import (
        ADMIN_NUMS, SAFETY_NUMS, FOOD_NUMS, _get_shift_and_late, _is_exempt,
    )
    from hb_attendance_app.hbos_attendance.pairing import (
        pair_employee_checkins, dedup_checkins_with_mapping,
    )

    if not rows:
        return {}
    # 前后各扩 2 天: 早晨卡向前配对需要前一天 14 点后的卡，
    # 而前一天的早晨卡又可能需要再前一天晚上的卡
    times = [r.time for r in rows]
    fetch_start = (min(times).date() - timedelta(days=2)).strftime("%Y-%m-%d")
    fetch_end = (max(times).date() + timedelta(days=2)).strftime("%Y-%m-%d")
    employees = sorted({r.employee for r in rows})

    all_rows = frappe.db.sql(
        """
        select ec.name, ec.employee, ec.time
        from `tabEmployee Checkin` ec
        where ec.employee in ({emp_placeholders})
          and date(ec.time) between %s and %s
        order by ec.employee, ec.time
        """.format(emp_placeholders=", ".join("%s" for _ in employees)),
        tuple(employees) + (fetch_start, fetch_end),
        as_dict=True,
    )

    by_emp = defaultdict(list)
    for r in all_rows:
        by_emp[r.employee].append(r)

    role_map = {}
    for emp, cks in by_emp.items():
        emp_num = frappe.db.get_value("Employee", emp, "employee_number") or ""
        sorted_cks = sorted(cks, key=lambda x: x["time"])
        deduped, mapping = dedup_checkins_with_mapping(sorted_cks)
        is_admin = emp_num in ADMIN_NUMS
        skip_forward = is_admin or emp_num in SAFETY_NUMS or emp_num in FOOD_NUMS or _is_exempt(emp_num)
        skip_night_lock = is_admin or emp_num in SAFETY_NUMS or emp_num in FOOD_NUMS
        _, roles = pair_employee_checkins(
            deduped, emp, emp_num, _get_shift_and_late,
            is_exempt=_is_exempt(emp_num),
            is_admin=is_admin,
            skip_forward=skip_forward,
            skip_night_lock=skip_night_lock,
            track_roles=True,
        )
        for orig_idx, dedup_idx in mapping.items():
            role_map[(emp, sorted_cks[orig_idx]["name"])] = roles[dedup_idx]
    return role_map


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
	has_terminal_sn = frappe.db.has_column("Employee Checkin", "hbos_terminal_sn")
	terminal_sn_field = "ec.hbos_terminal_sn" if has_terminal_sn else "null"
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
			{terminal_sn_field} as hbos_terminal_sn,
			ec.skip_auto_attendance
		from `tabEmployee Checkin` ec
		left join `tabEmployee` emp on emp.name = ec.employee
		where {where}
		order by ec.time desc
		""",
		values,
		as_dict=True,
	)
	from hb_attendance_app.hbos_attendance.pairing import role_from_terminal
	role_map = _role_map_for_rows(rows)
	# 固定班次映射: 员工 -> 固定班次名(优先显示)
	fixed_shift_map = {
		e.name: e.hbos_fixed_shift
		for e in frappe.db.get_all("Employee",
			fields=["name", "hbos_fixed_shift"],
			filters={"hbos_fixed_shift": ["is", "set"]})
	}
	data = []
	for row in rows:
		shift = row.shift or ""
		# 班次列优先级: 人员固定班次 > 判定班次 > 空
		if row.employee in fixed_shift_map:
			fixed = fixed_shift_map[row.employee]
			if fixed:
				rule = frappe.db.get_value("HBOS Shift Rule", fixed, "rule_name")
				shift = rule or fixed
		# 方向判定优先级: 设备 SN(分机规则, 8/15 起) > 配对算法推断 > 默认上班
		role = role_from_terminal(row.get("hbos_terminal_sn") or "", row.time)
		if role is None:
			role = role_map.get((row.employee, row.name), "in")
		checkin_status = "上班打卡" if role == "in" else "下班打卡"
		data.append(
			{
				"employee": row.employee,
				"employee_name": row.employee_name,
				"employee_number": row.employee_number,
				"department": row.department,
				"time": row.time,
				"shift": shift,
				"checkin_status": checkin_status,
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
		{"label": "员工（HRMS）", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 130},
		{"label": "打卡时间", "fieldname": "time", "fieldtype": "Datetime", "width": 170},
		{"label": "打卡状态", "fieldname": "checkin_status", "fieldtype": "Data", "width": 120},
		{"label": "班次", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 170},
		{"label": "来源批次", "fieldname": "source_batch", "fieldtype": "Data", "width": 210},
		{"label": "来源类型", "fieldname": "source_type", "fieldtype": "Data", "width": 190},
		{"label": "来源设备", "fieldname": "source_device", "fieldtype": "Data", "width": 190},
		{"label": "是否重复跳过", "fieldname": "duplicate_skipped", "fieldtype": "Data", "width": 130},
	]
