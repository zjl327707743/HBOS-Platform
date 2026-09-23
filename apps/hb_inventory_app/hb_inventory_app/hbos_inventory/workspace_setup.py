"""仓库工作台入口同步（幂等）

**这个工作台要同时解决两件事**：

1. 给海滨特有的东西一个入口——入库拍照识别页 + 四个报表（原生没有）；
2. **让在这里做的操作不要跳到原生库存模块去**。

第 2 点曾被误判。2026-09-23 Owner 问「为什么要单独做仓库工作台、不能集成在
原生库存里」，我一度把侧边栏里指向原生单据（Stock Entry / Batch / Item /
Warehouse）的条目当成「重复导航」撤掉，结果 Owner 报「点进单据就跳到原生
库存、回不来，侧边栏整条都换了」。

查框架源码后确认：**那些条目在做一件看不见的事**——`sidebar.js` 的
`resolve_sidebar()` 第 1 条规则是「当前侧边栏若已链接到该单据，就保持不变」，
`get_workspace_sidebars()` 拿 bootinfo 里所有侧边栏去匹配；我们的侧边栏一旦
不含该单据，就不再是候选，于是掉回原生。详见 `SIDEBAR_ITEMS` 与
`WORKSPACE_SHORTCUTS` 上方的注释（两层机制是分开的）。

以代码方式同步 Workspace + Workspace Sidebar + Desktop Icon，
沿用 `hb_attendance_app` 的既有做法（`after_migrate` 钩子调用，幂等）。
"""

import json

import frappe

MODULE = "HBOS Inventory"

# ⚠ 三者同名不是审美选择，是**硬约束**：`Workspace` / `Workspace Sidebar` /
# `Desktop Icon` 的 `name` 都等于标题，而 Frappe 的 `get_desktop_icons()`
# 会拿图标 label 去侧边栏映射里查，**查不到就静默丢弃**（不报错、不提示）。
# 详见 `DESKTOP_ICON` 下方与 `_sync_desktop_icon()` 的注释。
WORKSPACE_TITLE = "仓库工作台"
DESKTOP_LABEL = WORKSPACE_TITLE

# 图标不用 "stock"——那是 ERPNext 原生 Stock 模块的图标，桌面上两个一模一样的
# 图形并排，点错就进了原生库存模块，而那边没有本 App 的侧边栏，回不来。
# 也不用 "warehouse"（曾用过）：`boxes` 语义更贴「仓库」，且与两者都不撞。
DESKTOP_ICON = "boxes"

# 本 App 用过的历史标题。改名后**必须把旧对象删掉**——三者的 name 都等于标题，
# 换标题等于换主键，旧记录不会自动消失；留着会被 Frappe 当成
# 「label 查不到侧边栏」的僵尸图标，而**挂在它下面的图标会跟着一起消失**。
LEGACY_TITLES = ("仓储库存工作台", "仓储库存")

# 侧边栏条目。分两类，**第二类是必需的、不是重复导航**（见下方长注释）。
#
# 一、本 App 独有的：1 个页面 + 4 个报表。
# 二、原生库存单据 / 主数据的入口（Stock Entry / Batch / Item / Warehouse）。
#
# ⚠ **第二类别删**。2026-09-23 我一度以为它们只是「与原生库存重复的导航」而撤掉，
# 结果 Owner 报「点进单据就跳到原生库存、回不来，侧边栏整条都换了」。
# 查了框架源码才知道它们在做一件看不见的事：
#
#   `sidebar.js` 的 `resolve_sidebar()` 第 1 条规则是——
#   **当前侧边栏若已链接到该单据（sidebar item 的 link_to 命中），就保持不变。**
#   `get_workspace_sidebars()` 是拿 bootinfo 里**所有**侧边栏去匹配的；
#   我们的侧边栏一旦不含该单据，就不再是候选，于是掉回原生。
#   （实测：`Batch` 只被原生 `Stock` 侧边栏链接 → 唯一候选 → 必然切走。）
#
# 所以这几个条目的收益是「侧边栏不换、上下文不断」，顺带也给了入口。
# **但只保留一条 Stock Entry**：原来那三条（入库登记 / 出库核销 / 货位变更）
# 指向的是同一个原生列表，只是标签不同、点下去不会按用途过滤，
# 那是假分类，反而误导。原生这一个列表本来就同时管入库、出库、移库。
SIDEBAR_ITEMS = [
	{"label": WORKSPACE_TITLE, "link_type": "Workspace", "link_to": WORKSPACE_TITLE, "type": "Link", "icon": "home"},
	# 入库拍照识别：本 App 的 Desk 页面（拍照 → 识别 → 校对 → 生成草稿）
	{"label": "入库拍照识别", "link_type": "Page", "link_to": "hbos-photo-intake", "type": "Link", "icon": "camera"},
	# ↓ 第二类：原生入口，承担「侧边栏不换」的职责，**不要删**
	{"label": "库存单据（入库/出库/移库）", "link_type": "DocType", "link_to": "Stock Entry", "type": "Link", "icon": "stock-entry"},
	{"label": "批次", "link_type": "DocType", "link_to": "Batch", "type": "Link", "icon": "file"},
	{"label": "物料", "link_type": "DocType", "link_to": "Item", "type": "Link", "icon": "stock"},
	{"label": "货位", "link_type": "DocType", "link_to": "Warehouse", "type": "Link", "icon": "organization"},
	{"label": "按批号查货位", "link_type": "Report", "link_to": "按批号查货位", "type": "Link", "icon": "search"},
	{"label": "货位明细表", "link_type": "Report", "link_to": "货位明细表", "type": "Link", "icon": "list"},
	{"label": "效期预警", "link_type": "Report", "link_to": "效期预警", "type": "Link", "icon": "milestone"},
	{"label": "库级盘点三对账", "link_type": "Report", "link_to": "库级盘点三对账", "type": "Link", "icon": "clipboard-list"},
]

# 工作台快捷方式。除了拍照识别入口，**这里还决定面包屑**：
# `FormMeta.load_workspaces()` 先查 `Workspace Shortcut`（type=DocType），
# **查到就用它**，查不到才回落到 `Workspace Link`。所以给某个单据加一条
# 快捷方式，就能把它的归属工作台从原生改到我们这边（面包屑随之改变）。
#
# ⚠ **不要给 `Item` 加快捷方式**：原生 `Home` 工作台已经有一条 Item 快捷方式，
# 而 `load_workspaces()` 取的是 `shortcut[0][0]`、**查询里没有 order_by** ——
# 再加一条会让结果不确定（有时 Home、有时我们）。Item 的面包屑就留给原生。
WORKSPACE_SHORTCUTS = [
	{"label": "入库拍照识别", "type": "Page", "link_to": "hbos-photo-intake", "color": "Blue", "doc_view": ""},
	{"label": "库存单据（入库/出库/移库）", "type": "DocType", "link_to": "Stock Entry", "color": "Gray", "doc_view": ""},
	{"label": "批次", "type": "DocType", "link_to": "Batch", "color": "Gray", "doc_view": ""},
	{"label": "货位", "type": "DocType", "link_to": "Warehouse", "color": "Gray", "doc_view": ""},
]

WORKSPACE_CONTENT = """[
 {"id":"hdr","type":"header","data":{"text":"<span class=\\"h4\\"><b>仓库工作台</b></span>","col":12}},
 {"id":"sb1","type":"paragraph","data":{"text":"本工作台集中仓库日常：左侧可直接进入入库拍照识别、库存单据（入库 / 出库 / 移库）、批次与四个报表；进去之后**不会跳去原生库存模块**。","col":12}},
 {"id":"sc_photo","type":"shortcut","data":{"shortcut_name":"入库拍照识别","col":3}},
 {"id":"sc_in","type":"shortcut","data":{"shortcut_name":"库存单据（入库/出库/移库）","col":3}},
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
]


def _parse_content(payload):
	if not payload:
		return []

	return json.loads(payload)


def sync_inventory_workspace():
	"同步 Workspace、入口快捷方式、侧边栏与桌面图标（幂等）。"

	# **必须最先做**：标题即主键，改过名就要先把旧对象清掉，
	# 否则旧 Desktop Icon 会变成「查不到侧边栏」的僵尸，连累后续图标。
	_cleanup_legacy_objects()

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

	workspace.set("shortcuts", WORKSPACE_SHORTCUTS)
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


def _cleanup_legacy_objects():
	"""删掉本 App 历史标题下的 Workspace / Sidebar / Desktop Icon。

	**为什么必须清**：这三者的 `name` 都等于标题，改标题等于换主键——
	旧记录不会自动消失。而残留的旧 Desktop Icon 会被
	`get_desktop_icons()` 静默丢弃（label 在侧边栏映射里查不到），
	屏幕上不显示、记录却还在，**挂在它下面的图标还会跟着一起消失**。

	删子图标要排在删父图标之前：`Desktop Icon` 有 `parent_icon` 自关联，
	父被删而子还指着它，会留下悬空引用。这里先把指向旧标题的图标清空
	`parent_icon`，再按 图标 → 侧边栏 → 工作台 的顺序删。

	只删 `LEGACY_TITLES` 里登记过的名字，不做泛化清理，避免误伤其他 App。
	"""
	for legacy in LEGACY_TITLES:
		frappe.db.set_value(
			"Desktop Icon", {"parent_icon": legacy}, "parent_icon", "", update_modified=False
		)
		for doctype in ("Desktop Icon", "Workspace Sidebar", "Workspace"):
			if not frappe.db.exists(doctype, legacy):
				continue
			frappe.delete_doc(doctype, legacy, ignore_permissions=True, force=True)
			frappe.logger("hbos_inventory").info(f"清理历史对象：{doctype} / {legacy}")
