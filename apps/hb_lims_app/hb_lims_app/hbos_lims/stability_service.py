# -*- coding: utf-8 -*-
"""M2-R8A 稳定性业务服务（Frappe 层）：通知单 / 方案状态机、冻结快照与只读聚合。

约定（与 lims_service.py / retention_service.py 一致）：
- 公开方法为 @frappe.whitelist 模块级函数，入口先校验角色（`_check_action`）。
- 显式事务管理（commit / rollback）。
- 系统字段（状态/签署/版本链）单一写路径：本模块是唯一合法写入者，
  控制器层 stability_guards 负责拦截其它直写路径（方案 8.6）。

R8A 落地范围：4 主数据 + 通知单 + 方案（方案 11.1）。
R8B~R8D 的样品/时间点/结果/报告/变更/故障方法按子轮增量补入本模块。
"""

import frappe

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import workflow_contract as wf


def _user():
	return frappe.session.user


def _now():
	return frappe.utils.now_datetime()


def _today():
	return frappe.utils.today()


def _commit():
	frappe.db.commit()


def _truthy(value):
	"""whitelist 参数经 POST 过来可能是字符串（"1" / "0" / "true"），统一判定。"""
	if value is None:
		return False
	if isinstance(value, str):
		return value.strip().lower() in ("1", "true", "yes", "on")
	return bool(value)


def _rollback():
	frappe.db.rollback()


def _check_action(action, doctype_target, doc_name=""):
	"""角色校验。失败时先独立提交「越权拦截」审计再抛错（方案 8.7 / 门禁 17）。

	审计写入本身失败不得掩盖权限拒绝——包一层 try 并落错误日志。
	"""
	roles = frappe.get_roles(_user())
	if not any(wf.action_allowed(action, role) for role in roles):
		_audit_violation(doctype_target, doc_name,
						 "角色不足：{}".format(action),
						 "当前用户（{}）没有执行「{}」的权限".format(_user(), action))
		frappe.throw("当前用户（{}）没有执行「{}」的权限。".format(_user(), action))


def _audit_on(doctype, log_type, doc_name, action_text="", old_value="", new_value="", reason=""):
	from hb_lims_app.hbos_lims.lims_service import audit_log
	audit_log(log_type, doctype, doc_name, action_text=action_text,
			  old_value=old_value, new_value=new_value, reason=reason, commit=False)


def _audit_commit(doctype, log_type, doc_name, action_text="", old_value="", new_value="", reason=""):
	"""违规尝试（SoD/越权/非法转移）审计：抛错前独立提交，避免随主事务回滚丢失（write-once 合规）。"""
	from hb_lims_app.hbos_lims.lims_service import audit_log
	audit_log(log_type, doctype, doc_name, action_text=action_text,
			  old_value=old_value, new_value=new_value, reason=reason, commit=True)


def _audit_violation(doctype, doc_name, action_text, reason=""):
	"""违规拦截审计，失败时降级为错误日志，不阻断后续的权限/状态拒绝。"""
	try:
		_audit_commit(doctype, "越权拦截", doc_name or "-",
					  action_text=action_text, reason=reason)
	except Exception as exc:
		frappe.log_error("越权拦截审计写入失败：{}".format(exc), "HBOS Stability 越权审计")


def _reject(doctype, doc_name, message, action_text):
	"""非法状态操作统一处置：先独立提交审计再抛错（方案 8.7 / 门禁 17）。"""
	_audit_violation(doctype, doc_name, action_text, message)
	frappe.throw(message)


def _load(doctype, name):
	"""装载文档并开关系统字段写入标记（业务服务是系统字段的合法写入者）。"""
	doc = frappe.get_doc(doctype, name)
	doc.flags.allow_system_fields = True
	return doc


def _set_status(doc, flow, target):
	current = doc.status
	if not wf.can_transition(flow, current, target):
		_reject(doc.doctype, doc.name,
				"非法状态流转：{} -> {}（{}）".format(current, target, flow),
				"非法状态转移：{} -> {}".format(current, target))
	doc.status = target


def _product_of_notice(notice):
	return frappe.get_doc("HBOS Stability Product", notice.stability_product)


# ---------------------------------------------------------------------------
# 通知单（FLOW_STB_NOTICE，方案 6.3.1 / 5.2.1）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_stability_notice(stability_product, study_reason, study_conditions=None,
							batches=None, extra_condition_reason=None,
							qty=None, qty_uom=None, pack_desc=None,
							test_cycle=None, test_method=None, spec_ref=None,
							spec_version=None, method_version=None, limits_snapshot=None):
	"""新建考察通知单（草稿）。study_conditions / batches 为子表行列表。

	`extra_condition_reason` 为条件 > 2 个时的补充原因（方案 4.1）；DocType 层对 LIMS
	角色只读（方案 8.6），该字段只能由本服务写入，故必须在建档入口一次收齐，
	否则 > 2 条件的通知单无法通过 submit_notice 的前置校验。
	"""
	_check_action("create_notice", "HBOS Stability Notice", stability_product)
	product = frappe.get_doc("HBOS Stability Product", stability_product)
	if not product.is_active:
		frappe.throw("该稳定性产品已停用，不再新建考察。")
	try:
		doc = frappe.get_doc({
			"doctype": "HBOS Stability Notice",
			"stability_product": stability_product,
			"study_reason": study_reason,
			"study_conditions": study_conditions or [],
			"batches": batches or [],
			"extra_condition_reason": extra_condition_reason,
			"is_inverted_required": 1 if product.need_inverted else 0,
			"qty": qty,
			"qty_uom": qty_uom or product.default_uom,
			"pack_desc": pack_desc or product.pack_desc,
			"test_cycle": test_cycle,
			"test_method": test_method,
			"spec_ref": spec_ref,
			"spec_version": spec_version,
			"method_version": method_version,
			"limits_snapshot": limits_snapshot,
			"vd_months_snapshot": product.vd_months,
			"status": stb.NOTICE_DRAFT,
		})
		doc.insert(ignore_permissions=True)
		_audit_on("HBOS Stability Notice", "创建", doc.name,
				  action_text="创建考察通知单草稿",
				  new_value="product={}".format(stability_product))
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def register_review(notice_name, review_date=None):
	"""注册人员复核（准入动作）：条件 > 2 个时为 submit_notice 的前置（方案 6.3.1）。"""
	_check_action("register_review", "HBOS Stability Notice", notice_name)
	try:
		doc = _load("HBOS Stability Notice", notice_name)
		if doc.status != stb.NOTICE_DRAFT:
			_reject("HBOS Stability Notice", notice_name,
					"仅草稿状态的通知单可做注册人员复核（当前：{}）。".format(doc.status),
					"非法状态：非草稿调用 register_review")
		doc.register_review_by = _user()
		doc.register_review_date = review_date or _today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Notice", "多条件复核", doc.name,
				  action_text="注册人员复核",
				  new_value="conditions_count={}".format(doc.conditions_count))
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def submit_notice(notice_name):
	"""提交通知单：草稿 → 待QC经理确认。

	前置（方案 6.3.1）：考察原因细化必填；> 2 个条件须先 register_review。
	"""
	_check_action("submit_notice", "HBOS Stability Notice", notice_name)
	try:
		doc = _load("HBOS Stability Notice", notice_name)
		if doc.status != stb.NOTICE_DRAFT:
			_reject("HBOS Stability Notice", notice_name,
					"仅草稿状态可提交（当前：{}）。".format(doc.status),
					"非法状态：非草稿调用 submit_notice")
		ok, err = stb.check_multi_condition_review(
			doc.conditions_count, doc.extra_condition_reason, doc.register_review_by)
		if not ok:
			frappe.throw(err)
		_set_status(doc, stb.FLOW_STB_NOTICE, stb.NOTICE_WAIT_QC)
		doc.qa_applicant = _user()
		doc.apply_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Notice", "通知单提出", doc.name,
				  action_text="通知单提交", new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def confirm_notice_qc(notice_name):
	"""QC 经理确认：待QC经理确认 → 待批准。（QC 线）"""
	_check_action("confirm_notice_qc", "HBOS Stability Notice", notice_name)
	try:
		doc = _load("HBOS Stability Notice", notice_name)
		if doc.status != stb.NOTICE_WAIT_QC:
			_reject("HBOS Stability Notice", notice_name,
					"仅「待QC经理确认」状态可确认（当前：{}）。".format(doc.status),
					"非法状态：非待QC经理确认调用 confirm_notice_qc")
		_guard_sod(doc, "HBOS Stability Notice", doc.qa_applicant, "QC 经理确认人")
		_set_status(doc, stb.FLOW_STB_NOTICE, stb.NOTICE_WAIT_APPROVE)
		doc.qc_manager_confirm_by = _user()
		doc.qc_manager_confirm_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Notice", "通知单确认", doc.name,
				  action_text="QC 经理确认", new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def approve_notice(notice_name):
	"""批准通知单：待批准 → 已批准，并冻结快照（方案 6.3.1 / 7.7）。

	快照写入：`vd_months_snapshot` 未填时取产品当前有效期；随后置 `snapshot_frozen=1`，
	其后 SNAPSHOT_FIELDS_NOTICE 只读（控制器守卫）。
	"""
	_check_action("approve_notice", "HBOS Stability Notice", notice_name)
	try:
		doc = _load("HBOS Stability Notice", notice_name)
		if doc.status != stb.NOTICE_WAIT_APPROVE:
			_reject("HBOS Stability Notice", notice_name,
					"仅「待批准」状态可批准（当前：{}）。".format(doc.status),
					"非法状态：非待批准调用 approve_notice")
		_guard_sod(doc, "HBOS Stability Notice", doc.qa_applicant, "批准人")
		_guard_sod(doc, "HBOS Stability Notice", doc.qc_manager_confirm_by, "批准人")
		if not doc.vd_months_snapshot:
			doc.vd_months_snapshot = _product_of_notice(doc).vd_months
		if doc.spec_ref and not doc.spec_version:
			frappe.throw("已填写质量标准时，必须同时写入标准版本快照（spec_version）。")
		_set_status(doc, stb.FLOW_STB_NOTICE, stb.NOTICE_APPROVED)
		doc.approver_by = _user()
		doc.approve_date = _today()
		doc.snapshot_frozen = 1
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Notice", "通知单批准", doc.name,
				  action_text="通知单批准并冻结快照",
				  new_value="status={} vd_months_snapshot={}".format(doc.status, doc.vd_months_snapshot))
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def reject_notice(notice_name, reason):
	"""驳回通知单：待QC经理确认 / 待批准 → 已驳回（终态）。"""
	_check_action("reject_notice", "HBOS Stability Notice", notice_name)
	if not (reason or "").strip():
		frappe.throw("驳回原因必填。")
	try:
		doc = _load("HBOS Stability Notice", notice_name)
		if doc.status not in (stb.NOTICE_WAIT_QC, stb.NOTICE_WAIT_APPROVE):
			_reject("HBOS Stability Notice", notice_name,
					"仅「待QC经理确认 / 待批准」状态可驳回（当前：{}）。".format(doc.status),
					"非法状态：调用 reject_notice")
		_set_status(doc, stb.FLOW_STB_NOTICE, stb.NOTICE_REJECTED)
		doc.reject_reason = reason
		doc.reject_by = _user()
		doc.reject_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Notice", "驳回", doc.name,
				  action_text="通知单驳回", reason=reason, new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def cancel_notice(notice_name, reason=None):
	"""取消通知单：草稿 → 已取消（终态）。"""
	_check_action("cancel_notice", "HBOS Stability Notice", notice_name)
	try:
		doc = _load("HBOS Stability Notice", notice_name)
		if doc.status != stb.NOTICE_DRAFT:
			_reject("HBOS Stability Notice", notice_name,
					"仅草稿状态可取消（当前：{}）。".format(doc.status),
					"非法状态：非草稿调用 cancel_notice")
		_set_status(doc, stb.FLOW_STB_NOTICE, stb.NOTICE_CANCELLED)
		doc.cancel_reason = reason or ""
		doc.cancel_by = _user()
		doc.cancel_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Notice", "通知单取消", doc.name,
				  action_text="通知单取消", reason=reason or "", new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def close_notice(notice_name):
	"""关闭通知单：已批准 → 已关闭。

	前置（方案 6.3.1）：该 Notice 下全部 Timepoint 均达终态（已完成 / 已取消）。
	R8A 尚未建 Timepoint（R8B 交付），此时恒满足；R8B 落地后本前置自动生效。
	"""
	_check_action("close_notice", "HBOS Stability Notice", notice_name)
	try:
		doc = _load("HBOS Stability Notice", notice_name)
		if doc.status != stb.NOTICE_APPROVED:
			_reject("HBOS Stability Notice", notice_name,
					"仅「已批准」状态可关闭（当前：{}）。".format(doc.status),
					"非法状态：非已批准调用 close_notice")
		pending = _open_timepoint_count(doc.name)
		if pending:
			frappe.throw("该通知单下仍有 {} 个未达终态的时间点，不可关闭。".format(pending))
		_set_status(doc, stb.FLOW_STB_NOTICE, stb.NOTICE_CLOSED)
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Notice", "通知单关闭", doc.name,
				  action_text="通知单关闭", new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


def _open_timepoint_count(notice_name):
	"""未达终态的时间点数（R8B 落地 Timepoint 后启用；此前恒为 0）。"""
	if not frappe.db.exists("DocType", "HBOS Stability Timepoint"):
		return 0
	samples = frappe.get_all("HBOS Stability Sample", filters={"notice": notice_name},
							 pluck="name")
	if not samples:
		return 0
	return frappe.db.count("HBOS Stability Timepoint", {
		"stability_sample": ["in", samples],
		"status": ["not in", ["已完成", "已取消"]],
	})


# ---------------------------------------------------------------------------
# 方案（FLOW_STB_PROTOCOL，方案 6.3.2 / 5.2.2）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_stability_protocol(notice, purpose=None, scope=None, batches=None,
							  study_conditions=None, items=None, qty=None,
							  qty_uom=None, pack_desc=None,
							  room_temp_recovery_days=0, spec_ref=None,
							  spec_version=None, test_method_ref=None,
							  method_version=None):
	"""新建稳定性方案（草稿）。年度持续稳定性考察类不建方案单（方案 4.2.5）。"""
	_check_action("submit_protocol", "HBOS Stability Protocol", notice)
	try:
		notice_doc = frappe.get_doc("HBOS Stability Notice", notice)
		product = _product_of_notice(notice_doc)
		if stb.check_year_long_study_no_protocol(product.category):
			frappe.throw("年度持续稳定性考察类不建方案单，按通知单执行（方案 4.2.5）。")
		doc = frappe.get_doc({
			"doctype": "HBOS Stability Protocol",
			"notice": notice,
			"purpose": purpose,
			"scope": scope,
			"batches": batches or [],
			"study_conditions": study_conditions or [],
			"items": items or [],
			"qty": qty,
			"qty_uom": qty_uom or product.default_uom,
			"pack_desc": pack_desc or product.pack_desc,
			"room_temp_recovery_days": room_temp_recovery_days or 0,
			"spec_ref": spec_ref,
			"spec_version": spec_version,
			"test_method_ref": test_method_ref,
			"method_version": method_version,
			"vd_months_snapshot": product.vd_months,
			"status": stb.PROTOCOL_DRAFT,
		})
		doc.insert(ignore_permissions=True)
		_audit_on("HBOS Stability Protocol", "创建", doc.name,
				  action_text="创建稳定性方案草稿", new_value="notice={}".format(notice))
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def submit_protocol(protocol_name):
	"""提交方案：草稿 → 待QA审核（前置：关联通知单已批准）。"""
	_check_action("submit_protocol", "HBOS Stability Protocol", protocol_name)
	try:
		doc = _load("HBOS Stability Protocol", protocol_name)
		if doc.status != stb.PROTOCOL_DRAFT:
			_reject("HBOS Stability Protocol", protocol_name,
					"仅草稿状态可提交（当前：{}）。".format(doc.status),
					"非法状态：非草稿调用 submit_protocol")
		notice_status = frappe.db.get_value("HBOS Stability Notice", doc.notice, "status")
		if notice_status != stb.NOTICE_APPROVED:
			frappe.throw("关联通知单须为「已批准」方可提交方案（当前：{}）。".format(notice_status))
		_set_status(doc, stb.FLOW_STB_PROTOCOL, stb.PROTOCOL_WAIT_QA)
		doc.drafted_by = _user()
		doc.draft_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Protocol", "方案起草提交", doc.name,
				  action_text="方案提交", new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def approve_protocol(protocol_name, effective_date=None):
	"""批准方案：待QA审核 → 已批准，并冻结快照（方案 6.3.2 / 7.7）。"""
	_check_action("approve_protocol", "HBOS Stability Protocol", protocol_name)
	try:
		doc = _load("HBOS Stability Protocol", protocol_name)
		if doc.status != stb.PROTOCOL_WAIT_QA:
			_reject("HBOS Stability Protocol", protocol_name,
					"仅「待QA审核」状态可批准（当前：{}）。".format(doc.status),
					"非法状态：非待QA审核调用 approve_protocol")
		_guard_sod(doc, "HBOS Stability Protocol", doc.drafted_by, "QA 批准人")
		if doc.qa_review_by:
			_guard_sod(doc, "HBOS Stability Protocol", doc.qa_review_by, "QA 批准人")
		if not doc.vd_months_snapshot:
			notice = frappe.get_doc("HBOS Stability Notice", doc.notice)
			doc.vd_months_snapshot = _product_of_notice(notice).vd_months
		if doc.spec_ref and not doc.spec_version:
			frappe.throw("已填写质量标准时，必须同时写入标准版本快照（spec_version）。")
		_set_status(doc, stb.FLOW_STB_PROTOCOL, stb.PROTOCOL_APPROVED)
		doc.qa_approve_by = _user()
		doc.approve_date = _today()
		doc.effective_date = effective_date or _today()
		doc.snapshot_frozen = 1
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Protocol", "方案批准", doc.name,
				  action_text="方案批准并冻结快照",
				  new_value="status={} effective_date={}".format(doc.status, doc.effective_date))
		_commit()
		return {"name": doc.name, "status": doc.status, "effective_date": doc.effective_date}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def review_protocol(protocol_name):
	"""QA 审核记录（准入动作，状态不变）：填 `qa_review_by`/`qa_review_date`。

	方案 5.2.2 定义审核与批准两个签署位，6.4 要求「QA 审核人 ≠ QA 批准人」，
	approve_protocol 在审核人已填时做 SoD 校验。
	"""
	_check_action("review_protocol", "HBOS Stability Protocol", protocol_name)
	try:
		doc = _load("HBOS Stability Protocol", protocol_name)
		if doc.status != stb.PROTOCOL_WAIT_QA:
			_reject("HBOS Stability Protocol", protocol_name,
					"仅「待QA审核」状态可记录审核（当前：{}）。".format(doc.status),
					"非法状态：非待QA审核调用 review_protocol")
		doc.qa_review_by = _user()
		doc.qa_review_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Protocol", "复核", doc.name,
				  action_text="QA 审核记录", new_value=doc.qa_review_by)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def reject_protocol(protocol_name, reason):
	"""驳回方案：待QA审核 → 已驳回（终态）。"""
	_check_action("reject_protocol", "HBOS Stability Protocol", protocol_name)
	if not (reason or "").strip():
		frappe.throw("驳回原因必填。")
	try:
		doc = _load("HBOS Stability Protocol", protocol_name)
		if doc.status != stb.PROTOCOL_WAIT_QA:
			_reject("HBOS Stability Protocol", protocol_name,
					"仅「待QA审核」状态可驳回（当前：{}）。".format(doc.status),
					"非法状态：非待QA审核调用 reject_protocol")
		_set_status(doc, stb.FLOW_STB_PROTOCOL, stb.PROTOCOL_REJECTED)
		doc.reject_reason = reason
		doc.reject_by = _user()
		doc.reject_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Protocol", "驳回", doc.name,
				  action_text="方案驳回", reason=reason, new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def void_protocol(protocol_name, reason):
	"""作废方案：草稿 / 已批准 → 已作废（QP / Manager，原因必填）。"""
	_check_action("void_protocol", "HBOS Stability Protocol", protocol_name)
	if not (reason or "").strip():
		frappe.throw("作废原因必填。")
	try:
		doc = _load("HBOS Stability Protocol", protocol_name)
		if doc.status not in (stb.PROTOCOL_DRAFT, stb.PROTOCOL_APPROVED):
			_reject("HBOS Stability Protocol", protocol_name,
					"仅「草稿 / 已批准」状态可作废（当前：{}）。".format(doc.status),
					"非法状态：调用 void_protocol")
		_set_status(doc, stb.FLOW_STB_PROTOCOL, stb.PROTOCOL_VOIDED)
		doc.void_reason = reason
		doc.void_by = _user()
		doc.void_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Stability Protocol", "方案作废", doc.name,
				  action_text="方案作废", reason=reason, new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


# ---------------------------------------------------------------------------
# SoD 硬校验（方案 6.4）
# ---------------------------------------------------------------------------

def _guard_sod(doc, doctype, prev_signer, role_label):
	"""SoD：申请人/起草人不得自批；同一用户不得在同一单据连续两级签署。"""
	me = _user()
	if prev_signer and prev_signer == me:
		_audit_commit(doctype, "SoD 拦截", doc.name,
					  action_text="{} 违反职责分离".format(role_label),
					  reason="上一签署人同为 {}".format(prev_signer))
		frappe.throw("{}不得由上一签署人兼任（SoD，方案 6.4）。".format(role_label))


# ---------------------------------------------------------------------------
# 只读聚合（工作台 / 通知单台账；R8A 范围）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_stability_dashboard():
	"""稳定性工作台 KPI（R8A 可计算部分）。

	R8B~R8D 的时间点/结果/报告类 KPI 待对应子轮落地后并入，此处不返回占位值，
	前端对缺失项显示「待 R8B/C 落地」而不是伪造数字。
	"""
	_check_action("get_stability_dashboard", "HBOS Stability Notice", "-")
	notice_pending = frappe.db.count("HBOS Stability Notice", {
		"status": ["in", [stb.NOTICE_WAIT_QC, stb.NOTICE_WAIT_APPROVE]]})
	notice_approved = frappe.db.count("HBOS Stability Notice", {"status": stb.NOTICE_APPROVED})
	protocol_pending = frappe.db.count("HBOS Stability Protocol", {"status": stb.PROTOCOL_WAIT_QA})
	protocol_approved = frappe.db.count("HBOS Stability Protocol", {"status": stb.PROTOCOL_APPROVED})
	return {
		"notice_pending": notice_pending,
		"notice_approved": notice_approved,
		"protocol_pending": protocol_pending,
		"protocol_approved": protocol_approved,
		"product_count": frappe.db.count("HBOS Stability Product", {"is_active": 1}),
		"master": {
			"condition": frappe.db.count("HBOS Stability Condition", {"is_active": 1}),
			"room": frappe.db.count("HBOS Stability Room", {"is_active": 1}),
			"test_item": frappe.db.count("HBOS Stability Test Item", {"is_active": 1}),
		},
		"scope": "R8A：主数据 + 通知单 + 方案（时间点/结果/报告类 KPI 待 R8B~R8D）",
	}


@frappe.whitelist()
def get_stability_notices(keyword=None, status=None, limit=50, offset=0):
	"""考察通知单台账（列表 + 详情摘要），供前端「考察申请与方案」视图。"""
	_check_action("get_stability_notices", "HBOS Stability Notice", "-")
	filters = {}
	if status:
		filters["status"] = status
	or_filters = None
	if keyword:
		or_filters = [
			["name", "like", "%{}%".format(keyword)],
			["stability_product", "like", "%{}%".format(keyword)],
		]
	rows = frappe.get_all(
		"HBOS Stability Notice",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "stability_product", "status", "version", "conditions_count",
				"qa_applicant", "apply_date", "approver_by", "approve_date",
				"reject_reason", "creation"],
		order_by="creation desc",
		limit_page_length=int(limit),
		limit_start=int(offset),
	)
	for r in rows:
		product = frappe.db.get_value(
			"HBOS Stability Product", r.stability_product,
			["product_name", "category", "dosage_form"], as_dict=True) or {}
		r["product_name"] = product.get("product_name")
		r["category"] = product.get("category")
		r["dosage_form"] = product.get("dosage_form")
	return {"rows": rows}


# ---------------------------------------------------------------------------
# 主数据与方案的只读接口（前端「考察申请与方案」建档与各 tab 的数据源）
# ---------------------------------------------------------------------------

# 主数据只读白名单：DocType -> (返回字段, 关键字可搜索字段)
# 用白名单而非直接透传 doctype，避免本方法被当成任意 DocType 的读取入口。
STABILITY_MASTER_QUERY = {
	"HBOS Stability Condition": (
		["name", "condition_code", "description", "condition_type", "temp_min", "temp_max",
		 "humidity_min", "humidity_max", "climate_zone", "is_active"],
		["condition_code", "description"],
	),
	"HBOS Stability Room": (
		["name", "room_code", "room_name", "location", "temp_min", "temp_max",
		 "humidity_min", "humidity_max", "is_locked_managed", "is_active"],
		["room_code", "room_name"],
	),
	"HBOS Stability Test Item": (
		["name", "item_code", "item_name", "item_category", "result_type", "is_full_test_only",
		 "is_key_item", "significant_change_rule", "change_threshold", "is_active"],
		["item_code", "item_name"],
	),
}


@frappe.whitelist()
def get_stability_master(doctype, keyword=None, include_inactive=0):
	"""主数据只读列表（储存条件 / 稳定性室 / 检验项目）。doctype 走白名单校验。"""
	_check_action("get_stability_master", "HBOS Stability Product", "-")
	conf = STABILITY_MASTER_QUERY.get(doctype)
	if not conf:
		_reject("HBOS Stability Product", "-",
				"不支持的主数据类型：{}".format(doctype), "非法主数据类型请求")
	fields, searchable = conf
	filters = {}
	if not _truthy(include_inactive):
		filters["is_active"] = 1
	or_filters = None
	kw = (keyword or "").strip()
	if kw:
		or_filters = [[f, "like", "%{}%".format(kw)] for f in searchable]
	return {"rows": frappe.get_all(
		doctype, filters=filters, or_filters=or_filters, fields=fields,
		order_by="name asc", limit_page_length=0)}


@frappe.whitelist()
def get_stability_products(keyword=None, include_inactive=0):
	"""稳定性产品主数据只读列表（建档选产品 + 「产品规则」tab）。"""
	_check_action("get_stability_products", "HBOS Stability Product", "-")
	filters = {}
	if not _truthy(include_inactive):
		filters["is_active"] = 1
	or_filters = None
	kw = (keyword or "").strip()
	if kw:
		or_filters = [["product_code", "like", "%{}%".format(kw)],
					  ["product_name", "like", "%{}%".format(kw)]]
	return {"rows": frappe.get_all(
		"HBOS Stability Product", filters=filters, or_filters=or_filters,
		fields=["name", "product_code", "product_name", "category", "dosage_form",
				"default_uom", "vd_months", "qty_factor", "pack_desc", "is_outsource",
				"need_inverted", "is_active", "storage_cond_long", "storage_cond_acc",
				"storage_cond_inter"],
		order_by="product_code asc", limit_page_length=0)}


@frappe.whitelist()
def get_stability_protocols(notice=None, status=None, keyword=None, limit=50, offset=0):
	"""稳定性方案台账（「稳定性方案」tab）。"""
	_check_action("get_stability_protocols", "HBOS Stability Protocol", "-")
	filters = {}
	if notice:
		filters["notice"] = notice
	if status:
		filters["status"] = status
	or_filters = None
	kw = (keyword or "").strip()
	if kw:
		or_filters = [["name", "like", "%{}%".format(kw)],
					  ["notice", "like", "%{}%".format(kw)]]
	rows = frappe.get_all(
		"HBOS Stability Protocol", filters=filters, or_filters=or_filters,
		fields=["name", "notice", "status", "version", "effective_date", "drafted_by",
				"draft_date", "qa_review_by", "qa_approve_by", "approve_date",
				"reject_reason", "void_reason", "creation"],
		order_by="creation desc",
		limit_page_length=int(limit), limit_start=int(offset))
	_enrich_protocol_products(rows)
	return {"rows": rows}


def _enrich_protocol_products(rows):
	"""批量补产品编码/名称（notice → stability_product），避免逐行 N+1。"""
	notice_names = sorted({r["notice"] for r in rows if r.get("notice")})
	if not notice_names:
		return
	notice_product = dict(frappe.get_all(
		"HBOS Stability Notice", filters={"name": ["in", notice_names]},
		fields=["name", "stability_product"], as_list=True))
	product_codes = sorted({p for p in notice_product.values() if p})
	product_names = {}
	if product_codes:
		product_names = dict(frappe.get_all(
			"HBOS Stability Product", filters={"name": ["in", product_codes]},
			fields=["name", "product_name"], as_list=True))
	for row in rows:
		code = notice_product.get(row.get("notice"))
		row["stability_product"] = code
		row["product_name"] = product_names.get(code)


@frappe.whitelist()
def get_stability_protocol_detail(protocol_name):
	"""方案详情（批次 / 条件 / 项目子表 + 冻结快照 + 签署链），供详情与起草抽屉。"""
	_check_action("get_stability_protocols", "HBOS Stability Protocol", protocol_name)
	doc = frappe.get_doc("HBOS Stability Protocol", protocol_name)
	notice = frappe.get_doc("HBOS Stability Notice", doc.notice)
	product = _product_of_notice(notice)
	return {
		"name": doc.name,
		"notice": doc.notice,
		"notice_status": notice.status,
		"stability_product": product.name,
		"product_code": product.product_code,
		"product_name": product.product_name,
		"category": product.category,
		"status": doc.status,
		"version": doc.version,
		"purpose": doc.purpose,
		"scope": doc.scope,
		"batches": [{
			"batch_no": r.batch_no, "batch_size": r.batch_size,
			"manufacture_date": r.manufacture_date, "finish_date": r.finish_date,
			"is_inverted": r.is_inverted, "remark": r.remark,
		} for r in (doc.batches or [])],
		"study_conditions": [{
			"condition_type": r.condition_type, "storage_cond": r.storage_cond,
			"exposure_days": r.exposure_days, "is_required": r.is_required,
			"remark": r.remark,
		} for r in (doc.study_conditions or [])],
		"items": [{
			"stability_test_item": r.stability_test_item, "is_full_test": r.is_full_test,
			"is_key_item": r.is_key_item, "test_method": r.test_method,
			"method_version": r.method_version,
		} for r in (doc.items or [])],
		"qty": doc.qty,
		"qty_uom": doc.qty_uom,
		"pack_desc": doc.pack_desc,
		"room_temp_recovery_days": doc.room_temp_recovery_days,
		"snapshot": {
			"spec_ref": doc.spec_ref,
			"spec_version": doc.spec_version,
			"test_method_ref": doc.test_method_ref,
			"method_version": doc.method_version,
			"vd_months_snapshot": doc.vd_months_snapshot,
			"frozen": bool(doc.snapshot_frozen),
		},
		"signoff": {
			"drafted_by": doc.drafted_by, "draft_date": doc.draft_date,
			"qa_review_by": doc.qa_review_by, "qa_review_date": doc.qa_review_date,
			"qa_approve_by": doc.qa_approve_by, "approve_date": doc.approve_date,
			"effective_date": doc.effective_date,
			"reject_reason": doc.reject_reason, "reject_by": doc.reject_by,
			"reject_date": doc.reject_date,
			"void_reason": doc.void_reason, "void_by": doc.void_by,
			"void_date": doc.void_date,
		},
	}


# 稳定性板块纳入审计摘要的 DocType（R8A 已交付范围；R8B~R8D 落地后追加）
STABILITY_AUDIT_DOCTYPES = [
	"HBOS Stability Product", "HBOS Stability Condition", "HBOS Stability Room",
	"HBOS Stability Test Item", "HBOS Stability Notice", "HBOS Stability Protocol",
]


@frappe.whitelist()
def get_stability_audit(doc_name=None, limit=20):
	"""稳定性板块的合规审计摘要（只读），供详情抽屉的「审计」页签。

	按 `doctype_target` 限定在稳定性 DocType 内（既有 `get_audit_log` 只支持单值精确匹配，
	无法做板块前缀筛选，故在此做稳定性作用域的只读投影，不改 R6D 既有方法）。
	"""
	_check_action("get_stability_audit", "HBOS Stability Notice", doc_name or "-")
	filters = {"doctype_target": ["in", STABILITY_AUDIT_DOCTYPES]}
	if doc_name:
		filters["doc_name"] = doc_name
	rows = frappe.get_all(
		"HBOS Audit Log", filters=filters,
		fields=["name", "log_type", "doctype_target", "doc_name", "action_text",
				"old_value", "new_value", "reason", "user", "created_at"],
		order_by="created_at desc", limit_page_length=int(limit))
	return {"events": rows, "total": frappe.db.count("HBOS Audit Log", filters)}


@frappe.whitelist()
def get_stability_notice_detail(notice_name):
	"""通知单详情（含条件、批次与冻结摘要），供详情面板与抽屉。"""
	_check_action("get_stability_notices", "HBOS Stability Notice", notice_name)
	doc = frappe.get_doc("HBOS Stability Notice", notice_name)
	product = _product_of_notice(doc)
	protocols = frappe.get_all(
		"HBOS Stability Protocol",
		filters={"notice": notice_name},
		fields=["name", "status", "version", "effective_date"],
		order_by="creation desc",
	)
	return {
		"name": doc.name,
		"status": doc.status,
		"version": doc.version,
		"stability_product": doc.stability_product,
		"product_name": product.product_name,
		"category": product.category,
		"dosage_form": product.dosage_form,
		"study_reason": doc.study_reason,
		"conditions_count": doc.conditions_count,
		"extra_condition_reason": doc.extra_condition_reason,
		"register_review_by": doc.register_review_by,
		"register_review_date": doc.register_review_date,
		"study_conditions": [{
			"condition_type": r.condition_type,
			"storage_cond": r.storage_cond,
			"exposure_days": r.exposure_days,
			"is_required": r.is_required,
			"remark": r.remark,
		} for r in (doc.study_conditions or [])],
		"batches": [{
			"batch_no": r.batch_no,
			"batch_size": r.batch_size,
			"manufacture_date": r.manufacture_date,
			"is_inverted": r.is_inverted,
			"remark": r.remark,
		} for r in (doc.batches or [])],
		"qty": doc.qty,
		"qty_uom": doc.qty_uom,
		"pack_desc": doc.pack_desc,
		"test_cycle": doc.test_cycle,
		"test_method": doc.test_method,
		"snapshot": {
			"spec_ref": doc.spec_ref,
			"spec_version": doc.spec_version,
			"method_version": doc.method_version,
			"limits_snapshot": doc.limits_snapshot,
			"vd_months_snapshot": doc.vd_months_snapshot,
			"frozen": bool(doc.snapshot_frozen),
		},
		"signoff": {
			"qa_applicant": doc.qa_applicant, "apply_date": doc.apply_date,
			"qc_manager_confirm_by": doc.qc_manager_confirm_by,
			"qc_manager_confirm_date": doc.qc_manager_confirm_date,
			"approver_by": doc.approver_by, "approve_date": doc.approve_date,
			"reject_reason": doc.reject_reason, "reject_by": doc.reject_by,
			"reject_date": doc.reject_date,
		},
		"protocols": protocols,
	}
