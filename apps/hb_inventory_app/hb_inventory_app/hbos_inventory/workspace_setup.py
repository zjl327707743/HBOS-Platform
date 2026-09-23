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

# 桌面图标的 label **必须等于某个已存在的 `Workspace Sidebar` 名**。
# Frappe 的 `get_desktop_icons()` 会拿 `label.lower()` 去
# `bootinfo.workspace_sidebar_item` 里查，**查不到就直接丢弃这个图标**——
# 不报错、不提示，图标就是不出现。
#
# 曾用 `仓储库存` 当 label（短名好看），但本 App 的侧边栏叫 `仓储库存工作台`，
# 于是查不到、图标始终不显示 —— Owner 反馈「桌面上没有入口、回不来」即此。
# 工作台、侧边栏、桌面图标三者用**同一个名字**，与 ERPNext 原生 Stock 的做法一致。
DESKTOP_LABEL = WORKSPACE_TITLE

# 不能用 "stock"——那是 ERPNext 原生 Stock 模块的图标，桌面上两个一模一样的
# 图形并排，点错就进了原生库存模块，而那边没有本 App 的侧边栏，回不来。
# 换成语义贴切的 warehouse，与原生 Stock 一眼可分。
DESKTOP_ICON = "warehouse"

# 本 App 早期留下的、不指向任何 `Workspace Sidebar` 的桌面图标名。
# 这类图标会被 Frappe 静默丢弃（见 DESKTOP_LABEL 处说明），需要清掉。
STALE_DESKTOP_LABELS = ("仓储库存",)

SIDEBAR_ITEMS = [
	{"label": "仓储库存工作台", "link_type": "Workspace", "link_to": WORKSPACE_TITLE, "type": "Link", "icon": "home"},
	# 入库拍照识别：本 App 的 Desk 页面（拍照 → 识别 → 校对 → 生成草稿）
	{"label": "入库拍照识别", "link_type": "Page", "link_to": "hbos-photo-intake", "type": "Link", "icon": "camera"},
	# 入库登记：走原生 Stock Entry（Material Receipt）表单
	{"label": "入库登记（原生）", "link_type": "DocType", "link_to": "Stock Entry", "type": "Link", "icon": "stock-entry"},
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
	{"label": "货位二维码（在货位上打印）", "link_type": "DocType", "link_to": "Warehouse", "type": "Link", "icon": "qr-code"},
]

WORKSPACE_CONTENT = """[
 {"id":"hdr","type":"header","data":{"text":"<span class=\\"h4\\"><b>仓储库存</b></span>","col":12}},
 {"id":"sb1","type":"paragraph","data":{"text":"入库可走「入库拍照识别」（拍照 → 识别 → 人工校对 → 生成草稿）；出库核销与货位变更使用 ERPNext 原生库存单据；出库须先取得 QA 放行与合格证。","col":12}},
 {"id":"sc_photo","type":"shortcut","data":{"shortcut_name":"入库拍照识别","col":3}},
 {"id":"sc_in","type":"shortcut","data":{"shortcut_name":"入库登记（原生）","col":3}},
 {"id":"sc_out","type":"shortcut","data":{"shortcut_name":"出库核销","col":3}},
 {"id":"sc_mv","type":"shortcut","data":{"shortcut_name":"货位变更","col":3}},
 {"id":"sc_bt","type":"shortcut","data":{"shortcut_name":"批次","col":3}},
 {"id":"sp1","type":"spacer","data":{"col":12}},
 {"id":"cd_q","type":"card","data":{"card_name":"查询与台账","col":12}},
 {"id":"r1","type":"paragraph","data":{"text":"按批号查货位、货位明细表——批次与货位的双向查询。","col":12}},
 {"id":"sp2","type":"spacer","data":{"col":12}},
 {"id":"cd_m","type":"card","data":{"card_name":"效期与盘点","col":12}},
 {"id":"r2","type":"paragraph","data":{"text":"效期预警按产品质量标准的到期日提前预警；库级盘点三对账用于导出后现场盘点。","col":12}},
 {"id":"cd_p","type":"card","data":{"card_name":"打印与二维码","col":12}},
 {"id":"r3","type":"paragraph","data":{"text":"批次上可打印待检证与货位卡（自产 / 外购两种版式）；货位上可打印货位二维码，贴于货架，手机扫码即可查看该货位在库明细（需登录）。","col":12}}
]"""

WORKSPACE_LINKS = [
	{"label": "入库", "type": "Card Break", "hidden": 0, "is_query_report": 0, "link_count": 1},
	{"label": "入库拍照识别", "type": "Link", "link_type": "Page", "link_to": "hbos-photo-intake", "hidden": 0, "is_query_report": 0, "link_count": 0},
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
		{"label": "入库拍照识别", "type": "Page", "link_to": "hbos-photo-intake", "color": "Blue", "doc_view": ""},
		{"label": "入库登记（原生）", "type": "DocType", "link_to": "Stock Entry", "color": "Gray", "doc_view": ""},
		{"label": "出库核销", "type": "DocType", "link_to": "Stock Entry", "color": "Blue", "doc_view": ""},
		{"label": "货位变更", "type": "DocType", "link_to": "Stock Entry", "color": "Gray", "doc_view": ""},
		{"label": "批次", "type": "DocType", "link_to": "Batch", "color": "Gray", "doc_view": ""},
	])
	workspace.set("links", WORKSPACE_LINKS)
	workspace.set("roles", [{"role": "System Manager"}, {"role": "Stock Manager"}, {"role": "Stock User"}])
	workspace.save(ignore_permissions=True)

	_sync_sidebar()
	_sync_desktop_icon()
	_cleanup_stale_desktop_icons()


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
	#
	# label 也必须等于该侧边栏名，否则 `get_desktop_icons()` 会静默丢弃
	# 这个图标（见 DESKTOP_LABEL 处的说明）。这里三者同源，天然满足。
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
	# **必须显式清空**：`parent_icon` 若残留指向一个已被删掉/不显示的父图标，
	# Frappe 会把本图标一起过滤掉（父不在 permitted 集合里 → 子也出不来）。
	# 早期版本把它挂在 `仓储库存` 下，那个父图标已被清理，残留值必须抹掉。
	icon.parent_icon = ""
	icon.bg_color = "blue"
	icon.hidden = 0
	icon.idx = 1
	icon.restrict_removal = 1
	icon.save(ignore_permissions=True)


def _cleanup_stale_desktop_icons():
	"""删掉本 App 早期留下、且**不指向任何侧边栏**的桌面图标。

	为什么必须清：这类图标 label 在 `workspace_sidebar_item` 里查不到，
	会被 `get_desktop_icons()` 静默丢弃 —— 屏幕上不显示，但记录还在，
	而且**挂在它下面的图标会跟着一起消失**（父图标不在 permitted 集合里，
	子图标被同一条规则过滤）。留着它只会继续误导后来的人以为「配过了」。

	只删**本模块留下的已知陈旧名**，不做泛化清理，避免误伤其他 App。
	"""
	for stale in STALE_DESKTOP_LABELS:
		if not frappe.db.exists("Desktop Icon", stale):
			continue
		frappe.delete_doc("Desktop Icon", stale, ignore_permissions=True, force=True)
		frappe.logger("hbos_inventory").info(
			f"Desktop Icon 清理陈旧：{stale}（不指向任何侧边栏，被 Frappe 静默丢弃）"
		)
