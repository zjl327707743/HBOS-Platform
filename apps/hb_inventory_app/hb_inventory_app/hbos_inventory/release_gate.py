"""出库放行门禁

业务规则（Owner 确认）：
    出库须有 QA 出具的**放行手续与合格证**，缺任一项不可出库。

实现：挂在 `before_submit`（而非 `validate`），使草稿仍可自由保存与修改，
仅在提交时拦截。

判定范围（仅"真正出库"，内部流转不拦）：
    - `Delivery Note`（销售发货路径）
    - `Stock Entry` 且 `purpose` 属于 `OUTWARD_STOCK_ENTRY_PURPOSES`：
        - `Material Issue`      领用 / 出库
        - `Send to Subcontractor`  **发外协**：原辅料发到受托方，我方批次离开公司

不拦的情况（**逐条列在 `INTERNAL_STOCK_ENTRY_PURPOSES`，有意为之**）：
    - `Material Receipt`（入库）：待检物料本就该能入库
    - `Material Transfer`（库间 / 货位间移库）：**含移入不合格品库、退回产品区等
      「正常内部隔离移库」**——但目标已由提交的外协订单登记为受托方仓时，
      对该行按出库校验；公司账务归属相同不代表物理内部
    - 其余 ERPNext purpose 见该常量，均写明理由

分类必须**覆盖 ERPNext 的全部 purpose**：`erpnext.stock.doctype.stock_entry.stock_entry`
的 `validate_purpose` 是闭集；本模块把它的取值分成「出库 / 非出库」两类，
分类不全或出现未分类取值时**明确报错**（`_outward_rows`），
并由 `tests/test_release_gate_purposes.py` 钉住覆盖——宁可报错，也不静默漏拦。

批次取法：
    v16 中 `Stock Ledger Entry.batch_no` 为空列，批次在 `Serial and Batch Entry`。
    明细行优先取 `batch_no` 字段；取不到则回落到 `serial_and_batch_bundle` 查子表。
    （M3-R1 实测结论，详见 M3-R1 主文档第四节）
"""

import frappe
from frappe import _

# 需要放行的出库单据类型
GATED_DOCTYPES = ("Delivery Note", "Stock Entry")

# ── Stock Entry purpose 分类 ──
#
# 判据：**批次是否离开公司**。只离开仓库（货位/库位/库区之间）不算出库。

#: 出库方向：我方批次离开公司，**必须**过质量放行门禁。
OUTWARD_STOCK_ENTRY_PURPOSES = (
    "Material Issue",  # 领用 / 出库
    "Send to Subcontractor",  # 发外协：原辅料发到受托方
)

#: 非出库：库内流转或入向，**故意不拦**。逐条写明理由，
#: 免得后来者以为是漏配。
INTERNAL_STOCK_ENTRY_PURPOSES = (
    "Material Receipt",  # 入库：待检物料本就该能入库
    # 货位 / 库位间移库——**含移入不合格品库、退回产品区等「正常内部隔离移库」**。
    # 这是本项目明确要求「与出库区分开」的一条：物仍在公司内，账仍在我们手上，
    # 拿放行门禁去挡它只会让仓管无法把货挪到隔离区。
    "Material Transfer",  # 默认内部；受托方目标在 _outward_rows 中逐行判定
    "Material Transfer for Manufacture",  # 发料到在制品仓，仍在公司内
    "Material Consumption for Manufacture",  # 在制品消耗
    "Manufacture",  # 生产入库
    "Repack",  # 改包
    "Disassemble",  # 拆解
    "Receive from Customer",  # 客户来料入库
    "Subcontracting Return",  # 受托方退回多余原辅料（入向）
    # 退还客户来料：批次是**客户**的，不是我方放行对象
    "Return Raw Material to Customer",
    # 受托方交付：`s_warehouse` 取的是 SIO 的 `delivery_warehouse`（受托方货位），
    # 出的是**对方**的货，同样不是我方放行对象
    "Subcontracting Delivery",
)

RELEASED = "已放行"


def is_outward_stock_entry(doc) -> bool:
	"""该 purpose 是否固定属于「我方批次出库」。

	Material Transfer 的受托方目标由 _outward_rows 额外逐行判定。

	未分类的 purpose **报错**而不是放过：ERPNext 的 purpose 是闭集，
	出现新值说明上游变了，需要人来重新分类，不该静默漏拦。
	"""
	purpose = str(doc.get("purpose") or "").strip()
	if purpose in OUTWARD_STOCK_ENTRY_PURPOSES:
		return True
	if purpose in INTERNAL_STOCK_ENTRY_PURPOSES:
		return False
	frappe.throw(
		_(
			"未分类的 Stock Entry 用途「{0}」：无法判断是否为出库，"
			"请先在 hb_inventory_app 的 release_gate 中分类后再提交。"
		).format(purpose or _("（空）"))
	)



def _batch_nos_from_row(row):
	"""从明细行取批号：优先 batch_no，回落 serial_and_batch_bundle。"""
	nos = []
	if row.get("batch_no"):
		nos.append(row.batch_no)
	elif row.get("serial_and_batch_bundle"):
		nos.extend(
			frappe.db.sql(
				"""select distinct batch_no from `tabSerial and Batch Entry`
				   where parent = %s and ifnull(batch_no, '') != ''""",
				row.serial_and_batch_bundle,
				pluck=True,
			)
		)
	return [n for n in nos if n]



def _registered_subcontractor_targets(doc, rows):
	"""Read native submitted order facts once per document, not once per row.

	The Warehouse company is an accounting owner; it does not identify physical
	custody. Both current Subcontracting Orders and subcontracted Purchase Orders
	can register a supplier warehouse. No naming convention or user-supplied
	Stock Entry supplier flag is used as authority.
	"""
	targets = sorted({row.get("t_warehouse") for row in rows if row.get("t_warehouse")})
	if not targets:
		return set()
	filters = {
		"company": doc.get("company"),
		"docstatus": 1,
		"supplier_warehouse": ["in", targets],
	}
	external = set(frappe.get_all(
		"Subcontracting Order", filters=filters, pluck="supplier_warehouse",
	))
	external.update(frappe.get_all(
		"Purchase Order", filters={**filters, "is_subcontracted": 1},
		pluck="supplier_warehouse",
	))
	return external


def _outward_rows(doc):
	"""返回该单据中属于"出库方向"的明细行。"""
	if doc.doctype == "Delivery Note":
		# 退货单是入库方向，不放行门禁
		if doc.get("is_return"):
			return []
		return list(doc.items)

	if doc.doctype == "Stock Entry":
		# Always classify first: an unknown purpose must still fail closed.
		fixed_outward = is_outward_stock_entry(doc)
		source_rows = [row for row in doc.items if row.get("s_warehouse")]
		if fixed_outward:
			return source_rows
		if str(doc.get("purpose") or "").strip() == "Material Transfer":
			external_targets = _registered_subcontractor_targets(doc, source_rows)
			# Only the destination determines outward direction. A return from a
			# job worker to an internal/quarantine warehouse remains possible.
			return [row for row in source_rows if row.get("t_warehouse") in external_targets]
		return []

	return []


def validate_release(doc, method=None):
	"""before_submit 钩子：校验出库批次的放行状态与合格证。"""
	rows = _outward_rows(doc)
	if not rows:
		return

	blocked = []
	seen = set()
	for row in rows:
		for batch_no in _batch_nos_from_row(row):
			if batch_no in seen:
				continue
			seen.add(batch_no)

			info = frappe.db.get_value(
				"Batch",
				batch_no,
				["hbos_release_status", "hbos_release_date", "hbos_certificate_no",
				 "hbos_certificate_file", "hbos_lims_reference", "hbos_release_source"],
				as_dict=True,
			)
			if not info:
				# 批次不存在的情况交由 ERPNext 自身校验处理
				continue

			status = (info.hbos_release_status or "").strip()
			cert = (info.hbos_certificate_no or "").strip()
			cert_file = (info.hbos_certificate_file or "").strip()
			release_date = info.hbos_release_date
			lims_ref = (info.hbos_lims_reference or "").strip()
			source = (info.hbos_release_source or "").strip()

			if (
				status != RELEASED
				or not release_date
				or not cert
				or not cert_file
				or not lims_ref
				or source != "LIMS"
			):
				missing = []
				if status != RELEASED:
					missing.append(_("放行状态为「{0}」").format(status or _("未设置")))
				if not release_date:
					missing.append(_("无放行日期"))
				if not cert:
					missing.append(_("无合格证编号"))
				if not cert_file:
					missing.append(_("无合格证附件"))
				if not lims_ref:
					missing.append(_("无 LIMS 放行引用"))
				if source != "LIMS":
					missing.append(_("放行来源不是 LIMS"))
				blocked.append(f"{batch_no}（{'、'.join(missing)}）")

	if blocked:
		frappe.throw(
			_("以下批次未取得 QA 放行手续或合格证，不可出库：<br>{0}<br><br>"
			  "请由 LIMS 完成检验、COA 发布与质量放行后再提交。").format(
				"<br>".join(blocked)
			),
			title=_("出库放行校验未通过"),
		)
