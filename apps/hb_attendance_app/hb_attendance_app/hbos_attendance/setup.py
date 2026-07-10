import frappe
import json
from pathlib import Path

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
    sync_attendance_workspace()


def sync_attendance_workspace():
	"""以受版本控制的 fixture 覆盖早期仅含标题的公共工作台。"""
	fixture = Path(__file__).parent / "workspace" / "海滨考勤工作台" / "海滨考勤工作台.json"
	payload = json.loads(fixture.read_text())
	workspace = frappe.get_doc("Workspace", payload["name"]) if frappe.db.exists("Workspace", payload["name"]) else frappe.new_doc("Workspace")
	for field in ("app", "content", "icon", "is_hidden", "label", "module", "public", "sequence_id", "title", "type"):
		workspace.set(field, payload[field])
	for field in ("links", "roles", "shortcuts"):
		workspace.set(field, payload[field])
	workspace.save(ignore_permissions=True)
