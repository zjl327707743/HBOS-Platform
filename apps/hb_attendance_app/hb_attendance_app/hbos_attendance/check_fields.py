import frappe

def check_fields():
    # Check if custom fields are properly registered
    for fn in ["hbos_delicloud_id", "hbos_employee_num", "hbos_dept_name", "hbos_check_type", "hbos_terminal_sn"]:
        cf = frappe.db.get_value("Custom Field", {"dt": "Employee Checkin", "fieldname": fn}, ["name", "fieldname", "label", "in_list_view", "insert_after"], as_dict=1)
        print(f"  CF: {cf}")

    # Force refresh DocType
    frappe.clear_cache(doctype="Employee Checkin")
    meta = frappe.get_meta("Employee Checkin")
    print(f"\nDocType fields with hbos_: {[f.fieldname for f in meta.fields if f.fieldname.startswith('hbos_')]}")

    # Sample data
    print("\n--- Sample data ---")
    for r in frappe.db.sql("SELECT employee_name, hbos_employee_num, hbos_dept_name, hbos_check_type, hbos_terminal_sn, time, device_id FROM `tabEmployee Checkin` LIMIT 3", as_dict=1):
        print(r)