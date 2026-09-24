import frappe

READ_ROLES = {"HR User", "HR Manager", "System Manager"}
WRITE_ROLES = {"HR Manager", "System Manager"}


def _require_roles(allowed):
    if not (set(frappe.get_roles()) & set(allowed)):
        frappe.throw("你无权访问考勤人员管理。", frappe.PermissionError)


def _require_hr_read():
    _require_roles(READ_ROLES)


def _require_hr_write():
    _require_roles(WRITE_ROLES)



@frappe.whitelist()
def get_employees(department=None, search=None, fixed_shift=None):
    """人员列表: 工号/姓名/部门/联系方式/固定班次。

    filters: department(可选), search(姓名/工号模糊), fixed_shift(可选)
    """
    _require_hr_read()
    conditions = ["e.status = 'Active'"]
    values = {}
    if department:
        conditions.append("e.department = %(department)s")
        values["department"] = department
    if search:
        conditions.append("(e.employee_name LIKE %(search)s OR e.employee_number LIKE %(search)s)")
        values["search"] = f"%{search}%"
    if fixed_shift:
        conditions.append("e.hbos_fixed_shift = %(fixed_shift)s")
        values["fixed_shift"] = fixed_shift
    where = " AND ".join(conditions)
    rows = frappe.db.sql(f"""
        SELECT e.name, e.employee_name, e.employee_number, e.department,
               e.cell_number, e.image, e.date_of_joining,
               e.hbos_fixed_shift, sr.shift_type, sr.start_time, sr.end_time
        FROM tabEmployee e
        LEFT JOIN `tabHBOS Shift Rule` sr ON sr.name = e.hbos_fixed_shift
        WHERE {where}
        ORDER BY e.department, e.employee_number
    """, values, as_dict=True)
    return rows


@frappe.whitelist()
def get_departments():
    """部门列表(带人数), 用于筛选下拉。"""
    _require_hr_read()
    rows = frappe.db.sql("""
        SELECT department, COUNT(*) cnt FROM tabEmployee
        WHERE status = 'Active' GROUP BY department ORDER BY department
    """, as_dict=True)
    return rows


@frappe.whitelist()
def get_shift_options():
    """生效中的班次规则(用于绑定下拉)。"""
    _require_hr_read()
    return frappe.db.get_all(
        "HBOS Shift Rule",
        filters={"status": "生效"},
        fields=["name", "rule_name", "shift_type", "start_time", "end_time"],
        order_by="rule_name",
    )


def _stable_rule_code(value):
    """Accept a stable rule_code or a legacy concrete Shift Rule docname."""
    value = str(value or "").strip()
    if not value:
        return ""
    if frappe.db.exists("HBOS Shift Rule", {"rule_code": value}):
        return value
    if frappe.db.exists("HBOS Shift Rule", value):
        return frappe.db.get_value("HBOS Shift Rule", value, "rule_code") or ""
    frappe.throw(f"班次规则不存在：{value}")


@frappe.whitelist()
def bind_shift(employee, shift_rule):
    """兼容入口：单班次绑定也统一写稳定 rule_code。"""
    _require_hr_write()
    import json
    from hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data import (
        bind_employee_shifts,
    )
    code = _stable_rule_code(shift_rule)
    return bind_employee_shifts(employee, json.dumps([code] if code else []))


@frappe.whitelist()
def bulk_bind_shift(employees, shift_rule):
    """兼容入口：批量绑定稳定 rule_code。"""
    _require_hr_write()
    import json
    from hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data import (
        bind_employee_shifts,
    )
    code = _stable_rule_code(shift_rule)
    names = [e.strip() for e in (employees or "").split(",") if e.strip()]
    bound = 0
    for emp in names:
        if frappe.db.exists("Employee", emp):
            bind_employee_shifts(emp, json.dumps([code] if code else []))
            bound += 1
    return {"bound": bound, "shift_rule": code or None}

