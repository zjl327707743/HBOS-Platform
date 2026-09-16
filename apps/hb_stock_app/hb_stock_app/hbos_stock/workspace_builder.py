"""把 ERPNext 原生 Stock 工作台的 payload 转换为海滨库存工作台 payload。

纯函数模块：不导入 frappe，不访问数据库，可离线测试。
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

TOP_LEVEL_KEEP_FIELDS = (
	"app", "content", "icon", "is_hidden", "label", "module",
	"public", "sequence_id", "title", "type",
)
LINK_KEEP_FIELDS = (
	"type", "label", "icon", "description", "hidden", "link_type", "link_to",
	"report_ref_doctype", "dependencies", "only_for", "onboard",
	"is_query_report", "link_count",
)
CHART_KEEP_FIELDS = ("chart_name", "label")
NUMBER_CARD_KEEP_FIELDS = ("number_card_name", "label")
SHORTCUT_KEEP_FIELDS = ("color", "doc_view", "label", "link_to", "stats_filter", "type")

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

	payload["content"] = _prepend_title_header(source.get("content"))
	return payload


def _pick(row, fields):
	return {f: row.get(f) for f in fields if f in row}


def _prepend_title_header(content):
	"""在 content 顶部插入海滨库存标题块，其余块逐字保留；已插入则不重复。"""
	blocks = json.loads(content) if content else []
	if any(b.get("id") == TITLE_HEADER_ID for b in blocks):
		return content
	header = {"id": TITLE_HEADER_ID, "type": "header",
	          "data": {"text": TITLE_HEADER_TEXT, "col": 12}}
	return json.dumps([header, *blocks], ensure_ascii=False)
