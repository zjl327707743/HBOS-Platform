import json

import frappe
from pathlib import Path

MODULE = "HBOS LIMS"
WORKSPACE_TITLE = "海滨LIMS工作台"
DESKTOP_LABEL = "海滨LIMS"
DESKTOP_LOGO_URL = "/assets/hb_lims_app/hbos-lims-logo.svg"
LIMS_ROLES = ["LIMS Manager", "LIMS Analyst", "LIMS Reviewer"]
PRIMARY_SIDEBAR_ITEMS = []  # R2+ 轮次填充：样品登记 / 待检任务看板 / 检验结果清单 / 质量标准等


def after_migrate():
	"""M2-LIMS 入口单一同步点：幂等创建角色并同步工作台 / 侧边栏 / 桌面图标。"""
	for role in LIMS_ROLES:
		_sync_role(role)
	sync_lims_workspace()


def _sync_role(role_name):
	if frappe.db.exists("Role", role_name):
		return
	role = frappe.new_doc("Role")
	role.role_name = role_name
	role.desk_access = 1
	role.restrict_to_domain = None
	role.save(ignore_permissions=True)


def sync_lims_workspace():
	"""以版本化 fixture 和运行态派生对象收敛海滨LIMS入口（M1-FIX-B4 方案 A 模式）。"""
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
	sidebar.header_icon = "flask"
	sidebar.module = MODULE
	sidebar.standard = 0
	sidebar.app = ""
	sidebar.set("items", [_sidebar_home_item(), *PRIMARY_SIDEBAR_ITEMS])
	sidebar.save(ignore_permissions=True)


def _sidebar_home_item():
	return {"label": "海滨LIMS工作台", "link_type": "Workspace", "link_to": WORKSPACE_TITLE, "type": "Link", "icon": "home"}


def _sync_desktop_icon():
	icon = frappe.get_doc("Desktop Icon", DESKTOP_LABEL) if frappe.db.exists("Desktop Icon", DESKTOP_LABEL) else frappe.new_doc("Desktop Icon")
	icon.label = DESKTOP_LABEL
	icon.icon_type = "Link"
	icon.link_type = "Workspace Sidebar"
	icon.link_to = DESKTOP_LABEL
	icon.sidebar = DESKTOP_LABEL
	icon.icon = "flask"
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
		stale_icon.icon = "flask"
		stale_icon.logo_url = DESKTOP_LOGO_URL
		stale_icon.icon_image = DESKTOP_LOGO_URL
		stale_icon.bg_color = "green"
		stale_icon.save(ignore_permissions=True)
