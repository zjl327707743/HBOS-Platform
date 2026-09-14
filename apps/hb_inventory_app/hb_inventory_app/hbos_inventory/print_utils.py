"""打印辅助方法（供 Print Format 的 Jinja 调用）

由 `hooks.py` 的 `jinja.methods` 注册整个模块，因此在模板中可直接调用这些
函数名（无需模块前缀），例如：

    {{ hbos_packaging_count(doc.name) }}

设计约束：
- 所有函数以 `hbos_` 前缀命名，避免与 Frappe / ERPNext 自带的 Jinja 方法与
  过滤器重名。
- 均为只读查询，不做任何写入。
"""

import frappe

# 注意：本模块整体被 hooks.jinja.methods 注册为 Jinja 全局方法，注册逻辑会
# 收集模块内**所有**函数（含 import 进来的函数）。因此这里只 `import frappe`，
# 不 `from frappe.utils import ...`，避免把 flt / getdate 等外部函数一并注册、
# 覆盖 Frappe 既有的同名 Jinja 全局。
# 模块内一律使用 frappe.utils.xxx 的全限定调用。

# 自产 / 外购的取值
SOURCE_SELF = "自产"
SOURCE_OUTSOURCED = "外购"

# 空值占位（与纸质表习惯一致）
BLANK = "/"


def hbos_blank():
	"""空白取值占位，与纸质表习惯一致。"""
	return BLANK


def hbos_fmt_weight(value):
	"""重量格式化：至少保留两位小数，最多三位；整数补足两位。

	例：5 → 5.00 ／ 4.95 → 4.95 ／ 0.004 → 0.004
	"""
	flt = frappe.utils.flt
	if value is None or value == "":
		return ""
	s = f"{flt(value):.3f}".rstrip("0")
	if s.endswith("."):
		return f"{flt(value):.2f}"
	decimals = s.split(".")[1]
	return s if len(decimals) >= 2 else f"{flt(value):.2f}"


def hbos_packaging_spec(batch):
	"""包装规格：如 `5.00kg*9件 4.95kg*1件 0.03kg*4听`。"""
	if not batch:
		return ""
	rows = frappe.get_all(
		"HBOS Packaging Detail",
		filters={"parent": batch, "parenttype": "Batch"},
		fields=["container_type", "unit_weight", "count", "is_tail"],
		order_by="idx",
	)
	parts = []
	for r in rows:
		if r.unit_weight:
			parts.append(f"{hbos_fmt_weight(r.unit_weight)}kg*{r.count}{r.container_type}")
		else:
			parts.append(f"{r.count}{r.container_type}")
	return "  ".join(parts) if parts else BLANK


def hbos_packaging_count(batch):
	"""件数：如 `42件5听10瓶`。

	**按容器类型汇总**（同一容器类型的件数相加），顺序为首次出现顺序。
	依据纸质货位卡实际写法：包装规格 `5.00kg*41件 1.34kg*1件 0.03kg*4听
	0.02kg*1听 0.01kg*9瓶 0.007kg*1瓶` 对应件数 `42件5听10瓶`
	（41+1=42、4+1=5、9+1=10）。
	"""
	if not batch:
		return ""
	rows = frappe.get_all(
		"HBOS Packaging Detail",
		filters={"parent": batch, "parenttype": "Batch"},
		fields=["container_type", "count"],
		order_by="idx",
	)
	if not rows:
		return BLANK
	totals = {}
	order = []
	for r in rows:
		key = r.container_type or ""
		if key not in totals:
			totals[key] = 0
			order.append(key)
		totals[key] += int(r.count or 0)
	return "".join(f"{totals[k]}{k}" for k in order)


def hbos_batch_bins(batch):
	"""该批次当前所在的全部货位（含数量），返回 [{warehouse, qty}]。

	依据 M3-R1 实测：v16 中 `Stock Ledger Entry.batch_no` 为空列，
	批次与货位的对应关系在 `Serial and Batch Entry`。
	"""
	if not batch:
		return []
	return frappe.db.sql(
		"""
		select sbe.warehouse, sum(sbe.qty) as qty
		from `tabSerial and Batch Entry` sbe
		join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
		where sbb.docstatus = 1 and sbb.is_cancelled = 0 and sbb.is_rejected = 0
			and sbe.is_cancelled = 0 and sbe.batch_no = %(batch)s
		group by sbe.warehouse
		having sum(sbe.qty) != 0
		order by sbe.warehouse
		""",
		{"batch": batch},
		as_dict=True,
	)


def hbos_batch_bins_html(batch):
	"""货位号单元格内容：一个批次可能散放多个货位，逐行列出。

	纸质货位卡的「货位号」是单个单元格，因此多货位时在同一格内换行，
	不改变表结构。
	"""
	rows = hbos_batch_bins(batch)
	if not rows:
		return BLANK
	# 去掉公司后缀，只保留短码（如 `16-03-221 - HB` → `16-03-221`）
	return "<br>".join((r.warehouse or "").split(" - ")[0] for r in rows)


def hbos_batch_total_qty(batch):
	"""该批次当前结存总量。"""
	return sum(frappe.utils.flt(r.qty) for r in hbos_batch_bins(batch))


def hbos_batch_uom(batch):
	"""批次的计量单位（取物料的基本单位）。

	`Kg` 统一显示为 `kg`，与纸质表写法一致。
	"""
	if not batch:
		return ""
	item = frappe.db.get_value("Batch", batch, "item")
	uom = frappe.db.get_value("Item", item, "stock_uom") or ""
	return "kg" if uom.lower() == "kg" else uom


def hbos_first_receipt_date(batch):
	"""首次入库日期：取该批次最早一笔入库的记账日期。"""
	if not batch:
		return None
	d = frappe.db.sql(
		"""
		select min(sle.posting_date)
		from `tabStock Ledger Entry` sle
		join `tabSerial and Batch Bundle` sbb on sbb.name = sle.serial_and_batch_bundle
		join `tabSerial and Batch Entry` sbe on sbe.parent = sbb.name
		where sbb.docstatus = 1 and sbb.is_cancelled = 0
			and sbe.is_cancelled = 0 and sbe.batch_no = %(batch)s
			and sle.actual_qty > 0
		""",
		{"batch": batch},
	)
	return d[0][0] if d and d[0] and d[0][0] else None


def hbos_batch_in_date(batch):
	"""货位卡的「入库」日期：优先首次入库日期，回落批次创建日期。"""
	return hbos_first_receipt_date(batch) or frappe.db.get_value("Batch", batch, "creation")


def hbos_operator(batch):
	"""操作人：取批次创建人姓名，回落创建人账号。"""
	if not batch:
		return ""
	owner = frappe.db.get_value("Batch", batch, "owner")
	if not owner:
		return ""
	return frappe.db.get_value("User", owner, "full_name") or owner


def hbos_datetime_cn(value):
	"""日期格式化为 `2026.09.14` 形式（与纸质表一致）。"""
	if not value:
		return ""
	return frappe.utils.getdate(value).strftime("%Y.%m.%d")


def hbos_batch_source(batch):
	"""批次来源：自产 / 外购。字段未设置时回落推断（有供应商即外购）。"""
	if not batch:
		return SOURCE_SELF
	row = frappe.db.get_value(
		"Batch", batch, ["hbos_source_type", "supplier"], as_dict=True
	)
	if row and row.get("hbos_source_type"):
		return row.hbos_source_type
	if row and row.get("supplier"):
		return SOURCE_OUTSOURCED
	return SOURCE_SELF


def hbos_production_unit(batch):
	"""生产单位：外购取「生产单位」（批次字段），自产取「生产车间」（物料字段）。"""
	if not batch:
		return BLANK
	row = frappe.db.get_value("Batch", batch, ["hbos_manufacturer", "item"], as_dict=True)
	if not row:
		return BLANK
	if hbos_batch_source(batch) == SOURCE_OUTSOURCED:
		return (row.hbos_manufacturer or "").strip() or BLANK
	# 自产：生产车间（在 Item 上）优先，回落批次的「生产单位」
	workshop = (frappe.db.get_value("Item", row.item, "hbos_workshop") or "").strip()
	return workshop or (row.hbos_manufacturer or "").strip() or BLANK


def hbos_supplier_name(batch):
	"""供货单位：外购取批次供应商，自产无此项。"""
	if not batch:
		return BLANK
	supplier = frappe.db.get_value("Batch", batch, "supplier")
	return (supplier or "").strip() or BLANK


def hbos_item_workshop(item):
	"""物料上的生产车间（用于自产卡）。"""
	if not item:
		return BLANK
	return (frappe.db.get_value("Item", item, "hbos_workshop") or "").strip() or BLANK


def hbos_shelf_life_marks(item):
	"""复检期 / 有效期 的勾选标记，返回二元素元组。"""
	kind = (frappe.db.get_value("Item", item, "hbos_shelf_life_type") or "").strip() if item else ""
	return ("☑" if kind == "复检期" else "□", "☑" if kind == "有效期" else "□")


def hbos_storage_condition(item):
	"""储存条件（待检证用）。"""
	if not item:
		return BLANK
	return (frappe.db.get_value("Item", item, "hbos_storage_condition") or "").strip() or BLANK


def hbos_qty_with_count(batch):
	"""`数量/件数` 合并式，如 `200个/10件`（外购卡与待检证用）。"""
	qty = hbos_batch_total_qty(batch)
	uom = hbos_batch_uom(batch)
	count = hbos_packaging_count(batch)
	left = f"{hbos_fmt_weight(qty)}{uom}" if uom else hbos_fmt_weight(qty)
	if not count or count == BLANK:
		return left
	return f"{left}/{count}"


def hbos_batch_flow(batch):
	"""该批次的**出库流水**（用于货位卡的流水表预填）。

	返回 [{date, out_qty, balance}]。

	关键口径：**按单据合并后取净减少**。库内移库（Material Transfer）在同一张
	单据里一出一进、对该批次的净影响为 0，若按单行取负值会把"换货位"误记成
	"发出"，与实际业务不符，故按 `voucher_type + voucher_no` 汇总后再判断：
	仅净减少的单据计入流水。

	`件数` 与「去向 / 领料单位 / 用途」系统中无法准确获得，留空供手写。
	结存量按批次维度累加（跨货位合并），与该卡"一个批号一张卡"的口径一致。
	"""
	if not batch:
		return []

	movements = frappe.db.sql(
		"""
		select
			sle.posting_date as posting_date,
			sle.posting_datetime as posting_datetime,
			sle.voucher_type as voucher_type,
			sle.voucher_no as voucher_no,
			sum(sbe.qty) as net_qty
		from `tabSerial and Batch Entry` sbe
		join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
		join `tabStock Ledger Entry` sle on sle.serial_and_batch_bundle = sbb.name
		where sbb.docstatus = 1 and sbb.is_cancelled = 0 and sbb.is_rejected = 0
			and sbe.is_cancelled = 0 and sle.is_cancelled = 0
			and sbe.batch_no = %(batch)s
		group by sle.voucher_type, sle.voucher_no, sle.posting_date, sle.posting_datetime
		order by sle.posting_datetime, sle.voucher_no
		""",
		{"batch": batch},
		as_dict=True,
	)

	flt = frappe.utils.flt
	balance = 0.0
	flow = []
	for m in movements:
		net = flt(m.net_qty)
		balance += net
		if net < 0:
			flow.append(
				{
					"date": m.posting_date,
					"out_qty": abs(net),
					"balance": balance,
					"voucher": m.voucher_no,
				}
			)
	return flow


def hbos_blank_date():
	"""未填日期的占位：与纸质表「年　　月　　日」一致。"""
	return "年&nbsp;&nbsp;&nbsp;&nbsp;月&nbsp;&nbsp;&nbsp;&nbsp;日"


def hbos_batch_date_cn(batch, field="in"):
	"""按字段渲染批次日期：in（入库）/ 待检（无）/ 放行。

	无数据时返回占位。返回的是 HTML（含 &nbsp;），模板中勿再转义。
	"""
	if field == "release":
		value = frappe.db.get_value("Batch", batch, "hbos_release_date")
	else:
		value = hbos_batch_in_date(batch)
	if not value:
		return hbos_blank_date()
	d = frappe.utils.getdate(value)
	return f"{d.year}年&nbsp;&nbsp;{d.month}月&nbsp;&nbsp;{d.day}日"


def hbos_release_marks(batch):
	"""放行□ 不放行□ 的勾选标记，返回二元素元组。"""
	status = (frappe.db.get_value("Batch", batch, "hbos_release_status") or "").strip() if batch else ""
	return ("☑" if status == "已放行" else "□", "☑" if status == "不放行" else "□")

