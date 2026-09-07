import frappe
import json
from pathlib import Path

MODULE = "HBOS Attendance"
WORKSPACE_TITLE = "海滨考勤工作台"
DESKTOP_LABEL = "海滨考勤"
DESKTOP_LOGO_URL = "/assets/hb_attendance_app/hbos-attendance-logo.svg"
PRIMARY_SIDEBAR_ITEMS = [
	{"label": "月度考勤汇总", "link_type": "Report", "link_to": "月度考勤汇总", "type": "Link", "icon": "milestone"},
	{"label": "班次管理", "link_type": "Page", "link_to": "hbos-shift-management", "type": "Link", "icon": "setting"},
	{"label": "人员管理", "link_type": "Page", "link_to": "hbos-employee-management", "type": "Link", "icon": "users"},
	{"label": "导入考勤机导出表", "link_type": "Page", "link_to": "hbos-attendance-import", "type": "Link", "icon": "upload"},
	{"label": "考勤异常仪表盘", "link_type": "Page", "link_to": "hbos-attendance-dashboard", "type": "Link", "icon": "dashboard"},
	{"label": "考勤导入日志", "link_type": "DocType", "link_to": "HBOS Attendance Import Log", "type": "Link", "icon": "list"},
	{"label": "飞书请假记录", "link_type": "DocType", "link_to": "HBOS Leave Record", "type": "Link", "icon": "leave"},
	{"label": "飞书加班记录", "link_type": "DocType", "link_to": "HBOS Overtime Record", "type": "Link", "icon": "clock"},
	{"label": "HBOS 打卡流水", "link_type": "Report", "link_to": "打卡流水", "type": "Link", "icon": "clock"},
	{"label": "HBOS 考勤结果", "link_type": "Report", "link_to": "考勤结果", "type": "Link", "icon": "calendar-check"},
	{"label": "月度汇总 / 对账暂存", "link_type": "Report", "link_to": "HBOS 月度汇总暂存（对账）", "type": "Link", "icon": "clipboard-list"},
]


def after_migrate():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({
        "Employee Checkin": [
            {"fieldname": "hbos_source_type", "label": "HBOS 来源类型", "fieldtype": "Select",
             "options": "HBOS raw checkin import\nHBOS monthly adapter\nHRMS native / existing", "read_only": 1},
            {"fieldname": "hbos_import_log", "label": "HBOS 导入批次", "fieldtype": "Link",
             "options": "HBOS Attendance Import Log", "read_only": 1},
            {"fieldname": "hbos_calc_version", "label": "HBOS 计算版本", "fieldtype": "Data", "read_only": 1},
        ],
        "Attendance": [
            {"fieldname": "hbos_source_type", "label": "HBOS 来源类型", "fieldtype": "Select",
             "options": "HRMS Auto Attendance\nHBOS fallback\nMonthly Summary staging\nManual correction", "read_only": 1},
            {"fieldname": "hbos_import_log", "label": "HBOS 导入批次", "fieldtype": "Link",
             "options": "HBOS Attendance Import Log", "read_only": 1},
            {"fieldname": "hbos_fallback_generated", "label": "HBOS 兜底生成", "fieldtype": "Check", "read_only": 1},
            {"fieldname": "hbos_calc_version", "label": "HBOS 计算版本", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "hbos_raw_reference", "label": "HBOS 原始引用", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "hbos_missing_out", "label": "HBOS 缺下班卡", "fieldtype": "Check", "read_only": 1},
        ]
    })
    sync_attendance_workspace()


def sync_attendance_workspace():
	"""以版本化 fixture 和运行态派生对象收敛海滨考勤入口。"""
	fixture = Path(__file__).parent / "workspace" / WORKSPACE_TITLE / f"{WORKSPACE_TITLE}.json"
	payload = json.loads(fixture.read_text())
	workspace = frappe.get_doc("Workspace", payload["name"]) if frappe.db.exists("Workspace", payload["name"]) else frappe.new_doc("Workspace")
	for field in ("app", "content", "icon", "is_hidden", "label", "module", "public", "sequence_id", "title", "type"):
		workspace.set(field, payload[field])
	for field in ("links", "roles", "shortcuts"):
		workspace.set(field, payload[field])
	workspace.save(ignore_permissions=True)
	_sync_sidebar(DESKTOP_LABEL)
	_sync_sidebar(WORKSPACE_TITLE)
	_sync_desktop_icon()
	_hide_stale_workspace_desktop_icon()


def _sync_sidebar(title):
	sidebar = frappe.get_doc("Workspace Sidebar", title) if frappe.db.exists("Workspace Sidebar", title) else frappe.new_doc("Workspace Sidebar")
	sidebar.title = title
	sidebar.header_icon = "calendar-check"
	sidebar.module = MODULE
	sidebar.standard = 0
	sidebar.app = ""
	sidebar.set("items", [_sidebar_home_item(), *PRIMARY_SIDEBAR_ITEMS])
	sidebar.save(ignore_permissions=True)


def _sidebar_home_item():
	return {"label": "海滨考勤工作台", "link_type": "Workspace", "link_to": WORKSPACE_TITLE, "type": "Link", "icon": "home"}


def _sync_desktop_icon():
	icon = frappe.get_doc("Desktop Icon", DESKTOP_LABEL) if frappe.db.exists("Desktop Icon", DESKTOP_LABEL) else frappe.new_doc("Desktop Icon")
	icon.label = DESKTOP_LABEL
	icon.icon_type = "Link"
	icon.link_type = "Workspace Sidebar"
	icon.link_to = DESKTOP_LABEL
	icon.sidebar = DESKTOP_LABEL
	icon.icon = "calendar-check"
	icon.logo_url = DESKTOP_LOGO_URL
	icon.icon_image = DESKTOP_LOGO_URL
	icon.bg_color = "blue"
	icon.hidden = 0
	icon.idx = 0
	icon.restrict_removal = 1
	icon.save(ignore_permissions=True)


def _hide_stale_workspace_desktop_icon():
	if frappe.db.exists("Desktop Icon", WORKSPACE_TITLE):
		stale_icon = frappe.get_doc("Desktop Icon", WORKSPACE_TITLE)
		stale_icon.hidden = 0
		stale_icon.parent_icon = DESKTOP_LABEL
		stale_icon.icon = "calendar-check"
		stale_icon.logo_url = DESKTOP_LOGO_URL
		stale_icon.icon_image = DESKTOP_LOGO_URL
		stale_icon.bg_color = "blue"
		stale_icon.save(ignore_permissions=True)
