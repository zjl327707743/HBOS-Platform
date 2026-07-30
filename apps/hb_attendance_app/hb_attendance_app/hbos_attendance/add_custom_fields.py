import frappe

def add_custom_fields():
    fields = [
        {"fieldname": "hbos_delicloud_id", "label": "得力云记录ID", "fieldtype": "Data", "insert_after": "employee_name", "read_only": 1, "in_list_view": 1},
        {"fieldname": "hbos_employee_num", "label": "工号", "fieldtype": "Data", "insert_after": "hbos_delicloud_id", "read_only": 1, "in_list_view": 1},
        {"fieldname": "hbos_dept_name", "label": "部门", "fieldtype": "Data", "insert_after": "hbos_employee_num", "read_only": 1, "in_list_view": 1},
        {"fieldname": "hbos_check_type", "label": "打卡方式", "fieldtype": "Data", "insert_after": "log_type", "read_only": 1, "in_list_view": 1},
        {"fieldname": "hbos_terminal_sn", "label": "设备SN", "fieldtype": "Data", "insert_after": "device_id", "read_only": 1, "in_list_view": 1},
    ]

    for f in fields:
        if not frappe.db.exists("Custom Field", f"Employee Checkin-{f['fieldname']}"):
            cf = frappe.get_doc({"doctype": "Custom Field", "dt": "Employee Checkin", **f})
            cf.insert(ignore_permissions=True)
            print(f"  Created: {f['fieldname']}")
        else:
            print(f"  Exists: {f['fieldname']}")

    frappe.db.commit()
    print("Custom fields done")