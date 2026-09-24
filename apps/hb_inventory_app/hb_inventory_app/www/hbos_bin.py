"""货位扫码页（Frappe 原生 Web 页）

扫码目标：贴在货架上的二维码，内容为 `{site}/hbos-bin?bin={货位短码}`。

设计要点：
- **二维码不存静态物料信息**，扫码后由本页实时查库，信息动态更新（Owner 在 M3-R0 已定）。
- 展示**全部字段、不做脱敏**（Owner 在 M3-R5 确认）。
- 需登录访问：未登录跳转登录页，登录后回到本页。这是 Frappe 的默认安全边界，
  与"字段不脱敏"并不冲突——字段对**已登录的普通员工**全开放。

数据源：`Serial and Batch Entry` 关联 `Serial and Batch Bundle`
（v16 中 `Stock Ledger Entry.batch_no` 为空列不可用，详见 M3-R1 主文档第四节）。
"""

import frappe

BIN_QUERY_KEY = "bin"


def get_context(context):
	context.no_cache = 1
	context.title = "货位信息"

	# 需登录：未登录时跳登录页，登录后回跳本页（redirect-to 需整体 URL 编码）
	if frappe.session.user == "Guest":
		from urllib.parse import quote

		target = frappe.local.request.path
		code = frappe.form_dict.get(BIN_QUERY_KEY)
		if code:
			target = f"{target}?{BIN_QUERY_KEY}={code}"
		frappe.local.flags.redirect_location = f"/login?redirect-to={quote(target, safe='')}"
		raise frappe.Redirect

	code = (frappe.form_dict.get(BIN_QUERY_KEY) or "").strip()

	# 先给全部上下文变量兜底，避免模板出现 undefined
	context.bin_code = code
	context.rows = []
	context.warehouse = None
	context.warehouse_label = code
	context.is_group = False
	context.error = None
	context.total_qty = 0.0
	context.batch_count = 0
	context.item_count = 0

	if not code:
		context.error = "缺少货位参数。请扫描货架上的二维码，或手动在网址后添加 ?bin=货位号。"
		return

	warehouses, warehouse_doc, is_group = _resolve_warehouse(code)
	if not warehouses:
		context.error = f"未找到货位「{code}」。请确认二维码是否有效。"
		return

	context.warehouse = warehouse_doc.name
	context.warehouse_label = _short(warehouse_doc.name)
	context.is_group = is_group
	context.rows = _fetch_rows(warehouses)
	context.total_qty = sum(r["qty"] for r in context.rows)
	context.batch_count = len({r["batch_no"] for r in context.rows if r["batch_no"]})
	context.item_count = len({r["item_code"] for r in context.rows})
	return context


def _short(name):
	"""去掉公司后缀，显示短码。"""
	return (name or "").split(" - ")[0]


def _resolve_warehouse(code):
	"""把短码解析为 Warehouse。

匹配顺序（先精确后宽松）：
	1. 完整名称精确命中（含公司后缀）；
	2. 短码精确命中（去掉 ` - HB` 后完全相等）；
	3. 短码前缀命中（如手输 `3904` 命中 `3904 六车间中间库`）。

命中分组节点（库位 / 层）时展开其下全部叶子货位。
"""
	rows = frappe.db.sql(
		"""select name, is_group, lft, rgt from `tabWarehouse`
		   order by lft""",
		as_dict=True,
	)
	if not rows:
		return [], None, False

	target = rows
	doc = None

	# 1) 完整名
	for r in target:
		if r.name == code:
			doc = r
			break
	# 2) 短码精确
	if doc is None:
		for r in target:
			if _short(r.name) == code:
				doc = r
				break
	# 3) 短码前缀
	if doc is None:
		for r in target:
			if _short(r.name).startswith(code):
				doc = r
				break

	if doc is None:
		return [], None, False

	warehouse_doc = frappe.get_doc("Warehouse", doc.name)

	if not doc.is_group:
		return [doc.name], warehouse_doc, False

	# 分组节点：取子树内的叶子货位
	leaves = frappe.db.sql(
		"""select name from `tabWarehouse`
		   where lft >= %(lft)s and rgt <= %(rgt)s and is_group = 0
		   order by lft""",
		{"lft": doc.lft, "rgt": doc.rgt},
		pluck=True,
	)
	return leaves, warehouse_doc, True


def _fetch_rows(warehouses):
	"""按货位取全部批次明细（含全部字段，不脱敏）。"""
	if not warehouses:
		return []

	placeholders = ", ".join(f"%(wh_{i})s" for i in range(len(warehouses)))
	values = {f"wh_{i}": name for i, name in enumerate(warehouses)}

	rows = frappe.db.sql(
		f"""
		select
			sbe.warehouse,
			sbe.item_code,
			i.item_name,
			sbe.batch_no,
			sum(sbe.qty) as qty,
			i.stock_uom as uom,
			b.manufacturing_date,
			b.expiry_date,
			b.hbos_release_status as release_status,
			b.hbos_certificate_no as certificate_no,
			b.hbos_release_date as release_date,
			b.hbos_source_type as source_type,
			b.hbos_supplier_batch_no as supplier_batch_no,
			b.supplier as supplier,
			b.hbos_manufacturer as manufacturer,
			i.hbos_workshop as workshop,
			i.hbos_shelf_life_type as shelf_life_type
		from `tabSerial and Batch Entry` sbe
		join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
		left join `tabItem` i on i.name = sbe.item_code
		left join `tabBatch` b on b.name = sbe.batch_no
		where sbb.docstatus = 1 and sbb.is_cancelled = 0 and sbb.is_rejected = 0
			and sbe.is_cancelled = 0
			and sbe.warehouse in ({placeholders})
		group by sbe.warehouse, sbe.item_code, sbe.batch_no
		having sum(sbe.qty) != 0
		order by sbe.warehouse, sbe.item_code, b.expiry_date, sbe.batch_no
		""",
		values,
		as_dict=True,
	)

	from hb_inventory_app.hbos_inventory.print_utils import (
		hbos_packaging_count,
		hbos_packaging_spec,
	)

	out = []
	for r in rows:
		out.append(
			{
				"warehouse": _short(r.warehouse),
				"item_code": r.item_code,
				"item_name": r.item_name,
				"batch_no": r.batch_no,
				"qty": frappe.utils.flt(r.qty),
				"uom": "kg" if (r.uom or "").lower() == "kg" else (r.uom or ""),
				"manufacturing_date": r.manufacturing_date,
				"expiry_date": r.expiry_date,
				"release_status": r.release_status or "未设置",
				"certificate_no": r.certificate_no,
				"release_date": r.release_date,
				"source_type": r.source_type or "未设置",
				"supplier_batch_no": r.supplier_batch_no,
				"supplier": r.supplier,
				"manufacturer": r.manufacturer,
				"workshop": r.workshop,
				"shelf_life_type": r.shelf_life_type,
				"packaging_spec": hbos_packaging_spec(r.batch_no),
				"packaging_count": hbos_packaging_count(r.batch_no),
			}
		)
	return out
