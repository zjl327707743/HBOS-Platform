import frappe

def fix_frontend():
    """修复 Employee Checkin 前端展示问题"""

    # 1. 恢复员工姓名自动获取
    frappe.db.set_value("DocField",
        {"parent": "Employee Checkin", "fieldname": "employee_name"},
        "fetch_from", "employee.employee_name")
    frappe.db.commit()

    # 2. 确保 employee 字段可空
    frappe.db.set_value("DocField",
        {"parent": "Employee Checkin", "fieldname": "employee"},
        "reqd", 0)
    frappe.db.commit()

    # 3. 确保所有 hbos_ 自定义字段正确
    for fn, label, insert_after in [
        ("hbos_delicloud_id", "得力云记录ID", "employee_name"),
        ("hbos_employee_num", "工号", "hbos_delicloud_id"),
        ("hbos_dept_name", "部门", "hbos_employee_num"),
        ("hbos_check_type", "打卡方式", "log_type"),
        ("hbos_terminal_sn", "设备SN", "device_id"),
    ]:
        cf_name = f"Employee Checkin-{fn}"
        if frappe.db.exists("Custom Field", cf_name):
            frappe.db.set_value("Custom Field", cf_name, {
                "in_list_view": 1,
                "read_only": 1,
                "insert_after": insert_after,
            })
        else:
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "Employee Checkin",
                "fieldname": fn, "label": label,
                "fieldtype": "Data",
                "insert_after": insert_after,
                "read_only": 1, "in_list_view": 1,
            }).insert(ignore_permissions=True)
    frappe.db.commit()

    # 4. 修复 HRMS doctype JSON
    import json
    hrms_path = "/home/frappe/frappe-bench/apps/hrms/hrms/hr/doctype/employee_checkin/employee_checkin.json"
    with open(hrms_path) as f:
        dt = json.load(f)

    # 恢复 employee_name fetch_from
    for field in dt["fields"]:
        if field["fieldname"] == "employee_name":
            field["fetch_from"] = "employee.employee_name"
        if field["fieldname"] == "employee":
            field["reqd"] = 0
            if "fetch_from" in field:
                del field["fetch_from"]

    # 确保 field_order 包含所有自定义字段
    fo = dt.setdefault("field_order", [])
    for fn in ["hbos_delicloud_id", "hbos_employee_num", "hbos_dept_name",
               "hbos_check_type", "hbos_terminal_sn"]:
        if fn not in fo:
            fo.append(fn)

    dt["field_order"] = fo
    with open(hrms_path, "w") as f:
        json.dump(dt, f, indent=4)

    # 5. 清除所有缓存
    frappe.clear_cache(doctype="Employee Checkin")
    frappe.db.commit()
    frappe.clear_cache()

    # 6. 重建系统文档
    from frappe.modules.utils import sync_customizations
    sync_customizations("hrms")

    print("Frontend fix applied successfully")
    print(f"employee_name: fetch_from=employee.employee_name, reqd=0")
    print(f"employee: reqd=0")

    return "OK"