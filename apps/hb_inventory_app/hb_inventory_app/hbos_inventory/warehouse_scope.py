"""货位可见范围（四张库存报表共用）

## 为什么必须单独有一层

四张库存报表都直接用 `frappe.db.sql` 查 `Serial and Batch Entry`——
**raw SQL 不走 Frappe 的权限过滤**。任何能打开报表的用户都能看到**全部货位**
的批号与数量，包括他没有权限的仓库。这是跨仓读取。

Frappe 的 User Permission（`allow = "Warehouse"`）只作用在 ORM 层
（`frappe.get_list` / `frappe.get_all`）。本模块把**同一份可见范围**取出来，
转成报表 SQL 的 `warehouse in (...)` 条件——让 raw SQL 与 ORM 看到同一个范围。

## 语义（四张报表统一）

- **未指定货位** → 只返回**当前用户可见**的叶子货位。**不是全部**。
  这是本模块存在的理由：缺了这个默认，报表就是全量泄漏。
- **指定了不可见的货位** → 抛 `PermissionError`，明确拒绝。
  **不静默变空**——空结果与「这里确实没有库存」无法区分，
  会把越权失败伪装成正常空结果，事后查不出来。
- **指定了可见的库位 + 勾选「含下级」** → 展开为该库位下**可见的**叶子货位；
  展开本身用树查询（`lft`/`rgt`），但结果仍与可见范围求交。
- 可见集合恒为**具体列表**（可能为空）。调用方拿到空列表时必须直接返回空结果，
  不得退回全量、也不得拼 `in ()`（无效 SQL）。

## 与 Portal 摘要的关系

`portal/summary.py::_load_permission_aware_inventory` 已用同样思路取可见货位。
两处口径一致（都是 `frappe.get_list("Warehouse", {"is_group": 0, "disabled": 0})`）；
此处不合并，是因为一个在 Portal 投影层、一个在报表 SQL 层，返回形态不同。
"""

import frappe

#: 报表的货位筛选字段名（四张报表一致）
WAREHOUSE_FILTER = "warehouse"

#: 「含下级」复选框字段名（只有库位型报表有）
INCLUDE_CHILDREN_FILTER = "include_children"


def visible_leaf_warehouses() -> list[str]:
	"""当前会话用户可读的**叶子**货位（排除分组节点与已停用）。

	用 `frappe.get_list` —— 它施加角色权限与 User Permission 过滤。
	绝不能换成 `frappe.db.get_all` / 裸 SQL，那会绕开权限。
	"""
	return [
		str(name)
		for name in frappe.get_list(
			"Warehouse",
			filters={"is_group": 0, "disabled": 0},
			pluck="name",
			order_by="name",
			limit_page_length=0,
		)
		if name
	]


def can_read_warehouse(warehouse: str) -> bool:
	"""该货位对当前用户是否**可读**（含分组节点）。

	与 `visible_leaf_warehouses` 分开：用户可能有权看到一个**库位/层**这类分组
	节点（但叶子集合里没有它），勾选「含下级」时正需要这种。
	"""
	if not warehouse:
		return False
	return bool(
		frappe.get_list(
			"Warehouse",
			filters={"name": warehouse},
			pluck="name",
			limit_page_length=1,
		)
	)


def _descendants(root: str) -> list[str]:
	"""`root` 自身及其全部后代（按 Warehouse 树的 lft/rgt 展开）。"""
	return [
		str(name)
		for name in frappe.db.sql(
			"""
			select name from `tabWarehouse`
			where lft >= (select lft from `tabWarehouse` where name = %(root)s)
			  and rgt <= (select rgt from `tabWarehouse` where name = %(root)s)
			""",
			{"root": root},
			pluck=True,
		)
		if name
	]


def resolve_scope(filters) -> list[str]:
	"""把报表筛选解析为**已经与用户可见范围求交**的货位列表。

	返回值恒为具体列表（可能为空）；调用方见空必须返回空结果。
	"""
	filters = filters or {}
	requested = str(filters.get(WAREHOUSE_FILTER) or "").strip()
	visible = set(visible_leaf_warehouses())

	if not requested:
		# 核心修复：没有筛选 ≠ 看全部，而是「看我可见的那部分」。
		return sorted(visible)

	if not can_read_warehouse(requested):
		frappe.throw(
			frappe._("无权查看货位「{0}」的库存。").format(requested),
			frappe.PermissionError,
		)

	candidates = _descendants(requested) if filters.get(INCLUDE_CHILDREN_FILTER) else [requested]
	return sorted({name for name in candidates if name in visible})
