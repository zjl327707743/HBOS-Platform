import frappe


@frappe.whitelist()
def get_employees(department=None, search=None, fixed_shift=None):
    """人员列表: 工号/姓名/部门/联系方式/固定班次。

    filters: department(可选), search(姓名/工号模糊), fixed_shift(可选)
    """
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
    rows = frappe.db.sql("""
        SELECT department, COUNT(*) cnt FROM tabEmployee
        WHERE status = 'Active' GROUP BY department ORDER BY department
    """, as_dict=True)
    return rows


@frappe.whitelist()
def get_shift_options():
    """生效中的班次规则(用于绑定下拉)。"""
    return frappe.db.get_all(
        "HBOS Shift Rule",
        filters={"status": "生效"},
        fields=["name", "rule_name", "shift_type", "start_time", "end_time"],
        order_by="rule_name",
    )


@frappe.whitelist()
def bind_shift(employee, shift_rule):
    """绑定/解绑固定班次。shift_rule 传空字符串 = 解绑。"""
    if shift_rule:
        frappe.db.set_value("Employee", employee, "hbos_fixed_shift", shift_rule,
                            update_modified=False)
    else:
        frappe.db.set_value("Employee", employee, "hbos_fixed_shift", None,
                            update_modified=False)
    frappe.db.commit()
    return {"employee": employee, "shift_rule": shift_rule or None}


@frappe.whitelist()
def bulk_bind_shift(employees, shift_rule):
    """批量绑定固定班次。employees: 逗号分隔的员工名列表。"""
    names = [e.strip() for e in (employees or "").split(",") if e.strip()]
    bound = 0
    for emp in names:
        if frappe.db.exists("Employee", emp):
            frappe.db.set_value("Employee", emp, "hbos_fixed_shift", shift_rule,
                                update_modified=False)
            bound += 1
    frappe.db.commit()
    return {"bound": bound, "shift_rule": shift_rule}
