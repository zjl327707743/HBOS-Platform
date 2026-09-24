"""按批号查货位

给定批号（或物料），返回该批次当前分布在哪些货位、各多少。

数据源：`Serial and Batch Entry` 关联 `Serial and Batch Bundle`。
注意：ERPNext v16 中 `Stock Ledger Entry.batch_no` 为空列，批次数据不在 SLE；
`Bin` 只到「物料 × 货位」粒度，也不含批次。详见 M3-R1 主文档第四节。
"""

import frappe


def execute(filters=None):
	filters = filters or {}
	conditions = []
	values = {}

	if filters.get("batch_no"):
		conditions.append("sbe.batch_no like %(batch_no)s")
		values["batch_no"] = f"%{filters['batch_no']}%"
	if filters.get("item_code"):
		conditions.append("sbe.item_code = %(item_code)s")
		values["item_code"] = filters["item_code"]
	if filters.get("warehouse"):
		conditions.append("sbe.warehouse = %(warehouse)s")
		values["warehouse"] = filters["warehouse"]
	if filters.get("release_status"):
		conditions.append("b.hbos_release_status = %(release_status)s")
		values["release_status"] = filters["release_status"]

	where = " and ".join(conditions) if conditions else "1 = 1"

	rows = frappe.db.sql(
		f"""
		select
			sbe.batch_no,
			sbe.item_code,
			i.item_name,
			sbe.warehouse,
			sum(sbe.qty) as qty,
			i.stock_uom as uom,
			b.manufacturing_date,
			b.expiry_date,
			b.hbos_release_status as release_status,
			b.hbos_supplier_batch_no as supplier_batch_no
		from `tabSerial and Batch Entry` sbe
		join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
		left join `tabItem` i on i.name = sbe.item_code
		left join `tabBatch` b on b.name = sbe.batch_no
		where sbb.docstatus = 1 and sbb.is_cancelled = 0 and sbb.is_rejected = 0
			and sbe.is_cancelled = 0
			and {where}
		group by sbe.batch_no, sbe.item_code, sbe.warehouse
		having sum(sbe.qty) != 0
		order by sbe.batch_no, sbe.warehouse
		""",
		values,
		as_dict=True,
	)

	data = []
	for row in rows:
		data.append(
			{
				"batch_no": row.batch_no,
				"item_code": row.item_code,
				"item_name": row.item_name,
				"warehouse": row.warehouse,
				"qty": row.qty,
				"uom": row.uom,
				"manufacturing_date": row.manufacturing_date,
				"expiry_date": row.expiry_date,
				"release_status": row.release_status,
				"supplier_batch_no": row.supplier_batch_no,
			}
		)

	return _columns(), data


def _columns():
	return [
		{"label": "批号", "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 160},
		{"label": "物料代码", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": "物料名称", "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": "货位", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
		{"label": "数量", "fieldname": "qty", "fieldtype": "Float", "precision": 3, "width": 110},
		{"label": "单位", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": "生产日期", "fieldname": "manufacturing_date", "fieldtype": "Date", "width": 110},
		{"label": "有效期至", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
		{"label": "放行状态", "fieldname": "release_status", "fieldtype": "Data", "width": 100},
		{"label": "原厂批号", "fieldname": "supplier_batch_no", "fieldtype": "Data", "width": 140},
	]
