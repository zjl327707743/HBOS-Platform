"""出库放行门禁

业务规则（Owner 确认）：
    出库须有 QA 出具的**放行手续与合格证**，缺任一项不可出库。

实现：挂在 `before_submit`（而非 `validate`），使草稿仍可自由保存与修改，
仅在提交时拦截。

判定范围（仅"真正出库"，内部移库不拦）：
    - `Delivery Note`（销售发货路径）
    - `Stock Entry` 且 `purpose == "Material Issue"`（非销售领用 / 出库路径）

不拦的情况（有意为之）：
    - `Material Receipt`（入库）：待检物料本就该能入库
    - `Material Transfer`（库间 / 货位间移库）：含移入不合格品库，属库内流转

批次取法：
    v16 中 `Stock Ledger Entry.batch_no` 为空列，批次在 `Serial and Batch Entry`。
    明细行优先取 `batch_no` 字段；取不到则回落到 `serial_and_batch_bundle` 查子表。
    （M3-R1 实测结论，详见 M3-R1 主文档第四节）
"""

import frappe
from frappe import _

# 需要放行的出库单据类型
GATED_DOCTYPES = ("Delivery Note", "Stock Entry")

# Stock Entry 中属于"出库"的用途
OUTWARD_STOCK_ENTRY_PURPOSES = ("Material Issue",)

RELEASED = "已放行"


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


def _outward_rows(doc):
	"""返回该单据中属于"出库方向"的明细行。"""
	if doc.doctype == "Delivery Note":
		# 退货单是入库方向，不放行门禁
		if doc.get("is_return"):
			return []
		return list(doc.items)

	if doc.doctype == "Stock Entry":
		if doc.get("purpose") not in OUTWARD_STOCK_ENTRY_PURPOSES:
			return []
		# 出库行 = 有来源仓库的行
		return [r for r in doc.items if r.get("s_warehouse")]

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
				["hbos_release_status", "hbos_certificate_no"],
				as_dict=True,
			)
			if not info:
				# 批次不存在的情况交由 ERPNext 自身校验处理
				continue

			status = (info.hbos_release_status or "").strip()
			cert = (info.hbos_certificate_no or "").strip()

			if status != RELEASED or not cert:
				missing = []
				if status != RELEASED:
					missing.append(_("放行状态为「{0}」").format(status or _("未设置")))
				if not cert:
					missing.append(_("无合格证编号"))
				blocked.append(f"{batch_no}（{'、'.join(missing)}）")

	if blocked:
		frappe.throw(
			_("以下批次未取得 QA 放行手续或合格证，不可出库：<br>{0}<br><br>"
			  "请先在批次上录入放行状态（已放行）、放行日期与合格证编号后再提交。").format(
				"<br>".join(blocked)
			),
			title=_("出库放行校验未通过"),
		)
