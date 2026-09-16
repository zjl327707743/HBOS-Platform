"""海滨库存工作台的幂等同步。

模式对齐 hb_attendance_app.hbos_attendance.setup 的 after_migrate 同步。
"""

import json
from pathlib import Path

import frappe

from hb_stock_app.hbos_stock.workspace_builder import TOP_LEVEL_KEEP_FIELDS

WORKSPACE_TITLE = "海滨库存"
CHILD_TABLES = ("links", "charts", "number_cards", "roles", "shortcuts",
                "custom_blocks", "quick_lists")


def after_migrate():
	sync_stock_workspace()


def load_workspace_fixture():
	path = (Path(__file__).parent / "workspace" / WORKSPACE_TITLE
	        / f"{WORKSPACE_TITLE}.json")
	return json.loads(path.read_text())


def sync_stock_workspace():
	"""以版本化 fixture 幂等同步「海滨库存」工作台（新建或更新）。"""
	payload = load_workspace_fixture()
	name = payload["name"]

	if frappe.db.exists("Workspace", name):
		workspace = frappe.get_doc("Workspace", name)
		_apply_payload(workspace, payload)
		workspace.save(ignore_permissions=True)
	else:
		workspace = frappe.new_doc("Workspace")
		_apply_payload(workspace, payload)
		# 新建时显式指定 docname。Workspace 的 autoname 实测为 field:label，
		# 不能把 docname 交给 autoname 推导：frappe 的 set_new_name 会先清空
		# doc.name 再按 autoname 重推，仅赋值 doc.name 不生效，必须经
		# insert(set_name=...) 传入。若放任推导且结果不等于 name，
		# frappe.db.exists 将永远为假，每次 migrate 都重复新建同名工作台。
		workspace.name = name
		workspace.insert(set_name=name, ignore_permissions=True)

	_assert_docname(workspace, name)


def _apply_payload(workspace, payload):
	"""顶层字段严格索引：fixture 与代码口径不一致时立刻报错，不静默跳过。"""
	for field in TOP_LEVEL_KEEP_FIELDS:
		workspace.set(field, payload[field])
	for table in CHILD_TABLES:
		workspace.set(table, payload[table] or [])


def _assert_docname(workspace, expected):
	"""docname 与 fixture 不一致时当场报错，而不是按站点静默堆积同名工作台。"""
	if workspace.name != expected:
		frappe.throw(
			f"海滨库存工作台 docname 异常：期望「{expected}」，实际「{workspace.name}」。"
			"请核对 Workspace 的命名规则与 setup.sync_stock_workspace 的命名方式。"
		)
