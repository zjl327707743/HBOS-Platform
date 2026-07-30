import frappe
import json


def patch_employee_checkin_doctype():
    """修补 HRMS Employee Checkin DocType，允许不关联 Employee"""

    # 1. 保证自定义字段都已存在
    custom_fields = [
        {"fieldname": "hbos_delicloud_id", "label": "得力云记录ID", "fieldtype": "Data",
         "insert_after": "employee_name", "read_only": 1, "in_list_view": 1,
         "allow_in_quick_entry": 0, "translatable": 0},
        {"fieldname": "hbos_employee_num", "label": "工号", "fieldtype": "Data",
         "insert_after": "hbos_delicloud_id", "read_only": 1, "in_list_view": 1,
         "allow_in_quick_entry": 0, "translatable": 0},
        {"fieldname": "hbos_dept_name", "label": "部门", "fieldtype": "Data",
         "insert_after": "hbos_employee_num", "read_only": 1, "in_list_view": 1,
         "allow_in_quick_entry": 0, "translatable": 0},
        {"fieldname": "hbos_check_type", "label": "打卡方式", "fieldtype": "Data",
         "insert_after": "log_type", "read_only": 1, "in_list_view": 1,
         "allow_in_quick_entry": 0, "translatable": 0},
        {"fieldname": "hbos_terminal_sn", "label": "设备SN", "fieldtype": "Data",
         "insert_after": "device_id", "read_only": 1, "in_list_view": 1,
         "allow_in_quick_entry": 0, "translatable": 0},
    ]

    for f in custom_fields:
        existing = frappe.db.get_value("Custom Field", {"dt": "Employee Checkin", "fieldname": f["fieldname"]}, "name")
        if not existing:
            frappe.get_doc({"doctype": "Custom Field", "dt": "Employee Checkin", **f}).insert(ignore_permissions=True)
            print(f"  Created Custom Field: {f['fieldname']}")
        else:
            # Update in_list_view flag
            frappe.db.set_value("Custom Field", existing, "in_list_view", 1)
            frappe.db.set_value("Custom Field", existing, "read_only", 1)
            print(f"  Updated Custom Field: {f['fieldname']}")

    frappe.db.commit()

    # 2. 修补 HRMS DocType: 取消 employee 的 require 和 fetch_from
    dt_name = "Employee Checkin"
    hrms_path = "/home/frappe/frappe-bench/apps/hrms/hrms/hr/doctype/employee_checkin/employee_checkin.json"

    try:
        with open(hrms_path) as f:
            dt_json = json.load(f)
    except Exception:
        print("Cannot read HRMS doctype JSON, will patch via DB")
        dt_json = None

    # Patch the employee field to remove reqd
    patched = False
    if dt_json:
        for field in dt_json.get("fields", []):
            if field.get("fieldname") == "employee":
                if field.get("reqd"):
                    field["reqd"] = 0
                    print("  Patched employee.reqd from 1 to 0 in HRMS JSON")
                    patched = True
                if "fetch_from" in field:
                    del field["fetch_from"]
                    print("  Removed fetch_from from employee field")
                    patched = True
            if field.get("fieldname") == "employee_name":
                if "fetch_from" in field:
                    del field["fetch_from"]
                    print("  Removed fetch_from from employee_name field")
                    patched = True

        if patched:
            with open(hrms_path, "w") as f:
                json.dump(dt_json, f, indent=4)
            print("  Saved patched HRMS doctype JSON")

    # 3. Patch via frappe.db to make reqd=0
    frappe.db.set_value("DocField", {"parent": "Employee Checkin", "fieldname": "employee"}, "reqd", 0)
    frappe.db.commit()
    print("  Patched DocField: employee.reqd = 0")

    # 4. Add custom fields to Employee Checkin list view settings
    lv_name = "Employee Checkin"
    try:
        frappe.db.sql("""
            DELETE FROM `tabList View Settings` WHERE name = %s
        """, (lv_name,))
    except Exception:
        pass
    frappe.db.commit()

    # 5. Clear all caches
    frappe.clear_cache(doctype="Employee Checkin")
    frappe.clear_cache()
    print("  Cleared caches")

    # 6. Verify
    meta = frappe.get_meta("Employee Checkin")
    emp_field = meta.get_field("employee")
    if emp_field:
        print(f"  employee field: reqd={emp_field.reqd}, fetch_from={emp_field.fetch_from}")
    custom_fns = [f.fieldname for f in meta.fields if f.fieldname.startswith("hbos_")]
    print(f"  Custom fields on meta: {custom_fns}")

    return "OK"