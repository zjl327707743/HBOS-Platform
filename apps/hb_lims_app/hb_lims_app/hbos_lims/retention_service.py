# -*- coding: utf-8 -*-
"""M2-R7A 留样业务服务（Frappe 层）：登记入库 + 从检验样品创建 + 库存写路径。

约定（与 lims_service.py 一致）：
- 公开方法为 @frappe.whitelist 模块级函数，入口先校验角色。
- 显式事务管理（commit / rollback）。
- 库存 current_qty / reserved_qty 单一写路径（方案 7.4）：
  登记入库 / （R7C 交付：confirm_stock / execute_usage / execute_disposal /
  transfer_out / adjust_stock / 驳回释放）。
"""

import frappe

from hb_lims_app.hbos_lims import retention_contract as rtc
from hb_lims_app.hbos_lims import workflow_contract as wf


def _user():
	return frappe.session.user


def _now():
	return frappe.utils.now_datetime()


def _commit():
	frappe.db.commit()


def _rollback():
	frappe.db.rollback()


def _check_action(action):
	roles = frappe.get_roles(_user())
	if not any(wf.action_allowed(action, role) for role in roles):
		frappe.throw(f"当前用户（{_user()}）没有执行「{action}」的权限。")


# ---------------------------------------------------------------------------
# 登记（记录一电子化）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def register_retention(retention_product=None, batch_no=None, retention_date=None,
					   retention_qty=None, package_count=None, package_spec=None,
					   source=None, expiry_type=None, expiry_date=None,
					   retention_due_date=None, storage_location=None,
					   observed_flag=0, container_no=1, source_sample=None,
					   obs_year=None, obs_selected_by=None, obs_selected_date=None,
					   obs_selected_reason=None, remarks=None, auto_calc=None):
	"""留样登记（Analyst/Manager）。

	- 液体物料硬拦截；受托产品直接以已转出落位（不经在库）。
	- 留样量：auto_calc=1 且 UOM 一致性闸通过时按 2 倍计算；否则用传入值。
	- 留样期至：未传时自动 = expiry_date + 3 年。
	- 在库登记：current_qty 初始化 + 入库流水；受托登记：0 量 + 审计事件。
	"""
	_check_action("register_retention")
	try:
		product = frappe.get_doc("HBOS Retention Product", retention_product)
		if product.is_liquid:
			frappe.throw("液体物料不留样（规程 4.1），该产品已标记为液体物料。")
		if not product.is_active:
			frappe.throw("该留样产品已停用，不再登记新留样。")

		# 留样量（2 倍自动计算 + UOM 一致性闸）
		qty = retention_qty
		if auto_calc:
			qty, err = rtc.calc_retention_qty(
				product.retention_qty_rule, product.full_test_qty,
				product.full_test_qty_uom, product.default_uom)
			if err:
				frappe.throw(err)
		if qty is None:
			frappe.throw("请填写留样量（未自动计算：产品规则非 2 倍、全检量未维护或 UOM 不一致）。")

		is_outsource = bool(product.is_outsource)

		# 外售产品每批观察（规程 4.3.1）：自动补观察字段（DocType validate 兜底 reason）
		if product.category == "外售产品" and product.obs_rule == "每批观察（外售产品）":
			observed_flag = 1
			obs_selected_reason = obs_selected_reason or "外售产品每批"
			obs_year = obs_year or frappe.utils.getdate(retention_date).year

		doc = frappe.get_doc({
			"doctype": "HBOS Retention Sample",
			"retention_product": retention_product,
			"batch_no": batch_no,
			"container_no": container_no or 1,
			"source": source,
			"retention_date": retention_date,
			"expiry_type": expiry_type,
			"expiry_date": expiry_date,
			"retention_due_date": retention_due_date,
			"retention_qty": qty,
			"package_count": package_count,
			"package_spec": package_spec,
			"storage_location": storage_location,
			"observed_flag": observed_flag,
			"obs_year": obs_year,
			"obs_selected_by": obs_selected_by or _user(),
			"obs_selected_date": obs_selected_date or frappe.utils.today(),
			"obs_selected_reason": obs_selected_reason,
			"source_sample": source_sample,
			"retained_by": _user(),
			"remarks": remarks,
			"status": "已转出" if is_outsource else "在库",
			"current_qty": 0 if is_outsource else qty,
			"reserved_qty": 0,
		})
		# 全检量 < 1g 提示（非硬拦截）
		note = rtc.min_qty_note(product.full_test_qty, product.full_test_qty_uom)
		doc.insert(ignore_permissions=True)
		# 注意：insert 提交后 current_qty 由 on_insert 钩子在内存置值，
		# 这里统一走 _write_stock_log（append 流水 + save 落库 current_qty 与流水）。

		if not is_outsource:
			_write_stock_log(doc, "入库（登记）", qty, "HBOS Retention Sample", doc.name)
			_audit("登记入库", doc.name, new_value="qty={}".format(qty))
		else:
			# 受托转出落位（rev6）：不经在库，0 量审计事件
			_audit("受托转出", doc.name,
				   action_text="受托产品登记直接以已转出状态创建（不经在库）",
				   new_value="qty=0")
		_commit()

		message = note or None
		return {"name": doc.name, "qty": qty, "note": message,
				"status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def create_retention_from_sample(sample_name, retention_qty=None, container_no=1,
								 storage_location=None, remarks=None):
	"""从检验完成批次（HBOS Sample）一键创建留样（方案第九节映射 6 规则）。"""
	_check_action("register_retention")
	try:
		sample = frappe.get_doc("HBOS Sample", sample_name)
		product_exists = bool(frappe.db.exists(
			"HBOS Retention Product", {"product_code": sample.material_code}))
		ok, err = rtc.check_sample_source_mapping(
			sample.sample_type, sample.status, sample.sample_source,
			sample.material_code, product_exists)
		if not ok:
			frappe.throw(err)

		# 产品匹配（规则 4：不自动创建）
		product = frappe.get_doc("HBOS Retention Product",
								 {"product_code": sample.material_code})
		qty = retention_qty
		if qty is None and product.retention_qty_rule == "全检量 2 倍":
			qty, err = rtc.calc_retention_qty(
				product.retention_qty_rule, product.full_test_qty,
				product.full_test_qty_uom, product.default_uom)
			if err:
				frappe.throw(err)

		return register_retention(
			retention_product=product.name,
			batch_no=sample.batch_no,
			retention_date=frappe.utils.today(),
			retention_qty=qty,
			source="检验样品 {}".format(sample_name),
			expiry_type="有效期至",
			expiry_date=None,  # 检验样品不携带效期，留样期至人工补
			storage_location=storage_location,
			container_no=container_no,
			source_sample=sample_name,
			remarks=remarks or "从检验样品 {} 创建".format(sample_name),
		)
	except Exception:
		_rollback()
		raise


# ---------------------------------------------------------------------------
# 手动调整（R7A 交付；预占相关用例在 R7C）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def adjust_stock(retention_name, new_current_qty, reason):
	"""手动调整结存（仅 Manager，原因必填，审计留痕）。

	R7A 边界：reserved_qty 恒为 0，校验 current_qty >= 0；
	R7C 后同方法校验 current_qty >= reserved_qty（retention_contract.check_adjust_stock 已含）。
	"""
	_check_action("adjust_stock")
	if not reason:
		frappe.throw("手动调整必须填写原因。")
	try:
		# 四步锁协议（方案 7.2）
		row = _lock_row(retention_name)
		ok, err = rtc.check_adjust_stock(row.current_qty, row.reserved_qty, new_current_qty)
		if not ok:
			frappe.throw(err)

		doc = frappe.get_doc("HBOS Retention Sample", retention_name)
		delta = (new_current_qty or 0) - (row.current_qty or 0)
		doc.current_qty = new_current_qty
		doc.save(ignore_permissions=True)
		_write_stock_log(doc, "手动调整", delta, "", None)
		_audit("手动调整", retention_name, reason=reason,
			   old_value="current_qty={}".format(row.current_qty),
			   new_value="current_qty={}".format(new_current_qty))
		_commit()
		return {"name": retention_name, "current_qty": new_current_qty}
	except Exception:
		_rollback()
		raise


# ---------------------------------------------------------------------------
# 内部：库存写路径唯一入口（方案 7.4）
# ---------------------------------------------------------------------------

def _lock_row(retention_name):
	"""四步锁协议第 2 步：FOR UPDATE 行级锁并返回锁内值。"""
	row = frappe.db.sql(
		"SELECT current_qty, reserved_qty FROM `tabHBOS Retention Sample`"
		" WHERE name=%s FOR UPDATE",
		retention_name, as_dict=True)
	if not row:
		frappe.throw("留样 {} 不存在。".format(retention_name))
	return row[0]


def _write_stock_log(doc, transaction_type, qty_delta, source_doctype, source_name):
	"""写库存操作流水子表（入库/使用/销毁/转出/调整全来源通用）。"""
	today = frappe.utils.today()
	doc.append("stock_logs", {
		"transaction_date": today,
		"transaction_type": transaction_type,
		"source_doctype": source_doctype or "",
		"source_name": source_name or "",
		"qty_delta": qty_delta or 0,
		"qty_uom": doc.qty_uom,
		"remaining_qty": doc.current_qty or 0,
		"operator": _user(),
	})
	doc.save(ignore_permissions=True)


def _audit(log_type, doc_name, action_text="", old_value="", new_value="", reason=""):
	"""审计埋点（复用 R6D audit_log，事件枚举受控——方案 8.1）。"""
	from hb_lims_app.hbos_lims.lims_service import audit_log
	audit_log(log_type, "HBOS Retention Sample", doc_name,
			  action_text=action_text, old_value=old_value, new_value=new_value,
			  reason=reason, commit=False)
