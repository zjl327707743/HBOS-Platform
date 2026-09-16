"""把 ERPNext 原生 Stock 工作台的 payload 转换为海滨库存工作台 payload。

纯函数模块：不导入 frappe，不访问数据库，可离线测试。

产物的使用者有两个，字段取舍必须同时满足：
1. Frappe 的 fixture 导入链路（`frappe/model/sync.py::sync_for` →
   `frappe/modules/import_file.py::import_file_by_path`）会按约定路径
   `<module>/workspace/<name>/<name>.json` 读到它。该链路要求顶层带
   `doctype` 与 `name`，缺 `doctype` 会 `KeyError` 并中断 install-app / migrate。
2. `hb_stock_app.hbos_stock.setup.sync_stock_workspace()` 按
   `TOP_LEVEL_KEEP_FIELDS` / 各子表白名单逐字段落库。
"""

import json

TARGET_WORKSPACE = "海滨库存"
TARGET_MODULE = "HBOS Stock"
TARGET_APP = "hb_stock_app"

# 子表行上的身份/父级/审计字段：复制时必须剥离。
# 子表 docname（如实测到的 si4ekhi8tq）在各自 child doctype 内全局唯一，
# 原样带过去会让 frappe 复用同名子文档，等于把原生 Stock 工作台的子表行搬走。
ROW_DROP_FIELDS = (
	"name", "owner", "creation", "modified", "modified_by",
	"docstatus", "idx", "parent", "parentfield", "parenttype", "doctype",
)

# 顶层保留字段。判据不是「我觉得该留什么」，而是「生成的 fixture 能否被 Frappe
# 正常导入」，以运行态源 payload 与已上线的「海滨考勤工作台」参考产物（同样放在
# <module>/workspace/<name>/<name>.json，走同一条导入链路）的交集为准。
#
# doctype 必须保留：Frappe 安装/迁移时按模块目录同步，链路是
# frappe/model/sync.py::sync_for → frappe/modules/import_file.py::
# import_file_by_path，该函数第一步就取 doc["doctype"]（import_file.py:123），
# 缺了这个键会 KeyError: 'doctype'，整个 install-app / migrate 直接中断。
# custom_blocks、quick_lists 是 Workspace 的子表字段（源 payload 与参考产物都有），
# 同 links/charts/number_cards/roles/shortcuts 一样需要输出。
# for_user、hide_custom 同样在源与参考产物中都存在，保留成本为零。
#
# 未保留的源字段：external_link / indicator_color / link_to / link_type /
# parent_page / restrict_to_domain。它们在运行态源里全为空值（None / ''），参考
# 产物也不含；保留会把原生 Stock 的页面归属与域限制语义带进目标站点，且对导入
# 无任何必要性。
TOP_LEVEL_KEEP_FIELDS = (
	"app", "content", "doctype", "for_user", "hide_custom", "icon",
	"is_hidden", "label", "module", "public", "sequence_id", "title", "type",
)
LINK_KEEP_FIELDS = (
	"type", "label", "icon", "description", "hidden", "link_type", "link_to",
	"report_ref_doctype", "dependencies", "only_for", "onboard",
	"is_query_report", "link_count",
)
CHART_KEEP_FIELDS = ("chart_name", "label")
NUMBER_CARD_KEEP_FIELDS = ("number_card_name", "label")
SHORTCUT_KEEP_FIELDS = ("color", "doc_view", "label", "link_to", "stats_filter", "type")
# Workspace Custom Block / Workspace Quick List 的字段白名单（只留数据字段，
# 布局用的 section_break_* / column_break_* 不带）。
CUSTOM_BLOCK_KEEP_FIELDS = ("custom_block_name", "label")
QUICK_LIST_KEEP_FIELDS = ("document_type", "label", "quick_list_filter")

TITLE_HEADER_ID = "hbos-stock-title"
TITLE_HEADER_TEXT = (
	'<span class="h4"><b>海滨库存</b></span><br>'
	'<span class="text-muted">本工作台承载海滨独立库存数据，复用 ERPNext 原生库存单据与报表；'
	'与考勤站点数据完全隔离。</span>'
)


def build_workspace_payload(source):
	"""把 Stock 工作台 payload 转成海滨库存工作台 payload。

	纯函数：返回全新 dict，不修改入参，不访问数据库。
	"""
	payload = _pick(source, TOP_LEVEL_KEEP_FIELDS)
	payload["name"] = TARGET_WORKSPACE
	payload["label"] = TARGET_WORKSPACE
	payload["title"] = TARGET_WORKSPACE
	payload["module"] = TARGET_MODULE
	payload["app"] = TARGET_APP

	payload["links"] = [_pick(r, LINK_KEEP_FIELDS) for r in source.get("links") or []]
	payload["charts"] = [_pick(r, CHART_KEEP_FIELDS) for r in source.get("charts") or []]
	payload["number_cards"] = [
		_pick(r, NUMBER_CARD_KEEP_FIELDS) for r in source.get("number_cards") or []
	]
	payload["roles"] = [_pick(r, ("role",)) for r in source.get("roles") or []]
	payload["shortcuts"] = [
		_pick(r, SHORTCUT_KEEP_FIELDS) for r in source.get("shortcuts") or []
	]
	payload["custom_blocks"] = [
		_pick(r, CUSTOM_BLOCK_KEEP_FIELDS) for r in source.get("custom_blocks") or []
	]
	payload["quick_lists"] = [
		_pick(r, QUICK_LIST_KEEP_FIELDS) for r in source.get("quick_lists") or []
	]

	payload["content"] = _prepend_title_header(source.get("content"))
	_assert_no_drop_fields(payload)
	return payload


def _pick(row, fields):
	return {f: row.get(f) for f in fields if f in row}


def _assert_no_drop_fields(payload):
	"""任何输出子表行都不得携带 ROW_DROP_FIELDS 中的身份字段。

	剥离靠的是各 *_KEEP_FIELDS 白名单，这里是第二道防线：白名单一旦被改错
	（例如有人把 name 加回 LINK_KEEP_FIELDS），会当场报错，而不是把原生
	Stock 的子文档名悄悄带进目标站点。
	"""
	for table, rows in payload.items():
		if not isinstance(rows, list):
			continue
		for row in rows:
			if not isinstance(row, dict):
				continue
			leaked = sorted(set(row) & set(ROW_DROP_FIELDS))
			if leaked:
				raise ValueError(
					f"子表 {table} 的输出行携带了必须剥离的字段 {leaked}：{row}"
				)


def _prepend_title_header(content):
	"""在 content 顶部插入海滨库存标题块，其余块逐字保留；已插入则不重复。"""
	blocks = json.loads(content) if content else []
	if any(b.get("id") == TITLE_HEADER_ID for b in blocks):
		return content
	header = {"id": TITLE_HEADER_ID, "type": "header",
	          "data": {"text": TITLE_HEADER_TEXT, "col": 12}}
	return json.dumps([header, *blocks], ensure_ascii=False)
