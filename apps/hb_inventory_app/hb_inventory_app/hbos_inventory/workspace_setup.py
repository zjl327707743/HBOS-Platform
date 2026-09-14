"""仓储库存工作台入口同步（幂等）

补 M3-R2 遗漏的「入口」交付项：让仓库人员能直接从 Desk 触达
入库登记、批次、货位与各报表，而无需记忆 DocType 名称。

以代码方式同步 Workspace + Workspace Sidebar + Desktop Icon，
沿用 `hb_attendance_app` 的既有做法（`after_migrate` 钩子调用，幂等）。
"""

import json

import frappe

MODULE = "HBOS Inventory"
WORKSPACE_TITLE = "仓储库存工作台"
DESKTOP_LABEL = "仓储库存"
DESKTOP_ICON = "stock"

SIDEBAR_ITEMS = [
	{"label": "仓储库存工作台", "link_type": "Workspace", "link_to": WORKSPACE_TITLE, "type": "Link", "icon": "home"},
	# 入库登记：走原生 Stock Entry（Material Receipt）表单
	{"label": "入库登记", "link_type": "DocType", "link_to": "Stock Entry", "type": "Link", "icon": "stock-entry"},
	# 出库核销：走原生 Stock Entry（Material Issue）表单，受 QA 放行门禁约束
	{"label": "出库核销", "link_type": "DocType", "link_to": "Stock Entry", "type": "Link", "icon": "stock-entry"},
	# 货位变更：走原生 Stock Entry（Material Transfer）表单
	{"label": "货位变更", "link_type": "DocType", "link_to": "Stock Entry", "type": "Link", "icon": "stock-entry"},
	{"label": "批次", "link_type": "DocType", "link_to": "Batch", "type": "Link", "icon": "file"},
	{"label": "物料", "link_type": "DocType", "link_to": "Item", "type": "Link", "icon": "stock"},
	{"label": "货位", "link_type": "DocType", "link_to": "Warehouse", "type": "Link", "icon": "organization"},
	{"label": "按批号查货位", "link_type": "Report", "link_to": "按批号查货位", "type": "Link", "icon": "search"},
	{"label": "货位明细表", "link_type": "Report", "link_to": "货位明细表", "type": "Link", "icon": "list"},
	{"label": "效期预警", "link_type": "Report", "link_to": "效期预警", "type": "Link", "icon": "milestone"},
	{"label": "库级盘点三对账", "link_type": "Report", "link_to": "库级盘点三对账", "type": "Link", "icon": "clipboard-list"},
]

WORKSPACE_CONTENT = """[
 {"id":"hdr","type":"header","data":{"text":"<span class=\\"h4\\"><b>仓储库存</b></span>","col":12}},
 {"id":"sb1","type":"paragraph","data":{"text":"入库登记、出库核销、货位变更均使用 ERPNext 原生库存单据；出库须先取得 QA 放行与合格证。","col":12}},
 {"id":"sc_in","type":"shortcut","data":{"shortcut_name":"入库登记","col":3}},
 {"id":"sc_out","type":"shortcut","data":{"shortcut_name":"出库核销","col":3}},
 {"id":"sc_mv","type":"shortcut","data":{"shortcut_name":"货位变更","col":3}},
 {"id":"sc_bt","type":"shortcut","data":{"shortcut_name":"批次","col":3}},
 {"id":"sp1","type":"spacer","data":{"col":12}},
 {"id":"cd_q","type":"card","data":{"card_name":"查询与台账","col":12}},
 {"id":"r1","type":"paragraph","data":{"text":"按批号查货位、货位明细表——批次与货位的双向查询。","col":12}},
 {"id":"sp2","type":"spacer","data":{"col":12}},
 {"id":"cd_m","type":"card","data":{"card_name":"效期与盘点","col":12}},
 {"id":"r2","type":"paragraph","data":{"text":"效期预警按产品质量标准的到期日提前预警；库级盘点三对账用于导出后现场盘点。","col":12}}
]"""

WORKSPACE_LINKS = [
	{"label": "查询与台账", "type": "Card Break", "hidden": 0, "is_query_report": 0, "link_count": 2},
	{"label": "按批号查货位", "type": "Link", "link_type": "Report", "link_to": "按批号查货位", "hidden": 0, "is_query_report": 1, "link_count": 0},
	{"label": "货位明细表", "type": "Link", "link_type": "Report", "link_to": "货位明细表", "hidden": 0, "is_query_report": 1, "link_count": 0},
	{"label": "效期与盘点", "type": "Card Break", "hidden": 0, "is_query_report": 0, "link_count": 2},
	{"label": "效期预警", "type": "Link", "link_type": "Report", "link_to": "效期预警", "hidden": 0, "is_query_report": 1, "link_count": 0},
	{"label": "库级盘点三对账", "type": "Link", "link_type": "Report", "link_to": "库级盘点三对账", "hidden": 0, "is_query_report": 1, "link_count": 0},
	{"label": "基础数据", "type": "Card Break", "hidden": 0, "is_query_report": 0, "link_count": 3},
	{"label": "批次", "type": "Link", "link_type": "DocType", "link_to": "Batch", "hidden": 0, "is_query_report": 0, "link_count": 0},
	{"label": "物料", "type": "Link", "link_type": "DocType", "link_to": "Item", "hidden": 0, "is_query_report": 0, "link_count": 0},
	{"label": "货位", "type": "Link", "link_type": "DocType", "link_to": "Warehouse", "hidden": 0, "is_query_report": 0, "link_count": 0},
]


def _parse_content(payload):
	if not payload:
		return []

	return json.loads(payload)


def sync_inventory_workspace():
	"同步 Workspace、入口快捷方式、侧边栏与桌面图标（幂等）。"

	workspace = (
		frappe.get_doc("Workspace", WORKSPACE_TITLE)
		if frappe.db.exists("Workspace", WORKSPACE_TITLE)
		else frappe.new_doc("Workspace")
	)
	workspace.title = WORKSPACE_TITLE
	workspace.label = WORKSPACE_TITLE
	workspace.module = MODULE
	workspace.app = "hb_inventory_app"
	workspace.icon = DESKTOP_ICON
	workspace.public = 1
	workspace.is_hidden = 0
	workspace.sequence_id = 1.0
	workspace.type = "Workspace"
	workspace.content = json.dumps(_parse_content(WORKSPACE_CONTENT))

	workspace.set("shortcuts", [
		{"label": "入库登记", "type": "DocType", "link_to": "Stock Entry", "color": "Blue", "doc_view": ""},
		{"label": "出库核销", "type": "DocType", "link_to": "Stock Entry", "color": "Blue", "doc_view": ""},
		{"label": "货位变更", "type": "DocType", "link_to": "Stock Entry", "color": "Gray", "doc_view": ""},
		{"label": "批次", "type": "DocType", "link_to": "Batch", "color": "Gray", "doc_view": ""},
	])
	workspace.set("links", WORKSPACE_LINKS)
	workspace.set("roles", [{"role": "System Manager"}, {"role": "Stock Manager"}, {"role": "Stock User"}])
	workspace.save(ignore_permissions=True)

	_sync_sidebar()
	_sync_desktop_icon()


def _sync_sidebar():
	sidebar = (
		frappe.get_doc("Workspace Sidebar", WORKSPACE_TITLE)
		if frappe.db.exists("Workspace Sidebar", WORKSPACE_TITLE)
		else frappe.new_doc("Workspace Sidebar")
	)
	sidebar.title = WORKSPACE_TITLE
	sidebar.header_icon = DESKTOP_ICON
	sidebar.module = MODULE
	sidebar.standard = 0
	sidebar.app = ""
	sidebar.set("items", SIDEBAR_ITEMS)
	sidebar.save(ignore_permissions=True)


def _sync_desktop_icon():
	# 桌面图标的 link_to / sidebar 必须指向已存在的 Workspace Sidebar，
	# 否则抛 LinkValidationError（此处指向与 _sync_sidebar 同名的工作台）。
	icon = (
		frappe.get_doc("Desktop Icon", DESKTOP_LABEL)
		if frappe.db.exists("Desktop Icon", DESKTOP_LABEL)
		else frappe.new_doc("Desktop Icon")
	)
	icon.label = DESKTOP_LABEL
	icon.icon_type = "Link"
	icon.link_type = "Workspace Sidebar"
	icon.link_to = WORKSPACE_TITLE
	icon.sidebar = WORKSPACE_TITLE
	icon.icon = DESKTOP_ICON
	icon.bg_color = "blue"
	icon.hidden = 0
	icon.idx = 1
	icon.restrict_removal = 1
	icon.save(ignore_permissions=True)
