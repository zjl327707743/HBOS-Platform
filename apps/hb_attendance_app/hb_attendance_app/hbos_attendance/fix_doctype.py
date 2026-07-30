"""修复 Employee Checkin DocType，恢复 employee_name 的 fetch_from"""
import frappe
import json


def fix_doctype():
    hrms_path = "/home/frappe/frappe-bench/apps/hrms/hrms/hr/doctype/employee_checkin/employee_checkin.json"

    with open(hrms_path) as f:
        dt_json = json.load(f)

    # 恢复 employee_name 的 fetch_from
    for field in dt_json["fields"]:
        if field["fieldname"] == "employee_name":
            field["fetch_from"] = "employee.employee_name"
            print("Restored fetch_from on employee_name")

    # 确保自定义字段在 field_order 中
    fo = dt_json.get("field_order", [])
    custom_fields = ["hbos_delicloud_id", "hbos_employee_num", "hbos_dept_name",
                     "hbos_check_type", "hbos_terminal_sn"]
    for cf in custom_fields:
        if cf not in fo:
            fo.append(cf)
    dt_json["field_order"] = fo

    with open(hrms_path, "w") as f:
        json.dump(dt_json, f, indent=4)
    print("Saved doctype JSON")

    # 确保 DocField 表里 employee_name 的 fetch_from 正确
    frappe.db.set_value("DocField",
        {"parent": "Employee Checkin", "fieldname": "employee_name"},
        "fetch_from", "employee.employee_name")
    frappe.db.commit()
    print("Updated DocField employee_name.fetch_from")

    # 清除缓存
    frappe.clear_cache(doctype="Employee Checkin")
    frappe.clear_cache()
    print("Cleared caches")

    # 验证
    meta = frappe.get_meta("Employee Checkin")
    en_field = meta.get_field("employee_name")
    print(f"employee_name: fetch_from={en_field.fetch_from}")

    return "OK"