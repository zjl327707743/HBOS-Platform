"""海滨库存工作台的幂等同步。

模式对齐 hb_attendance_app.hbos_attendance.setup 的 after_migrate 同步。
"""

import json
from pathlib import Path

import frappe

MODULE = "HBOS Stock"
WORKSPACE_TITLE = "海滨库存"

TOP_LEVEL_FIELDS = (
	"app", "content", "icon", "is_hidden", "label", "module",
	"public", "sequence_id", "title", "type",
)
CHILD_TABLES = ("links", "charts", "number_cards", "roles", "shortcuts")


def after_migrate():
	sync_stock_workspace()


def load_workspace_fixture():
	path = (Path(__file__).parent / "workspace" / WORKSPACE_TITLE
	        / f"{WORKSPACE_TITLE}.json")
	return json.loads(path.read_text())


def sync_stock_workspace():
	"""以版本化 fixture 幂等同步「海滨库存」工作台（新建或更新）。"""
	payload = load_workspace_fixture()
	exists = frappe.db.exists("Workspace", payload["name"])
	workspace = (frappe.get_doc("Workspace", payload["name"]) if exists
	             else frappe.new_doc("Workspace"))
	for field in TOP_LEVEL_FIELDS:
		workspace.set(field, payload.get(field))
	for table in CHILD_TABLES:
		workspace.set(table, payload.get(table) or [])
	workspace.save(ignore_permissions=True)
