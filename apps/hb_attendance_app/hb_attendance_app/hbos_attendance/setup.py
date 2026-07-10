import frappe

def after_migrate():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({
        "Attendance": [
            {"fieldname": "hbos_source_type", "label": "HBOS 来源类型", "fieldtype": "Select",
             "options": "HRMS Auto Attendance\nHBOS fallback\nMonthly Summary staging\nManual correction", "read_only": 1},
            {"fieldname": "hbos_import_log", "label": "HBOS 导入批次", "fieldtype": "Link",
             "options": "HBOS Attendance Import Log", "read_only": 1},
            {"fieldname": "hbos_fallback_generated", "label": "HBOS 兜底生成", "fieldtype": "Check", "read_only": 1},
            {"fieldname": "hbos_calc_version", "label": "HBOS 计算版本", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "hbos_raw_reference", "label": "HBOS 原始引用", "fieldtype": "Data", "read_only": 1},
        ]
    })
