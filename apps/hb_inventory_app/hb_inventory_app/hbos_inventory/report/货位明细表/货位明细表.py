"""货位明细表

给定货位（或其某个父级，如库位 / 整层），列出该范围内所有批号与数量。
这是「按批号查货位」的反向视图，数据源相同。

数据源：`Serial and Batch Entry` 关联 `Serial and Batch Bundle`。
"""

import frappe


def _warehouse_scope(filters):
	"""返回 (warehouse 列表, 参数)。勾选含子级时按 Warehouse 树展开。"""
	warehouse = filters.get("warehouse")
	if not warehouse:
		return None, {}

	if not filters.get("include_children"):
		return [warehouse], {}

	descendants = frappe.db.sql(
		"""
		select name from `tabWarehouse`
		where lft >= (select lft from `tabWarehouse` where name = %(root)s)
		  and rgt <= (select rgt from `tabWarehouse` where name = %(root)s)
		""",
		{"root": warehouse},
		pluck=True,
	)
	return descendants, {}


def execute(filters=None):
	filters = filters or {}
	conditions = []
	values = {}

	scope, scope_values = _warehouse_scope(filters)
	if scope is not None:
		placeholders = ", ".join(f"%(wh_{i})s" for i in range(len(scope)))
		conditions.append(f"sbe.warehouse in ({placeholders})")
		for i, name in enumerate(scope):
			values[f"wh_{i}"] = name

	if filters.get("item_code"):
		conditions.append("sbe.item_code = %(item_code)s")
		values["item_code"] = filters["item_code"]
	if filters.get("batch_no"):
		conditions.append("sbe.batch_no like %(batch_no)s")
		values["batch_no"] = f"%{filters['batch_no']}%"

	where = " and ".join(conditions) if conditions else "1 = 1"

	rows = frappe.db.sql(
		f"""
		select
			sbe.warehouse,
			sbe.item_code,
			i.item_name,
			sbe.batch_no,
			sum(sbe.qty) as qty,
			i.stock_uom as uom,
			b.expiry_date,
			b.hbos_release_status as release_status
		from `tabSerial and Batch Entry` sbe
		join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
		left join `tabItem` i on i.name = sbe.item_code
		left join `tabBatch` b on b.name = sbe.batch_no
		where sbb.docstatus = 1 and sbb.is_cancelled = 0 and sbb.is_rejected = 0
			and sbe.is_cancelled = 0
			and {where}
		group by sbe.warehouse, sbe.item_code, sbe.batch_no
		having sum(sbe.qty) != 0
		order by sbe.warehouse, sbe.item_code, sbe.batch_no
		""",
		values,
		as_dict=True,
	)

	data = []
	for row in rows:
		data.append(
			{
				"warehouse": row.warehouse,
				"item_code": row.item_code,
				"item_name": row.item_name,
				"batch_no": row.batch_no,
				"qty": row.qty,
				"uom": row.uom,
				"expiry_date": row.expiry_date,
				"release_status": row.release_status,
			}
		)

	return _columns(), data


def _columns():
	return [
		{"label": "货位", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 190},
		{"label": "物料代码", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": "物料名称", "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": "批号", "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 160},
		{"label": "数量", "fieldname": "qty", "fieldtype": "Float", "precision": 3, "width": 110},
		{"label": "单位", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": "有效期至", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
		{"label": "放行状态", "fieldname": "release_status", "fieldtype": "Data", "width": 100},
	]
