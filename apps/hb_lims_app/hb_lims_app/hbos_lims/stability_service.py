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

from hb_lims_app.hbos_lims import result_contract as rc
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
	try:
		from hb_lims_app.hbos_lims.todo_service import invalidate_my_todo_summary_cache
		invalidate_my_todo_summary_cache()
	except Exception as exc:
		if hasattr(frappe, "log_error"):
			frappe.log_error(str(exc), "HBOS 我的待办摘要缓存失效失败")


def _truthy(value):
	"""whitelist 参数经 POST 过来可能是字符串（"1" / "0" / "true"），统一判定。"""
	if value is None:
		return False
	if isinstance(value, str):
		return value.strip().lower() in ("1", "true", "yes", "on")
	return bool(value)


def _rollback():
	frappe.db.rollback()


def _check_action(action, doctype_target, doc_name="", system=False):
	"""角色校验。失败时先独立提交「越权拦截」审计再抛错（方案 8.7 / 门禁 17）。

	审计写入本身失败不得掩盖权限拒绝——包一层 try 并落错误日志。
	`system=True` 用于系统触发动作（complete_testing / reopen_timepoint / mark_superseded）：
	**角色豁免、动作名不豁免**（门禁 10 / 20）——动作名仍须登记在 ACTION_ROLES，
	但由服务内部调用，不做调用者角色判定。
	"""
	if system:
		return
	roles = frappe.get_roles(_user())
	# scope=doctype_target：同名动作（R3 检验流程 vs 稳定性结果）按 DocType 分别授权
	if not any(wf.action_allowed(action, role, scope=doctype_target) for role in roles):
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
		doc.flags.allow_system_fields = True
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
		doc.flags.allow_system_fields = True
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
	"""稳定性工作台 KPI（R8A~R8D 全量：主数据 + 通知单 + 方案 + 样品/时间点/结果）。

	R8B~R8D 落地后，样品 / 时间点 / 结果三类计数与时间点执行结构已并入本接口
	（此前前端以「待 R8B~R8D」占位）。
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
		"sample_count": frappe.db.count("HBOS Stability Sample"),
		"timepoint_count": frappe.db.count("HBOS Stability Timepoint"),
		"result_count": frappe.db.count("HBOS Stability Result"),
		"timepoint_by_status": {
			"wait_sample": frappe.db.count("HBOS Stability Timepoint", {"status": stb.TP_WAIT_SAMPLE}),
			"wait_test": frappe.db.count("HBOS Stability Timepoint", {"status": stb.TP_WAIT_TEST}),
			"testing": frappe.db.count("HBOS Stability Timepoint", {"status": stb.TP_TESTING}),
			"done": frappe.db.count("HBOS Stability Timepoint", {"status": stb.TP_DONE}),
			"cancelled": frappe.db.count("HBOS Stability Timepoint", {"status": stb.TP_CANCELLED}),
		},
		"master": {
			"condition": frappe.db.count("HBOS Stability Condition", {"is_active": 1}),
			"room": frappe.db.count("HBOS Stability Room", {"is_active": 1}),
			"test_item": frappe.db.count("HBOS Stability Test Item", {"is_active": 1}),
		},
		"scope": "R8A~R8D：主数据 + 通知单 + 方案 + 样品/时间点/结果",
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
		["name", "item_code", "item_name", "base_test_item", "item_category", "result_type",
		 "is_full_test_only", "is_key_item", "significant_change_rule", "change_threshold", "is_active"],
		["item_code", "item_name"],
	),
	"HBOS Test Item": (
		["name", "item_code", "item_name", "item_category", "test_unit", "limits_type"],
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
	if not _truthy(include_inactive) and "is_active" in fields:
		filters["is_active"] = 1
	or_filters = None
	kw = (keyword or "").strip()
	if kw:
		or_filters = [[f, "like", "%{}%".format(kw)] for f in searchable]
	return {"rows": frappe.get_all(
		doctype, filters=filters, or_filters=or_filters, fields=fields,
		order_by="name asc", limit_page_length=0)}


@frappe.whitelist()
def update_stability_test_item_mapping(stability_test_item, base_test_item=None):
	"""LIMS Manager 维护稳定性项目与业务检验项目的一对一映射。"""
	_check_action("manage_stability_master", "HBOS Stability Test Item", stability_test_item)
	try:
		base_test_item = base_test_item or None
		if base_test_item:
			if not frappe.db.exists("HBOS Test Item", base_test_item):
				frappe.throw("业务检验项目「{}」不存在。".format(base_test_item))
			frappe.db.get_value("HBOS Test Item", base_test_item, "name", for_update=True)
		item = _lock_row("HBOS Stability Test Item", stability_test_item)
		if not item.is_active:
			frappe.throw("稳定性检验项目「{}」已停用，不能维护映射。".format(stability_test_item))
		if frappe.db.exists(RESULT_DOCTYPE, {"stability_test_item": stability_test_item}):
			frappe.throw("稳定性检验项目「{}」已有结果，禁止修改映射。".format(stability_test_item))

		if base_test_item:
			conflict = frappe.db.get_value(
				"HBOS Stability Test Item",
				{"base_test_item": base_test_item, "name": ["!=", stability_test_item]},
				"name")
			if conflict:
				frappe.throw("业务检验项目「{}」已映射到稳定性项目「{}」。"
						 .format(base_test_item, conflict))

		old_value = item.base_test_item or ""
		item.base_test_item = base_test_item
		item.save(ignore_permissions=True)
		_audit_on("HBOS Stability Test Item", "修改", item.name,
				  action_text="维护业务检验项目映射",
				  old_value=old_value, new_value=base_test_item or "未配置")
		_commit()
		return {"name": item.name, "base_test_item": item.base_test_item}
	except Exception:
		_rollback()
		raise


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


# ===========================================================================
# M2-R8B：样品与时间点（方案 5.3 / 6.3.3 / 6.3.4 / 7.1 / 7.2 / 7.3 / 7.8）
# ===========================================================================

SAMPLE_DOCTYPE = "HBOS Stability Sample"
TIMEPOINT_DOCTYPE = "HBOS Stability Timepoint"

# 日期工具在契约层（纯函数，可离线单测）；此处给短别名便于阅读
_add_days = stb._add_days


# ---- 通用工具 -------------------------------------------------------------

def _lock_row(doctype, name):
	"""四步锁协议第 2 步：`SELECT ... FOR UPDATE` 锁行（方案 7.8）。

	调用方须遵守**固定锁顺序 Sample → Timepoint**（同事务需要两把锁时）。
	"""
	if not frappe.db.exists(doctype, name):
		frappe.throw("{}「{}」不存在。".format(doctype, name))
	frappe.db.get_value(doctype, name, "name", for_update=True)
	return _load(doctype, name)


def _has_result_doctype():
	return bool(frappe.db.exists("DocType", "HBOS Stability Result"))


def _result_fields():
	if not _has_result_doctype():
		return set()
	return {f.fieldname for f in frappe.get_meta("HBOS Stability Result").fields}


def _approved_item_codes(timepoint_name):
	"""该时间点「已批准且生效」的结果所覆盖的检验项目集合。

	`HBOS Stability Result` 属 R8C。未落地（或缺所需字段）时返回空集合——语义上即
	「没有任何必检项目有已批准结果」，故 `complete_testing` 会被前置校验拒绝；
	这是**正确判定而非桩**，R8C 落地后本函数自动生效。
	"""
	need = {"timepoint", "stability_test_item", "status", "is_current"}
	if not need <= _result_fields():
		return set()
	return set(frappe.get_all(
		"HBOS Stability Result",
		filters={"timepoint": timepoint_name, "status": "已批准", "is_current": 1},
		pluck="stability_test_item"))


def _has_inflight_result(timepoint_name):
	"""该时间点是否有在途（草稿/已提交/已复核）结果（方案 6.3.4 取消前置）。"""
	if "timepoint" not in _result_fields():
		return False
	return bool(frappe.db.exists("HBOS Stability Result", {
		"timepoint": timepoint_name, "status": ["in", ["草稿", "已提交", "已复核"]]}))


def _has_approved_result(timepoint_name):
	"""该时间点是否有已批准结果（取消前置：有则须先全部作废）。"""
	if "timepoint" not in _result_fields():
		return False
	return bool(frappe.db.exists("HBOS Stability Result", {
		"timepoint": timepoint_name, "status": "已批准"}))


def _delay_dicts(tp):
	return [{"delay_type": d.delay_type, "status": d.status,
			 "approve_at": d.approve_at, "approved_due_date": d.approved_due_date}
			for d in (tp.delays or [])]


def _policy_latest_sample(tp):
	return _add_days(tp.plan_sample_date, stb.delay_limit_days(tp.time_point_value, tp.time_point_unit))


def _effective_sample_due(tp):
	policy = _policy_latest_sample(tp)
	return stb.effective_due_date(_delay_dicts(tp), "取样延期", policy), policy


def _validate_actual_sample_date(tp, actual_sample_date=None):
	"""统一校验实际取样日期：延期须批准，且不得超过政策硬上限。"""
	actual = stb._as_date(actual_sample_date) or _today()
	if not actual:
		frappe.throw("实际取样日期必填。")
	effective, policy = _effective_sample_due(tp)
	ok, err = stb.check_sampling_not_late(actual, effective, policy)
	if not ok:
		frappe.throw(err)

	planned = stb._as_date(tp.plan_sample_date)
	if planned and actual > planned:
		approved = [d for d in (tp.delays or [])
					if d.delay_type == "取样延期" and d.status == stb.DELAY_APPROVED]
		if not any(stb._as_date(d.approved_due_date) and
				   stb._as_date(d.approved_due_date) >= actual for d in approved):
			frappe.throw(
				"实际取样日期（{}）晚于计划日期（{}），必须先提交并批准取样延期。".format(
					actual, planned))
	return actual


def _product_of_sample(sample):
	if not sample.stability_product:
		return None
	return frappe.get_doc("HBOS Stability Product", sample.stability_product)


def _policy_latest_test(plan_test_date, is_outsource=None, outsourced_window=None):
	"""检测侧政策硬上限：`plan_test_date + 30 天`；委外产品按 `outsourced_test_window_days`（留空=不限制）。"""
	window = outsourced_window if is_outsource else None
	if is_outsource and (window is None or window == ""):
		return None      # 委外且窗口留空 = 不限制（Owner 2026-09-16 决定）
	if window is None:
		window = stb.TEST_WINDOW_DAYS
	return _add_days(plan_test_date, int(window))


def _effective_test_due(tp, product=None):
	policy = _policy_latest_test(
		tp.plan_test_date,
		product.is_outsource if product is not None else None,
		product.outsourced_test_window_days if product is not None else None)
	return stb.effective_due_date(_delay_dicts(tp), "检测延期", policy), policy


def _append_sample_log(sample, transaction_type, qty_delta=0, remaining_qty=0,
					   source_timepoint=None, sampling_reason=None, remarks="",
					   reviewer=None, transaction_date=None,
					   sample_no_out=None, return_sample_no=None, remaining_sample_no=None):
	sample.append("logs", {
		"transaction_date": transaction_date or _today(),
		"transaction_type": transaction_type,
		"source_timepoint": source_timepoint,
		"sampling_reason": sampling_reason,
		"sample_no_out": sample_no_out,
		"return_sample_no": return_sample_no,
		"remaining_sample_no": remaining_sample_no,
		"qty_delta": qty_delta,
		"qty_uom": sample.qty_uom,
		"remaining_qty": remaining_qty,
		"operator": _user(),
		"reviewer": reviewer,
		"remarks": remarks,
	})


def _set_sample_status(sample, target):
	if not wf.can_transition(stb.FLOW_STB_SAMPLE, sample.status, target):
		_reject(SAMPLE_DOCTYPE, sample.name,
				"非法状态流转：{} -> {}（样品）".format(sample.status, target),
				"非法状态转移：{} -> {}".format(sample.status, target))
	sample.status = target


def _inbox_status(current_qty, init_qty):
	"""按结存判定在箱/部分取样/已取尽（方案 6.1 三态）。"""
	if float(current_qty or 0) <= 0:
		return stb.SAMPLE_DEPLETED
	if float(current_qty) < float(init_qty or 0):
		return stb.SAMPLE_PARTIAL
	return stb.SAMPLE_IN_STORAGE


# ---- 样品：登记与复核 -----------------------------------------------------

@frappe.whitelist()
def register_stability_sample(notice, stability_product, batch_no, in_date,
							  protocol=None, sample_name=None, material_code=None,
							  batch_size=None, manufacture_date=None, finish_date=None,
							  send_date=None, full_test_sample_date=None,
							  storage_cond=None, room=None, storage_location=None,
							  pack_desc=None, is_sterile_pack=0, package_count=None,
							  package_spec=None, inverted_flag=None,
							  init_qty=None, qty_uom=None, source_sample=None,
							  label_no=None, evaluation_conclusion=None,
							  evaluated_by=None, evaluation_date=None):
	"""样品入箱登记（记录二）：→ 在箱；登记成功后触发时间点生成（方案 6.3.3 / 7.1）。"""
	_check_action("register_stability_sample", SAMPLE_DOCTYPE, batch_no)
	try:
		product = frappe.get_doc("HBOS Stability Product", stability_product)
		if not product.is_active:
			frappe.throw("该稳定性产品已停用，不再登记样品。")

		notice_doc = frappe.get_doc("HBOS Stability Notice", notice)
		if notice_doc.stability_product != stability_product:
			frappe.throw("通知单关联产品与入参稳定性产品不一致，禁止错配样品。")
		yearly = stb.check_year_long_study_no_protocol(product.category)
		if yearly and protocol:
			frappe.throw("年度持续稳定性考察类不建方案单，样品只挂通知单（方案 4.2.5）。")
		if not yearly:
			if not protocol:
				frappe.throw("非年度持续稳定性考察类必须关联已批准的稳定性方案。")
			protocol_doc = frappe.get_doc("HBOS Stability Protocol", protocol)
			if protocol_doc.notice != notice:
				frappe.throw("稳定性方案未关联该通知单，禁止错配样品。")
			protocol_product = frappe.db.get_value(
				"HBOS Stability Notice", protocol_doc.notice, "stability_product")
			if protocol_product != stability_product:
				frappe.throw("稳定性方案对应产品与入参稳定性产品不一致，禁止错配样品。")
			if protocol_doc.status != stb.PROTOCOL_APPROVED:
				frappe.throw("关联方案须为「已批准」方可登记样品（当前：{}）。".format(protocol_doc.status))
		if notice_doc.status != stb.NOTICE_APPROVED:
			frappe.throw("关联通知单须为「已批准」方可登记样品（当前：{}）。".format(notice_doc.status))

		in_d = stb._as_date(in_date)
		if not in_d:
			frappe.throw("进箱日期必填。")
		# 送样 ≤ 全检样 + 3 周（方案 4.1 / 6.3.3）
		if send_date and full_test_sample_date:
			limit = _add_days(full_test_sample_date, 21)
			if stb._as_date(send_date) > limit:
				frappe.throw("送样日期（{}）距全检样送样日期超过 3 周（上限 {}）。".format(
					send_date, limit))

		# 进箱超生产 1 个月 → 强制评估四件套（不拦截，方案 P1-2）
		need_eval = 0
		if manufacture_date and in_d > _add_months(manufacture_date, 1):
			need_eval = 1
			if not (evaluation_conclusion or "").strip() or not evaluated_by or not evaluation_date:
				frappe.throw("进箱日期超过生产日期 1 个月：必须填写评估结论、评估人与评估日期（方案 5.3.1）。")

		cond_snapshot = None
		if storage_cond:
			cond_snapshot = frappe.db.get_value("HBOS Stability Condition", storage_cond, "description")

		doc = frappe.get_doc({
			"doctype": SAMPLE_DOCTYPE,
			"notice": notice,
			"protocol": protocol,
			"stability_product": stability_product,
			"sample_name": sample_name,
			"material_code": material_code,
			"batch_no": batch_no,
			"batch_size": batch_size,
			"manufacture_date": manufacture_date,
			"finish_date": finish_date,
			"send_date": send_date,
			"full_test_sample_date": full_test_sample_date,
			"storage_cond": storage_cond,
			"condition_snapshot": cond_snapshot,
			"room": room,
			"storage_location": storage_location,
			"pack_desc": pack_desc or product.pack_desc,
			"is_sterile_pack": 1 if is_sterile_pack else 0,
			"package_count": package_count,
			"package_spec": package_spec,
			"inverted_flag": inverted_flag,
			"init_qty": init_qty,
			"current_qty": init_qty,
			"qty_uom": qty_uom,
			"source_sample": source_sample,
			"label_no": label_no,
			"in_date": in_date,
			"start_date": in_date,
			"need_evaluation": need_eval,
			"evaluation_conclusion": evaluation_conclusion,
			"evaluated_by": evaluated_by,
			"evaluation_date": evaluation_date,
			"stored_by": _user(),
			"status": stb.SAMPLE_IN_STORAGE,
		})
		doc.flags.allow_system_fields = True
		_append_sample_log(doc, "入库", qty_delta=init_qty or 0,
						   remaining_qty=init_qty or 0, transaction_date=in_date,
						   remarks="入箱登记")
		doc.insert(ignore_permissions=True)
		_audit_on(SAMPLE_DOCTYPE, "入箱登记", doc.name,
				  action_text="稳定性样品入箱登记",
				  new_value="batch={} qty={}".format(batch_no, init_qty))
		if need_eval:
			_audit_on(SAMPLE_DOCTYPE, "超期进箱评估", doc.name,
					  action_text="进箱超生产 1 个月，已强制评估",
					  new_value=evaluation_conclusion or "")
		_commit()
	except Exception:
		_rollback()
		raise

	# 登记先提交（进箱是物理事实）；生成失败不回滚登记（方案 7.1 失败语义）
	try:
		generate_timepoints(doc.name)
	except Exception as exc:
		frappe.db.rollback()
		_audit_commit(SAMPLE_DOCTYPE, "时间点生成失败", doc.name,
					  action_text="入箱后自动生成时间点失败", reason=str(exc)[:200])
		frappe.db.set_value(SAMPLE_DOCTYPE, doc.name, "timepoint_gen_error",
							str(exc)[:500], update_modified=False)
		frappe.db.commit()
	return {"name": doc.name, "status": frappe.db.get_value(SAMPLE_DOCTYPE, doc.name, "status")}


def _add_months(date_value, months):
	d = stb._as_date(date_value)
	if not d:
		return None
	return stb.add_time_point(d, months, "月")


@frappe.whitelist()
def review_sample_storage(sample_name):
	"""储存复核（状态不变，方案 6.3.3）。"""
	_check_action("review_sample_storage", SAMPLE_DOCTYPE, sample_name)
	try:
		doc = _lock_row(SAMPLE_DOCTYPE, sample_name)
		doc.reviewed_by = _user()
		doc.reviewed_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on(SAMPLE_DOCTYPE, "储存复核", doc.name, action_text="储存复核")
		_commit()
		return {"name": doc.name}
	except Exception:
		_rollback()
		raise


# ---- 样品：取样 / 返还 ----------------------------------------------------

@frappe.whitelist()
def record_sampling(sample_name, timepoint=None, qty=None, sampling_reason=None,
					sample_date=None, sample_no_out=None, remarks=""):
	"""取样出库：在箱/部分取样 → 在箱/部分取样/已取尽；扣减结存并写流水（方案 6.3.3 / 7.3）。"""
	_check_action("record_sampling", SAMPLE_DOCTYPE, sample_name)
	if qty is None or float(qty) <= 0:
		frappe.throw("取样数量必须大于 0。")
	try:
		sample = _lock_row(SAMPLE_DOCTYPE, sample_name)
		actual = stb._as_date(sample_date) or _today()

		tp = None
		if timepoint:
			tp = _load(TIMEPOINT_DOCTYPE, timepoint)   # 锁顺序：Sample 已锁，再取 Timepoint
			if tp.stability_sample != sample.name:
				frappe.throw("时间点「{}」不属于样品「{}」。".format(timepoint, sample.name))
			actual = _validate_actual_sample_date(tp, actual)

		new_qty = float(sample.current_qty or 0) - float(qty)
		if new_qty < 0:
			frappe.throw("取样后结存为负（当前结存 {}，取样 {}）。".format(sample.current_qty, qty))

		sample.current_qty = new_qty
		_set_sample_status(sample, _inbox_status(new_qty, sample.init_qty))
		_append_sample_log(sample, "取样出库", qty_delta=-float(qty), remaining_qty=new_qty,
						   source_timepoint=timepoint, sampling_reason=sampling_reason,
						   remarks=remarks, sample_no_out=sample_no_out,
						   transaction_date=actual)
		sample.save(ignore_permissions=True)

		if tp:
			tp.flags.allow_system_fields = True
			tp.sample_by = _user()
			tp.save(ignore_permissions=True)
		_audit_on(SAMPLE_DOCTYPE, "取样出库", sample.name,
				  action_text="取样出库", new_value="qty=-{} remaining={}".format(qty, new_qty))
		_commit()
		return {"name": sample.name, "status": sample.status, "current_qty": new_qty}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def return_sample(sample_name, qty=None, timepoint=None, return_sample_no=None,
				  remarks="", reviewer=None):
	"""取样返还：自环（在箱→在箱 / 部分取样→部分取样），回补结存（方案 6.3.3）。"""
	_check_action("return_sample", SAMPLE_DOCTYPE, sample_name)
	if qty is None or float(qty) <= 0:
		frappe.throw("返还数量必须大于 0。")
	try:
		sample = _lock_row(SAMPLE_DOCTYPE, sample_name)
		if sample.status not in (stb.SAMPLE_IN_STORAGE, stb.SAMPLE_PARTIAL):
			_reject(SAMPLE_DOCTYPE, sample_name,
					"仅「在箱 / 部分取样」状态可返还（当前：{}）。".format(sample.status),
					"非法状态：{} 调用 return_sample".format(sample.status))
		new_qty = float(sample.current_qty or 0) + float(qty)
		if new_qty > float(sample.init_qty or 0):
			frappe.throw("返还后结存超过初始量（{} > {}）。".format(new_qty, sample.init_qty))
		sample.current_qty = new_qty
		_set_sample_status(sample, _inbox_status(new_qty, sample.init_qty))
		_append_sample_log(sample, "返还", qty_delta=float(qty), remaining_qty=new_qty,
						   source_timepoint=timepoint, remarks=remarks,
						   reviewer=reviewer, return_sample_no=return_sample_no)
		sample.save(ignore_permissions=True)
		_audit_on(SAMPLE_DOCTYPE, "返还", sample.name,
				  action_text="取样返还", new_value="qty=+{} remaining={}".format(qty, new_qty))
		_commit()
		return {"name": sample.name, "status": sample.status, "current_qty": new_qty}
	except Exception:
		_rollback()
		raise


# ---- 样品：处置四件套 -----------------------------------------------------

@frappe.whitelist()
def mark_for_disposal(sample_name, reason):
	"""进入待处置：在箱/部分取样/已取尽 → 待处理；写 pre_disposal_status 快照（方案 6.3.3 / 门禁 13）。"""
	_check_action("mark_for_disposal", SAMPLE_DOCTYPE, sample_name)
	if not (reason or "").strip():
		frappe.throw("进入待处置的原因必填。")
	try:
		sample = _lock_row(SAMPLE_DOCTYPE, sample_name)
		if sample.status not in stb.SAMPLE_DISPOSAL_SOURCE_STATES:
			_reject(SAMPLE_DOCTYPE, sample_name,
					"仅「在箱 / 部分取样 / 已取尽」可进入待处置（当前：{}）。".format(sample.status),
					"非法状态：{} 调用 mark_for_disposal".format(sample.status))
		sample.pre_disposal_status = sample.status
		_set_sample_status(sample, stb.SAMPLE_PENDING_DISPOSAL)
		sample.disposal_mark_reason = reason
		sample.disposal_marked_by = _user()
		sample.disposal_marked_date = _today()
		sample.save(ignore_permissions=True)
		_audit_on(SAMPLE_DOCTYPE, "样品进入待处置", sample.name,
				  action_text="样品进入待处置", reason=reason,
				  new_value="pre_status={}".format(sample.pre_disposal_status))
		_commit()
		return {"name": sample.name, "status": sample.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def cancel_disposal(sample_name, reason):
	"""取消待处置（回库）：待处理 → 按 pre_disposal_status 快照恢复三态之一（方案 6.3.3 / 门禁 13）。"""
	_check_action("cancel_disposal", SAMPLE_DOCTYPE, sample_name)
	if not (reason or "").strip():
		frappe.throw("取消待处置的原因必填。")
	try:
		sample = _lock_row(SAMPLE_DOCTYPE, sample_name)
		if sample.status != stb.SAMPLE_PENDING_DISPOSAL:
			_reject(SAMPLE_DOCTYPE, sample_name,
					"仅「待处理」状态可取消待处置（当前：{}）。".format(sample.status),
					"非法状态：{} 调用 cancel_disposal".format(sample.status))
		target = sample.pre_disposal_status
		if target not in stb.SAMPLE_PRE_DISPOSAL_STATES:
			frappe.throw("进入待处置前的状态快照缺失或非法（{}），无法回退。".format(target))
		if not wf.can_transition(stb.FLOW_STB_SAMPLE, sample.status, target):
			frappe.throw("按快照回退到「{}」不在样品状态机允许的转移内。".format(target))
		sample.status = target
		sample.disposal_cancel_reason = reason
		sample.disposal_cancelled_by = _user()
		sample.disposal_cancelled_date = _today()
		sample.save(ignore_permissions=True)
		_audit_on(SAMPLE_DOCTYPE, "待处置取消（回库）", sample.name,
				  action_text="取消待处置并回库", reason=reason, new_value="restored={}".format(target))
		_commit()
		return {"name": sample.name, "status": sample.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def dispose_sample(sample_name, qty=None, remarks="", reviewer=None, location=None):
	"""销毁：待处理 → 已销毁；销毁量须等于当前结存，且须先 mark_for_disposal（方案 6.3.3）。"""
	_check_action("dispose_sample", SAMPLE_DOCTYPE, sample_name)
	try:
		sample = _lock_row(SAMPLE_DOCTYPE, sample_name)
		if sample.status != stb.SAMPLE_PENDING_DISPOSAL:
			_reject(SAMPLE_DOCTYPE, sample_name,
					"仅「待处理」状态可销毁；须先执行「进入待处置」（当前：{}）。".format(sample.status),
					"非法状态：{} 调用 dispose_sample".format(sample.status))
		current = float(sample.current_qty or 0)
		destroy_qty = current if qty is None else float(qty)
		if abs(destroy_qty - current) > 1e-9:
			frappe.throw("销毁数量（{}）必须等于当前结存（{}）。".format(destroy_qty, current))
		_set_sample_status(sample, stb.SAMPLE_DESTROYED)
		sample.current_qty = 0
		_append_sample_log(sample, "销毁", qty_delta=-destroy_qty, remaining_qty=0,
						   remarks=remarks or (location or ""), reviewer=reviewer)
		sample.save(ignore_permissions=True)
		_audit_on(SAMPLE_DOCTYPE, "销毁出库", sample.name,
				  action_text="样品销毁", new_value="destroyed={} supervisor={}".format(
					  destroy_qty, reviewer or "—"))
		_commit()
		return {"name": sample.name, "status": sample.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def adjust_stock(sample_name, qty_delta, remarks):
	"""手动调整结存（状态不变，原因必填；调整后结存 ≥ 0，方案 6.3.3）。"""
	_check_action("adjust_stock", SAMPLE_DOCTYPE, sample_name)
	if not (remarks or "").strip():
		frappe.throw("手动调整必须填写原因。")
	try:
		sample = _lock_row(SAMPLE_DOCTYPE, sample_name)
		if sample.status in stb.SAMPLE_TERMINAL_STATES:
			frappe.throw("终态样品不可调整结存（当前：{}）。".format(sample.status))
		new_qty = float(sample.current_qty or 0) + float(qty_delta or 0)
		if new_qty < 0:
			frappe.throw("调整后结存不得为负（{}）。".format(new_qty))
		sample.current_qty = new_qty
		if sample.status not in (stb.SAMPLE_PENDING_DISPOSAL,):
			_set_sample_status(sample, _inbox_status(new_qty, sample.init_qty))
		_append_sample_log(sample, "手动调整", qty_delta=float(qty_delta or 0),
						   remaining_qty=new_qty, remarks=remarks)
		sample.save(ignore_permissions=True)
		_audit_on(SAMPLE_DOCTYPE, "手动调整", sample.name,
				  action_text="手动调整结存", reason=remarks,
				  new_value="delta={} remaining={}".format(qty_delta, new_qty))
		_commit()
		return {"name": sample.name, "status": sample.status, "current_qty": new_qty}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def transfer_out(sample_name, remarks=""):
	"""受托转出：在箱/部分取样/已取尽 → 已转出（方案 6.3.3；流水记「受托转出」）。"""
	_check_action("transfer_out", SAMPLE_DOCTYPE, sample_name)
	try:
		sample = _lock_row(SAMPLE_DOCTYPE, sample_name)
		if sample.status not in stb.SAMPLE_DISPOSAL_SOURCE_STATES:
			_reject(SAMPLE_DOCTYPE, sample_name,
					"仅「在箱 / 部分取样 / 已取尽」可转出（当前：{}）。".format(sample.status),
					"非法状态：{} 调用 transfer_out".format(sample.status))
		_set_sample_status(sample, stb.SAMPLE_TRANSFERRED)
		remaining = float(sample.current_qty or 0)
		_append_sample_log(sample, "受托转出", qty_delta=-remaining, remaining_qty=0,
						   remarks=remarks or "受托转出")
		sample.current_qty = 0
		sample.save(ignore_permissions=True)
		_audit_on(SAMPLE_DOCTYPE, "受托转出", sample.name,
				  action_text="受托转出", new_value="remaining_cleared={}".format(remaining))
		_commit()
		return {"name": sample.name, "status": sample.status}
	except Exception:
		_rollback()
		raise


# ---- 时间点：生成 ---------------------------------------------------------

@frappe.whitelist()
def generate_timepoints(sample_name):
	"""按样品逐条件生成时间点（幂等、可重跑；方案 7.1）。

	方案/Notice 已批准 + 样品已入箱为前置资格；锁 Sample 行（方案 7.8）。
	已存在的 `sample_cond_point_key` 一律跳过，绝不覆盖。
	"""
	_check_action("generate_timepoints", SAMPLE_DOCTYPE, sample_name)
	try:
		sample = _lock_row(SAMPLE_DOCTYPE, sample_name)
		created = _generate_timepoints_impl(sample)
		if frappe.db.get_value(SAMPLE_DOCTYPE, sample.name, "timepoint_gen_error"):
			frappe.db.set_value(SAMPLE_DOCTYPE, sample.name, "timepoint_gen_error", "",
								update_modified=False)
		_commit()
		return {"sample": sample.name, "created": created}
	except Exception:
		_rollback()
		raise


def _timepoint_source(sample):
	"""返回 (category, vd_months, conditions, room_temp_recovery_days)。"""
	product = _product_of_sample(sample)
	category = product.category
	vd_months = product.vd_months
	recovery = 0
	conditions = []
	if sample.protocol:
		proto = frappe.get_doc("HBOS Stability Protocol", sample.protocol)
		recovery = proto.room_temp_recovery_days or 0
		for row in proto.study_conditions or []:
			conditions.append({
				"condition_type": row.condition_type,
				"condition_code": row.storage_cond or row.condition_type,
				"exposure_days": row.exposure_days,
			})
	else:
		notice = frappe.get_doc("HBOS Stability Notice", sample.notice)
		for row in notice.study_conditions or []:
			conditions.append({
				"condition_type": row.condition_type,
				"condition_code": row.storage_cond or row.condition_type,
				"exposure_days": row.exposure_days,
			})
	return category, vd_months, conditions, recovery


def _timepoint_items(sample):
	"""时间点检测项目来源：方案 items（is_key_item → is_required）；无方案时留空。"""
	items = []
	if sample.protocol:
		proto = frappe.get_doc("HBOS Stability Protocol", sample.protocol)
		for row in proto.items or []:
			if not row.stability_test_item:
				continue
			items.append({
				"stability_test_item": row.stability_test_item,
				"is_full_test": 1 if row.is_full_test else 0,
				"is_required": 1 if (row.is_key_item or row.is_full_test) else 0,
			})
	return items


def _generate_timepoints_impl(sample):
	"""生成实现（供 generate_timepoints 与 append_conditions 复用）。假定 Sample 已锁。"""
	category, vd_months, conditions, recovery = _timepoint_source(sample)
	plan = stb.plan_timepoints(category, vd_months, conditions, recovery)
	items = _timepoint_items(sample)
	start = sample.start_date or sample.in_date
	created = 0
	for point in plan:
		key = stb.make_sample_cond_point_key(sample.name, point["condition_code"],
											 point["value"], point["unit"])
		if frappe.db.exists(TIMEPOINT_DOCTYPE, {"sample_cond_point_key": key}):
			continue      # 锁内幂等：已存在一律跳过（方案 7.1）
		plan_sample = stb.add_time_point(start, point["value"], point["unit"])
		plan_test = _add_days(plan_sample, recovery)
		doc = frappe.get_doc({
			"doctype": TIMEPOINT_DOCTYPE,
			"stability_sample": sample.name,
			"condition_type": point["condition_type"],
			"storage_cond": point["condition_code"] if frappe.db.exists(
				"HBOS Stability Condition", point["condition_code"]) else None,
			"time_point_value": point["value"],
			"time_point_unit": point["unit"],
			"time_point_label": point["label"],
			"sample_cond_point_key": key,
			"plan_sample_date": plan_sample,
			"plan_test_date": plan_test,
			"delay_limit_days": stb.delay_limit_days(point["value"], point["unit"]),
			"is_full_test": point["is_full_test"],
			"is_zero_month": 1 if (point["unit"] == "月" and point["value"] == 0) else 0,
			"test_items": items,
			"status": stb.TP_WAIT_SAMPLE,
		})
		doc.flags.allow_system_fields = True
		doc.insert(ignore_permissions=True)
		created += 1
	if created:
		_audit_on(SAMPLE_DOCTYPE, "时间点生成", sample.name,
				  action_text="生成稳定性时间点", new_value="created={}".format(created))
	return created


# ---- 时间点：取样 → 检测 → 完成 -------------------------------------------

@frappe.whitelist()
def complete_sampling(timepoint_name, actual_sample_date=None):
	"""取样完成：待取样 → 待检测（方案 6.3.4）。"""
	_check_action("complete_sampling", TIMEPOINT_DOCTYPE, timepoint_name)
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		if tp.status != stb.TP_WAIT_SAMPLE:
			_reject(TIMEPOINT_DOCTYPE, timepoint_name,
					"仅「待取样」可完成取样（当前：{}）。".format(tp.status),
					"非法状态：{} 调用 complete_sampling".format(tp.status))
		tp.flags.allow_system_fields = True
		tp.actual_sample_date = _validate_actual_sample_date(
			tp, actual_sample_date or tp.actual_sample_date or _today())
		_set_status(tp, stb.FLOW_STB_TIMEPOINT, stb.TP_WAIT_TEST)
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "取样完成", tp.name,
				  action_text="取样完成", new_value=str(tp.actual_sample_date))
		_commit()
		return {"name": tp.name, "status": tp.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def import_zero_month_result(timepoint_name, source, baseline_doctype=None, baseline_name=None,
							 actual_sample_date=None):
	"""0 月免取样：待取样 → 待检测（豁免 #1/#2 校验，写豁免审计，方案 7.3 / P1-1）。

	结果落库（`HBOS Stability Result` 与 `baseline_*` 字段）属 R8C；本轮记录来源并留痕。
	"""
	_check_action("import_zero_month_result", TIMEPOINT_DOCTYPE, timepoint_name)
	if not stb.zero_month_exempt(1, source):
		frappe.throw("仅 0 月时间点、且来源为「出厂全检 / 委外」时适用免取样导入（当前来源：{}）。".format(source))
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		if not tp.is_zero_month:
			frappe.throw("该时间点不是 0 月点，不适用免取样导入。")
		if tp.status != stb.TP_WAIT_SAMPLE:
			_reject(TIMEPOINT_DOCTYPE, timepoint_name,
					"仅「待取样」可导入 0 月数据（当前：{}）。".format(tp.status),
					"非法状态：{} 调用 import_zero_month_result".format(tp.status))
		tp.flags.allow_system_fields = True
		tp.actual_sample_date = actual_sample_date or tp.actual_sample_date
		_set_status(tp, stb.FLOW_STB_TIMEPOINT, stb.TP_WAIT_TEST)
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "0 月数据豁免校验", tp.name,
				  action_text="0 月免取样导入（豁免 #1/#2 日期校验）",
				  new_value="source={} baseline={}/{}".format(source, baseline_doctype, baseline_name))
		_commit()
		return {"name": tp.name, "status": tp.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def start_testing(timepoint_name):
	"""检测开始：待检测 → 检测中（方案 6.3.4）。"""
	_check_action("start_testing", TIMEPOINT_DOCTYPE, timepoint_name)
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		if tp.status != stb.TP_WAIT_TEST:
			_reject(TIMEPOINT_DOCTYPE, timepoint_name,
					"仅「待检测」可开始检测（当前：{}）。".format(tp.status),
					"非法状态：{} 调用 start_testing".format(tp.status))
		tp.flags.allow_system_fields = True
		tp.test_by = _user()
		_set_status(tp, stb.FLOW_STB_TIMEPOINT, stb.TP_TESTING)
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "检测开始", tp.name, action_text="检测开始")
		_commit()
		return {"name": tp.name, "status": tp.status}
	except Exception:
		_rollback()
		raise


def complete_testing(timepoint_name):
	"""检测完成：检测中 → 已完成（**系统动作**，角色豁免、动作名不豁免）。

	**非公开入口**（无 `@frappe.whitelist`）：仅由 `approve_result` 在「该时间点全部必检
	项目均已批准」时自动调用（方案 6.3.4「全部必检项目批准后自动完成」/ 门禁 10）。

	前置：该时间点**全部必检项目均有已批准结果**（方案 6.3.4）。Result（R8C）未落地时
	`_approved_item_codes` 返回空集合，故本动作会被前置校验拒绝——这是正确判定（没有
	结果就不能完成检测），R8C 落地后自动生效。
	"""
	_check_action("complete_testing", TIMEPOINT_DOCTYPE, timepoint_name, system=True)
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		if tp.status != stb.TP_TESTING:
			_reject(TIMEPOINT_DOCTYPE, timepoint_name,
					"仅「检测中」可完成检测（当前：{}）。".format(tp.status),
					"非法状态：{} 调用 complete_testing".format(tp.status))
		required = {row.stability_test_item for row in (tp.test_items or [])
					if row.is_required and row.stability_test_item}
		approved = _approved_item_codes(tp.name)
		missing = sorted(required - approved)
		if missing:
			frappe.throw("以下必检项目尚无已批准结果，不能完成检测：{}".format(" / ".join(missing)))
		_set_status(tp, stb.FLOW_STB_TIMEPOINT, stb.TP_DONE)
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "检测完成", tp.name, action_text="检测完成")
		_commit()
		return {"name": tp.name, "status": tp.status}
	except Exception:
		_rollback()
		raise


def _maybe_complete_testing(tp):
	"""结果批准后按必检项目粒度判定自动完成检测（方案 6.3.4 / 门禁 10）。

	仅当 `status=检测中` 且该时间点**全部必检项目均有生效批准结果**时才调用
	`complete_testing`；否则保持原状态（与 `_maybe_reopen_timepoint` 对称）。
	"""
	if tp.status != stb.TP_TESTING:
		return
	required = {r.stability_test_item for r in (tp.test_items or [])
				if r.is_required and r.stability_test_item}
	if not required or (required - _approved_item_codes(tp.name)):
		return
	complete_testing(tp.name)


def reopen_timepoint(timepoint_name):
	"""时间点重开：已完成 → 检测中（**系统动作**，由 R8C 的 `void_result` 同事务调用）。

	守卫（方案 6.3.4 / P1 rev12）：**仅当 `status=已完成` 时才调用**；已是「检测中」则不调用
	本动作（保持原状态，仅记审计），避免非法转移。用户不可直接调用。
	"""
	_check_action("reopen_timepoint", TIMEPOINT_DOCTYPE, timepoint_name, system=True)
	tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
	if tp.status != stb.TP_DONE:
		_audit_on(TIMEPOINT_DOCTYPE, "时间点重开", tp.name,
				  action_text="跳过重开（非「已完成」）", new_value="status={}".format(tp.status))
		return {"name": tp.name, "status": tp.status, "reopened": False}
	tp.flags.allow_system_fields = True
	_set_status(tp, stb.FLOW_STB_TIMEPOINT, stb.TP_TESTING)
	tp.save(ignore_permissions=True)
	_audit_on(TIMEPOINT_DOCTYPE, "时间点重开", tp.name, action_text="时间点重开")
	return {"name": tp.name, "status": tp.status, "reopened": True}


@frappe.whitelist()
def cancel_timepoint(timepoint_name, reason):
	"""取消时间点：待取样/待检测/检测中 → 已取消（方案 6.3.4）。

	前置：原因必填；**若已有已批准结果须先全部作废**；**无在途结果**（草稿/已提交/已复核）。
	（Result 属 R8C，未落地时这两项判定恒为「无」，即不受限。）
	"""
	_check_action("cancel_timepoint", TIMEPOINT_DOCTYPE, timepoint_name)
	if not (reason or "").strip():
		frappe.throw("取消原因必填。")
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		if tp.status not in stb.TIMEPOINT_CANCELLABLE_STATES:
			_reject(TIMEPOINT_DOCTYPE, timepoint_name,
					"仅「待取样 / 待检测 / 检测中」可取消（当前：{}）。".format(tp.status),
					"非法状态：{} 调用 cancel_timepoint".format(tp.status))
		if _has_approved_result(tp.name):
			frappe.throw("该时间点已有已批准结果，须先全部作废方可取消（方案 6.3.4）。")
		if _has_inflight_result(tp.name):
			frappe.throw("该时间点存在在途结果（草稿/已提交/已复核），须先处理后再取消。")
		tp.flags.allow_system_fields = True
		tp.cancel_reason = reason
		_set_status(tp, stb.FLOW_STB_TIMEPOINT, stb.TP_CANCELLED)
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "时间点取消", tp.name,
				  action_text="时间点取消", reason=reason)
		_commit()
		return {"name": tp.name, "status": tp.status}
	except Exception:
		_rollback()
		raise


# ---- 时间点：追加条件 / 超方案取样 ----------------------------------------

@frappe.whitelist()
def append_conditions(change_name):
	"""追加条件/时间点（受控入口，准入动作，**不推进变更单状态**；方案 7.1 / 6.3.4）。

	单独调用要求变更单 `status=已批准 且 change_scope ∈ {涉条件与时间点, 涉方案}`。
	`HBOS Stability Change` 属 R8D；未落地时本入口一律拒绝——这是正确判定，
	R8D 的 `implement_change` 会在同事务内直接调用 `_append_conditions_impl`。
	"""
	_check_action("append_conditions", SAMPLE_DOCTYPE, change_name)
	if not frappe.db.exists("DocType", "HBOS Stability Change"):
		frappe.throw("追加条件须由变更实施发起（变更单 DocType 尚未落地，属 R8D）。")
	change = frappe.get_doc("HBOS Stability Change", change_name)
	if change.status != "已批准" or change.change_scope not in ("涉条件与时间点", "涉方案"):
		frappe.throw("仅「已批准」且落点为「涉条件与时间点 / 涉方案」的变更单可追加条件（当前：{} / {}）。".format(
			change.status, change.get("change_scope")))
	sample_name = change.get("stability_sample")
	if not sample_name:
		frappe.throw("变更单未指定稳定性样品。")
	try:
		sample = _lock_row(SAMPLE_DOCTYPE, sample_name)
		created = _append_conditions_impl(sample, _extra_conditions_of(change))
		_commit()
		return {"sample": sample.name, "created": created}
	except Exception:
		_rollback()
		raise


def _extra_conditions_of(change):
	"""从变更单取追加条件（字段属 R8D，落地前返回空）。"""
	rows = change.get("extra_conditions") or []
	return [{"condition_type": r.get("condition_type"),
			 "condition_code": r.get("storage_cond") or r.get("condition_type"),
			 "exposure_days": r.get("exposure_days")} for r in rows]


def _append_conditions_impl(sample, extra_conditions):
	"""锁内只新增（幂等、不覆盖、不改期、不删）；供 `implement_change`（R8D）同事务调用。"""
	created = 0
	category, vd_months, _conds, recovery = _timepoint_source(sample)
	items = _timepoint_items(sample)
	start = sample.start_date or sample.in_date
	for point in stb.plan_timepoints(category, vd_months, extra_conditions, recovery):
		key = stb.make_sample_cond_point_key(sample.name, point["condition_code"],
											 point["value"], point["unit"])
		if frappe.db.exists(TIMEPOINT_DOCTYPE, {"sample_cond_point_key": key}):
			continue
		plan_sample = stb.add_time_point(start, point["value"], point["unit"])
		doc = frappe.get_doc({
			"doctype": TIMEPOINT_DOCTYPE,
			"stability_sample": sample.name,
			"condition_type": point["condition_type"],
			"storage_cond": point["condition_code"] if frappe.db.exists(
				"HBOS Stability Condition", point["condition_code"]) else None,
			"time_point_value": point["value"],
			"time_point_unit": point["unit"],
			"time_point_label": point["label"],
			"sample_cond_point_key": key,
			"plan_sample_date": plan_sample,
			"plan_test_date": _add_days(plan_sample, recovery),
			"delay_limit_days": stb.delay_limit_days(point["value"], point["unit"]),
			"is_full_test": point["is_full_test"],
			"is_zero_month": 1 if (point["unit"] == "月" and point["value"] == 0) else 0,
			"test_items": items,
			"status": stb.TP_WAIT_SAMPLE,
		})
		doc.flags.allow_system_fields = True
		doc.insert(ignore_permissions=True)
		created += 1
	if created:
		_audit_on(SAMPLE_DOCTYPE, "追加条件/时间点", sample.name,
				  action_text="追加条件与时间点", new_value="created={}".format(created))
	return created


@frappe.whitelist()
def approve_extra_sampling(timepoint_name, reason=None):
	"""超方案取样批准（准入动作，状态不变；方案 6.3.4）。"""
	_check_action("approve_extra_sampling", TIMEPOINT_DOCTYPE, timepoint_name)
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		tp.flags.allow_system_fields = True
		tp.is_extra = 1
		tp.extra_reason = reason or tp.extra_reason
		tp.extra_approver_by = _user()
		tp.extra_approve_date = _today()
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "超方案取样批准", tp.name,
				  action_text="超方案取样批准", reason=reason or "")
		_commit()
		return {"name": tp.name}
	except Exception:
		_rollback()
		raise


# ---- 延期三段流程（方案 7.3 / 门禁 7、12、18） ----------------------------

def _delay_rows(tp, delay_type):
	return [d for d in (tp.delays or []) if d.delay_type == delay_type]


def _planned_due_of(tp, delay_type):
	return tp.plan_sample_date if delay_type == "取样延期" else tp.plan_test_date


def _policy_latest_of(tp, delay_type, product=None):
	if delay_type == "取样延期":
		return _policy_latest_sample(tp)
	return _policy_latest_test(tp.plan_test_date,
							   product.is_outsource if product is not None else None,
							   product.outsourced_test_window_days if product is not None else None)


@frappe.whitelist()
def apply_delay(timepoint_name, delay_type, requested_due_date, reason):
	"""延期申请：追加一条 Delay 子表行（`— → 待批准`）；日期链前半段校验（方案 6.3.4）。"""
	_check_action("apply_delay", TIMEPOINT_DOCTYPE, timepoint_name)
	if delay_type not in stb.DELAY_TYPES:
		frappe.throw("延期类型必须是「取样延期」或「检测延期」。")
	if not (reason or "").strip():
		frappe.throw("延期原因必填。")
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		if any(d.status == stb.DELAY_WAIT_APPROVE for d in _delay_rows(tp, delay_type)):
			frappe.throw("该类型的延期申请已有在途（待批准）记录，须先处理。")
		sample = frappe.get_doc(SAMPLE_DOCTYPE, tp.stability_sample)
		planned = _planned_due_of(tp, delay_type)
		policy = _policy_latest_of(tp, delay_type, _product_of_sample(sample))
		ok, err = stb.check_delay_apply(planned, requested_due_date, policy)
		if not ok:
			frappe.throw(err)
		tp.append("delays", {
			"delay_type": delay_type,
			"planned_due_date": planned,
			"policy_latest_due_date": policy,
			"requested_due_date": requested_due_date,
			"reason": reason,
			"apply_by": _user(),
			"apply_date": _today(),
			"status": stb.DELAY_WAIT_APPROVE,
		})
		tp.flags.allow_system_fields = True
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "{}申请".format(delay_type), tp.name,
				  action_text="{}申请".format(delay_type), reason=reason,
				  new_value="requested={}".format(requested_due_date))
		_commit()
		return {"name": tp.name, "delay_type": delay_type}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def approve_delay(timepoint_name, delay_type, approved_due_date):
	"""延期批准：`待批准 → 已批准`；SoD（申请≠批准）+ 日期链后半段 + 禁止批准倒退（方案 6.3.4 / 7.3）。"""
	_check_action("approve_delay", TIMEPOINT_DOCTYPE, timepoint_name)
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		row = next((d for d in _delay_rows(tp, delay_type)
					if d.status == stb.DELAY_WAIT_APPROVE), None)
		if not row:
			frappe.throw("该类型没有「待批准」的延期申请。")
		me = _user()
		if row.apply_by and row.apply_by == me:
			_audit_commit(TIMEPOINT_DOCTYPE, "SoD 拦截", tp.name,
						  action_text="延期批准违反职责分离",
						  reason="申请人同为 {}".format(row.apply_by))
			frappe.throw("延期批准人不得为申请人（SoD，方案 6.4）。")
		ok, err = stb.check_delay_approve(row.planned_due_date, row.requested_due_date,
										  approved_due_date, row.policy_latest_due_date)
		if not ok:
			frappe.throw(err)
		prev = [d for d in _delay_rows(tp, delay_type) if d.status == stb.DELAY_APPROVED]
		prev_sorted = sorted(prev, key=lambda d: str(d.approve_at or ""), reverse=True)
		if prev_sorted:
			ok, err = stb.check_approve_not_backwards(
				prev_sorted[0].approved_due_date, prev_sorted[0].approve_at,
				approved_due_date, _now())
			if not ok:
				frappe.throw(err)
		if not wf.can_transition(stb.FLOW_STB_TIMEPOINT_DELAY, row.status, stb.DELAY_APPROVED):
			frappe.throw("非法状态流转：{} -> 已批准（延期）".format(row.status))
		row.status = stb.DELAY_APPROVED
		row.approver_by = me
		row.approve_at = _now()
		row.approved_due_date = approved_due_date
		tp.flags.allow_system_fields = True
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "{}批准".format(delay_type), tp.name,
				  action_text="{}批准".format(delay_type),
				  new_value="approved={}".format(approved_due_date))
		_commit()
		return {"name": tp.name, "delay_type": delay_type, "approved_due_date": approved_due_date}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def reject_delay(timepoint_name, delay_type, reason):
	"""延期驳回：`待批准 → 已驳回`（驳回后仍按原截止日判定，可重新申请）。"""
	_check_action("reject_delay", TIMEPOINT_DOCTYPE, timepoint_name)
	if not (reason or "").strip():
		frappe.throw("驳回原因必填。")
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		row = next((d for d in _delay_rows(tp, delay_type)
					if d.status == stb.DELAY_WAIT_APPROVE), None)
		if not row:
			frappe.throw("该类型没有「待批准」的延期申请。")
		if not wf.can_transition(stb.FLOW_STB_TIMEPOINT_DELAY, row.status, stb.DELAY_REJECTED):
			frappe.throw("非法状态流转：{} -> 已驳回（延期）".format(row.status))
		row.status = stb.DELAY_REJECTED
		row.reject_reason = reason
		row.approver_by = _user()
		row.approve_at = _now()
		tp.flags.allow_system_fields = True
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "{}驳回".format(delay_type), tp.name,
				  action_text="{}驳回".format(delay_type), reason=reason)
		_commit()
		return {"name": tp.name, "delay_type": delay_type}
	except Exception:
		_rollback()
		raise


# ---- 只读接口（供 R8H 前端接入；方案 §10 API 复用模式） --------------------

@frappe.whitelist()
def get_stability_samples(keyword=None, status=None, stability_product=None,
						  limit=200, offset=0):
	"""稳定性样品台账（「样品入箱与台账」视图）。"""
	_check_action("get_stability_samples", SAMPLE_DOCTYPE, "-")
	filters = {}
	if status:
		filters["status"] = status
	if stability_product:
		filters["stability_product"] = stability_product
	or_filters = None
	kw = (keyword or "").strip()
	if kw:
		or_filters = [["name", "like", "%{}%".format(kw)], ["batch_no", "like", "%{}%".format(kw)],
					  ["sample_name", "like", "%{}%".format(kw)]]
	rows = frappe.get_all(
		SAMPLE_DOCTYPE, filters=filters, or_filters=or_filters,
		fields=["name", "notice", "protocol", "stability_product", "sample_name", "batch_no",
				"batch_size", "storage_cond", "condition_snapshot", "room", "storage_location",
				"inverted_flag", "init_qty", "current_qty", "qty_uom", "in_date", "start_date",
				"need_evaluation", "evaluation_conclusion", "timepoint_gen_error",
				"pack_desc", "is_sterile_pack", "package_count", "label_no", "status"],
		order_by="creation desc", limit_page_length=int(limit), limit_start=int(offset))
	_enrich_sample_products(rows)
	return {"rows": rows}


def _enrich_sample_products(rows):
	applied = sorted({r["stability_product"] for r in rows if r.get("stability_product")})
	if not applied:
		return
	names = dict(frappe.get_all("HBOS Stability Product", filters={"name": ["in", applied]},
								fields=["name", "product_name"], as_list=True))
	for row in rows:
		row["product_name"] = names.get(row.get("stability_product"))


@frappe.whitelist()
def get_stability_sample_detail(sample_name):
	"""样品详情（含库存流水），供下钻抽屉。"""
	_check_action("get_stability_sample_detail", SAMPLE_DOCTYPE, sample_name)
	doc = frappe.get_doc(SAMPLE_DOCTYPE, sample_name)
	product = _product_of_sample(doc)
	return {
		"name": doc.name,
		"notice": doc.notice,
		"protocol": doc.protocol,
		"stability_product": doc.stability_product,
		"product_name": product.product_name if product else None,
		"category": product.category if product else None,
		"sample_name": doc.sample_name,
		"material_code": doc.material_code,
		"batch_no": doc.batch_no,
		"batch_size": doc.batch_size,
		"manufacture_date": doc.manufacture_date,
		"finish_date": doc.finish_date,
		"send_date": doc.send_date,
		"full_test_sample_date": doc.full_test_sample_date,
		"in_date": doc.in_date,
		"start_date": doc.start_date,
		"storage_cond": doc.storage_cond,
		"condition_snapshot": doc.condition_snapshot,
		"room": doc.room,
		"storage_location": doc.storage_location,
		"inverted_flag": doc.inverted_flag,
		"pack_desc": doc.pack_desc,
		"is_sterile_pack": doc.is_sterile_pack,
		"package_count": doc.package_count,
		"package_spec": doc.package_spec,
		"init_qty": doc.init_qty,
		"current_qty": doc.current_qty,
		"qty_uom": doc.qty_uom,
		"label_no": doc.label_no,
		"timepoint_gen_error": doc.timepoint_gen_error,
		"need_evaluation": doc.need_evaluation,
		"evaluation_conclusion": doc.evaluation_conclusion,
		"evaluated_by": doc.evaluated_by,
		"evaluation_date": doc.evaluation_date,
		"stored_by": doc.stored_by,
		"reviewed_by": doc.reviewed_by,
		"reviewed_date": doc.reviewed_date,
		"pre_disposal_status": doc.pre_disposal_status,
		"disposal_mark_reason": doc.disposal_mark_reason,
		"disposal_marked_by": doc.disposal_marked_by,
		"disposal_marked_date": doc.disposal_marked_date,
		"disposal_cancel_reason": doc.disposal_cancel_reason,
		"disposal_cancelled_by": doc.disposal_cancelled_by,
		"disposal_cancelled_date": doc.disposal_cancelled_date,
		"status": doc.status,
		"logs": [{
			"transaction_date": r.transaction_date, "transaction_type": r.transaction_type,
			"source_timepoint": r.source_timepoint, "sampling_reason": r.sampling_reason,
			"sample_no_out": r.sample_no_out, "return_sample_no": r.return_sample_no,
			"remaining_sample_no": r.remaining_sample_no,
			"qty_delta": r.qty_delta, "qty_uom": r.qty_uom, "remaining_qty": r.remaining_qty,
			"operator": r.operator, "reviewer": r.reviewer, "remarks": r.remarks,
		} for r in (doc.logs or [])],
		"timepoints": frappe.get_all(
			TIMEPOINT_DOCTYPE, filters={"stability_sample": sample_name},
			fields=["name", "time_point_label", "condition_type", "status",
					"plan_sample_date", "plan_test_date", "actual_sample_date", "actual_test_date"],
			order_by="plan_sample_date asc", limit_page_length=0),
	}


@frappe.whitelist()
def get_stability_schedule(month=None, condition=None, exec_status=None, keyword=None,
						   limit=500):
	"""取样与检测计划看板数据（逾期为纯派生，不改状态；方案 5.6 / 8.4）。"""
	_check_action("get_stability_schedule", TIMEPOINT_DOCTYPE, "-")
	filters = {}
	if condition:
		filters["condition_type"] = condition
	month_key = str(month or "").strip()
	if month_key:
		# 月份过滤必须在分页前下推，否则前一页数据不足会漏项。
		filters["plan_sample_date"] = ["like", month_key[:7] + "%"]
	or_filters = None
	kw = (keyword or "").strip()
	if kw:
		or_filters = [["name", "like", "%{}%".format(kw)],
					  ["stability_sample", "like", "%{}%".format(kw)]]
	rows = frappe.get_all(
		TIMEPOINT_DOCTYPE, filters=filters, or_filters=or_filters,
		fields=["name", "stability_sample", "condition_type", "storage_cond",
				"time_point_label", "time_point_value", "time_point_unit",
				"plan_sample_date", "actual_sample_date", "plan_test_date", "actual_test_date",
				"delay_limit_days", "is_full_test", "is_zero_month", "status",
				"sample_cond_point_key"],
		order_by="plan_sample_date asc, time_point_value asc",
		limit_page_length=int(limit))
	rows = _enrich_schedule(rows)
	# 结果录入页需要从计划直接拿到检验项目，避免详情接口之外出现空下拉。
	item_map = {}
	tp_names = [r["name"] for r in rows]
	if tp_names:
		for item in frappe.get_all(
				"HBOS Stability Timepoint Item",
				filters={"parent": ["in", tp_names], "parenttype": TIMEPOINT_DOCTYPE},
				fields=["parent", "stability_test_item", "is_full_test", "is_required"],
				order_by="idx asc", limit_page_length=0):
			item_map.setdefault(item.parent, []).append({
				"stability_test_item": item.stability_test_item,
				"is_full_test": item.is_full_test,
				"is_required": item.is_required,
			})
	for row in rows:
		row["test_items"] = item_map.get(row["name"], [])
	if exec_status:
		rows = [r for r in rows if r.get("exec_state") == exec_status or r.get("status") == exec_status]
	return {"rows": rows, "summary": _schedule_summary(rows)}


def _enrich_schedule(rows):
	today = _today()
	if isinstance(today, str):
		today = stb._as_date(today)
	sample_names = sorted({r["stability_sample"] for r in rows if r.get("stability_sample")})
	samples = {}
	if sample_names:
		for s in frappe.get_all(SAMPLE_DOCTYPE, filters={"name": ["in", sample_names]},
								fields=["name", "batch_no", "sample_name", "stability_product",
										"room", "status", "current_qty"], limit_page_length=0):
			samples[s.name] = s
	prod_names = sorted({s["stability_product"] for s in samples.values() if s.get("stability_product")})
	products = {}
	if prod_names:
		for p in frappe.get_all("HBOS Stability Product", filters={"name": ["in", prod_names]},
								fields=["name", "product_name", "is_outsource",
										"outsourced_test_window_days"], limit_page_length=0):
			products[p.name] = p
	# 延期：按时间点批量取（算有效截止日与延期状态），避免逐行 N+1
	delay_map = {}
	tp_names = [r["name"] for r in rows]
	if tp_names:
		for d in frappe.get_all(
				"HBOS Stability Timepoint Delay",
				filters={"parent": ["in", tp_names], "parenttype": TIMEPOINT_DOCTYPE},
				fields=["parent", "delay_type", "status", "approve_at", "approved_due_date"],
				limit_page_length=0):
			delay_map.setdefault(d.parent, []).append(d)
	for r in rows:
		s = samples.get(r["stability_sample"]) or {}
		p = products.get(s.get("stability_product")) or {}
		r["batch_no"] = s.get("batch_no")
		r["sample_name"] = s.get("sample_name")
		r["room"] = s.get("room")
		r["product_name"] = p.get("product_name")
		r["sample_status"] = s.get("status")
		r["current_qty"] = s.get("current_qty")
		delays = delay_map.get(r["name"], [])

		policy_sample = stb._add_days(r["plan_sample_date"], r.get("delay_limit_days") or 0)
		policy_test = _policy_latest_test(r["plan_test_date"], p.get("is_outsource"),
										  p.get("outsourced_test_window_days"))
		eff_sample = stb.effective_due_date(delays, "取样延期", policy_sample)
		eff_test = stb.effective_due_date(delays, "检测延期", policy_test)
		r["policy_latest_sample_due"] = str(policy_sample) if policy_sample else None
		r["policy_latest_test_due"] = str(policy_test) if policy_test else None
		r["effective_sample_due"] = str(eff_sample) if eff_sample else None
		r["effective_test_due"] = str(eff_test) if eff_test else None

		inflight = [d for d in delays if d.status == stb.DELAY_WAIT_APPROVE]
		approved = [d for d in delays if d.status == stb.DELAY_APPROVED]
		if inflight:
			r["delay_state"] = "{}（待批准）".format(inflight[-1].delay_type)
		elif approved:
			latest = sorted(approved, key=lambda d: str(d.approve_at or ""))[-1]
			r["delay_state"] = "{} 延至 {}".format(latest.delay_type, latest.approved_due_date)
		else:
			r["delay_state"] = ""

		r["sample_overdue"] = 0
		r["test_overdue"] = 0
		r["exec_state"] = r["status"]
		if r["status"] == stb.TP_WAIT_SAMPLE and eff_sample and today > eff_sample:
			r["sample_overdue"] = 1
			r["exec_state"] = "取样逾期"
		if r["status"] in (stb.TP_WAIT_TEST, stb.TP_TESTING) and eff_test and today > eff_test:
			r["test_overdue"] = 1
			r["exec_state"] = "检测逾期"
	return rows


def _schedule_summary(rows):
	return {
		"total": len(rows),
		"wait_sample": sum(1 for r in rows if r["status"] == stb.TP_WAIT_SAMPLE),
		"wait_test": sum(1 for r in rows if r["status"] == stb.TP_WAIT_TEST),
		"testing": sum(1 for r in rows if r["status"] == stb.TP_TESTING),
		"done": sum(1 for r in rows if r["status"] == stb.TP_DONE),
		"cancelled": sum(1 for r in rows if r["status"] == stb.TP_CANCELLED),
		"sample_overdue": sum(1 for r in rows if r.get("sample_overdue")),
		"test_overdue": sum(1 for r in rows if r.get("test_overdue")),
	}


@frappe.whitelist()
def get_stability_timepoint_detail(timepoint_name):
	"""时间点详情（含检测项目与延期历史）。"""
	_check_action("get_stability_timepoint_detail", TIMEPOINT_DOCTYPE, timepoint_name)
	doc = frappe.get_doc(TIMEPOINT_DOCTYPE, timepoint_name)
	sample = frappe.get_doc(SAMPLE_DOCTYPE, doc.stability_sample)
	product = _product_of_sample(sample)
	effective_sample, policy_sample = _effective_sample_due(doc)
	effective_test, policy_test = _effective_test_due(doc, product)
	return {
		"name": doc.name,
		"stability_sample": doc.stability_sample,
		"batch_no": sample.batch_no,
		"sample_name": sample.sample_name,
		"product_name": product.product_name if product else None,
		"condition_type": doc.condition_type,
		"storage_cond": doc.storage_cond,
		"time_point_value": doc.time_point_value,
		"time_point_unit": doc.time_point_unit,
		"time_point_label": doc.time_point_label,
		"plan_sample_date": doc.plan_sample_date,
		"actual_sample_date": doc.actual_sample_date,
		"plan_test_date": doc.plan_test_date,
		"actual_test_date": doc.actual_test_date,
		"delay_limit_days": doc.delay_limit_days,
		"effective_sample_due": str(effective_sample) if effective_sample else None,
		"policy_latest_sample_due": str(policy_sample) if policy_sample else None,
		"effective_test_due": str(effective_test) if effective_test else None,
		"policy_latest_test_due": str(policy_test) if policy_test else None,
		"is_full_test": doc.is_full_test,
		"is_zero_month": doc.is_zero_month,
		"is_extra": doc.is_extra,
		"extra_reason": doc.extra_reason,
		"extra_approver_by": doc.extra_approver_by,
		"extra_approve_date": doc.extra_approve_date,
		"sample_by": doc.sample_by,
		"test_by": doc.test_by,
		"eval_date": doc.eval_date,
		"evaluator": doc.evaluator,
		"trend_conclusion": doc.trend_conclusion,
		"cancel_reason": doc.cancel_reason,
		"status": doc.status,
		"test_items": [{
			"stability_test_item": r.stability_test_item,
			"is_full_test": r.is_full_test, "is_required": r.is_required,
		} for r in (doc.test_items or [])],
		"delays": [{
			"delay_type": d.delay_type, "planned_due_date": d.planned_due_date,
			"policy_latest_due_date": d.policy_latest_due_date,
			"requested_due_date": d.requested_due_date, "reason": d.reason,
			"apply_by": d.apply_by, "apply_date": d.apply_date, "status": d.status,
			"approver_by": d.approver_by, "approve_at": d.approve_at,
			"approved_due_date": d.approved_due_date, "reject_reason": d.reject_reason,
		} for d in (doc.delays or [])],
	}


@frappe.whitelist()
def get_stability_delays(delay_type=None, status=None, keyword=None, limit=200):
	"""延期申请列表（跨时间点），供「延期审批」tab（方案 7.3 / 6.3.4）。

	延期是 `HBOS Stability Timepoint Delay` 子表行，此处按需扁平成独立行并补出
	产品/批号/时间点标签等展示字段（批量取，避免 N+1）。
	"""
	_check_action("get_stability_delays", TIMEPOINT_DOCTYPE, "-")
	filters = {"parenttype": TIMEPOINT_DOCTYPE}
	if delay_type:
		filters["delay_type"] = delay_type
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		"HBOS Stability Timepoint Delay", filters=filters,
		fields=["name", "parent", "idx", "delay_type", "planned_due_date",
				"policy_latest_due_date", "requested_due_date", "reason",
				"apply_by", "apply_date", "status", "approver_by", "approve_at",
				"approved_due_date", "reject_reason"],
		order_by="apply_date desc, creation desc", limit_page_length=int(limit))
	if not rows:
		return {"rows": [], "summary": {"pending": 0, "approved": 0, "rejected": 0}}

	tp_names = sorted({r["parent"] for r in rows})
	timepoints = {}
	for t in frappe.get_all(TIMEPOINT_DOCTYPE, filters={"name": ["in", tp_names]},
							fields=["name", "stability_sample", "condition_type",
									"time_point_label", "status", "plan_sample_date",
									"plan_test_date", "actual_sample_date"],
							limit_page_length=0):
		timepoints[t.name] = t
	sample_names = sorted({t["stability_sample"] for t in timepoints.values()
						   if t.get("stability_sample")})
	samples, products = {}, {}
	if sample_names:
		for s in frappe.get_all(SAMPLE_DOCTYPE, filters={"name": ["in", sample_names]},
								fields=["name", "batch_no", "sample_name", "stability_product"],
								limit_page_length=0):
			samples[s.name] = s
		prod_names = sorted({s["stability_product"] for s in samples.values()
							 if s.get("stability_product")})
		if prod_names:
			products = dict(frappe.get_all("HBOS Stability Product",
										   filters={"name": ["in", prod_names]},
										   fields=["name", "product_name"], as_list=True))

	kw = (keyword or "").strip().lower()
	out = []
	for r in rows:
		t = timepoints.get(r["parent"]) or {}
		s = samples.get(t.get("stability_sample")) or {}
		r["batch_no"] = s.get("batch_no")
		r["sample_name"] = s.get("sample_name")
		r["product_name"] = products.get(s.get("stability_product"))
		r["time_point_label"] = t.get("time_point_label")
		r["condition_type"] = t.get("condition_type")
		r["timepoint_status"] = t.get("status")
		if kw and kw not in "{} {} {} {}".format(
				r["parent"], r["batch_no"] or "", r["product_name"] or "",
				r["reason"] or "").lower():
			continue
		out.append(r)
	return {"rows": out, "summary": {
		"pending": sum(1 for r in rows if r["status"] == stb.DELAY_WAIT_APPROVE),
		"approved": sum(1 for r in rows if r["status"] == stb.DELAY_APPROVED),
		"rejected": sum(1 for r in rows if r["status"] == stb.DELAY_REJECTED),
	}}


# ---- scheduler（方案 8.4：逾期纯派生，不改状态、不推送） -------------------

def scheduler_scan():
	"""每日扫描：取样/检测逾期、检测临近、检测完成推荐期到期、在箱无时间点。

	结果写 site cache `hbos_stability_scheduler_summary` 供报表/看板派生展示；
	**不改单据状态、不做推送**（逾期为纯派生标识，方案 P1-10）。
	"""
	today = stb._as_date(_today())
	rows = frappe.get_all(
		TIMEPOINT_DOCTYPE,
		filters={"status": ["in", [stb.TP_WAIT_SAMPLE, stb.TP_WAIT_TEST, stb.TP_TESTING]]},
		fields=["name", "stability_sample", "status", "plan_sample_date", "plan_test_date",
				"actual_sample_date", "delay_limit_days", "time_point_value", "time_point_unit"],
		limit_page_length=0)
	sample_overdue, test_overdue, test_near, recommend_due = [], [], [], []
	for r in rows:
		if r["status"] == stb.TP_WAIT_SAMPLE and r["plan_sample_date"]:
			policy = stb._add_days(r["plan_sample_date"], r["delay_limit_days"] or 0)
			if policy and today > policy:
				sample_overdue.append(r["name"])
		if r["status"] in (stb.TP_WAIT_TEST, stb.TP_TESTING) and r["plan_test_date"]:
			policy = stb._add_days(r["plan_test_date"], stb.TEST_WINDOW_DAYS)
			if policy and today > policy:
				test_overdue.append(r["name"])
			if stb._as_date(r["plan_test_date"]) >= today and \
					(stb._as_date(r["plan_test_date"]) - today).days <= 7:
				test_near.append(r["name"])
		if r["status"] in (stb.TP_WAIT_TEST, stb.TP_TESTING) and r["actual_sample_date"]:
			limit_days = 14 if _to_days_of(r) <= 1 else 28
			due = stb._add_days(r["actual_sample_date"], limit_days)
			if due and today > due:
				recommend_due.append(r["name"])
	# 在箱但无任何时间点的样品（方案 7.1：可恢复的正常中间态，看板单列提示）
	samples = frappe.get_all(SAMPLE_DOCTYPE, filters={"status": stb.SAMPLE_IN_STORAGE},
							 fields=["name"], limit_page_length=0)
	no_timepoint = []
	for s in samples:
		if not frappe.db.exists(TIMEPOINT_DOCTYPE, {"stability_sample": s["name"]}):
			no_timepoint.append(s["name"])
	# 趋势评估逾期（方案 8.4）：已完成时间点，末次结果批准后 > 5 个工作日仍未评估
	holidays = _holiday_set()
	trend_overdue = []
	if frappe.db.exists("DocType", RESULT_DOCTYPE):
		done_tps = frappe.get_all(
			TIMEPOINT_DOCTYPE,
			filters={"status": stb.TP_DONE, "eval_date": ["is", "not set"]},
			pluck="name", limit_page_length=0)
		for name in done_tps:
			last = frappe.get_all(
				RESULT_DOCTYPE, filters={"timepoint": name, "status": stb.RESULT_APPROVED},
				fields=["approved_at"], order_by="approved_at desc", limit_page_length=1)
			if not last or not last[0].approved_at:
				continue
			due = stb.add_working_days(stb._as_date(last[0].approved_at), 5, holidays)
			if due and today > due:
				trend_overdue.append(name)
	# 设备/校准/确认到期（方案 8.4）：任一到期日距今 ≤ 30 天
	equipment_due = []
	if frappe.db.exists("DocType", EQUIPMENT_DOCTYPE):
		for eq in frappe.get_all(
				EQUIPMENT_DOCTYPE,
				filters={"status": ["in", [stb.EQUIPMENT_STATUSES[0], stb.EQUIPMENT_STATUSES[2]]]},
				fields=["name", "calibration_due", "maintenance_due", "qualification_due"],
				limit_page_length=0):
			for field in ("calibration_due", "maintenance_due", "qualification_due"):
				due = stb._as_date(eq.get(field))
				if due and stb._add_days(today, 30) >= due >= today:
					equipment_due.append({"name": eq.name, "field": field, "due": str(due)})
					break
	# 温湿度缺卡（方案 8.4 P3）：某房间某工作日（依 Holiday List）缺上午或下午记录
	room_log_missing = []
	if frappe.db.exists("DocType", ROOM_LOG_DOCTYPE):
		rooms = frappe.get_all("HBOS Stability Room", filters={"is_active": 1},
							   pluck="name", limit_page_length=0)
		if rooms:
			holiday_dates = _holiday_set()
			for offset in range(1, 8):
				day = stb._as_date(frappe.utils.add_days(str(today), -offset))
				if day.weekday() >= 5 or day in holiday_dates:
					continue
				for room in rooms:
					logged = {r.period for r in frappe.get_all(
						ROOM_LOG_DOCTYPE, filters={"room": room, "log_date": str(day)},
						fields=["period"], limit_page_length=0)}
					missing = [p for p in stb.LOG_PERIODS if p not in logged]
					if missing:
						room_log_missing.append(
							{"room": room, "date": str(day), "missing": missing})
	# 运行期一致性扫描（方案 8.6 / P2 rev12）
	consistency_violations = _consistency_scan()
	summary = {
		"date": str(today),
		"sample_overdue": len(sample_overdue),
		"test_overdue": len(test_overdue),
		"test_near_7d": len(test_near),
		"recommend_due": len(recommend_due),
		"trend_eval_overdue": len(trend_overdue),
		"sample_without_timepoint": len(no_timepoint),
		"equipment_due": len(equipment_due),
		"room_log_missing": len(room_log_missing),
		"consistency_violations": len(consistency_violations),
		"details": {
			"sample_overdue": sample_overdue[:200],
			"test_overdue": test_overdue[:200],
			"test_near_7d": test_near[:200],
			"recommend_due": recommend_due[:200],
			"trend_eval_overdue": trend_overdue[:200],
			"sample_without_timepoint": no_timepoint[:200],
			"equipment_due": equipment_due[:200],
			"room_log_missing": room_log_missing[:200],
			"consistency_violations": consistency_violations[:200],
		},
	}
	frappe.cache.set_value("hbos_stability_scheduler_summary", summary)
	return summary


def _consistency_scan():
	"""运行期一致性扫描（方案 8.6 / P2 rev12）：只检出与告警，不自动修复。

	四类不变式：生效指针 / 流水对账 / 日期链 / 业务键唯一。违反写审计事件「一致性异常」。
	"""
	violations = []
	# ① 生效指针不变式（7.7 / 门禁 11、15）
	if frappe.db.exists("DocType", RESULT_DOCTYPE):
		for row in frappe.get_all(
				RESULT_DOCTYPE, filters={"is_current": 1},
				fields=["name", "timepoint", "stability_test_item", "status"],
				limit_page_length=0):
			if row.status != stb.RESULT_APPROVED:
				violations.append(("生效指针不变式", RESULT_DOCTYPE, row.name,
								   "is_current=1 但 status={}".format(row.status)))
			elif not frappe.db.exists("HBOS Stability Timepoint Item",
									  {"current_result": row.name}):
				violations.append(("生效指针不变式", RESULT_DOCTYPE, row.name,
								   "无 Timepoint Item.current_result 指向"))
	# 同一 (时间点, 项目) 至多一条 is_current=1
		dup_rows = frappe.get_all(
			RESULT_DOCTYPE, filters={"is_current": 1},
			fields=["timepoint", "stability_test_item"], limit_page_length=0)
		seen = {}
		for r in dup_rows:
			k = (r.timepoint, r.stability_test_item)
			if k in seen:
				violations.append(("生效指针不变式", RESULT_DOCTYPE, seen[k],
								   "与 {} 同键均 is_current=1".format(r.name)))
			seen[k] = r.name
	# ② 流水对账（7.8 / 门禁 7）
	for s in frappe.get_all(SAMPLE_DOCTYPE, fields=["name", "current_qty"],
							limit_page_length=0):
		logs = frappe.get_all("HBOS Stability Sample Log", filters={"parent": s.name},
							  fields=["qty_delta"], limit_page_length=0)
		total = sum(float(l.qty_delta or 0) for l in logs)
		if abs(total - float(s.current_qty or 0)) > 1e-6:
			violations.append(("流水对账", SAMPLE_DOCTYPE, s.name,
							   "流水累计 {} ≠ current_qty {}".format(total, s.current_qty)))
	# ③ 日期链（7.3 / 门禁 18）：已批准延期行 planned ≤ requested ≤ approved ≤ policy_latest
	for d in frappe.get_all("HBOS Stability Timepoint Delay",
							filters={"status": stb.DELAY_APPROVED},
							fields=["name", "planned_due_date", "requested_due_date",
									"approved_due_date", "policy_latest_due_date"],
							limit_page_length=0):
		chain = [d.planned_due_date, d.requested_due_date, d.approved_due_date,
				 d.policy_latest_due_date]
		if all(chain) and not (chain[0] <= chain[1] <= chain[2] <= chain[3]):
			violations.append(("日期链", "HBOS Stability Timepoint Delay", d.name,
							   "planned≤requested≤approved≤policy_latest 不成立"))
	# ④ 业务键唯一（5.6）：DB unique 之外的应用层抽查
	for check in ((TIMEPOINT_DOCTYPE, "sample_cond_point_key"),
				  (RESULT_DOCTYPE, "result_version_key"),
				  (ROOM_LOG_DOCTYPE, "room_date_period_key")):
		if not frappe.db.exists("DocType", check[0]):
			continue
		names = frappe.get_all(check[0], pluck=check[1], limit_page_length=0)
		seen_keys = set()
		for key in names:
			if not key:
				continue
			if key in seen_keys:
				violations.append(("业务键唯一", check[0], key, "重复业务键"))
			seen_keys.add(key)
	# 违反写审计（独立提交，扫描器自身不成为写路径）
	for invariant, dt, name, detail in violations:
		try:
			_audit_on(dt, "一致性异常", name, action_text="运行期一致性扫描",
					  reason="{}：{}".format(invariant, detail))
		except Exception as exc:
			frappe.log_error("一致性异常审计写入失败：{}".format(exc), "HBOS Stability 一致性扫描")
	_commit()
	return violations


def _to_days_of(timepoint_row):
	"""时间点折算天数（1 月点 = 30 天 → 推荐期 14 天；更长点 28 天）。"""
	return stb._to_days(timepoint_row.get("time_point_value"), timepoint_row.get("time_point_unit"))


# ===========================================================================
# M2-R8C：结果与报告（方案 6.3.5 / 6.3.6 / 7.4 / 7.5 / 7.6 / 7.7）
# ===========================================================================

RESULT_DOCTYPE = "HBOS Stability Result"
REPORT_DOCTYPE = "HBOS Stability Report"
_SYNCABLE_TIMEPOINT_STATES = (stb.TP_WAIT_TEST, stb.TP_TESTING, stb.TP_DONE)


# ---- 来源链与快照 ---------------------------------------------------------

def _source_doc_of_sample(sample):
	"""按样品类别分派来源链（方案 7.7）：有方案 → Protocol；年度类无方案 → Notice。"""
	if sample.protocol:
		return frappe.get_doc("HBOS Stability Protocol", sample.protocol)
	if sample.notice:
		return frappe.get_doc("HBOS Stability Notice", sample.notice)
	return None


def _spec_row_for(spec_ref, stability_test_item):
	"""在质量标准里找到该稳定性检验项目对应的限度行（经 base_test_item 映射）。"""
	if not spec_ref:
		return None
	base = frappe.db.get_value("HBOS Stability Test Item", stability_test_item, "base_test_item")
	if not base:
		return None
	spec = frappe.get_doc("HBOS Specification", spec_ref)
	for row in (spec.items or []):
		if row.item == base:
			return row
	return None


def _limit_text_of(row):
	if row is None:
		return None
	return stb._limit_text(row.limits_type, row.lower_limit, row.upper_limit)


def _spec_context_for(sample, stability_test_item):
	"""按类别来源链解析标准上下文（方案 7.7）。

	返回 (spec_ref, spec_version, method_version, test_method, spec_row)。
	Result 不存 `spec_ref`（方案 5.4.1 字段表无该字段），标准溯源一律实时走来源链。
	"""
	src = _source_doc_of_sample(sample)
	spec_ref = src.spec_ref if src is not None else None
	# Protocol 用 `test_method_ref`、Notice 用 `test_method`，两者字段不同名
	test_method = None
	if src is not None:
		test_method = getattr(src, "test_method_ref", None) or getattr(src, "test_method", None)
	return (
		spec_ref,
		src.spec_version if src is not None else None,
		src.method_version if src is not None else None,
		test_method,
		_spec_row_for(spec_ref, stability_test_item),
	)


# ---- 基线选取与显著变化（方案 7.4） ---------------------------------------

def _results_of_item(timepoint_name, item_code):
	return frappe.get_all(
		RESULT_DOCTYPE,
		filters={"timepoint": timepoint_name, "stability_test_item": item_code},
		fields=["name", "status", "is_current", "result_value", "is_zero_month", "source",
				"baseline_doctype", "baseline_name", "revision_no"],
		limit_page_length=0)


def _approved_results_of_sample(sample_name, item_code, condition_type=None):
	"""该样品该项目的全部**已批准且生效**结果（按时间点计划日排序）。"""
	rows = frappe.get_all(
		RESULT_DOCTYPE,
		filters={"stability_sample": sample_name, "stability_test_item": item_code,
				 "status": stb.RESULT_APPROVED, "is_current": 1},
		fields=["name", "timepoint", "result_value", "is_zero_month", "source"],
		limit_page_length=0)
	if not rows:
		return []
	tp_ids = [r.timepoint for r in rows]
	tps = {t.name: t for t in frappe.get_all(
		TIMEPOINT_DOCTYPE, filters={"name": ["in", tp_ids]},
		fields=["name", "condition_type", "plan_sample_date", "time_point_value",
				"time_point_unit"], limit_page_length=0)}
	out = []
	for r in rows:
		t = tps.get(r.timepoint) or {}
		if condition_type and t.get("condition_type") != condition_type:
			continue
		r["condition_type"] = t.get("condition_type")
		r["plan_sample_date"] = t.get("plan_sample_date")
		out.append(r)
	out.sort(key=lambda x: str(x.get("plan_sample_date") or ""))
	return out


def _pick_baseline(sample_name, item_code, condition_type, current_result_name=None):
	"""基线选择（方案 7.4）：① 0 月已批准 → ② source=出厂全检 → ③ 首个已批准点。"""
	approved = [r for r in _approved_results_of_sample(sample_name, item_code, condition_type)
				if r["name"] != current_result_name]
	if not approved:
		return None
	zero = [r for r in approved if r["is_zero_month"]]
	if zero:
		return {"value": zero[0]["result_value"], "ref": "0月",
				"doctype": "HBOS Stability Result", "name": zero[0]["name"]}
	outsourced = [r for r in approved if r["source"] == "出厂全检"]
	if outsourced:
		return {"value": outsourced[0]["result_value"], "ref": "出厂全检",
				"doctype": "HBOS Stability Result", "name": outsourced[0]["name"]}
	first = approved[0]
	return {"value": first["result_value"], "ref": "首点",
			"doctype": "HBOS Stability Result", "name": first["name"]}


def _apply_judgement(res, item, spec_row, baseline, source_doc):
	"""符合性 + 显著变化判定（方案 7.4），并把依据写入。"""
	limits_type = spec_row.limits_type if spec_row is not None else None
	lower = spec_row.lower_limit if spec_row is not None else None
	upper = spec_row.upper_limit if spec_row is not None else None

	verdict = rc.judge_result(res.result_value, limits_type or rc.LIMITS_RECORD, lower, upper)
	res.is_qualified = 1 if verdict == rc.VERDICT_PASS else 0
	res.oos_flag = 1 if verdict == rc.VERDICT_FAIL else 0

	sig, basis = stb.check_significant_change(
		item.significant_change_rule, res.result_value,
		baseline=baseline.get("value") if baseline else None,
		threshold=item.change_threshold, limits_type=limits_type,
		lower=lower, upper=upper, result_type=item.result_type)
	res.is_significant_change = 1 if sig else 0
	res.significant_change_basis = basis
	return sig, basis


def _current_result_of(timepoint_name, item_code, exclude=None):
	rows = frappe.get_all(
		RESULT_DOCTYPE,
		filters={"timepoint": timepoint_name, "stability_test_item": item_code,
				 "is_current": 1},
		pluck="name", limit_page_length=1)
	if not rows:
		return None
	return rows[0] if rows[0] != exclude else None


def _next_revision_no(timepoint_name, item_code):
	rows = frappe.get_all(
		RESULT_DOCTYPE,
		filters={"timepoint": timepoint_name, "stability_test_item": item_code},
		pluck="revision_no", limit_page_length=0)
	return (max([int(r or 0) for r in rows]) + 1) if rows else 1


def _write_current_pointer(tp, item_code, result_name):
	tp.flags.allow_system_fields = True
	for row in (tp.test_items or []):
		if row.stability_test_item == item_code:
			row.current_result = result_name
	tp.save(ignore_permissions=True)


def _clear_current_pointer(tp, item_code):
	_write_current_pointer(tp, item_code, None)


def _stability_test_item_for_standard_result(result, tp):
	"""按 HBOS Test Item 映射稳定性检验项目，并确认该项目属于时间点。"""
	rows = frappe.get_all(
		"HBOS Stability Test Item",
		filters={"base_test_item": result.test_item, "is_active": 1},
		fields=["name"], limit_page_length=0,
	)
	if not rows:
		frappe.throw("业务检验项目「{}」未配置稳定性检验项目映射，无法同步结果。"
					 .format(result.test_item))
	if len(rows) > 1:
		frappe.throw("业务检验项目「{}」存在多个稳定性项目映射，请先完成唯一映射。"
					 .format(result.test_item))
	stability_item = rows[0].name
	if not any(row.stability_test_item == stability_item for row in (tp.test_items or [])):
		frappe.throw("稳定性时间点「{}」未配置项目「{}」，无法同步业务结果。"
					 .format(tp.name, stability_item))
	return stability_item


def _standard_result_value(result):
	"""把业务检验结果转换为稳定性结果的 Data 值，保留原始文本优先级。"""
	if result.result_value is not None and result.result_value != "":
		return result.result_value
	return result.result_text or result.raw_value or ""


def _standard_result_date(result):
	"""稳定性结果的检测日期取业务结果提交时间的日期部分。"""
	stamp = result.submitted_at or _now()
	return frappe.utils.getdate(stamp)


def _ensure_manual_stability_result_allowed(res):
	"""业务结果投影只能由业务操作流转，阻止在稳定性页面重复录入/审批。"""
	if res.source_test_result:
		frappe.throw("该结果由业务检验结果 {} 自动同步，请在业务操作中录入、复核和批准。"
					 .format(res.source_test_result))


def _validate_stability_approval(standard, approver=None):
	"""稳定性投影批准必须走稳定性 QA 线，并满足职责分离。"""
	approver = approver or standard.approver or _user()
	roles = frappe.get_roles(approver)
	if not any(wf.action_allowed("approve_result", role, scope=RESULT_DOCTYPE)
			   for role in roles):
		frappe.throw("业务结果批准人「{}」不具备稳定性结果批准权限。".format(approver))
	if not standard.reviewer:
		frappe.throw("稳定性结果批准前必须记录复核人。")
	if standard.reviewer == approver:
		frappe.throw("稳定性结果批准人不得与复核人相同（SoD）。")


def _assert_independent_approver_exists(reviewer):
	"""复核后必须仍存在「他人」可批准，否则记录会永久停在「已复核」。

	业务 `approve_result` 与稳定性 `approve_result` 的**角色交集**（排除 System Manager）
	是本流程唯一可用的批准线；若复核人已占满该角色，复核后角色交集内再无他人可批，
	且业务状态机不允许 `已复核 -> 已提交`，修订逃生口同样走不通 —— 记录彻底卡死。
	"""
	business_roles = wf.ACTION_ROLES.get("approve_result", set())
	stability_roles = wf.SCOPED_ACTION_ROLES.get((RESULT_DOCTYPE, "approve_result"), set())
	eligible = set()
	for role in (business_roles & stability_roles) - {wf.ROLE_SYSTEM}:
		eligible.update(frappe.get_all(
			"Has Role", filters={"role": role, "parenttype": "User"},
			pluck="parent", limit_page_length=0))
	if [u for u in eligible if u != reviewer and frappe.db.get_value("User", u, "enabled")]:
		return
	frappe.throw(
		"稳定性取样样品的结果必须由他人批准：复核人「{}」是当前唯一具备批准权限的用户，"
		"复核后将无人可批准，且无法修订回退。请改由 Reviewer 复核。".format(reviewer))


def _validate_sync_timepoint(tp, audit=True):
	"""同步只允许非终止时间点；审计提交必须发生在业务源结果写入前。"""
	if tp.status in _SYNCABLE_TIMEPOINT_STATES:
		return
	message = "稳定性时间点「{}」当前为「{}」，禁止同步业务检验结果。".format(
		tp.name, tp.status)
	if audit:
		_audit_violation(TIMEPOINT_DOCTYPE, tp.name,
						 "业务结果同步被拒绝",
						 "{}（包括已取消时间点）".format(message))
	frappe.throw(message)


def _prepare_standard_sync_context(result_name, target_status=None, approver=None,
								   reviewer=None,
							   audit=True):
	"""同步前置校验，返回源结果、样品、锁定时间点和稳定性项目。"""
	standard = frappe.get_doc("HBOS Test Result", result_name)
	sample = frappe.get_doc("HBOS Sample", standard.sample)
	if not stb.is_stability_sample_source(sample.sample_source):
		return None
	if not sample.stability_timepoint:
		frappe.throw("稳定性样品 {} 未绑定稳定性时间点，无法同步结果。".format(sample.name))
	tp = _lock_row(TIMEPOINT_DOCTYPE, sample.stability_timepoint)
	_validate_sync_timepoint(tp, audit=audit)
	stability_item = _stability_test_item_for_standard_result(standard, tp)
	target = target_status or standard.result_status
	if target == stb.RESULT_REVIEWED:
		# 前置校验时 reviewer 尚未落库，取本次调用者（即将成为复核人）
		_assert_independent_approver_exists(reviewer or standard.reviewer or _user())
	if target == stb.RESULT_APPROVED:
		_validate_stability_approval(standard, approver=approver)
	return standard, sample, tp, stability_item


def validate_standard_test_result_sync(result_name, target_status=None, approver=None,
									   reviewer=None):
	"""业务结果写入前调用的同步准入校验，不创建稳定性投影。"""
	return _prepare_standard_sync_context(
		result_name, target_status=target_status, approver=approver,
		reviewer=reviewer, audit=True)


def sync_standard_test_result(result_name, target_status=None, supersedes_result_name=None):
	"""将业务 HBOS Test Result 幂等投影到稳定性结果与趋势数据。

	只有样品来源为稳定性且已绑定时间点时才执行；稳定性结果保存 source_test_result
	作为唯一幂等键，状态与版本随业务结果流转，趋势接口继续读取批准且当前的投影。
	"""
	context = _prepare_standard_sync_context(
		result_name, target_status=target_status, audit=False)
	if context is None:
		return None
	standard, sample, tp, stability_item = context
	if tp.status == stb.TP_DONE:
		_maybe_reopen_timepoint(tp)
		tp = _load(TIMEPOINT_DOCTYPE, tp.name)
	if tp.status == stb.TP_WAIT_TEST:
		_set_status(tp, stb.FLOW_STB_TIMEPOINT, stb.TP_TESTING)
		_audit_on(TIMEPOINT_DOCTYPE, "检测开始", tp.name,
				  action_text="业务检验结果同步触发检测开始")
	if tp.status == stb.TP_TESTING:
		tp.flags.allow_system_fields = True
		if not tp.test_by:
			tp.test_by = standard.analyst or _user()
		tp.save(ignore_permissions=True)
	stable_sample = frappe.get_doc(SAMPLE_DOCTYPE, tp.stability_sample)
	item = frappe.get_doc("HBOS Stability Test Item", stability_item)

	projection_name = frappe.db.get_value(RESULT_DOCTYPE,
		{"source_test_result": standard.name}, "name")
	if projection_name:
		res = _load(RESULT_DOCTYPE, projection_name)
	else:
		existing = _results_of_item(tp.name, stability_item)
		if supersedes_result_name:
			previous_name = frappe.db.get_value(RESULT_DOCTYPE,
				{"source_test_result": supersedes_result_name}, "name")
			if previous_name:
				previous = _load(RESULT_DOCTYPE, previous_name)
				if previous.status in stb.RESULT_INFLIGHT_STATES:
					previous.status = stb.RESULT_VOIDED
					previous.void_reason = "业务检验结果修订，旧投影作废"
					previous.save(ignore_permissions=True)
					_audit_on(RESULT_DOCTYPE, "结果作废", previous.name,
							  action_text="业务检验结果修订，旧稳定性投影退出在途")
			existing = _results_of_item(tp.name, stability_item)
		# 已批准结果是版本链中的历史/当前版本，允许业务修订生成新投影；
		# 仅未完成的在途结果阻止新的业务来源占用同一时间点项目。
		occupied = [row for row in existing if row.status in stb.RESULT_INFLIGHT_STATES]
		if occupied:
			frappe.throw("稳定性时间点「{}」项目「{}」已有结果（{}），业务结果不能覆盖。"
					 .format(tp.name, stability_item, occupied[0].name))
		revision_no = _next_revision_no(tp.name, stability_item)
		res = frappe.get_doc({
			"doctype": RESULT_DOCTYPE,
			"timepoint": tp.name,
			"stability_sample": stable_sample.name,
			"stability_test_item": stability_item,
			"source_test_result": standard.name,
			"result_value": _standard_result_value(standard),
			"unit": standard.unit or frappe.db.get_value(
				"HBOS Stability Product", stable_sample.stability_product, "default_uom"),
			"source": "自检",
			"is_zero_month": 1 if tp.is_zero_month else 0,
			"revision_no": revision_no,
			"result_version_key": stb.make_result_version_key(tp.name, stability_item, revision_no),
			"is_current": 0,
			"status": stb.RESULT_DRAFT,
			"analyst": standard.analyst or _user(),
			"test_date": _standard_result_date(standard),
		})
		res.flags.allow_system_fields = True
		_spec_ref, spec_version, method_version, test_method, spec_row = \
			_spec_context_for(stable_sample, stability_item)
		res.spec_version = spec_version
		res.method_version = method_version
		res.test_method = test_method
		res.item_snapshot = item.item_name
		if spec_row is not None:
			res.spec_limit = _limit_text_of(spec_row)
		baseline = _pick_baseline(stable_sample.name, stability_item, tp.condition_type)
		if baseline:
			res.result_baseline = baseline["value"]
			res.baseline_ref = baseline["ref"]
			res.baseline_doctype = baseline["doctype"]
			res.baseline_name = baseline["name"]
		_apply_judgement(res, item, spec_row, baseline, standard)
		res.insert(ignore_permissions=True)
		_audit_on(RESULT_DOCTYPE, "结果录入", res.name,
				  action_text="业务检验结果同步至稳定性结果",
				  new_value="source_test_result={} status={}".format(standard.name, standard.result_status))

	target = target_status or standard.result_status
	res.flags.allow_system_fields = True
	res.analyst = standard.analyst or res.analyst
	if target in (stb.RESULT_SUBMITTED, stb.RESULT_REVIEWED, stb.RESULT_APPROVED):
		res.test_date = _standard_result_date(standard)
		tp.flags.allow_system_fields = True
		tp.actual_test_date = res.test_date
		tp.save(ignore_permissions=True)
	if target == stb.RESULT_SUBMITTED:
		res.status = stb.RESULT_SUBMITTED
		res.submitted_by = standard.analyst or _user()
		res.submitted_at = standard.submitted_at or _now()
	elif target == stb.RESULT_REVIEWED:
		res.status = stb.RESULT_REVIEWED
		res.submitted_by = standard.analyst or res.submitted_by
		res.submitted_at = standard.submitted_at or res.submitted_at or _now()
		res.reviewed_by = standard.reviewer or _user()
		res.reviewed_at = standard.reviewed_at or _now()
	elif target == stb.RESULT_APPROVED:
		old_name = _current_result_of(tp.name, stability_item, exclude=res.name)
		if old_name:
			old = _load(RESULT_DOCTYPE, old_name)
			if old.status == stb.RESULT_APPROVED:
				mark_superseded(old.name)
				old = _load(RESULT_DOCTYPE, old.name)
			old.is_current = 0
			old.save(ignore_permissions=True)
		res.status = stb.RESULT_APPROVED
		res.is_current = 1
		res.submitted_by = standard.analyst or res.submitted_by
		res.submitted_at = standard.submitted_at or res.submitted_at or _now()
		res.reviewed_by = standard.reviewer or res.reviewed_by
		res.reviewed_at = standard.reviewed_at or res.reviewed_at or _now()
		res.approved_by = standard.approver or _user()
		res.approved_at = standard.approved_at or _now()
		res.save(ignore_permissions=True)
		_write_current_pointer(tp, stability_item, res.name)
		_audit_on(RESULT_DOCTYPE, "结果批准", res.name,
				  action_text="业务检验结果批准同步并切换稳定性生效指针",
				  new_value="source_test_result={}".format(standard.name))
		_maybe_complete_testing(tp)
		return {"name": res.name, "status": res.status, "is_current": 1}
	else:
		res.status = stb.RESULT_DRAFT
	res.save(ignore_permissions=True)
	return {"name": res.name, "status": res.status, "is_current": res.is_current}


# ---- 结果动作（方案 6.3.5） -----------------------------------------------

def _business_stability_items_for_timepoint(timepoint_name):
	"""返回已绑定业务样品覆盖的稳定性项目，仅用于项目粒度录入守卫。"""
	sample_names = frappe.get_all(
		"HBOS Sample", filters={"stability_timepoint": timepoint_name},
		pluck="name", limit_page_length=0)
	if not sample_names:
		return set()
	base_items = set()
	for sample_name in sample_names:
		sample = frappe.get_doc("HBOS Sample", sample_name)
		base_items.update(row.test_item for row in (sample.items or []) if row.test_item)
	if not base_items:
		return set()
	mappings = frappe.get_all(
		"HBOS Stability Test Item",
		filters={"base_test_item": ["in", sorted(base_items)]},
		fields=["name"], limit_page_length=0)
	return {row.name for row in mappings}

@frappe.whitelist()
def record_result(timepoint_name, stability_test_item, result_value, test_date=None,
				  unit=None, source="自检", remark=None):
	"""结果录入（→ 草稿）。仅 `Timepoint.status=检测中`；同一 (时间点, 项目) 无在途（方案 6.3.5）。"""
	_check_action("record_result", RESULT_DOCTYPE, timepoint_name)
	if result_value is None or str(result_value).strip() == "":
		frappe.throw("结果值必填。")
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		if tp.status != stb.TP_TESTING:
			_reject(TIMEPOINT_DOCTYPE, timepoint_name,
				"仅「检测中」的时间点可录入结果（当前：{}）。".format(tp.status),
				"非法状态：{} 调用 record_result".format(tp.status))
		if not frappe.db.exists("HBOS Stability Test Item", stability_test_item):
			frappe.throw("检验项目「{}」不存在。".format(stability_test_item))
		if not any(row.stability_test_item == stability_test_item
				   for row in (tp.test_items or [])):
			frappe.throw("检验项目「{}」不属于时间点「{}」。"
					 .format(stability_test_item, timepoint_name))
		covered_items = _business_stability_items_for_timepoint(timepoint_name)
		if stability_test_item in covered_items:
			frappe.throw("该时间点的业务检验样品已覆盖项目「{}」，请在业务操作中录入检验结果。"
					 .format(stability_test_item))
		inflight = [r for r in _results_of_item(tp.name, stability_test_item)
					if r.status in stb.RESULT_INFLIGHT_STATES]
		if inflight:
			frappe.throw("该项目已有在途结果（{}），须先处理后再录入。".format(inflight[0].name))

		sample = frappe.get_doc(SAMPLE_DOCTYPE, tp.stability_sample)
		revision_no = _next_revision_no(tp.name, stability_test_item)
		item = frappe.get_doc("HBOS Stability Test Item", stability_test_item)

		res = frappe.get_doc({
			"doctype": RESULT_DOCTYPE,
			"timepoint": tp.name,
			"stability_sample": sample.name,
			"stability_test_item": stability_test_item,
			"result_value": result_value,
			"unit": unit or (frappe.db.get_value("HBOS Stability Product",
												 sample.stability_product, "default_uom")),
			"source": source or "自检",
			"is_zero_month": 1 if tp.is_zero_month else 0,
			"revision_no": revision_no,
			"result_version_key": stb.make_result_version_key(
				tp.name, stability_test_item, revision_no),
			"is_current": 0,
			"status": stb.RESULT_DRAFT,
			"analyst": _user(),
			"test_date": test_date,
			"remark": remark,
		})
		res.flags.allow_system_fields = True
		_spec_ref, spec_version, method_version, test_method, spec_row = \
			_spec_context_for(sample, stability_test_item)
		res.spec_version = spec_version
		res.method_version = method_version
		res.test_method = test_method
		res.item_snapshot = item.item_name
		if spec_row is not None:
			res.spec_limit = _limit_text_of(spec_row)
		baseline = _pick_baseline(sample.name, stability_test_item, tp.condition_type)
		if baseline:
			res.result_baseline = baseline["value"]
			res.baseline_ref = baseline["ref"]
			res.baseline_doctype = baseline["doctype"]
			res.baseline_name = baseline["name"]
		sig, _basis = _apply_judgement(res, item, spec_row, baseline, None)
		res.insert(ignore_permissions=True)
		_audit_on(RESULT_DOCTYPE, "结果录入", res.name,
				  action_text="结果录入（v{}）".format(revision_no),
				  new_value="item={} result={}".format(stability_test_item, result_value))
		if sig:
			_audit_on(RESULT_DOCTYPE, "显著变化判定", res.name,
					  action_text="显著变化判定", new_value=res.significant_change_basis)
		_commit()
		return {"name": res.name, "status": res.status, "revision_no": revision_no,
				"is_significant_change": res.is_significant_change}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def submit_result(result_name, test_date=None):
	"""提交结果（草稿 → 已提交）。硬校验 #1–#3（方案 7.3）+ 快照一致性（7.7）。"""
	_check_action("submit_result", RESULT_DOCTYPE, result_name)
	try:
		res0 = frappe.get_doc(RESULT_DOCTYPE, result_name)
		_ensure_manual_stability_result_allowed(res0)
		tp = _lock_row(TIMEPOINT_DOCTYPE, res0.timepoint)
		res = _load(RESULT_DOCTYPE, result_name)
		if res.status != stb.RESULT_DRAFT:
			_reject(RESULT_DOCTYPE, result_name,
					"仅「草稿」可提交（当前：{}）。".format(res.status),
					"非法状态：{} 调用 submit_result".format(res.status))
		actual = test_date or res.test_date
		if not actual:
			frappe.throw("实际检测日期必填。")

		sample = frappe.get_doc(SAMPLE_DOCTYPE, tp.stability_sample)
		product = _product_of_sample(sample)
		effective, policy = _effective_test_due(tp, product)
		exempt = stb.zero_month_exempt(res.is_zero_month, res.source)
		ok, err = stb.check_test_dates(actual, tp.actual_sample_date, tp.plan_test_date,
									   effective, policy, exempt_zero_month=exempt)
		if not ok:
			frappe.throw(err)

		# 快照一致性（方案 7.7）：标准版本与限度须与来源链当前值一致
		_spec_ref, spec_version, _mv, _tm, row = _spec_context_for(sample, res.stability_test_item)
		if (spec_version or "") != (res.spec_version or ""):
			frappe.throw("结果的标准版本快照（{}）与来源链当前版本（{}）不一致，"
						 "请走变更流程后重录。".format(res.spec_version, spec_version))
		if row is not None and (_limit_text_of(row) or "") != (res.spec_limit or ""):
			frappe.throw("结果的限度快照（{}）与质量标准当前值（{}）不一致，请走变更流程后重录。".format(
				res.spec_limit, _limit_text_of(row)))

		res.flags.allow_system_fields = True
		res.test_date = actual
		res.status = stb.RESULT_SUBMITTED
		res.submitted_by = _user()
		res.submitted_at = _now()
		res.save(ignore_permissions=True)
		if not tp.actual_test_date:
			tp.flags.allow_system_fields = True
			tp.actual_test_date = actual
			tp.save(ignore_permissions=True)
		_audit_on(RESULT_DOCTYPE, "结果提交", res.name,
				  action_text="结果提交", new_value="test_date={}".format(actual))
		_commit()
		return {"name": res.name, "status": res.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def review_result(result_name):
	"""结果复核（已提交 → 已复核）。SoD：检测人 ≠ 复核人。"""
	_check_action("review_result", RESULT_DOCTYPE, result_name)
	try:
		res0 = frappe.get_doc(RESULT_DOCTYPE, result_name)
		_ensure_manual_stability_result_allowed(res0)
		_lock_row(TIMEPOINT_DOCTYPE, res0.timepoint)
		res = _load(RESULT_DOCTYPE, result_name)
		if res.status != stb.RESULT_SUBMITTED:
			_reject(RESULT_DOCTYPE, result_name,
					"仅「已提交」可复核（当前：{}）。".format(res.status),
					"非法状态：{} 调用 review_result".format(res.status))
		if res.analyst and res.analyst == _user():
			_audit_commit(RESULT_DOCTYPE, "SoD 拦截", res.name,
						  action_text="结果复核违反职责分离", reason="检测人同为 {}".format(res.analyst))
			frappe.throw("复核人不得为检测人（SoD，方案 6.4）。")
		res.flags.allow_system_fields = True
		res.status = stb.RESULT_REVIEWED
		res.reviewed_by = _user()
		res.reviewed_at = _now()
		res.save(ignore_permissions=True)
		_audit_on(RESULT_DOCTYPE, "结果复核", res.name, action_text="结果复核")
		_commit()
		return {"name": res.name, "status": res.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def return_result(result_name, reason):
	"""结果退回（已提交→草稿 / 已复核→已提交），原因必填。"""
	_check_action("return_result", RESULT_DOCTYPE, result_name)
	if not (reason or "").strip():
		frappe.throw("退回原因必填。")
	try:
		res0 = frappe.get_doc(RESULT_DOCTYPE, result_name)
		_ensure_manual_stability_result_allowed(res0)
		_lock_row(TIMEPOINT_DOCTYPE, res0.timepoint)
		res = _load(RESULT_DOCTYPE, result_name)
		if res.status == stb.RESULT_SUBMITTED:
			target = stb.RESULT_DRAFT
		elif res.status == stb.RESULT_REVIEWED:
			target = stb.RESULT_SUBMITTED
		else:
			_reject(RESULT_DOCTYPE, result_name,
					"仅「已提交 / 已复核」可退回（当前：{}）。".format(res.status),
					"非法状态：{} 调用 return_result".format(res.status))
		res.flags.allow_system_fields = True
		if not wf.can_transition(stb.FLOW_STB_RESULT, res.status, target):
			frappe.throw("非法状态流转：{} -> {}（结果）".format(res.status, target))
		res.status = target
		res.return_reason = reason
		res.save(ignore_permissions=True)
		_audit_on(RESULT_DOCTYPE, "结果退回", res.name,
				  action_text="结果退回", reason=reason, new_value=target)
		_commit()
		return {"name": res.name, "status": res.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def approve_result(result_name):
	"""结果批准（已复核 → 已批准）并**同事务六步切换生效指针**（方案 7.7 / 门禁 11、15）。

	六步：(a) 旧版 已批准→已修订 (b) 旧版 is_current 1→0 (c) 新版 已复核→已批准
	(d) 新版 is_current 0→1 (e) 回写 Timepoint Item.current_result (f) commit。
	首版（无旧版）只走新版侧。
	"""
	_check_action("approve_result", RESULT_DOCTYPE, result_name)
	try:
		res0 = frappe.get_doc(RESULT_DOCTYPE, result_name)
		_ensure_manual_stability_result_allowed(res0)
		tp = _lock_row(TIMEPOINT_DOCTYPE, res0.timepoint)     # 锁 Timepoint（方案 7.8）
		res = _load(RESULT_DOCTYPE, result_name)               # 锁内重读
		if res.status != stb.RESULT_REVIEWED:
			_reject(RESULT_DOCTYPE, result_name,
					"仅「已复核」可批准（当前：{}）。".format(res.status),
					"非法状态：{} 调用 approve_result".format(res.status))
		if not res.reviewed_by:
			frappe.throw("结果须先复核才能批准。")
		if res.reviewed_by == _user():
			_audit_commit(RESULT_DOCTYPE, "SoD 拦截", res.name,
						  action_text="结果批准违反职责分离", reason="复核人同为 {}".format(res.reviewed_by))
			frappe.throw("批准人不得为复核人（SoD，方案 6.4）。")

		old_name = _current_result_of(tp.name, res.stability_test_item, exclude=res.name)
		if old_name:
			old = _load(RESULT_DOCTYPE, old_name)
			if old.status == stb.RESULT_APPROVED:          # (a) 幂等：已是「已修订」则跳过
				mark_superseded(old_name)                  # 内部子步骤（含审计「结果被取代」）
				old = _load(RESULT_DOCTYPE, old_name)      # mark_superseded 已独立落库，重读防脏覆盖
			old.is_current = 0                             # (b) 须显式落库，否则残留「已修订+current=1」第三态
			old.save(ignore_permissions=True)

		res.flags.allow_system_fields = True
		res.status = stb.RESULT_APPROVED                   # (c)
		res.is_current = 1                                 # (d)
		res.approved_by = _user()
		res.approved_at = _now()
		res.save(ignore_permissions=True)
		_write_current_pointer(tp, res.stability_test_item, res.name)   # (e)
		_audit_on(RESULT_DOCTYPE, "结果批准", res.name,
				  action_text="结果批准（含生效切换）",
				  new_value="v{} current=1{}".format(res.revision_no,
													 " 取代 " + old_name if old_name else ""))
		_maybe_complete_testing(tp)                        # 全部必检项目获批 → 自动完成检测
		_commit()                                          # (f)
		return {"name": res.name, "status": res.status, "is_current": 1,
				"superseded": old_name}
	except Exception:
		_rollback()
		raise


def mark_superseded(result_name):
	"""**系统内部子步骤**（非公开入口）：旧版 已批准 → 已修订（方案 6.3.5 P2-4 rev11）。

	幂等：仅当旧版 `status=已批准` 时才置「已修订」，否则跳过（不重复写审计）。
	仅由 `approve_result` 在同一事务内调用。
	"""
	_check_action("mark_superseded", RESULT_DOCTYPE, result_name, system=True)
	old = _load(RESULT_DOCTYPE, result_name)
	if old.status != stb.RESULT_APPROVED:
		return {"name": old.name, "status": old.status, "changed": False}
	old.flags.allow_system_fields = True
	old.status = stb.RESULT_REVISED
	old.save(ignore_permissions=True)
	_audit_on(RESULT_DOCTYPE, "结果被取代", old.name, action_text="结果被新版取代")
	return {"name": old.name, "status": old.status, "changed": True}


@frappe.whitelist()
def revise_result(result_name):
	"""结果修订（准入行）：**不改旧版状态、不碰指针**，仅新建一条草稿（方案 7.7 P0-1）。"""
	_check_action("revise_result", RESULT_DOCTYPE, result_name)
	try:
		old0 = frappe.get_doc(RESULT_DOCTYPE, result_name)
		_ensure_manual_stability_result_allowed(old0)
		tp = _lock_row(TIMEPOINT_DOCTYPE, old0.timepoint)
		old = frappe.get_doc(RESULT_DOCTYPE, result_name)
		if old.status not in (stb.RESULT_APPROVED, stb.RESULT_VOIDED):
			frappe.throw("仅「已批准 / 已作废」的结果可修订（当前：{}）。".format(old.status))
		inflight = [r for r in _results_of_item(tp.name, old.stability_test_item)
					if r.status in stb.RESULT_INFLIGHT_STATES]
		if inflight:
			frappe.throw("该项目已有在途结果（{}），须先处理后再修订。".format(inflight[0].name))

		sample = frappe.get_doc(SAMPLE_DOCTYPE, tp.stability_sample)
		revision_no = _next_revision_no(tp.name, old.stability_test_item)
		item = frappe.get_doc("HBOS Stability Test Item", old.stability_test_item)
		res = frappe.get_doc({
			"doctype": RESULT_DOCTYPE,
			"timepoint": tp.name,
			"stability_sample": sample.name,
			"stability_test_item": old.stability_test_item,
			"result_value": old.result_value,
			"unit": old.unit,
			"source": old.source,
			"is_zero_month": old.is_zero_month,
			"revision_no": revision_no,
			"supersedes": old.name,
			"result_version_key": stb.make_result_version_key(
				tp.name, old.stability_test_item, revision_no),
			"spec_version": old.spec_version,
			"spec_limit": old.spec_limit,
			"test_method": old.test_method,
			"method_version": old.method_version,
			"item_snapshot": old.item_snapshot,
			"analyst": _user(),
			"test_date": old.test_date,
			"is_current": 0,
			"status": stb.RESULT_DRAFT,
		})
		res.flags.allow_system_fields = True
		baseline = _pick_baseline(sample.name, old.stability_test_item, tp.condition_type)
		_spec_ref, _sv, _mv, _tm, spec_row = _spec_context_for(sample, old.stability_test_item)
		if baseline:
			res.result_baseline = baseline["value"]
			res.baseline_ref = baseline["ref"]
			res.baseline_doctype = baseline["doctype"]
			res.baseline_name = baseline["name"]
		_apply_judgement(res, item, spec_row, baseline, None)
		res.insert(ignore_permissions=True)
		_audit_on(RESULT_DOCTYPE, "结果修订", res.name,
				  action_text="结果修订（新建修订件）",
				  old_value=old.name, new_value="v{}".format(revision_no))
		_commit()
		return {"name": res.name, "status": res.status, "revision_no": revision_no}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def void_result(result_name, reason):
	"""结果作废（草稿/已提交/已复核/已批准 → 已作废）。

	生效件作废时**同事务**清 `is_current` + 清指针 + 写 `生效结果作废` 审计；
	再按**必检项目粒度**判定是否重开时间点（方案 6.3.5 / 门禁 19）。
	"""
	_check_action("void_result", RESULT_DOCTYPE, result_name)
	if not (reason or "").strip():
		frappe.throw("作废原因必填。")
	try:
		res0 = frappe.get_doc(RESULT_DOCTYPE, result_name)
		_ensure_manual_stability_result_allowed(res0)
		tp = _lock_row(TIMEPOINT_DOCTYPE, res0.timepoint)
		res = _load(RESULT_DOCTYPE, result_name)
		if res.status not in (stb.RESULT_DRAFT, stb.RESULT_SUBMITTED,
							  stb.RESULT_REVIEWED, stb.RESULT_APPROVED):
			_reject(RESULT_DOCTYPE, result_name,
					"当前状态（{}）不可作废。".format(res.status),
					"非法状态：{} 调用 void_result".format(res.status))
		was_current = int(res.is_current or 0) == 1
		res.flags.allow_system_fields = True
		res.status = stb.RESULT_VOIDED
		res.void_reason = reason
		if was_current:
			res.is_current = 0
		res.save(ignore_permissions=True)
		_audit_on(RESULT_DOCTYPE, "结果作废", res.name,
				  action_text="结果作废", reason=reason)
		if was_current:
			_clear_current_pointer(tp, res.stability_test_item)
			_audit_on(RESULT_DOCTYPE, "生效结果作废", res.name,
					  action_text="生效结果作废并清空指针", reason=reason)
			_maybe_reopen_timepoint(tp)
		_commit()
		return {"name": res.name, "status": res.status, "was_current": was_current}
	except Exception:
		_rollback()
		raise


def _maybe_reopen_timepoint(tp):
	"""按必检项目粒度判定重开（方案 6.3.5 / P1-1 rev11）：

	该时间点**有任一必检项目当前无生效结果**即需回退；**仅当 status=已完成 才调用**
	`reopen_timepoint`，若已是「检测中」则保持原状态、仅记审计（不产生非法转移）。
	"""
	required = [r.stability_test_item for r in (tp.test_items or [])
				if r.is_required and r.stability_test_item]
	if not required:
		return
	missing = [code for code in required
			   if not frappe.db.exists(RESULT_DOCTYPE, {
				   "timepoint": tp.name, "stability_test_item": code,
				   "is_current": 1, "status": stb.RESULT_APPROVED})]
	if not missing:
		return
	if tp.status == stb.TP_DONE:
		reopen_timepoint(tp.name)
	else:
		_audit_on(TIMEPOINT_DOCTYPE, "结果作废", tp.name,
				  action_text="结果作废（时间点本已可重录）",
				  new_value="status={} missing={}".format(tp.status, " / ".join(missing)))


# ---- 趋势评估（方案 6.3.4 准入行，R8B 遗漏补入） --------------------------

@frappe.whitelist()
def eval_trend(timepoint_name, conclusion, remark=None):
	"""趋势评估（状态不变，准入动作；方案 6.3.4）。"""
	_check_action("eval_trend", TIMEPOINT_DOCTYPE, timepoint_name)
	if conclusion not in ("正常", "超趋势"):
		frappe.throw("趋势结论必须是「正常」或「超趋势」。")
	try:
		tp = _lock_row(TIMEPOINT_DOCTYPE, timepoint_name)
		tp.flags.allow_system_fields = True
		tp.eval_date = _today()
		tp.evaluator = _user()
		tp.trend_conclusion = conclusion
		tp.oot_ref = remark
		tp.save(ignore_permissions=True)
		_audit_on(TIMEPOINT_DOCTYPE, "趋势评估", tp.name,
				  action_text="趋势评估", new_value=conclusion)
		_commit()
		return {"name": tp.name, "trend_conclusion": conclusion}
	except Exception:
		_rollback()
		raise


# ---- 报告（方案 6.3.6 / 5.4.2 / 7.6） -------------------------------------

def _validity_inputs(product_name, sample_name=None):
	"""外推助手输入（方案 7.6）——**全部由系统从已批准结果推导**，并随建议一并返回以便追溯。

	口径（方案未逐条给出判定阈值，此处为显式化实现，见主文档「外推助手口径」）：
	- `x_months`：该产品**长期条件**已批准结果中时间点值（月）的最大值（覆盖时长）
	- `sig_change_3m` / `sig_change_6m`：加速条件 3 / 6 月点是否存在显著变化
	- `intermediate_ok`：存在中间条件已批准结果且**均无显著变化**（无中间条件视为不充分）
	- `correlated`：长期已批准结果 ≥ 3 点且趋势线 R² ≥ 0.8
	- `long_term_sufficient`：长期已批准结果 ≥ 4 点且覆盖 ≥ 12 月
	- `refrigerated`：长期储存条件描述含冷藏关键词（冷藏 / 2~8 / 5±3）
	"""
	rows = frappe.get_all(
		RESULT_DOCTYPE,
		filters={"status": stb.RESULT_APPROVED, "is_current": 1},
		fields=["name", "timepoint", "result_value", "is_significant_change"],
		limit_page_length=0)
	tp_ids = sorted({r.timepoint for r in rows})
	tps = {}
	if tp_ids:
		for t in frappe.get_all(TIMEPOINT_DOCTYPE, filters={"name": ["in", tp_ids]},
								fields=["name", "stability_sample", "condition_type",
										"time_point_value", "time_point_unit"],
								limit_page_length=0):
			tps[t.name] = t
	sample_names = sorted({t.stability_sample for t in tps.values() if t.get("stability_sample")})
	my_samples = set()
	if sample_names:
		for s in frappe.get_all(SAMPLE_DOCTYPE, filters={"name": ["in", sample_names]},
								fields=["name", "stability_product"], limit_page_length=0):
			if s.stability_product == product_name:
				my_samples.add(s.name)
	if sample_name:
		my_samples &= {sample_name}

	long_pts, acc_sig = [], {}
	inter_pts = []
	for r in rows:
		t = tps.get(r.timepoint)
		if not t or t.stability_sample not in my_samples:
			continue
		if t.condition_type == "长期" and t.time_point_unit == "月":
			long_pts.append((int(t.time_point_value or 0), r.result_value))
		elif t.condition_type == "加速" and t.time_point_unit == "月":
			acc_sig[int(t.time_point_value or 0)] = bool(r.is_significant_change)
		elif t.condition_type == "中间":
			inter_pts.append(bool(r.is_significant_change))

	long_pts.sort()
	x_months = max([p[0] for p in long_pts], default=0)
	trend = stb.fit_trend_line(long_pts)
	correlated = len(long_pts) >= 3 and trend is not None and trend.get("r2", 0) >= 0.8
	long_term_sufficient = len(long_pts) >= 4 and x_months >= 12

	refrigerated = False
	cond = frappe.db.get_value("HBOS Stability Product", product_name, "storage_cond_long")
	if cond:
		desc = frappe.db.get_value("HBOS Stability Condition", cond, "description") or ""
		refrigerated = any(k in desc for k in ("冷藏", "2~8", "2-8", "5±3"))

	return {
		"x_months": x_months,
		"long_points": len(long_pts),
		"sig_change_3m": bool(acc_sig.get(3)),
		"sig_change_6m": bool(acc_sig.get(6)),
		"intermediate_ok": bool(inter_pts) and not any(inter_pts),
		"correlated": correlated,
		"long_term_sufficient": long_term_sufficient,
		"refrigerated": refrigerated,
		"trend": trend,
	}


@frappe.whitelist()
def get_stability_validity_advice(stability_product, sample=None):
	"""ICH Q1E 有效期外推建议（只读预览）。返回输入口径 + 建议分支 + 依据（方案 7.6）。"""
	_check_action("get_stability_validity_advice", REPORT_DOCTYPE, stability_product)
	inputs = _validity_inputs(stability_product, sample)
	months, branch, basis = stb.advise_validity(
		inputs["x_months"], inputs["sig_change_3m"], inputs["sig_change_6m"],
		inputs["intermediate_ok"], inputs["correlated"],
		inputs["long_term_sufficient"], inputs["refrigerated"])
	return {"inputs": inputs, "advised_months": months, "branch": branch, "basis": basis}


def _next_report_seq(product, year, client_code):
	"""专项报告序号：锁 `HBOS Stability Product` 产品行取 max+1（方案 5.4.2 P1-4）。"""
	frappe.db.get_value("HBOS Stability Product", product, "name", for_update=True)
	rows = frappe.get_all(
		REPORT_DOCTYPE,
		filters={"stability_product": product, "year": int(year or 0),
				 "client_code": client_code},
		pluck="seq", limit_page_length=0)
	return (max([int(s or 0) for s in rows]) + 1) if rows else 1


@frappe.whitelist()
def create_stability_report(report_type, stability_product, year=None,
							source_doctype=None, source_name=None, customer=None,
							study_scope=None, period_from=None, period_to=None,
							storage_conds=None, spec_ref=None, client_requirement=None):
	"""报告建档（草稿）。`proposed_validity_*` 由**服务端计算并写入**（方案 7.6）。"""
	_check_action("create_stability_report", REPORT_DOCTYPE, stability_product)
	try:
		product = frappe.get_doc("HBOS Stability Product", stability_product)
		if report_type == stb.REPORT_TYPE_SPECIAL and not customer:
			frappe.throw("专项报告必须指定客户。")
		client_code = customer or None
		if customer:
			ok, err = stb.check_customer_code(customer)
			if not ok:
				frappe.throw(err)
		# 范围校验（方案 5.4.2 / rev14 P2-2）：非专项报告 customer/client_code/seq 必须为空
		scope_ok, scope_err = stb.check_report_scope(
			report_type, source_doctype, customer or None, client_code, None)
		if not scope_ok and "不得填写客户" in scope_err:
			frappe.throw(scope_err)
		# 常规报告：同产品同年度同类型同来源唯一
		seq = _next_report_seq(stability_product, year, client_code) \
			if report_type == stb.REPORT_TYPE_SPECIAL else None
		key = stb.make_report_period_key(product.product_code, year, report_type,
										 source_doctype, source_name, client_code, seq)

		inputs = _validity_inputs(stability_product)
		months, _branch, basis = stb.advise_validity(
			inputs["x_months"], inputs["sig_change_3m"], inputs["sig_change_6m"],
			inputs["intermediate_ok"], inputs["correlated"],
			inputs["long_term_sufficient"], inputs["refrigerated"])
		proposed_date = stb.add_time_point(period_from or _today(), months, "月") if months else None

		doc = frappe.get_doc({
			"doctype": REPORT_DOCTYPE,
			"report_type": report_type,
			"stability_product": stability_product,
			"year": int(year) if year else None,
			"source_doctype": source_doctype or None,
			"source_name": source_name or None,
			"customer": customer or None,
			"seq": seq,
			"report_period_key": key,
			"study_scope": study_scope,
			"period_from": period_from,
			"period_to": period_to,
			"storage_conds": storage_conds,
			"spec_ref": spec_ref,
			"client_requirement": client_requirement,
			"proposed_validity_months": months,
			"proposed_validity_date": proposed_date,
			"proposed_validity_type": "有效期",
			"proposed_validity_basis": "{}（{}）｜输入：X={}月 长期点={} 3月显著={} 6月显著={} "
									   "中间充分={} 相关支持={} 长期充分={} 冷藏={}".format(
										   _branch, basis, inputs["x_months"], inputs["long_points"],
										   inputs["sig_change_3m"], inputs["sig_change_6m"],
										   inputs["intermediate_ok"], inputs["correlated"],
										   inputs["long_term_sufficient"], inputs["refrigerated"]),
			"drafted_by": _user(),
			"draft_date": _today(),
			"status": stb.REPORT_DRAFT,
		})
		doc.flags.allow_system_fields = True
		for _attempt in range(3):     # `report_period_key` unique 兜底，冲突时有上限重试
			try:
				doc.insert(ignore_permissions=True)
				break
			except Exception as exc:
				if "1062" not in str(exc) and "Duplicate" not in str(exc):
					raise
				_rollback()
				if report_type != stb.REPORT_TYPE_SPECIAL:
					raise
				seq = _next_report_seq(stability_product, year, client_code)
				doc.seq = seq
				doc.report_period_key = stb.make_report_period_key(
					product.product_code, year, report_type, source_doctype, source_name,
					client_code, seq)
		else:
			frappe.throw("报告防重键冲突且重试 3 次仍未成功，请手工核查序号后重试。")
		_audit_on(REPORT_DOCTYPE, "创建", doc.name,
				  action_text="创建稳定性报告草稿",
				  new_value="type={} key={}".format(report_type, doc.report_period_key))
		_commit()
		return {"name": doc.name, "status": doc.status, "seq": doc.seq,
				"advised_months": months, "basis": basis}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def save_report_draft(report_name, conclusion=None, trend_analysis=None,
					  impurity_profile=None, trend_chart_ref=None):
	"""报告草稿内容保存（准入动作，状态不变）：评价与结论 / 趋势分析 / 杂质概况 / 趋势图引用。

	这四项在建档（`create_stability_report`）时不收——报告要素随分析推进逐步填写；而
	LIMS 角色对 Report 只读（方案 8.6），故必须经本方法与 `_load` 写入。`submit_report`
	的前置「报告评价与结论必填」（方案 4.6.4）依赖本方法先落 `conclusion`。
	"""
	_check_action("save_report_draft", REPORT_DOCTYPE, report_name)
	try:
		doc = _load(REPORT_DOCTYPE, report_name)
		if doc.status != stb.REPORT_DRAFT:
			_reject(REPORT_DOCTYPE, report_name,
					"仅「草稿」可修改报告内容（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 save_report_draft".format(doc.status))
		changed = []
		for field, value in (("conclusion", conclusion),
							 ("trend_analysis", trend_analysis),
							 ("impurity_profile", impurity_profile),
							 ("trend_chart_ref", trend_chart_ref)):
			if value is None:
				continue
			doc.set(field, value)
			changed.append(field)
		if not changed:
			frappe.throw("未提供任何可保存字段。")
		doc.save(ignore_permissions=True)
		_audit_on(REPORT_DOCTYPE, "报告起草", doc.name,
				  action_text="保存报告草稿内容", new_value=" / ".join(changed))
		_commit()
		return {"name": doc.name, "status": doc.status, "fields": changed}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def submit_report(report_name):
	"""报告提交（草稿 → 待QA审核）。"""
	_check_action("submit_report", REPORT_DOCTYPE, report_name)
	try:
		doc = _load(REPORT_DOCTYPE, report_name)
		if doc.status != stb.REPORT_DRAFT:
			_reject(REPORT_DOCTYPE, report_name,
					"仅「草稿」可提交（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 submit_report".format(doc.status))
		if not (doc.conclusion or "").strip():
			frappe.throw("报告评价与结论必填（方案 4.6.4 报告要素完整）。")
		_set_status(doc, stb.FLOW_STB_REPORT, stb.REPORT_WAIT_QA)
		doc.save(ignore_permissions=True)
		_audit_on(REPORT_DOCTYPE, "报告起草提交", doc.name,
				  action_text="报告提交", new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def review_report(report_name):
	"""报告 QA 审核记录（状态不变，准入动作）。"""
	_check_action("review_report", REPORT_DOCTYPE, report_name)
	try:
		doc = _load(REPORT_DOCTYPE, report_name)
		if doc.status != stb.REPORT_WAIT_QA:
			frappe.throw("仅「待QA审核」可记录审核（当前：{}）。".format(doc.status))
		doc.qa_review_by = _user()
		doc.qa_review_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on(REPORT_DOCTYPE, "报告审核", doc.name,
				  action_text="报告 QA 审核记录", new_value=doc.qa_review_by)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def approve_report(report_name, final_validity_months=None, final_validity_date=None,
				   final_validity_type=None):
	"""报告批准（待QA审核 → 已批准）并确定有效期（方案 6.3.6 三条硬前置）。"""
	_check_action("approve_report", REPORT_DOCTYPE, report_name)
	try:
		doc = _load(REPORT_DOCTYPE, report_name)
		if doc.status != stb.REPORT_WAIT_QA:
			_reject(REPORT_DOCTYPE, report_name,
					"仅「待QA审核」可批准（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 approve_report".format(doc.status))
		if not doc.qa_review_by or not doc.qa_review_date:
			frappe.throw("报告须先完成 QA 审核（review_report）才能批准。")
		if doc.qa_review_by == _user():
			_audit_commit(REPORT_DOCTYPE, "SoD 拦截", doc.name,
						  action_text="报告批准违反职责分离", reason="审核人同为 {}".format(doc.qa_review_by))
			frappe.throw("报告批准人不得为审核人（SoD，方案 6.4）。")
		months = final_validity_months or doc.final_validity_months
		date = final_validity_date or doc.final_validity_date
		vtype = final_validity_type or doc.final_validity_type
		if not months or not date or not vtype:
			frappe.throw("批准即确定有效期：QA 判定有效期（月数 / 至 / 类型）三项必填。")
		_set_status(doc, stb.FLOW_STB_REPORT, stb.REPORT_APPROVED)
		doc.final_validity_months = int(months)
		doc.final_validity_date = date
		doc.final_validity_type = vtype
		doc.qa_approve_by = _user()
		doc.approve_date = _today()
		doc.save(ignore_permissions=True)
		_audit_on(REPORT_DOCTYPE, "报告批准", doc.name,
				  action_text="报告批准并确定有效期",
				  new_value="{} {} 至 {}".format(vtype, months, date))
		_audit_on(REPORT_DOCTYPE, "有效期判定", doc.name,
				  action_text="QA 判定有效期",
				  old_value="建议 {} 月".format(doc.proposed_validity_months or "—"),
				  new_value="{} 月".format(months))
		_commit()
		return {"name": doc.name, "status": doc.status, "final_validity_months": doc.final_validity_months,
				"final_validity_date": str(doc.final_validity_date)}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def reject_report(report_name, reason):
	"""报告驳回（待QA审核 → 已驳回），原因必填。"""
	_check_action("reject_report", REPORT_DOCTYPE, report_name)
	if not (reason or "").strip():
		frappe.throw("驳回原因必填。")
	try:
		doc = _load(REPORT_DOCTYPE, report_name)
		if doc.status != stb.REPORT_WAIT_QA:
			_reject(REPORT_DOCTYPE, report_name,
					"仅「待QA审核」可驳回（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 reject_report".format(doc.status))
		_set_status(doc, stb.FLOW_STB_REPORT, stb.REPORT_REJECTED)
		doc.reject_reason = reason
		doc.save(ignore_permissions=True)
		_audit_on(REPORT_DOCTYPE, "驳回", doc.name,
				  action_text="报告驳回", reason=reason, new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def void_report(report_name, reason):
	"""报告作废（草稿 / 已批准 → 已作废；QP / Manager，原因必填）。"""
	_check_action("void_report", REPORT_DOCTYPE, report_name)
	if not (reason or "").strip():
		frappe.throw("作废原因必填。")
	try:
		doc = _load(REPORT_DOCTYPE, report_name)
		if doc.status not in (stb.REPORT_DRAFT, stb.REPORT_APPROVED):
			_reject(REPORT_DOCTYPE, report_name,
					"仅「草稿 / 已批准」可作废（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 void_report".format(doc.status))
		_set_status(doc, stb.FLOW_STB_REPORT, stb.REPORT_VOIDED)
		doc.void_reason = reason
		doc.save(ignore_permissions=True)
		_audit_on(REPORT_DOCTYPE, "报告作废", doc.name,
				  action_text="报告作废", reason=reason, new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


# ---- 结果与报告的只读接口（供 R8I 前端与报表） ----------------------------

@frappe.whitelist()
def get_stability_results(timepoint=None, stability_sample=None, stability_test_item=None,
						  status=None, limit=300):
	"""结果台账（按时间点 / 样品 / 项目筛选）。"""
	_check_action("get_stability_results", RESULT_DOCTYPE, timepoint or stability_sample or "-")
	filters = {}
	if timepoint:
		filters["timepoint"] = timepoint
	if stability_sample:
		filters["stability_sample"] = stability_sample
	if stability_test_item:
		filters["stability_test_item"] = stability_test_item
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		RESULT_DOCTYPE, filters=filters,
		fields=["name", "timepoint", "stability_sample", "stability_test_item", "item_snapshot",
				"result_value", "unit", "is_qualified", "is_significant_change",
				"significant_change_basis", "result_baseline", "baseline_ref",
				"baseline_doctype", "baseline_name", "is_zero_month", "source",
				"source_test_result",
				"revision_no", "is_current", "status", "analyst", "test_date",
				"submitted_by", "submitted_at", "reviewed_by", "reviewed_at",
				"approved_by", "approved_at", "return_reason", "void_reason",
				"spec_limit", "spec_version", "method_version", "test_method",
				"oos_flag", "oot_flag", "result_version_key", "supersedes"],
		order_by="creation desc", limit_page_length=int(limit))
	return {"rows": rows}


@frappe.whitelist()
def get_stability_result_detail(result_name):
	"""结果详情（含同 (时间点, 项目) 的**修订链**）。"""
	_check_action("get_stability_result_detail", RESULT_DOCTYPE, result_name)
	doc = frappe.get_doc(RESULT_DOCTYPE, result_name)
	chain = frappe.get_all(
		RESULT_DOCTYPE,
		filters={"timepoint": doc.timepoint, "stability_test_item": doc.stability_test_item},
		fields=["name", "revision_no", "status", "is_current", "result_value",
				"supersedes", "approved_at", "void_reason"],
		order_by="revision_no asc", limit_page_length=0)
	return {
		"name": doc.name,
		"timepoint": doc.timepoint,
		"stability_sample": doc.stability_sample,
		"stability_test_item": doc.stability_test_item,
		"item_snapshot": doc.item_snapshot,
		"result_value": doc.result_value,
		"unit": doc.unit,
		"is_qualified": doc.is_qualified,
		"is_significant_change": doc.is_significant_change,
		"significant_change_basis": doc.significant_change_basis,
		"result_baseline": doc.result_baseline,
		"baseline_ref": doc.baseline_ref,
		"baseline_doctype": doc.baseline_doctype,
		"baseline_name": doc.baseline_name,
		"is_zero_month": doc.is_zero_month,
		"source": doc.source,
		"source_test_result": doc.source_test_result,
		"revision_no": doc.revision_no,
		"is_current": doc.is_current,
		"status": doc.status,
		"spec_limit": doc.spec_limit,
		"spec_version": doc.spec_version,
		"test_method": doc.test_method,
		"method_version": doc.method_version,
		"analyst": doc.analyst,
		"test_date": doc.test_date,
		"submitted_by": doc.submitted_by,
		"submitted_at": doc.submitted_at,
		"reviewed_by": doc.reviewed_by,
		"reviewed_at": doc.reviewed_at,
		"approved_by": doc.approved_by,
		"approved_at": doc.approved_at,
		"return_reason": doc.return_reason,
		"void_reason": doc.void_reason,
		"oos_flag": doc.oos_flag,
		"oot_flag": doc.oot_flag,
		"revision_chain": chain,
	}


@frappe.whitelist()
def get_stability_trend(stability_product, stability_test_item, condition_type=None,
						sample=None):
	"""稳定性趋势图数据（方案 7.5）：时间点序列 + 规格限 + 线性趋势线。

	**只返回规格限、折线与趋势线拟合参数；不计算统计控制限**（`SOP-QA-2-00-005` 口径待 QA 确认）。
	取数一律 `is_current=1 且 status=已批准`。
	"""
	_check_action("get_stability_trend", RESULT_DOCTYPE, stability_product)
	q = frappe.get_all(SAMPLE_DOCTYPE, filters={"stability_product": stability_product},
					   fields=["name"], limit_page_length=0)
	sample_names = [s.name for s in q]
	if sample:
		sample_names = [n for n in sample_names if n == sample]
	series = []
	if sample_names:
		rows = frappe.get_all(
			RESULT_DOCTYPE,
			filters={"stability_sample": ["in", sample_names],
					 "stability_test_item": stability_test_item,
					 "status": stb.RESULT_APPROVED, "is_current": 1},
			fields=["name", "timepoint", "result_value", "unit", "is_significant_change",
					"significant_change_basis", "spec_limit", "spec_version"],
			limit_page_length=0)
		tp_ids = sorted({r.timepoint for r in rows})
		tps = {}
		if tp_ids:
			for t in frappe.get_all(TIMEPOINT_DOCTYPE, filters={"name": ["in", tp_ids]},
									fields=["name", "condition_type", "time_point_value",
											"time_point_unit", "plan_sample_date"],
									limit_page_length=0):
				tps[t.name] = t
		for r in rows:
			t = tps.get(r.timepoint)
			if not t:
				continue
			if condition_type and t.condition_type != condition_type:
				continue
			if t.time_point_unit != "月":
				continue
			series.append({
				"name": r.name,
				"timepoint": r.timepoint,
				"x": int(t.time_point_value or 0),
				"label": "{}月".format(int(t.time_point_value or 0)),
				"y": _to_float(r.result_value),
				"result_value": _to_float(r.result_value),
				"status": r.status,
				"is_current": r.is_current,
				"raw": r.result_value,
				"unit": r.unit,
				"condition_type": t.condition_type,
				"plan_sample_date": t.plan_sample_date,
				"is_significant_change": r.is_significant_change,
				"significant_change_basis": r.significant_change_basis,
				"spec_limit": r.spec_limit,
				"spec_version": r.spec_version,
			})
		series.sort(key=lambda x: x["x"])

	# 规格限：优先从来源链解析结构化限度；文本快照取最新一条生效结果
	spec_limit_text = series[-1]["spec_limit"] if series else None
	spec_version = series[-1]["spec_version"] if series else None
	limits_type, lower, upper = None, None, None
	resolved = _resolve_spec_limits(stability_product, stability_test_item)
	if resolved:
		limits_type, lower, upper = resolved

	return {
		"product": stability_product,
		"stability_test_item": stability_test_item,
		"condition_type": condition_type,
		"series": series,
		"spec": {"limits_type": limits_type, "lower": lower, "upper": upper,
				 "text": spec_limit_text, "version": spec_version},
		"trend_line": stb.fit_trend_line([(p["x"], p["y"]) for p in series if p["y"] is not None]),
		"note": "仅规格限 + 折线 + 线性趋势线；统计控制限口径（SOP-QA-2-00-005）待 QA 确认前不计算、不展示",
	}


def _to_float(value):
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def _resolve_spec_limits(stability_product, stability_test_item):
	"""从该产品任一已批准结果的来源链解析规格限度（结构化）。"""
	sample = frappe.get_all(SAMPLE_DOCTYPE, filters={"stability_product": stability_product},
							pluck="name", limit_page_length=1)
	if not sample:
		return None
	sample_doc = frappe.get_doc(SAMPLE_DOCTYPE, sample[0])
	src = _source_doc_of_sample(sample_doc)
	if src is None:
		return None
	row = _spec_row_for(src.spec_ref, stability_test_item)
	if row is None:
		return None
	return row.limits_type, row.lower_limit, row.upper_limit


@frappe.whitelist()
def get_stability_reports(report_type=None, status=None, keyword=None, limit=200):
	"""稳定性报告台账。"""
	_check_action("get_stability_reports", REPORT_DOCTYPE, "-")
	filters = {}
	if report_type:
		filters["report_type"] = report_type
	if status:
		filters["status"] = status
	or_filters = None
	kw = (keyword or "").strip()
	if kw:
		or_filters = [["name", "like", "%{}%".format(kw)],
					  ["study_scope", "like", "%{}%".format(kw)],
					  ["client", "like", "%{}%".format(kw)]]
	rows = frappe.get_all(
		REPORT_DOCTYPE, filters=filters, or_filters=or_filters,
		fields=["name", "report_type", "stability_product", "year", "source_doctype",
				"source_name", "customer", "client_code", "client", "seq",
				"period_from", "period_to", "proposed_validity_months",
				"proposed_validity_date", "final_validity_months", "final_validity_date",
				"final_validity_type", "status", "drafted_by", "draft_date",
				"qa_review_by", "qa_approve_by", "approve_date", "report_period_key"],
		order_by="creation desc", limit_page_length=int(limit))
	prod_names = sorted({r.stability_product for r in rows if r.get("stability_product")})
	products = dict(frappe.get_all("HBOS Stability Product", filters={"name": ["in", prod_names]},
								   fields=["name", "product_name"], as_list=True)) if prod_names else {}
	for r in rows:
		r["product_name"] = products.get(r.get("stability_product"))
	return {"rows": rows}


@frappe.whitelist()
def get_stability_report_detail(report_name):
	"""报告详情（全字段）。"""
	_check_action("get_stability_report_detail", REPORT_DOCTYPE, report_name)
	doc = frappe.get_doc(REPORT_DOCTYPE, report_name)
	out = {}
	for field in ("name", "report_type", "stability_product", "year", "source_doctype",
				  "source_name", "customer", "client_code", "client", "seq",
				  "report_period_key", "study_scope", "period_from", "period_to",
				  "storage_conds", "spec_ref", "trend_analysis", "impurity_profile",
				  "trend_chart_ref", "conclusion", "proposed_validity_months",
				  "proposed_validity_date", "proposed_validity_type", "proposed_validity_basis",
				  "final_validity_months", "final_validity_date", "final_validity_type",
				  "client_requirement", "drafted_by", "draft_date", "qa_review_by",
				  "qa_review_date", "qa_approve_by", "approve_date", "reject_reason",
				  "void_reason", "status"):
		out[field] = doc.get(field)
	out["product_name"] = frappe.db.get_value(
		"HBOS Stability Product", doc.stability_product, "product_name")
	return out


@frappe.whitelist()
def get_stability_customer_scan(limit=300):
	"""稳定性板块客户编码存量合规扫描（方案 P1 rev15 ②b）。

	列出全库 `Customer` 文档名中**不符合命名规范**的项，交 QA 处置（改名 / 停用）
	后专项报告方可引用。**只读**，不自动修改。
	"""
	_check_action("get_stability_customer_scan", REPORT_DOCTYPE, "-")
	names = frappe.get_all("Customer", pluck="name", limit_page_length=int(limit))
	bad = []
	for n in names:
		ok, err = stb.check_customer_code(n)
		if not ok:
			bad.append({"name": n, "reason": err,
						"referenced": bool(frappe.db.exists(
							REPORT_DOCTYPE, {"customer": n}))})
	return {"scanned": len(names), "non_compliant": bad}


def _holiday_set():
	"""公司默认假日表（用于「5 个工作日」判定）；无配置或读取失败时返回空集合（退化为自然日）。"""
	try:
		company = (frappe.defaults.get_user_default("Company")
				   or frappe.db.get_single_value("Global Defaults", "default_company"))
		hl = frappe.db.get_value("Company", company, "default_holiday_list") if company else None
		if not hl:
			return set()
		return {d.holiday_date for d in frappe.get_all(
			"Holiday", filters={"parent": hl, "weekly_off": 0},
			fields=["holiday_date"], limit_page_length=0) if d.holiday_date}
	except Exception:
		return set()


# ===========================================================================
# M2-R8D 变更、稳定性室与设备（方案 6.3.7 / 6.3.8 / 7.9）
# ===========================================================================

CHANGE_DOCTYPE = "HBOS Stability Change"
ROOM_LOG_DOCTYPE = "HBOS Stability Room Log"
EQUIPMENT_DOCTYPE = "HBOS Stability Equipment"
FAULT_DOCTYPE = "HBOS Stability Fault Ticket"


# ---- 6.3.7 变更审批链 ------------------------------------------------------

@frappe.whitelist()
def create_stability_change(change_scope, change_level, change_content, change_reason,
								impact_assessment, notice=None, protocol=None,
								stability_sample=None, supersedes=None,
								applicant_dept=None, effective_date=None,
								support_docs=None, extra_conditions=None):
	"""变更申请（草稿）。变更对象至少一项；落点与对象匹配由控制器校验（方案 5.5.1 / 7.9）。"""
	_check_action("create_change", CHANGE_DOCTYPE, "-")
	if change_scope not in stb.CHANGE_SCOPES:
		frappe.throw("变更落点「{}」不在受控枚举内。".format(change_scope))
	if change_level not in stb.CHANGE_LEVELS:
		frappe.throw("变更级别「{}」不在受控枚举内。".format(change_level))
	normalized_conditions = _normalize_change_conditions(extra_conditions)
	if change_scope == "涉条件与时间点" and not normalized_conditions:
		frappe.throw("涉条件与时间点的变更必须至少填写一条变更后条件。")
	try:
		doc = frappe.get_doc({
			"doctype": CHANGE_DOCTYPE,
			"change_scope": change_scope,
			"change_level": change_level,
			"notice": notice or None,
			"protocol": protocol or None,
			"stability_sample": stability_sample or None,
			"supersedes": supersedes or None,
			"change_content": change_content,
			"change_reason": change_reason,
			"impact_assessment": impact_assessment,
			"applicant_dept": applicant_dept or None,
			"effective_date": effective_date or None,
			"support_docs": support_docs or None,
			"extra_conditions": normalized_conditions,
			"applicant": _user(),
			"apply_date": _today(),
			"status": stb.CHANGE_DRAFT,
		})
		doc.flags.allow_system_fields = True
		doc.insert(ignore_permissions=True)
		_audit_on(CHANGE_DOCTYPE, "变更申请", doc.name,
				  action_text="变更申请", new_value="{} / {}".format(change_scope, change_level))
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


def _normalize_change_conditions(extra_conditions):
	"""把 API/表单传入的追加条件统一为共享子表可接受的字段。"""
	if not extra_conditions:
		return []
	if isinstance(extra_conditions, str):
		try:
			extra_conditions = frappe.parse_json(extra_conditions)
		except Exception:
			frappe.throw("变更后条件格式不正确。")
	if not isinstance(extra_conditions, (list, tuple)):
		frappe.throw("变更后条件必须是列表。")
	out = []
	for row in extra_conditions:
		if not isinstance(row, dict):
			frappe.throw("变更后条件行格式不正确。")
		condition_type = row.get("condition_type")
		storage_cond = row.get("storage_cond") or row.get("condition_code")
		if condition_type not in stb.CONDITION_TYPES:
			frappe.throw("变更后条件类型不在受控枚举内。")
		if not storage_cond:
			frappe.throw("变更后条件必须指定储存条件。")
		if not frappe.db.exists("HBOS Stability Condition", storage_cond):
			frappe.throw("变更后条件的储存条件不存在：{}。".format(storage_cond))
		out.append({
			"condition_type": condition_type,
			"storage_cond": storage_cond,
			"exposure_days": row.get("exposure_days"),
			"is_required": row.get("is_required", 1),
			"remark": row.get("remark"),
		})
	return out


@frappe.whitelist()
def submit_change(change_name):
	"""变更提交（草稿 → 待QA审核）。"""
	_check_action("submit_change", CHANGE_DOCTYPE, change_name)
	try:
		doc = _load(CHANGE_DOCTYPE, change_name)
		if doc.status != stb.CHANGE_DRAFT:
			_reject(CHANGE_DOCTYPE, change_name,
					"仅「草稿」可提交（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 submit_change".format(doc.status))
		_set_status(doc, stb.FLOW_STB_CHANGE, stb.CHANGE_WAIT_QA)
		doc.save(ignore_permissions=True)
		_audit_on(CHANGE_DOCTYPE, "变更申请", doc.name, action_text="变更提交")
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def review_change(change_name):
	"""变更 QA 审核（待QA审核 → 按级别分流：一般→待QA经理批准；重大→待QP批准）。"""
	_check_action("review_change", CHANGE_DOCTYPE, change_name)
	try:
		doc = _load(CHANGE_DOCTYPE, change_name)
		if doc.status != stb.CHANGE_WAIT_QA:
			_reject(CHANGE_DOCTYPE, change_name,
					"仅「待QA审核」可审核（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 review_change".format(doc.status))
		if doc.applicant and doc.applicant == _user():
			_audit_commit(CHANGE_DOCTYPE, "SoD 拦截", doc.name,
						  action_text="变更审核违反职责分离",
						  reason="申请人同为 {}".format(doc.applicant))
			frappe.throw("变更 QA 审核人不得为申请人（SoD，方案 6.4）。")
		target = stb.CHANGE_WAIT_QP if doc.change_level == "重大" else stb.CHANGE_WAIT_QAM
		doc.flags.allow_system_fields = True
		doc.qa_review_by = _user()
		doc.qa_review_date = _today()
		_set_status(doc, stb.FLOW_STB_CHANGE, target)
		doc.save(ignore_permissions=True)
		_audit_on(CHANGE_DOCTYPE, "变更QA审核", doc.name,
				  action_text="变更 QA 审核", new_value=target)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def approve_change_general(change_name):
	"""一般变更批准（待QA经理批准 → 已批准）。QA 经理专属（方案 S7，无 Manager 兜底）。"""
	_check_action("approve_change_general", CHANGE_DOCTYPE, change_name)
	return _approve_change(change_name, stb.CHANGE_WAIT_QAM, "一般变更批准")


@frappe.whitelist()
def approve_change_major(change_name):
	"""重大变更批准（待QP批准 → 已批准）。QP 专属。"""
	_check_action("approve_change_major", CHANGE_DOCTYPE, change_name)
	return _approve_change(change_name, stb.CHANGE_WAIT_QP, "重大变更批准")


def _approve_change(change_name, expected_status, event):
	doc = _load(CHANGE_DOCTYPE, change_name)
	if doc.status != expected_status:
		_reject(CHANGE_DOCTYPE, change_name,
				"仅「{}」可批准（当前：{}）。".format(expected_status, doc.status),
				"非法状态：{} 调用 {} ".format(doc.status, event))
	me = _user()
	if doc.applicant and doc.applicant == me:
		_audit_commit(CHANGE_DOCTYPE, "SoD 拦截", doc.name,
					  action_text="变更批准违反职责分离",
					  reason="申请人同为 {}".format(me))
		frappe.throw("变更批准人不得为申请人（SoD，方案 6.4）。")
	if doc.qa_review_by and doc.qa_review_by == me:
		_audit_commit(CHANGE_DOCTYPE, "SoD 拦截", doc.name,
					  action_text="变更批准违反职责分离",
					  reason="QA 审核人同为 {}".format(me))
		frappe.throw("变更批准人不得为 QA 审核人（SoD，方案 6.4）。")
	doc.flags.allow_system_fields = True
	doc.approver_by = me
	doc.approve_date = _today()
	_set_status(doc, stb.FLOW_STB_CHANGE, stb.CHANGE_APPROVED)
	doc.save(ignore_permissions=True)
	_audit_on(CHANGE_DOCTYPE, event, doc.name, action_text=event)
	_commit()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def reject_change(change_name, reason):
	"""变更驳回（三个在审状态 → 已驳回），原因必填。"""
	_check_action("reject_change", CHANGE_DOCTYPE, change_name)
	if not (reason or "").strip():
		frappe.throw("驳回原因必填。")
	try:
		doc = _load(CHANGE_DOCTYPE, change_name)
		if doc.status not in (stb.CHANGE_WAIT_QA, stb.CHANGE_WAIT_QAM, stb.CHANGE_WAIT_QP):
			_reject(CHANGE_DOCTYPE, change_name,
					"仅「在审」状态可驳回（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 reject_change".format(doc.status))
		doc.flags.allow_system_fields = True
		doc.reject_reason = reason
		_set_status(doc, stb.FLOW_STB_CHANGE, stb.CHANGE_REJECTED)
		doc.save(ignore_permissions=True)
		_audit_on(CHANGE_DOCTYPE, "驳回", doc.name, action_text="变更驳回", reason=reason)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def cancel_change(change_name, reason=None):
	"""变更取消（草稿 → 已取消）。"""
	_check_action("cancel_change", CHANGE_DOCTYPE, change_name)
	try:
		doc = _load(CHANGE_DOCTYPE, change_name)
		if doc.status != stb.CHANGE_DRAFT:
			_reject(CHANGE_DOCTYPE, change_name,
					"仅「草稿」可取消（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 cancel_change".format(doc.status))
		_set_status(doc, stb.FLOW_STB_CHANGE, stb.CHANGE_CANCELLED)
		doc.save(ignore_permissions=True)
		_audit_on(CHANGE_DOCTYPE, "变更取消", doc.name, action_text="变更取消", reason=reason or "")
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def implement_change(change_name, implement_record):
	"""变更实施（已批准 → 已实施）：**单一原子事务**（方案 7.9 / P1-9）。

	同事务内 (a) 按 `change_scope` 执行落点回写（方案升版 / 新通知单 / 追加条件 / 新样品），
	(b) 写落点审计 + 汇总审计，(c) 置「已实施」；任一步失败整体回滚，变更单停留「已批准」。
	"""
	_check_action("implement_change", CHANGE_DOCTYPE, change_name)
	if not (implement_record or "").strip():
		frappe.throw("实施记录必填（方案 5.5.1）。")
	try:
		doc = _load(CHANGE_DOCTYPE, change_name)
		if doc.status != stb.CHANGE_APPROVED:
			_reject(CHANGE_DOCTYPE, change_name,
					"仅「已批准」可实施（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 implement_change".format(doc.status))
		result = {"scope": doc.change_scope, "created": None, "appended": 0}
		if doc.change_scope == "涉方案":
			result["created"] = _implement_protocol_new_version(doc)
			_audit_on(CHANGE_DOCTYPE, "变更实施回写", doc.name,
					  action_text="变更实施-方案升版", new_value=result["created"])
		elif doc.change_scope == "涉通知单":
			result["created"] = _implement_new_notice(doc)
			_audit_on(CHANGE_DOCTYPE, "变更实施回写", doc.name,
					  action_text="变更实施-新通知单", new_value=result["created"])
		elif doc.change_scope == "涉条件与时间点":
			sample = _lock_row(SAMPLE_DOCTYPE, doc.stability_sample)
			result["appended"] = _append_conditions_impl(sample, _extra_conditions_of(doc))
			_audit_on(CHANGE_DOCTYPE, "变更实施回写", doc.name,
					  action_text="变更实施-追加条件",
					  new_value="{} 个时间点".format(result["appended"]))
		elif doc.change_scope == "涉样品":
			result["created"] = _implement_new_sample(doc)
			_audit_on(CHANGE_DOCTYPE, "变更实施回写", doc.name,
					  action_text="变更实施-新样品", new_value=result["created"])
		else:
			frappe.throw("变更落点「{}」无法分派实施动作。".format(doc.change_scope))
		doc.flags.allow_system_fields = True
		doc.implement_record = implement_record
		doc.implement_by = _user()
		doc.implement_date = _today()
		_set_status(doc, stb.FLOW_STB_CHANGE, stb.CHANGE_IMPLEMENTED)
		doc.save(ignore_permissions=True)
		_audit_on(CHANGE_DOCTYPE, "变更实施回写", doc.name,
				  action_text="变更实施完成", new_value=doc.status)
		_commit()
		return {"name": doc.name, "status": doc.status, "result": result}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def assess_change(change_name, post_assessment, post_assessment_result):
	"""变更后评估（已实施 → 已评估完成 / 后评估不通过）；不达标须另立新单（supersedes）。"""
	_check_action("assess_change", CHANGE_DOCTYPE, change_name)
	if not (post_assessment or "").strip():
		frappe.throw("后评估结论必填。")
	if post_assessment_result not in ("达标", "不达标需纠正"):
		frappe.throw("后评估结果须为「达标 / 不达标需纠正」。")
	try:
		doc = _load(CHANGE_DOCTYPE, change_name)
		if doc.status != stb.CHANGE_IMPLEMENTED:
			_reject(CHANGE_DOCTYPE, change_name,
					"仅「已实施」可后评估（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 assess_change".format(doc.status))
		target = stb.CHANGE_ASSESS_FAILED if post_assessment_result == "不达标需纠正" \
			else stb.CHANGE_ASSESSED
		doc.flags.allow_system_fields = True
		doc.post_assessment = post_assessment
		doc.post_assessment_result = post_assessment_result
		doc.post_assess_by = _user()
		doc.post_assess_date = _today()
		_set_status(doc, stb.FLOW_STB_CHANGE, target)
		doc.save(ignore_permissions=True)
		_audit_on(CHANGE_DOCTYPE, "变更后评估", doc.name,
				  action_text="变更后评估", new_value=target)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def reopen_change(change_name, new_change_name):
	"""变更重启校验（后评估不通过 → 另立新单）：仅校验 supersedes 指向，不改本单状态。"""
	_check_action("reopen_change", CHANGE_DOCTYPE, change_name)
	try:
		doc = frappe.get_doc(CHANGE_DOCTYPE, change_name)
		if doc.status != stb.CHANGE_ASSESS_FAILED:
			_reject(CHANGE_DOCTYPE, change_name,
					"仅「后评估不通过」的变更单可重启（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 reopen_change".format(doc.status))
		new_doc = frappe.get_doc(CHANGE_DOCTYPE, new_change_name)
		if new_doc.supersedes != change_name:
			frappe.throw("重启新单（{}）的 supersedes 必须指向本单（{}）（方案 6.1）。".format(
				new_change_name, change_name))
		_audit_on(CHANGE_DOCTYPE, "变更重启", doc.name,
				  action_text="变更重启校验通过", new_value=new_change_name)
		_commit()
		return {"name": new_change_name, "supersedes": change_name, "ok": True}
	except Exception:
		_rollback()
		raise


def _implement_protocol_new_version(change):
	"""落点「涉方案」：生成 Protocol 新版本（version+1 + supersedes），原版置已作废（7.9）。

	注意：快照字段随新版本复制，**不改原版任何字段**（冻结快照 7.7，作废为状态转移非字段改写）。
	"""
	if not change.protocol:
		frappe.throw("落点「涉方案」的变更单未指定方案（7.9）。")
	old = frappe.get_doc("HBOS Stability Protocol", change.protocol)
	old.flags.allow_system_fields = True
	_set_status(old, stb.FLOW_STB_PROTOCOL, stb.PROTOCOL_VOIDED)
	old.save(ignore_permissions=True)
	study_conditions = [r.as_dict() for r in (old.study_conditions or [])]
	for row in (change.get("extra_conditions") or []):
		study_conditions.append({
			"condition_type": row.get("condition_type"),
			"storage_cond": row.get("storage_cond"),
			"exposure_days": row.get("exposure_days"),
			"is_required": row.get("is_required", 1),
			"remark": row.get("remark"),
		})
	new = frappe.get_doc({
		"doctype": "HBOS Stability Protocol",
		"notice": old.notice,
		"version": (old.version or 1) + 1,
		"supersedes": old.name,
		"purpose": old.purpose,
		"scope": old.scope,
		"qty": old.qty,
		"qty_uom": old.qty_uom,
		"pack_desc": old.pack_desc,
		"room_temp_recovery_days": old.room_temp_recovery_days,
		"spec_ref": old.spec_ref,
		"spec_version": old.spec_version,
		"test_method_ref": old.test_method_ref,
		"method_version": old.method_version,
		"batches": [r.as_dict() for r in (old.batches or [])],
		"study_conditions": study_conditions,
		"items": [r.as_dict() for r in (old.items or [])],
		"status": stb.PROTOCOL_DRAFT,
	})
	new.flags.allow_system_fields = True
	new.insert(ignore_permissions=True)
	return new.name


def _implement_new_notice(change):
	"""落点「涉通知单」：另立新 Notice 草稿（version+1 + supersedes），原 Notice 不动（7.9）。

	新通知单为草稿，须走 R8A 的提交流程；本方法只完成"另立"动作。
	"""
	if not change.notice:
		frappe.throw("落点「涉通知单」的变更单未指定通知单（7.9）。")
	old = frappe.get_doc("HBOS Stability Notice", change.notice)
	new = frappe.get_doc({
		"doctype": "HBOS Stability Notice",
		"stability_product": old.stability_product,
		"version": (old.version or 1) + 1,
		"supersedes": old.name,
		"study_reason": "变更实施另立（源自 {}）：{}".format(old.name, old.study_reason or ""),
		"qty": old.qty,
		"qty_uom": old.qty_uom,
		"pack_desc": old.pack_desc,
		"test_cycle": old.test_cycle,
		"test_method": old.test_method,
		"spec_ref": old.spec_ref,
		"spec_version": old.spec_version,
		"method_version": old.method_version,
		"limits_snapshot": old.limits_snapshot,
		"study_conditions": [r.as_dict() for r in (old.study_conditions or [])],
		"batches": [r.as_dict() for r in (old.batches or [])],
		"status": stb.NOTICE_DRAFT,
	})
	new.flags.allow_system_fields = True
	new.insert(ignore_permissions=True)
	return new.name


def _implement_new_sample(change):
	"""落点「涉样品」：另立新 Sample（按新条件/包装重新入箱），原样品记录不动（7.9）。

	新样品复用原 Notice / Protocol 作为来源链；入箱信息由变更单上的支持性说明提供。
	"""
	if not change.stability_sample:
		frappe.throw("落点「涉样品」的变更单未指定样品（7.9）。")
	frappe.throw("落点「涉样品」须按新条件/包装重新入箱，请使用 `register_stability_sample` "
				 "建新样品后再在本变更单实施记录中登记新样品编号（7.9）。")


# ---- 6.3.8 稳定性室：温湿度记录 / 设备台账 / 故障工单 -----------------------

@frappe.whitelist()
def log_room_env(room, log_date, period, temperature, humidity,
				 checker=None, check_date=None, exception_desc=None, action_taken=None,
				 deviation_ref=None, capa_ref=None):
	"""温湿度手工记录（记录四）。同房间同日期同班次唯一；超标必填异常描述（方案 5.5.2）。

	`within_spec` 由控制器判定；快照上下限在控制器写入。此方法为唯一合法写入口。
	"""
	_check_action("log_room_env", ROOM_LOG_DOCTYPE, room)
	try:
		doc = frappe.get_doc({
			"doctype": ROOM_LOG_DOCTYPE,
			"room": room,
			"log_date": log_date,
			"period": period,
			"temperature": temperature,
			"humidity": humidity,
			"checker": checker or _user(),
			"check_date": check_date or _today(),
			"exception_desc": exception_desc or None,
			"action_taken": action_taken or None,
			"deviation_ref": deviation_ref or None,
			"capa_ref": capa_ref or None,
			"status": "正常",
		})
		doc.flags.allow_system_fields = True
		doc.insert(ignore_permissions=True)   # 控制器判 within_spec、生成业务键
		_audit_on(ROOM_LOG_DOCTYPE, "温湿度记录" if doc.within_spec else "温湿度超标",
				  doc.name, action_text="温湿度记录（{}）".format(period),
				  new_value="{}℃ / {}%RH".format(temperature, humidity))
		_commit()
		return {"name": doc.name, "within_spec": int(doc.within_spec)}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def manage_equipment(equipment_name=None, room=None, location=None, storage_cond=None,
					 qualification_status=None, qualification_due=None,
					 calibration_due=None, maintenance_due=None,
					 is_monitored=None, has_ups=None, has_alarm=None,
					 alarm_test_date=None, status=None, equipment=None):
	"""设备台账建档 / 变更（方案 6.3.8 `manage_equipment`）。

	`equipment` 传编号则为变更（受控字段仍经控制器守卫），否则建档。
	"""
	_check_action("manage_equipment", EQUIPMENT_DOCTYPE, equipment or equipment_name)
	try:
		if equipment:
			doc = _load(EQUIPMENT_DOCTYPE, equipment)
			for field in ("equipment_name", "room", "location", "storage_cond",
						  "qualification_status", "qualification_due", "calibration_due",
						  "maintenance_due", "is_monitored", "has_ups", "has_alarm",
						  "alarm_test_date", "status"):
				if locals().get(field) is not None:
					doc.set(field, locals()[field])
			doc.save(ignore_permissions=True)
			_audit_on(EQUIPMENT_DOCTYPE, "设备台账变更", doc.name, action_text="设备台账变更")
		else:
			if not equipment_name or not status:
				frappe.throw("设备建档须提供设备名称与状态。")
			doc = frappe.get_doc({
				"doctype": EQUIPMENT_DOCTYPE,
				"equipment_name": equipment_name,
				"room": room or None,
				"location": location or None,
				"storage_cond": storage_cond or None,
				"qualification_status": qualification_status or None,
				"qualification_due": qualification_due or None,
				"calibration_due": calibration_due or None,
				"maintenance_due": maintenance_due or None,
				"is_monitored": _truthy(is_monitored),
				"has_ups": _truthy(has_ups),
				"has_alarm": _truthy(has_alarm),
				"alarm_test_date": alarm_test_date or None,
				"status": status,
			})
			doc.flags.allow_system_fields = True
			doc.insert(ignore_permissions=True)
			_audit_on(EQUIPMENT_DOCTYPE, "设备台账变更", doc.name, action_text="设备建档")
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def open_fault_ticket(equipment, description, fault_start, fault_end=None,
					  affected_samples=None, emergency_action=None, transfer_path=None):
	"""设备故障工单（→ 待处理）。受影响样品子表由本方法写入（方案 5.5.4 / 8.3 流水表）。"""
	_check_action("open_fault_ticket", FAULT_DOCTYPE, equipment)
	if not (description or "").strip():
		frappe.throw("故障描述必填。")
	try:
		doc = frappe.get_doc({
			"doctype": FAULT_DOCTYPE,
			"equipment": equipment,
			"fault_start": fault_start,
			"fault_end": fault_end or None,
			"description": description,
			"emergency_action": emergency_action or None,
			"transfer_path": transfer_path or None,
			"status": stb.FAULT_PENDING,
		})
		for row in (affected_samples or []):
			doc.append("affected_samples", {
				"stability_sample": row.get("stability_sample"),
				"timepoint": row.get("timepoint") or None,
				"impact_desc": row.get("impact_desc") or None,
				"is_transferred": _truthy(row.get("is_transferred")),
			})
		doc.flags.allow_system_fields = True
		doc.insert(ignore_permissions=True)
		frappe.db.set_value(EQUIPMENT_DOCTYPE, equipment, "last_fault_date",
							str(fault_start)[:10], update_modified=False)
		_audit_on(FAULT_DOCTYPE, "设备故障", doc.name, action_text="设备故障", new_value=equipment)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def start_fault_handling(ticket_name, emergency_action):
	"""故障处理开始（待处理 → 处理中），紧急措施必填。"""
	_check_action("start_fault_handling", FAULT_DOCTYPE, ticket_name)
	if not (emergency_action or "").strip():
		frappe.throw("紧急措施必填（方案 6.3.8）。")
	try:
		doc = _load(FAULT_DOCTYPE, ticket_name)
		if doc.status != stb.FAULT_PENDING:
			_reject(FAULT_DOCTYPE, ticket_name,
					"仅「待处理」可开始处理（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 start_fault_handling".format(doc.status))
		doc.flags.allow_system_fields = True
		doc.emergency_action = emergency_action
		doc.handler = _user()
		doc.handle_date = _today()
		_set_status(doc, stb.FLOW_STB_FAULT, stb.FAULT_HANDLING)
		doc.save(ignore_permissions=True)
		_audit_on(FAULT_DOCTYPE, "故障处理中", doc.name, action_text="故障处理中")
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def submit_fault_assessment(ticket_name, risk_assessment):
	"""故障风险评估提交（处理中 → 待评估），风险评估必填。"""
	_check_action("submit_fault_assessment", FAULT_DOCTYPE, ticket_name)
	if not (risk_assessment or "").strip():
		frappe.throw("风险评估必填（方案 6.3.8）。")
	try:
		doc = _load(FAULT_DOCTYPE, ticket_name)
		if doc.status != stb.FAULT_HANDLING:
			_reject(FAULT_DOCTYPE, ticket_name,
					"仅「处理中」可提交评估（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 submit_fault_assessment".format(doc.status))
		doc.flags.allow_system_fields = True
		doc.risk_assessment = risk_assessment
		_set_status(doc, stb.FLOW_STB_FAULT, stb.FAULT_WAIT_ASSESS)
		doc.save(ignore_permissions=True)
		_audit_on(FAULT_DOCTYPE, "故障待评估", doc.name, action_text="故障待评估")
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def return_fault_handling(ticket_name, reason=None):
	"""故障退回处理（待评估 → 处理中）：风险评估未决需继续处置（P2-3）。"""
	_check_action("return_fault_handling", FAULT_DOCTYPE, ticket_name)
	try:
		doc = _load(FAULT_DOCTYPE, ticket_name)
		if doc.status != stb.FAULT_WAIT_ASSESS:
			_reject(FAULT_DOCTYPE, ticket_name,
					"仅「待评估」可退回处理（当前：{}）。".format(doc.status),
					"非法状态：{} 调用 return_fault_handling".format(doc.status))
		_set_status(doc, stb.FLOW_STB_FAULT, stb.FAULT_HANDLING)
		doc.save(ignore_permissions=True)
		_audit_on(FAULT_DOCTYPE, "退回处理", doc.name, action_text="故障退回处理", reason=reason or "")
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def close_fault_ticket(ticket_name, deviation_ref=None, capa_ref=None):
	"""故障关闭（待处理/处理中/待评估 → 已关闭）。直接关闭须关联偏差/CAPA（P2-3）。"""
	_check_action("close_fault_ticket", FAULT_DOCTYPE, ticket_name)
	try:
		doc = _load(FAULT_DOCTYPE, ticket_name)
		if doc.status not in (stb.FAULT_PENDING, stb.FAULT_HANDLING, stb.FAULT_WAIT_ASSESS):
			_reject(FAULT_DOCTYPE, ticket_name,
					"当前状态（{}）不可关闭。".format(doc.status),
					"非法状态：{} 调用 close_fault_ticket".format(doc.status))
		if not (deviation_ref or capa_ref):
			frappe.throw("关闭故障工单必须关联偏差或 CAPA 引用（方案 6.3.8）。")
		doc.flags.allow_system_fields = True
		doc.deviation_ref = deviation_ref or doc.deviation_ref
		doc.capa_ref = capa_ref or doc.capa_ref
		doc.fault_end = doc.fault_end or frappe.utils.now()
		doc.handler = doc.handler or _user()
		doc.handle_date = doc.handle_date or _today()
		_set_status(doc, stb.FLOW_STB_FAULT, stb.FAULT_CLOSED)
		doc.save(ignore_permissions=True)
		_audit_on(FAULT_DOCTYPE, "故障关闭", doc.name, action_text="故障关闭",
				  new_value="deviation={} capa={}".format(doc.deviation_ref or "-", doc.capa_ref or "-"))
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


# ---- R8D 只读接口 -----------------------------------------------------------

@frappe.whitelist()
def get_stability_changes(status=None, change_scope=None, keyword=None, limit=200):
	"""变更台账（只读投影）。"""
	_check_action("get_stability_changes", CHANGE_DOCTYPE, "-")
	filters = {}
	if status:
		filters["status"] = status
	if change_scope:
		filters["change_scope"] = change_scope
	rows = frappe.get_all(
		CHANGE_DOCTYPE, filters=filters,
		fields=["name", "change_scope", "change_level", "status", "notice", "protocol",
				"stability_sample", "change_content", "applicant", "apply_date",
				"approver_by", "approve_date", "supersedes",
				"implement_by", "implement_date", "post_assessment_result"],
		order_by="modified desc", limit_page_length=int(limit or 200))
	if keyword:
		kw = keyword.lower()
		rows = [r for r in rows if kw in (r.change_content or "").lower()
				or kw in (r.name or "").lower()]
	return {"rows": rows, "total": len(rows)}


@frappe.whitelist()
def get_stability_change_detail(change_name):
	"""变更详情（含落点与实施结果）。"""
	_check_action("get_stability_change_detail", CHANGE_DOCTYPE, change_name)
	doc = frappe.get_doc(CHANGE_DOCTYPE, change_name)
	return {"doc": doc.as_dict()}


@frappe.whitelist()
def get_stability_room_logs(room=None, from_date=None, to_date=None,
							only_abnormal=0, limit=500):
	"""温湿度记录查询（含超标筛选，方案 5.6 第 5 张报表数据源）。"""
	_check_action("get_stability_room_logs", ROOM_LOG_DOCTYPE, "-")
	filters = {}
	if room:
		filters["room"] = room
	if from_date:
		filters["log_date"] = [">=", from_date]
	if to_date:
		filters.setdefault("log_date", {})
		if isinstance(filters["log_date"], dict):
			filters["log_date"]["<="] = to_date
		else:
			filters["log_date"] = [">=", from_date]
	if _truthy(only_abnormal):
		filters["within_spec"] = 0
	rows = frappe.get_all(
		ROOM_LOG_DOCTYPE, filters=filters,
		fields=["name", "room", "log_date", "period", "temperature", "temp_min", "temp_max",
				"humidity", "humidity_min", "humidity_max", "within_spec",
				"exception_desc", "action_taken", "deviation_ref", "capa_ref",
				"checker", "check_date"],
		order_by="log_date desc, period desc", limit_page_length=int(limit or 500))
	return {"rows": rows, "total": len(rows)}


@frappe.whitelist()
def get_stability_equipments(room=None, status=None):
	"""设备台账列表（只读投影）。"""
	_check_action("get_stability_equipments", EQUIPMENT_DOCTYPE, "-")
	filters = {}
	if room:
		filters["room"] = room
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		EQUIPMENT_DOCTYPE, filters=filters,
		fields=["name", "equipment_name", "room", "location", "storage_cond",
				"qualification_status", "qualification_due", "calibration_due",
				"maintenance_due", "is_monitored", "has_ups", "has_alarm",
				"alarm_test_date", "last_fault_date", "status"],
		order_by="modified desc", limit_page_length=0)
	return {"rows": rows, "total": len(rows)}


@frappe.whitelist()
def get_stability_fault_tickets(status=None, equipment=None, limit=200):
	"""故障工单列表（只读投影）。"""
	_check_action("get_stability_fault_tickets", FAULT_DOCTYPE, "-")
	filters = {}
	if status:
		filters["status"] = status
	if equipment:
		filters["equipment"] = equipment
	rows = frappe.get_all(
		FAULT_DOCTYPE, filters=filters,
		fields=["name", "equipment", "fault_start", "fault_end", "status", "description",
				"emergency_action", "risk_assessment", "deviation_ref", "capa_ref",
				"handler", "handle_date"],
		order_by="modified desc", limit_page_length=int(limit or 200))
	for r in rows:
		r["affected_samples"] = frappe.get_all(
			"HBOS Stability Fault Sample", filters={"parent": r.name},
			fields=["stability_sample", "timepoint", "impact_desc", "is_transferred"],
			limit_page_length=0)
	return {"rows": rows, "total": len(rows)}
