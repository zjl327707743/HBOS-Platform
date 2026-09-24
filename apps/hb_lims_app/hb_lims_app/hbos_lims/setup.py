import json

import frappe
from pathlib import Path

MODULE = "HBOS LIMS"
WORKSPACE_TITLE = "海滨LIMS工作台"
DESKTOP_LABEL = "海滨LIMS"
DESKTOP_LOGO_URL = "/assets/hb_lims_app/hbos-lims-logo.svg"
# LIMS QA 为 M2-R7 方案 B 新增（Owner 2026-09-07 确认）：QA 线与 QC 线权限分离
# LIMS QA Manager / LIMS QP 为 M2-R8A 新增（Owner 2026-09-16 确认采纳方案 6.2）：
# QA 经理（一般变更批准）与质量受权人（重大变更批准）在权限层与 QA 审核人、Manager 分离。
# 人员权限、身份与群组管理后续统一设置，本轮只做角色结构性创建。
LIMS_ROLES = [
	"LIMS Manager", "LIMS Analyst", "LIMS Reviewer", "LIMS QA",
	"LIMS QA Manager", "LIMS QP",
]
# 侧边导航按业务模块分组（Section Break 分组 + collapsible 下拉 + child 子项），
# 与海滨LIMS工作台四卡片分区一一对应，由 Frappe 原生 Workspace Sidebar 渲染。
PRIMARY_SIDEBAR_ITEMS = [
	# —— 样品管理 ——
	{"label": "样品管理", "type": "Section Break", "collapsible": 1, "keep_closed": 0, "icon": "box"},
	{"label": "新建样品登记", "link_type": "DocType", "link_to": "HBOS Sample", "type": "Link", "icon": "box", "child": 1},
	{"label": "样品台账", "link_type": "Report", "link_to": "样品台账", "type": "Link", "icon": "list", "child": 1},
	{"label": "样品类型", "link_type": "DocType", "link_to": "HBOS Sample Type", "type": "Link", "icon": "tag", "child": 1},
	# —— 检验流程 ——
	{"label": "检验流程", "type": "Section Break", "collapsible": 1, "keep_closed": 1, "icon": "check-square"},
	{"label": "待检任务看板", "link_type": "Report", "link_to": "待检任务看板", "type": "Link", "icon": "kanban", "child": 1},
	{"label": "检验任务", "link_type": "DocType", "link_to": "HBOS Sample Task", "type": "Link", "icon": "list", "child": 1},
	{"label": "检验结果清单", "link_type": "Report", "link_to": "检验结果清单", "type": "Link", "icon": "flask", "child": 1},
	{"label": "检测记录", "link_type": "DocType", "link_to": "HBOS Test Result", "type": "Link", "icon": "file-text", "child": 1},
	# —— 报告管理 ——
	{"label": "报告管理", "type": "Section Break", "collapsible": 1, "keep_closed": 1, "icon": "file-text"},
	{"label": "新建检验报告书", "link_type": "DocType", "link_to": "HBOS COA", "type": "Link", "icon": "file-plus", "child": 1},
	{"label": "COA 发布记录", "link_type": "Report", "link_to": "COA 发布记录", "type": "Link", "icon": "paper-plane", "child": 1},
	# —— 质量主数据 ——
	{"label": "质量主数据", "type": "Section Break", "collapsible": 1, "keep_closed": 1, "icon": "book"},
	{"label": "质量标准", "link_type": "DocType", "link_to": "HBOS Specification", "type": "Link", "icon": "book", "child": 1},
	{"label": "检验项目", "link_type": "DocType", "link_to": "HBOS Test Item", "type": "Link", "icon": "list", "child": 1},
	{"label": "计算公式", "link_type": "DocType", "link_to": "HBOS Calculation", "type": "Link", "icon": "calculator", "child": 1},
	{"label": "检验组", "link_type": "DocType", "link_to": "HBOS Lab Department", "type": "Link", "icon": "users", "child": 1},
	# —— 留样管理 ——
	{"label": "留样管理", "type": "Section Break", "collapsible": 1, "keep_closed": 0, "icon": "archive"},
	{"label": "留样登记", "link_type": "DocType", "link_to": "HBOS Retention Sample", "type": "Link", "icon": "archive", "child": 1},
	{"label": "留样台账", "link_type": "Report", "link_to": "留样台账", "type": "Link", "icon": "list", "child": 1},
	{"label": "留样产品", "link_type": "DocType", "link_to": "HBOS Retention Product", "type": "Link", "icon": "tag", "child": 1},
	# —— 审计追踪 ——
	{"label": "审计追踪", "type": "Section Break", "collapsible": 1, "keep_closed": 1, "icon": "history"},
	{"label": "审计追踪查询", "link_type": "Report", "link_to": "审计追踪查询", "type": "Link", "icon": "search", "child": 1},
	{"label": "结果修订记录", "link_type": "DocType", "link_to": "HBOS Result Revision", "type": "Link", "icon": "history", "child": 1},
]


def after_migrate():
	"""M2-LIMS 入口单一同步点：幂等创建角色并同步工作台 / 侧边栏 / 桌面图标。"""
	for role in LIMS_ROLES:
		_sync_role(role)
	sync_lims_workspace()


def sync_user_perm_can_read_cache(bootinfo=None):
	"""Workaround（Frappe v16.26.3 核心 bug）：WorkspaceSidebar.get_can_read_items()
	缺少 return，user_perm_can_read 缓存恒为 None，导致非 Administrator 用户
	侧边栏中所有 DocType 项被 is_item_allowed 过滤（仅报表/看板项可见）。

	方案：在 boot_session hook 中按用户预置该缓存（与 frappe 原生的 6 小时
	缓存同 key/同语义），侧边栏 DocType 项恢复按角色权限展示。缓存值本身
	由 Frappe 权限系统计算，不改动权限语义；frappe 升级修复后此预置无副作用。
	"""
	user = frappe.get_user()
	if not user.can_read:
		user.build_permissions()
	frappe.cache.set_value("user_perm_can_read", user.can_read, frappe.session.user, 21600)


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
	"""Desk 桌面图标：点击进入 HBOS LIMS 独立 Vue 前端（/hbos-lims）。
	Frappe v16 Desktop Icon link_type 支持 External，link 指向独立前端根路径，
	点击在新标签页打开；after_migrate 幂等同步。"""
	icon = frappe.get_doc("Desktop Icon", DESKTOP_LABEL) if frappe.db.exists("Desktop Icon", DESKTOP_LABEL) else frappe.new_doc("Desktop Icon")
	icon.label = DESKTOP_LABEL
	icon.icon_type = "Link"
	icon.link_type = "External"
	icon.link = "/hbos-lims/dashboard"
	# 关键：sidebar 字段必须为空，否则 Frappe DesktopIcon 构造函数不会计算
	# icon_route（`!this.icon_data.sidebar`），External 跳转不生效。
	icon.sidebar = ""
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
		stale_icon.bg_color = "blue"
		stale_icon.save(ignore_permissions=True)
