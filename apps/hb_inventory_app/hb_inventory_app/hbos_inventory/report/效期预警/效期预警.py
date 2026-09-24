"""效期预警

列出临近到期的批次，供仓库提前处置（催用 / 复检 / 报废评估）。

效期口径（Owner 确认）：
    按产品种类区分，且分「复检期」与「有效期」两类，期限来源为该产品的质量标准
    （`Item.hbos_shelf_life_type` + `Item.hbos_shelf_life_months`，或原生
    `Item.shelf_life_in_days`）。批次上的 `Batch.expiry_date` 即到期日。

数据源：`Serial and Batch Entry` 关联 `Serial and Batch Bundle`
（v16 中 `SLE.batch_no` 为空列，不可用；详见 M3-R1 主文档第四节）。
"""

import frappe
from frappe.utils import add_days, date_diff, getdate, today


def execute(filters=None):
	filters = filters or {}
	within_days = int(filters.get("within_days") or 90)
	include_expired = 1 if filters.get("include_expired") is None else int(filters["include_expired"])

	conditions = [
		"b.expiry_date is not null",
		"b.expiry_date <= %(deadline)s",
	]
	values = {"deadline": add_days(today(), within_days)}

	if not include_expired:
		conditions.append("b.expiry_date >= %(today)s")
		values["today"] = today()

	if filters.get("warehouse"):
		conditions.append("sbe.warehouse = %(warehouse)s")
		values["warehouse"] = filters["warehouse"]
	if filters.get("item_code"):
		conditions.append("sbe.item_code = %(item_code)s")
		values["item_code"] = filters["item_code"]
	if filters.get("release_status"):
		conditions.append("b.hbos_release_status = %(release_status)s")
		values["release_status"] = filters["release_status"]

	where = " and ".join(conditions)
	today_date = getdate(today())

	rows = frappe.db.sql(
		f"""
		select
			sbe.item_code,
			i.item_name,
			sbe.batch_no,
			sbe.warehouse,
			sum(sbe.qty) as qty,
			i.stock_uom as uom,
			b.manufacturing_date,
			b.expiry_date,
			b.hbos_release_status as release_status,
			i.hbos_shelf_life_type as shelf_life_type
		from `tabSerial and Batch Entry` sbe
		join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
		left join `tabItem` i on i.name = sbe.item_code
		left join `tabBatch` b on b.name = sbe.batch_no
		where sbb.docstatus = 1 and sbb.is_cancelled = 0 and sbb.is_rejected = 0
			and sbe.is_cancelled = 0
			and {where}
		group by sbe.item_code, sbe.batch_no, sbe.warehouse
		having sum(sbe.qty) != 0
		order by b.expiry_date, sbe.item_code, sbe.batch_no
		""",
		values,
		as_dict=True,
	)

	data = []
	for row in rows:
		left = date_diff(row.expiry_date, today_date)
		if left < 0:
			urgency = "已过期"
		elif left <= 30:
			urgency = "紧急（≤30 天）"
		elif left <= 90:
			urgency = "关注（≤90 天）"
		else:
			urgency = "正常"

		data.append(
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"batch_no": row.batch_no,
				"warehouse": row.warehouse,
				"qty": row.qty,
				"uom": row.uom,
				"manufacturing_date": row.manufacturing_date,
				"expiry_date": row.expiry_date,
				"days_left": left,
				"urgency": urgency,
				"shelf_life_type": row.shelf_life_type or "未设置",
				"release_status": row.release_status,
			}
		)

	return _columns(), data


def _columns():
	return [
		{"label": "紧急度", "fieldname": "urgency", "fieldtype": "Data", "width": 130},
		{"label": "剩余天数", "fieldname": "days_left", "fieldtype": "Int", "width": 100},
		{"label": "有效期至", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
		{"label": "生产日期", "fieldname": "manufacturing_date", "fieldtype": "Date", "width": 110},
		{"label": "物料代码", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": "物料名称", "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": "批号", "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 160},
		{"label": "货位", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
		{"label": "数量", "fieldname": "qty", "fieldtype": "Float", "precision": 3, "width": 110},
		{"label": "单位", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": "效期类型", "fieldname": "shelf_life_type", "fieldtype": "Data", "width": 100},
		{"label": "放行状态", "fieldname": "release_status", "fieldtype": "Data", "width": 100},
	]
