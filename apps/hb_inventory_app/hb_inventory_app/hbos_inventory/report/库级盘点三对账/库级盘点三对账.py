"""库级盘点三对账（导出用）

对齐仓库现有纸质《物料及产品盘存记录》的口径：**按库位盘点**，
对每个「物料 + 批号」做三对账 —— ERP数量 / 货位卡数量 / 实物数量。

使用方式：
    1. 选库位（可含下级）运行报表，得到 ERP 数量；
    2. 用 Desk 报表右上角的「导出」导出 Excel；
    3. 现场在 Excel 里填写「货位卡数量」与「实物数量」两列；
    4. 报表内的「差异（货位卡-ERP）」「差异（实物-ERP）」两列留空，
       在 Excel 中由公式计算，或回填后再比对。

说明：
    「货位卡数量」与「实物数量」**不来自系统**（分别是纸质卡记录与实盘结果），
    故此处留空列，不做自动填充。系统只负责给出权威的 ERP 数量与全量批次清单。

数据源：`Serial and Batch Entry` 关联 `Serial and Batch Bundle`
（v16 中 `SLE.batch_no` 为空列，不可用；详见 M3-R1 主文档第四节）。
"""

import frappe


def _warehouse_scope(filters):
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

	scope, _ = _warehouse_scope(filters)
	if scope is not None:
		placeholders = ", ".join(f"%(wh_{i})s" for i in range(len(scope)))
		conditions.append(f"sbe.warehouse in ({placeholders})")
		for i, name in enumerate(scope):
			values[f"wh_{i}"] = name

	if filters.get("item_code"):
		conditions.append("sbe.item_code = %(item_code)s")
		values["item_code"] = filters["item_code"]

	where = " and ".join(conditions) if conditions else "1 = 1"

	rows = frappe.db.sql(
		f"""
		select
			sbe.warehouse,
			sbe.item_code,
			i.item_name,
			sbe.batch_no,
			i.stock_uom as uom,
			sum(sbe.qty) as erp_qty,
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
				"uom": row.uom,
				"erp_qty": row.erp_qty,
				# 以下三列由现场填写 / 在导出的 Excel 中计算
				"card_qty": None,
				"physical_qty": None,
				"variance_corrected": None,
				"expiry_date": row.expiry_date,
				"release_status": row.release_status,
			}
		)

	return _columns(), data


def _columns():
	return [
		{"label": "库位", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 190},
		{"label": "物料代码", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": "物料名称", "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": "批号", "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 160},
		{"label": "单位", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": "ERP数量", "fieldname": "erp_qty", "fieldtype": "Float", "precision": 3, "width": 110},
		{"label": "货位卡数量", "fieldname": "card_qty", "fieldtype": "Float", "precision": 3, "width": 110},
		{"label": "实物数量", "fieldname": "physical_qty", "fieldtype": "Float", "precision": 3, "width": 110},
		{"label": "差异（实物-ERP）", "fieldname": "variance_corrected", "fieldtype": "Float", "precision": 3, "width": 150},
		{"label": "有效期至", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
		{"label": "放行状态", "fieldname": "release_status", "fieldtype": "Data", "width": 100},
	]
