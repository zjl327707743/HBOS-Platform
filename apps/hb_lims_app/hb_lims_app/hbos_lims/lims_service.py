# -*- coding: utf-8 -*-
"""LIMS 检验流程业务服务（Frappe 层）：状态流转 + 自动判定 + 用户签署记录 + 修订留痕。

约定：
- 所有公开方法为 @frappe.whitelist 模块级函数，入口先校验角色（only_for）。
- 显式事务管理（commit / rollback）。
- 状态流转只允许 workflow_contract 中声明的合法转移。
- 判定不合格自动置 OOS 候选并锁定样品（参考开发方案模块 12 OOS 触发接口）。
"""

import json
import hashlib
from pathlib import Path

import frappe

from hb_lims_app.hbos_lims import result_contract as rc
from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import workflow_contract as wf

# 用户签署记录含义（当前为会话用户 + 时间归属，不宣称完整电子签名合规）
SIGN_ANALYST = "检验人"
SIGN_REVIEWER = "复核人"
SIGN_APPROVER = "批准人"


def _user():
	return frappe.session.user


def _now():
	return frappe.utils.now_datetime()


def _signature(meaning):
	return f"{meaning}: {_user()} @ {_now():%Y-%m-%d %H:%M:%S}"


def _check_action(action):
	roles = frappe.get_roles(_user())
	if not any(wf.action_allowed(action, role) for role in roles):
		frappe.throw(f"当前用户（{_user()}）没有执行「{action}」的权限。")


def _set_status(doc, flow, current, target):
	if not wf.can_transition(flow, current, target):
		frappe.throw(f"非法状态流转：{current} -> {target}（{flow}）")
	doc.status = target


def _commit():
	frappe.db.commit()
	try:
		from hb_lims_app.hbos_lims.todo_service import invalidate_my_todo_summary_cache
		invalidate_my_todo_summary_cache()
	except Exception as exc:
		if hasattr(frappe, "log_error"):
			frappe.log_error(str(exc), "HBOS 我的待办摘要缓存失效失败")


# ---------------------------------------------------------------------------
# 合规审计日志：write-once 全量事件捕获（创建/修改/删除/状态流转/仪器使用）
# ---------------------------------------------------------------------------

AUDIT_EXCLUDE_DOCTYPES = {"HBOS Audit Log"}  # 审计日志自身不入日志（避免递归）


def _checksum(payload):
	"""应用级完整性指纹（SHA-256），不是独立的防篡改证明。

	覆盖审计记录全部业务字段，用于发现应用层误修改。由于内容与指纹仍保存在
	同一数据库中，数据库管理员仍可同时改写两者；正式不可抵赖证据需另行接入
	append-only / HMAC / 外部锚定机制。
	"""
	keys = (
		"doctype_target", "doc_name", "log_type", "action_text", "field_changed",
		"old_value", "new_value", "reason", "user", "created_at",
	)
	raw = "|".join(str(payload.get(k) or "") for k in keys)
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def audit_log(log_type, doctype_target, doc_name, action_text="", field_changed="",
			  old_value="", new_value="", reason="", user=None, created_at=None,
			  commit=False):
	"""写入业务事务内审计事件。

	审计行与成功业务变更同一事务提交/回滚。commit 仅保留兼容旧调用，
	不会在此执行 frappe.db.commit()，避免拒绝/SoD 路径意外提交当前请求里
	尚未完成的业务修改。失败尝试若要求跨回滚留存，应走独立日志/Outbox。
	"""
	if user is None:
		user = frappe.session.user
	if not created_at:
		created_at = frappe.utils.now_datetime()

	payload = {
		"doctype": "HBOS Audit Log",
		"log_type": log_type,
		"doctype_target": doctype_target,
		"doc_name": str(doc_name),
		"action_text": action_text,
		"field_changed": field_changed,
		"old_value": str(old_value),
		"new_value": str(new_value),
		"reason": reason,
		"user": user,
		"created_at": created_at,
	}
	payload["checksum"] = _checksum(payload)
	doc = frappe.get_doc(payload)
	doc.flags.audit_immutable = True
	doc.insert(ignore_permissions=True)
	# 审计 helper 不得擅自提交当前业务事务；commit 参数为历史兼容 no-op。
	return doc.name


# ---- doc_events 全量捕获（创建 / 修改 / 删除） ----

def audit_on_insert(doc, method=None):
	if doc.doctype in AUDIT_EXCLUDE_DOCTYPES:
		return
	user = doc.get("owner") or doc.get("modified_by") or doc.get("requestor") or frappe.session.user
	audit_log("创建", doc.doctype, doc.name,
			  action_text=f"创建 {doc.doctype} 记录", user=user, commit=False)


def audit_on_update(doc, method=None):
	if doc.doctype in AUDIT_EXCLUDE_DOCTYPES:
		return
	before = doc.get_doc_before_save()
	if not before:
		return

	for field in AUDIT_WATCHED_FIELDS:
		old = before.get(field)
		new = doc.get(field)
		if str(old or "") == str(new or ""):
			continue
		audit_log(
			"修改", doc.doctype, doc.name,
			action_text=f"修改 {doc.doctype} 字段",
			field_changed=field, old_value=old, new_value=new,
			user=doc.get("modified_by") or frappe.session.user, commit=False,
		)


def audit_on_trash(doc, method=None):
	if doc.doctype in AUDIT_EXCLUDE_DOCTYPES:
		frappe.throw("审计日志不可删除（数据完整性）。")
	audit_log(
		"删除", doc.doctype, doc.name,
		action_text=f"删除 {doc.doctype} 记录", user=frappe.session.user, commit=False,
	)


AUDIT_WATCHED_FIELDS = [
	"status", "result_status", "report_status", "verdict", "result_value",
	"result_text", "raw_value", "unit", "lower_limit", "upper_limit",
	"material_name", "batch_no", "sample_type", "sample_source", "priority",
	"spec_version", "test_due_date", "oos_locked", "approver", "reviewer",
	"special_note", "remarks",
]


def _rollback():
	frappe.db.rollback()


def _reject_sod(message, *, doctype="", doc_name=""):
	"""Record a rejected separation-of-duties attempt without committing business data."""
	try:
		frappe.log_error(
			title="HBOS LIMS SoD 拦截",
			message=f"{doctype} {doc_name} · user={_user()} · {message}",
		)
	except Exception:
		pass
	frappe.throw(message, frappe.PermissionError)


def _result_display_value(result):
	"""结果展示值：记录型优先结果文本；数值结果带单位。"""
	if result.result_text:
		return result.result_text
	if result.result_value is not None and result.result_value != "":
		return f"{result.result_value}{result.unit or ''}"
	return str(result.raw_value or "")


# ---------------------------------------------------------------------------
# 样品登记与任务分配
# ---------------------------------------------------------------------------
# 独立前端辅助（HBOS LIMS Vue 前端挂载于 /hbos-lims，不经过 Frappe desk 渲染，
# 拿不到 frappe.csrf_token 变量；此处暴露 CSRF token 供 POST 请求携带）。
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_csrf_token():
	"""返回当前会话的 CSRF token（供独立前端 POST 请求使用）。"""
	from frappe.sessions import get_csrf_token
	return get_csrf_token()


@frappe.whitelist()
def get_user_roles(username=None):
	"""返回指定用户（缺省当前会话用户）的角色列表。
	基于 frappe.get_roles，避免前端直接读 Has Role（普通用户无权限）。"""
	if username and username != frappe.session.user:
		# 仅 Administrator / System Manager 可查询他人角色
		if "System Manager" not in frappe.get_roles() and not frappe.session.user == "Administrator":
			frappe.throw("无权查看其他用户的角色。")
		return frappe.get_roles(username)
	return frappe.get_roles()


# ---------------------------------------------------------------------------

def _validate_stability_sample_binding(sample_source, stability_timepoint,
									material_code, batch_no, specification):
	"""登记稳定性业务样品时校验产品、批号、标准与时间点的一致性。"""
	ok, error = stb.validate_stability_binding(sample_source, stability_timepoint)
	if not ok:
		frappe.throw(error)
	if not stb.is_stability_sample_source(sample_source):
		return None

	if not frappe.db.exists("HBOS Stability Timepoint", stability_timepoint):
		frappe.throw("稳定性时间点「{}」不存在。".format(stability_timepoint))
	# 绑定唯一性必须在时间点行锁内复核；否则两个并发登记请求可同时通过 exists 检查。
	frappe.db.get_value("HBOS Stability Timepoint", stability_timepoint, "name",
					   for_update=True)
	tp = frappe.get_doc("HBOS Stability Timepoint", stability_timepoint)
	if tp.status not in (stb.TP_WAIT_TEST, stb.TP_TESTING):
		frappe.throw("稳定性时间点「{}」当前状态为「{}」，仅待检测或检测中可登记业务样品。"
					 .format(stability_timepoint, tp.status))
	if not tp.stability_sample:
		frappe.throw("稳定性时间点「{}」未关联稳定性样品。".format(stability_timepoint))

	stable_sample = frappe.get_doc("HBOS Stability Sample", tp.stability_sample)
	product = frappe.get_doc("HBOS Stability Product", stable_sample.stability_product)
	if str(product.product_code or "") != str(material_code or ""):
		frappe.throw("样品物料编码（{}）与稳定性产品编码（{}）不一致。"
					 .format(material_code or "未填", product.product_code or "未填"))
	if str(stable_sample.batch_no or "") != str(batch_no or ""):
		frappe.throw("样品批号（{}）与稳定性样品批号（{}）不一致。"
					 .format(batch_no or "未填", stable_sample.batch_no or "未填"))

	source_doc = None
	if stable_sample.protocol:
		source_doc = frappe.get_doc("HBOS Stability Protocol", stable_sample.protocol)
	elif stable_sample.notice:
		source_doc = frappe.get_doc("HBOS Stability Notice", stable_sample.notice)
	source_spec = getattr(source_doc, "spec_ref", None) if source_doc else None
	if source_spec and str(source_spec) != str(specification or ""):
		frappe.throw("样品质量标准（{}）与稳定性来源标准（{}）不一致。"
					 .format(specification or "未填", source_spec))
	if frappe.db.exists("HBOS Sample", {"stability_timepoint": stability_timepoint}):
		frappe.throw("稳定性时间点「{}」已登记业务检验样品，不可重复绑定。"
					 .format(stability_timepoint))
	if frappe.db.exists("HBOS Stability Result", {"timepoint": stability_timepoint}):
		frappe.throw("稳定性时间点「{}」已有结果，不可再登记业务检验样品。"
					 .format(stability_timepoint))
	return tp


@frappe.whitelist()
def register_sample(sample_type=None, material_code=None, material_name=None,
					batch_no=None, sample_source="生产取样", specification=None,
					priority="常规", test_due_date=None, remarks=None,
					stability_timepoint=None, item_ref=None, batch_ref=None):
	"""样品登记：校验规格已生效，从规格复制检验项目快照，状态 草稿 -> 已登记。"""
	_check_action("register_sample")
	try:
		sample_source = stb.normalize_sample_source(sample_source)
		_validate_stability_sample_binding(sample_source, stability_timepoint,
										material_code, batch_no, specification)
		spec = frappe.get_doc("HBOS Specification", specification)
		if spec.status != "已生效":
			frappe.throw(f"质量标准 {specification} 未生效，样品登记只能引用已生效标准。")

		# ERPNext 主数据引用 + LIMS 历史快照。旧调用仍可只传 material_code/batch_no；
		# 若 ERP 中存在对应对象则自动建立 Link，历史显示字段继续冻结登记时值。
		item_ref = item_ref or (material_code if material_code and frappe.db.exists("Item", material_code) else None)
		batch_ref = batch_ref or (batch_no if batch_no and frappe.db.exists("Batch", batch_no) else None)
		if item_ref:
			if not frappe.db.exists("Item", item_ref):
				frappe.throw(f"ERP 物料不存在：{item_ref}")
			erp_item_name = frappe.db.get_value("Item", item_ref, "item_name") or ""
			material_code = item_ref
			material_name = erp_item_name or material_name
		if batch_ref:
			batch_item = frappe.db.get_value("Batch", batch_ref, "item")
			if not batch_item:
				frappe.throw(f"ERP 批次不存在：{batch_ref}")
			if item_ref and str(batch_item) != str(item_ref):
				frappe.throw(f"批次 {batch_ref} 属于物料 {batch_item}，与样品物料 {item_ref} 不一致。")
			if not item_ref:
				item_ref = batch_item
				material_code = batch_item
				material_name = frappe.db.get_value("Item", batch_item, "item_name") or material_name
			batch_no = batch_ref
		if getattr(spec, "item_ref", None) and item_ref and str(spec.item_ref) != str(item_ref):
			frappe.throw(f"质量标准 {specification} 绑定物料 {spec.item_ref}，与样品物料 {item_ref} 不一致。")

		sample = frappe.get_doc({
			"doctype": "HBOS Sample",
			"sample_type": sample_type,
			"item_ref": item_ref,
			"material_code": material_code,
			"material_name": material_name,
			"batch_ref": batch_ref,
			"batch_no": batch_no,
			"sample_source": sample_source,
			"stability_timepoint": stability_timepoint,
			"specification": specification,
			"spec_version": spec.version,
			"priority": priority,
			"test_due_date": test_due_date,
			"status": "草稿",
			"requestor": _user(),
			"items": [
				{"test_item": row.item, "limits_type": row.limits_type,
				 "lower_limit": row.lower_limit, "upper_limit": row.upper_limit,
				 "remark": row.remark}
				for row in spec.items
			],
			"remarks": remarks,
		})
		sample.flags.allow_system_fields = True
		sample.insert(ignore_permissions=True)
		_set_status(sample, wf.FLOW_SAMPLE, "草稿", "已登记")
		sample.save(ignore_permissions=True)
		_commit()
		return sample.name
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def generate_tasks(sample_name, lab_department=None):
	"""按样品待检项目生成检验任务（Manager）。每个项目一个任务，回填样品项目行的 task 链接。"""
	_check_action("generate_tasks")
	try:
		sample = frappe.get_doc("HBOS Sample", sample_name)
		if sample.status != "已登记":
			frappe.throw(f"样品 {sample_name} 状态为 {sample.status}，仅已登记样品可生成任务。")
		if not lab_department:
			frappe.throw("请指定检验组（lab_department）。")
		created = []
		for row in sample.items:
			if row.task:
				continue
			task = frappe.get_doc({
				"doctype": "HBOS Sample Task",
				"sample": sample.name,
				"test_item": row.test_item,
				"lab_department": lab_department,
				"assignee": _user(),
				"priority": sample.priority,
				"due_date": sample.test_due_date,
				"status": "待分配",
			})
			task.flags.allow_system_fields = True
			task.insert(ignore_permissions=True)
			row.task = task.name
			created.append(task.name)
		sample.save(ignore_permissions=True)
		_commit()
		return created
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def assign_task(task_name, assignee=None):
	"""分配检验任务（Manager）：待分配 -> 已分配。"""
	_check_action("assign_task")
	try:
		task = frappe.get_doc("HBOS Sample Task", task_name)
		_set_status(task, wf.FLOW_TASK, task.status, "已分配")
		task.assignee = assignee or task.assignee
		task.assigned_by = _user()
		task.assigned_date = _now()
		task.flags.allow_system_fields = True
		task.save(ignore_permissions=True)
		_commit()
		return task.name
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def start_task(task_name):
	"""检验员开始检验（本人或 Manager）：已分配 -> 检验中；自动创建检测记录（冻结限度快照）；样品同步 已登记 -> 检验中。"""
	_check_action("start_task")
	try:
		task = frappe.get_doc("HBOS Sample Task", task_name)
		if task.status != "已分配":
			frappe.throw(f"任务 {task_name} 状态为 {task.status}，仅已分配任务可开始。")
		if _user() not in ("Administrator", task.assignee) and "LIMS Manager" not in frappe.get_roles(_user()):
			frappe.throw("只能开始分配给自己的检验任务。")
		_set_status(task, wf.FLOW_TASK, task.status, "检验中")
		if not task.result:
			result = _create_result_for_task(task)
			task.result = result.name
		task.flags.allow_system_fields = True
		task.save(ignore_permissions=True)

		sample = frappe.get_doc("HBOS Sample", task.sample)
		if sample.status == "已登记":
			_set_status(sample, wf.FLOW_SAMPLE, sample.status, "检验中")
			sample.flags.allow_system_fields = True
			sample.save(ignore_permissions=True)
		_commit()
		return {"task": task.name, "result": task.result}
	except Exception:
		_rollback()
		raise


def _create_result_for_task(task):
	"""从样品项目快照创建检测记录：限度 / 单位 / 有效位数冻结（标准变更不追溯）。"""
	sample = frappe.get_doc("HBOS Sample", task.sample)
	row = next((r for r in sample.items if r.task == task.name), None)
	result = frappe.get_doc({
		"doctype": "HBOS Test Result",
		"task": task.name,
		"limits_type": row.limits_type if row else "",
		"lower_limit": row.lower_limit if row else None,
		"upper_limit": row.upper_limit if row else None,
		"unit": row.unit if row else "",
		"significant_digits": row.significant_digits if row else 2,
		"analyst": _user(),
		"result_status": "草稿",
	})
	result.flags.allow_system_fields = True
	result.insert(ignore_permissions=True)
	return result


# ---------------------------------------------------------------------------
# 检验执行与自动判定
# ---------------------------------------------------------------------------

@frappe.whitelist()
def submit_result(result_name, raw_value=None, result_value=None, result_text=None,
				  calc_input_json=None, calculation_used=None, instrument_used=None):
	"""检验员提交结果：自动判定（含公式计算）、用户签署记录、OOS 候选锁定。"""
	_check_action("submit_result")
	try:
		result = frappe.get_doc("HBOS Test Result", result_name)
		if result.analyst and result.analyst != _user() and "LIMS Manager" not in frappe.get_roles():
			_reject_sod("普通检验员只能提交本人负责的检验结果。", doctype=result.doctype, doc_name=result.name)
		if result.result_status != "草稿":
			frappe.throw(f"检测记录 {result_name} 状态为 {result.result_status}，仅草稿可提交。")
		from hb_lims_app.hbos_lims.stability_service import validate_standard_test_result_sync
		validate_standard_test_result_sync(result.name, target_status="已提交")

		# 公式计算（含量 % 等）：提供公式输入参数时自动计算 result_value
		if calculation_used:
			result.calculation_used = calculation_used
		if calc_input_json:
			params = json.loads(calc_input_json)
			result.calc_input_json = calc_input_json
			calc = frappe.get_doc("HBOS Calculation", result.calculation_used or calculation_used)
			result.result_value = rc.apply_formula(params, calc.formula_type)

		result.raw_value = raw_value
		if result_value is not None and result_value != "":
			result.result_value = result_value
		result.result_text = result_text
		result.instrument_used = instrument_used

		# 自动判定（限度冻结值）
		verdict_en, reason = _judge(result)
		result.verdict = rc.verdict_to_label(verdict_en)
		result.verdict_reason = reason
		if verdict_en == rc.VERDICT_FAIL:
			result.is_oos_candidate = 1

		# 用户签署记录
		result.result_status = "已提交"
		result.submitted_signature = _signature(SIGN_ANALYST)
		result.submitted_at = _now()
		result.flags.allow_system_fields = True
		result.save(ignore_permissions=True)

		# 合规审计：仪器使用（提交携带仪器时记一笔）
		if instrument_used:
			audit_log("仪器使用", "Instrument", instrument_used,
					  action_text=f"{result.item_name or result.test_item or ''} 使用仪器",
					  user=result.analyst, commit=False)
		# 合规审计：结果提交 + 自动判定
		audit_log("提交", result.doctype, result.name,
				  action_text=f"结果提交 · 自动判定 {result.verdict}",
				  field_changed="result_status", old_value="草稿", new_value="已提交",
				  user=result.analyst, commit=False)

		# 联动任务与样品（修订后的新版本提交时任务可能已在目标状态，避免自转移）
		task = frappe.get_doc("HBOS Sample Task", result.task)
		if result.is_oos_candidate:
			if task.status != "OOS候选":
				_set_status(task, wf.FLOW_TASK, task.status, "OOS候选")
			task.flags.allow_system_fields = True
			task.save(ignore_permissions=True)
			_lock_sample_oos(result.sample)
			audit_log("OOS", result.doctype, result.name,
					  action_text="检出 OOS 候选 · 样品锁定",
					  field_changed="result_status", old_value="已提交", new_value="OOS锁定",
					  reason=reason, user=result.analyst, commit=False)
		else:
			if task.status != "已提交":
				_set_status(task, wf.FLOW_TASK, task.status, "已提交")
			task.flags.allow_system_fields = True
			task.save(ignore_permissions=True)
		from hb_lims_app.hbos_lims.stability_service import sync_standard_test_result
		sync_standard_test_result(result.name, target_status="已提交")
		_commit()
		return {"result": result.name, "verdict": result.verdict, "is_oos_candidate": result.is_oos_candidate}
	except Exception:
		_rollback()
		raise


def _judge(result):
	"""基于冻结限度自动判定，返回 (英文判定, 中文说明)。"""
	if result.limits_type == rc.LIMITS_RECORD:
		return rc.VERDICT_NA, "记录型项目，以结果描述判定"
	value = result.result_value if result.result_value is not None else result.raw_value
	verdict = rc.judge_result(value, result.limits_type, result.lower_limit, result.upper_limit)
	reasons = {
		rc.VERDICT_PASS: f"结果在限度范围内（{_limits_text(result)}）",
		rc.VERDICT_FAIL: f"结果超出限度（{_limits_text(result)}），判定为不合格并触发 OOS 候选",
		rc.VERDICT_UNDETERMINED: "结果为空或无法判定，需人工确认",
	}
	return verdict, reasons.get(verdict, verdict)


def _limits_text(result):
	if result.limits_type == rc.LIMITS_UP:
		return f"≤{result.upper_limit}"
	if result.limits_type == rc.LIMITS_DOWN:
		return f"≥{result.lower_limit}"
	if result.limits_type == rc.LIMITS_RANGE:
		return f"{result.lower_limit} - {result.upper_limit}"
	return "记录型"


def _lock_sample_oos(sample_name):
	"""OOS 触发：样品锁定，禁止放行（MVP 仅锁定，调查流程留后续轮次）。"""
	sample = frappe.get_doc("HBOS Sample", sample_name)
	sample.oos_locked = 1
	_set_status(sample, wf.FLOW_SAMPLE, sample.status, "OOS锁定")
	sample.flags.allow_system_fields = True
	sample.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# 复核 / 批准
# ---------------------------------------------------------------------------

@frappe.whitelist()
def review_result(result_name):
	"""复核（Reviewer / Manager）：已提交 -> 已复核。复核人不可修改原始数据（validate 强制）。"""
	_check_action("review_result")
	try:
		result = frappe.get_doc("HBOS Test Result", result_name)
		if result.analyst and result.analyst == _user():
			_reject_sod("复核人与检验人必须为不同账号。", doctype=result.doctype, doc_name=result.name)
		if result.result_status != "已提交":
			frappe.throw(f"检测记录 {result_name} 状态为 {result.result_status}，仅已提交可复核。")
		from hb_lims_app.hbos_lims.stability_service import validate_standard_test_result_sync
		validate_standard_test_result_sync(result.name, target_status="已复核", reviewer=_user())
		result.result_status = "已复核"
		result.reviewer = _user()
		result.reviewed_signature = _signature(SIGN_REVIEWER)
		result.reviewed_at = _now()
		result.flags.allow_system_fields = True
		result.save(ignore_permissions=True)

		task = frappe.get_doc("HBOS Sample Task", result.task)
		_set_status(task, wf.FLOW_TASK, task.status, "已复核")
		task.flags.allow_system_fields = True
		task.save(ignore_permissions=True)
		from hb_lims_app.hbos_lims.stability_service import sync_standard_test_result
		sync_standard_test_result(result.name, target_status="已复核")
		audit_log("复核", result.doctype, result.name,
				  action_text="结果复核（第二人独立）",
				  field_changed="result_status", old_value="已提交", new_value="已复核",
				  user=result.reviewer, commit=False)
		_commit()
		return result.name
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def approve_result(result_name):
	"""批准（Reviewer / Manager）：已复核 -> 已批准；任务完成；样品全部任务完成后推进状态。"""
	_check_action("approve_result")
	try:
		result = frappe.get_doc("HBOS Test Result", result_name)
		if _user() in {result.analyst, result.reviewer}:
			_reject_sod("批准人必须同时区别于检验人和复核人。", doctype=result.doctype, doc_name=result.name)
		if result.result_status != "已复核":
			frappe.throw(f"检测记录 {result_name} 状态为 {result.result_status}，仅已复核可批准。")
		if result.is_oos_candidate:
			frappe.throw("OOS 候选结果不允许批准放行，需先完成 OOS 处理。")
		from hb_lims_app.hbos_lims.stability_service import validate_standard_test_result_sync
		validate_standard_test_result_sync(result.name, target_status="已批准", approver=_user())
		result.result_status = "已批准"
		result.approver = _user()
		result.approved_signature = _signature(SIGN_APPROVER)
		result.approved_at = _now()
		result.flags.allow_system_fields = True
		result.save(ignore_permissions=True)

		task = frappe.get_doc("HBOS Sample Task", result.task)
		task.result = result.name
		_set_status(task, wf.FLOW_TASK, task.status, "已批准")
		task.flags.allow_system_fields = True
		task.save(ignore_permissions=True)
		_advance_sample_after_task(task.sample)
		from hb_lims_app.hbos_lims.stability_service import sync_standard_test_result
		sync_standard_test_result(result.name, target_status="已批准")
		audit_log("批准", result.doctype, result.name,
				  action_text="结果批准",
				  field_changed="result_status", old_value="已复核", new_value="已批准",
				  user=result.approver, commit=False)
		_commit()
		return result.name
	except Exception:
		_rollback()
		raise


def _advance_sample_after_task(sample_name):
	"""样品全部任务已批准且无 OOS 时，样品 检验中 -> 检验完成。"""
	sample = frappe.get_doc("HBOS Sample", sample_name)
	if sample.oos_locked:
		return
	tasks = frappe.get_all("HBOS Sample Task", filters={"sample": sample_name},
						   fields=["status", "result"])
	if not tasks:
		return
	if all(t.status in ("已批准",) and t.result for t in tasks) and sample.status == "检验中":
		_set_status(sample, wf.FLOW_SAMPLE, sample.status, "检验完成")
		sample.flags.allow_system_fields = True
		sample.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# 修订（ALCOA：修改留痕 + 新版本）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def revise_result(result_name, new_value, reason, field="result_value"):
	"""结果修订（仅 LIMS Manager）：写修订记录 + 生成新版本结果（superseded 链），原记录置已修订。"""
	_check_action("revise_result")
	if not reason or not reason.strip():
		frappe.throw("修改原因必填（ALCOA：所有数据修改必须记录原因）。")
	try:
		old = frappe.get_doc("HBOS Test Result", result_name)
		if old.result_status not in ("已提交", "已复核", "已批准"):
			frappe.throw(f"检测记录 {result_name} 状态为 {old.result_status}，当前状态不可修订。")
		from hb_lims_app.hbos_lims.stability_service import validate_standard_test_result_sync
		validate_standard_test_result_sync(old.name, target_status="草稿")

		old_value = str(old.get(field) or "")
		if not old_value:
			# 记录型结果 result_value 可能为空，用展示值兜底（ALCOA：修改前值必填）
			old_value = _result_display_value(old) or ""

		revision = frappe.get_doc({
			"doctype": "HBOS Result Revision",
			"result": old.name,
			"field_changed": field,
			"old_value": old_value,
			"new_value": str(new_value),
			"changed_by": _user(),
			"changed_at": _now(),
			"change_reason": reason,
		})
		revision.insert(ignore_permissions=True)

		# 新版本：复制原记录，替换修订字段，重置流转状态与签名
		new_doc = frappe.copy_doc(old)
		new_doc.result_status = "草稿"
		new_doc.set(field, new_value)
		new_doc.verdict = ""
		new_doc.verdict_reason = ""
		new_doc.is_oos_candidate = 0
		new_doc.superseded_by = ""
		new_doc.submitted_signature = ""
		new_doc.submitted_at = None
		new_doc.reviewer = None
		new_doc.reviewed_signature = ""
		new_doc.reviewed_at = None
		new_doc.approver = None
		new_doc.approved_signature = ""
		new_doc.approved_at = None
		new_doc.remarks = f"修订自 {old.name}（原因：{reason}）"
		new_doc.flags.allow_system_fields = True
		new_doc.insert(ignore_permissions=True)

		old.superseded_by = new_doc.name
		old.result_status = "已修订"
		old.flags.allow_system_fields = True
		old.save(ignore_permissions=True)

		# 任务结果指针指向新版本，任务回到已提交（待重新复核批准；已提交状态则保持不变）
		task = frappe.get_doc("HBOS Sample Task", old.task)
		task.result = new_doc.name
		if task.status != "已提交":
			_set_status(task, wf.FLOW_TASK, task.status, "已提交")
		task.flags.allow_system_fields = True
		task.save(ignore_permissions=True)
		from hb_lims_app.hbos_lims.stability_service import sync_standard_test_result
		sync_standard_test_result(new_doc.name, target_status="草稿",
							  supersedes_result_name=old.name)
		audit_log("修订", old.doctype, old.name,
				  action_text="结果修订 · 生成新版本",
				  field_changed=field, old_value=old_value, new_value=str(new_value),
				  reason=reason, user=_user(), commit=False)
		_commit()
		return {"revision": revision.name, "new_result": new_doc.name}
	except Exception:
		_rollback()
		raise


# ---------------------------------------------------------------------------
# 样品放行 / 拒绝
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# COA 报告（创建 -> QA 审核 -> 发布 PDF 归档）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_coa(sample_name):
	"""生成 COA：仅样品检验完成且全部结果已批准时，提取已批准结果生成报告快照。"""
	_check_action("create_coa")
	try:
		sample = frappe.get_doc("HBOS Sample", sample_name)
		if sample.oos_locked or sample.status != "检验完成":
			frappe.throw(f"样品 {sample_name} 状态为 {sample.status}（OOS锁定={sample.oos_locked}），"
						 "仅检验完成且无 OOS 锁定的样品可生成 COA。")
		results = frappe.get_all(
			"HBOS Test Result",
			filters={"sample": sample_name, "result_status": "已批准", "is_oos_candidate": 0},
			order_by="creation asc",
		)
		if not results:
			frappe.throw(f"样品 {sample_name} 没有已批准且非 OOS 的检验结果，无法生成 COA。")
		if len(results) < len(sample.items):
			frappe.throw(f"样品 {sample_name} 仍有检验结果未批准，无法生成 COA。")

		existing = frappe.db.get_value("HBOS COA", {"sample": sample_name, "report_status": ["!=", "已发布"]}, "name")
		if existing:
			frappe.throw(f"样品 {sample_name} 已存在未发布 COA（{existing}），请勿重复生成。")

		coa = frappe.get_doc({
			"doctype": "HBOS COA",
			"sample": sample_name,
			"report_status": "草稿",
			"items": [_coa_item_from_result(r["name"]) for r in results],
		})
		coa.flags.allow_system_fields = True
		coa.insert(ignore_permissions=True)
		_commit()
		return coa.name
	except Exception:
		_rollback()
		raise


def _coa_print_html(coa):
	"""渲染 COA Print Format 模板：优先 Print Format 文档 html 字段，为空则读版本化 fixture 模板。"""
	from frappe.utils.jinja import render_template

	# 读取 fixture 模板（版本化来源，避免 DB 字段漂移）
	fixture = Path(__file__).parent / "print_format" / "hbos_coa" / "hbos_coa.html"
	template = fixture.read_text(encoding="utf-8")
	html = render_template(template, {"doc": coa})
	# 兜底：Print Format 文档自定义样式（css）
	pf = frappe.get_doc("Print Format", "HBOS COA")
	if pf.css:
		html = f"<style>{pf.css}</style>{html}"
	return html


def _coa_item_from_result(result_name):
	"""从已批准检测记录生成 COA 项目行（结果含单位 / 标准限度串 / 判定）。"""
	result = frappe.get_doc("HBOS Test Result", result_name)
	standard = _limits_text(result)
	return {
		"test_item": result.test_item,
		"item_name": result.item_name,
		"method_sop": frappe.get_value("HBOS Test Item", result.test_item, "method_sop") or "",
		"standard": standard,
		"result": _result_display_value(result),
		"verdict": result.verdict,
	}


@frappe.whitelist()
def review_coa(coa_name):
	"""QA 审核：草稿 -> 已审核。"""
	_check_action("review_coa")
	try:
		coa = frappe.get_doc("HBOS COA", coa_name)
		if coa.report_status != "草稿":
			frappe.throw(f"COA {coa_name} 状态为 {coa.report_status}，仅草稿可审核。")
		coa.report_status = "已审核"
		coa.qa_reviewer = _user()
		coa.qa_reviewed_at = _now()
		coa.flags.allow_system_fields = True
		coa.save(ignore_permissions=True)
		_commit()
		return coa.name
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def publish_coa(coa_name):
	"""发布 COA：生成 PDF 附件归档，状态 已审核 -> 已发布（发布后不可修改）。"""
	_check_action("publish_coa")
	try:
		coa = frappe.get_doc("HBOS COA", coa_name)
		if coa.qa_reviewer and coa.qa_reviewer == _user():
			_reject_sod("COA 发布人与审核人必须为不同账号。", doctype=coa.doctype, doc_name=coa.name)
		if coa.report_status != "已审核":
			frappe.throw(f"COA {coa_name} 状态为 {coa.report_status}，仅已审核可发布。")

		# 生成 PDF（直接渲染 Print Format 模板，绕开 website 渲染管线；中文支持）
		html = _coa_print_html(coa)
		pdf = frappe.utils.pdf.get_pdf(html)

		# 附件归档（私有文件，关联 COA）
		filename = f"{coa_name}.pdf"
		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": filename,
			"is_private": 1,
			"content": pdf,
			"attached_to_doctype": "HBOS COA",
			"attached_to_name": coa_name,
		})
		file_doc.insert(ignore_permissions=True)

		coa.pdf_attachment = file_doc.file_url
		coa.report_status = "已发布"
		coa.published_by = _user()
		coa.published_at = _now()
		coa.flags.allow_system_fields = True
		coa.save(ignore_permissions=True)
		_commit()
		return {"coa": coa.name, "pdf": file_doc.file_url}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def release_sample(sample_name):
	"""样品放行（Reviewer / Manager）：检验完成 -> 已放行。OOS 锁定不可放行。"""
	_check_action("release_sample")
	try:
		sample = frappe.get_doc("HBOS Sample", sample_name)
		if sample.oos_locked:
			frappe.throw(f"样品 {sample_name} 处于 OOS 锁定，不可放行。")
		if sample.status != "检验完成":
			frappe.throw(f"样品 {sample_name} 状态为 {sample.status}，仅检验完成样品可放行。")
		coa_name = frappe.db.get_value(
			"HBOS COA", {"sample": sample_name, "report_status": "已发布"}, "name"
		)
		if not coa_name:
			frappe.throw("样品放行前必须存在已发布 COA。")
		coa = frappe.get_doc("HBOS COA", coa_name)
		if not coa.pdf_attachment:
			frappe.throw(f"已发布 COA {coa_name} 缺少归档 PDF，不可放行。")

		_set_status(sample, wf.FLOW_SAMPLE, sample.status, "已放行")
		sample.flags.allow_system_fields = True
		sample.save(ignore_permissions=True)

		# 有 ERP Batch 引用时，把 LIMS 放行结果投影到 Inventory 的只读 Batch 字段。
		# Warehouse 只消费该投影，不拥有质量决定权。
		batch_ref = getattr(sample, "batch_ref", None)
		if batch_ref:
			from hb_inventory_app.hbos_inventory.quality_projection import project_release
			project_release(
				batch_ref,
				status="已放行",
				release_date=frappe.utils.today(),
				certificate_no=coa.name,
				certificate_file=coa.pdf_attachment,
				lims_reference=sample.name,
			)

		audit_log("放行", sample.doctype, sample.name,
				  action_text=f"样品放行 · COA {coa.name}",
				  field_changed="status", old_value="检验完成", new_value="已放行",
				  user=_user(), commit=False)
		_commit()
		return {"sample": sample.name, "coa": coa.name, "batch": batch_ref or ""}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def reject_sample(sample_name, reason=None):
	"""样品拒绝（Manager）：任意非终态 -> 已拒绝。"""
	_check_action("reject_sample")
	try:
		sample = frappe.get_doc("HBOS Sample", sample_name)
		_set_status(sample, wf.FLOW_SAMPLE, sample.status, "已拒绝")
		if reason:
			sample.remarks = (sample.remarks or "") + f" | 拒绝原因：{reason}"
		sample.flags.allow_system_fields = True
		sample.save(ignore_permissions=True)
		audit_log("拒绝", sample.doctype, sample.name,
				  action_text="样品拒绝",
				  field_changed="status", old_value="检验中", new_value="已拒绝",
				  reason=reason or "", user=_user(), commit=False)
		_commit()
		return sample.name
	except Exception:
		_rollback()
		raise


# ---------------------------------------------------------------------------
# 质量标准管理（新增 / 修订 / 升版 / 废止 / 删除）
# ---------------------------------------------------------------------------

SPEC_DRAFT = "草稿"
SPEC_ACTIVE = "已生效"
SPEC_OBSOLETE = "已废止"


def _spec_doc(spec_name):
	return frappe.get_doc("HBOS Specification", spec_name)


@frappe.whitelist()
def create_specification(spec_code, spec_name, material_code=None, material_name=None,
						 standard_source=None, effective_date=None, version=None, items=None,
						 remarks=None, storage_condition=None, retain_sample_qty=None):
	"""新增质量标准（Manager）：创建为草稿，检验项目明细从 items 传入。
	version 用于升版场景（基于当前版本 +0.1 复制为新版本）；缺省默认 1.0。
	storage_condition / retain_sample_qty 供样品登记时自动匹配。"""
	_check_action("create_specification")
	try:
		spec = frappe.get_doc({
			"doctype": "HBOS Specification",
			"spec_code": spec_code,
			"spec_name": spec_name,
			"material_code": material_code,
			"material_name": material_name,
			"standard_source": standard_source,
			"effective_date": effective_date,
			"version": version or "1.0",
			"status": SPEC_DRAFT,
			"remarks": remarks,
			"storage_condition": storage_condition,
			"retain_sample_qty": retain_sample_qty,
			"items": _normalize_spec_items(items),
		})
		spec.flags.allow_system_fields = True
		spec.insert(ignore_permissions=True)
		_commit()
		return spec.name
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def update_specification(spec_name, spec_code=None, spec_name_label=None, material_code=None,
						 material_name=None, standard_source=None, effective_date=None,
						 items=None, remarks=None, storage_condition=None, retain_sample_qty=None):
	"""修订质量标准（Manager）：编辑内容不改版本号；已废止不可再改。"""
	_check_action("update_specification")
	try:
		spec = _spec_doc(spec_name)
		if spec.status != SPEC_DRAFT:
			frappe.throw(f"质量标准 {spec_name} 状态为 {spec.status}，已生效/已废止版本不可原地修订；请复制生成新版本。")
		if spec_code:
			spec.spec_code = spec_code
		if spec_name_label:
			spec.spec_name = spec_name_label
		if material_code is not None:
			spec.material_code = material_code
		if material_name is not None:
			spec.material_name = material_name
		if standard_source:
			spec.standard_source = standard_source
		if effective_date:
			spec.effective_date = effective_date
		if remarks is not None:
			spec.remarks = remarks
		if storage_condition is not None:
			spec.storage_condition = storage_condition
		if retain_sample_qty is not None:
			spec.retain_sample_qty = retain_sample_qty
		if items is not None:
			spec.items = _normalize_spec_items(items)
		spec.flags.allow_system_fields = True
		spec.save(ignore_permissions=True)
		_commit()
		return spec.name
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def activate_specification(spec_name):
	"""生效质量标准（Manager）：草稿 -> 已生效。"""
	_check_action("activate_specification")
	try:
		spec = _spec_doc(spec_name)
		if spec.status != SPEC_DRAFT:
			frappe.throw(f"质量标准 {spec_name} 状态为 {spec.status}，仅草稿可生效。")
		spec.status = SPEC_ACTIVE
		spec.flags.allow_system_fields = True
		spec.save(ignore_permissions=True)
		audit_log("规格生效", spec.doctype, spec.name,
				  action_text="质量标准生效",
				  field_changed="status", old_value=SPEC_DRAFT, new_value=SPEC_ACTIVE,
				  user=_user(), commit=False)
		_commit()
		return spec.name
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def obsolete_specification(spec_name):
	"""废止质量标准（Manager）：已生效 -> 已废止。"""
	_check_action("obsolete_specification")
	try:
		spec = _spec_doc(spec_name)
		if spec.status != SPEC_ACTIVE:
			frappe.throw(f"质量标准 {spec_name} 状态为 {spec.status}，仅已生效可废止。")
		spec.status = SPEC_OBSOLETE
		spec.flags.allow_system_fields = True
		spec.save(ignore_permissions=True)
		audit_log("规格废止", spec.doctype, spec.name,
				  action_text="质量标准废止",
				  field_changed="status", old_value=SPEC_ACTIVE, new_value=SPEC_OBSOLETE,
				  user=_user(), commit=False)
		_commit()
		return spec.name
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def delete_specification(spec_name):
	"""删除质量标准（Manager）：仅草稿可删（已生效/已废止可能被样品引用）。"""
	_check_action("delete_specification")
	try:
		spec = _spec_doc(spec_name)
		if spec.status != SPEC_DRAFT:
			frappe.throw(f"质量标准 {spec_name} 状态为 {spec.status}，仅草稿可删除。")
		# 校验无样品引用
		referenced = frappe.db.exists("HBOS Sample", {"specification": spec_name})
		if referenced:
			frappe.throw(f"质量标准 {spec_name} 已被样品 {referenced} 引用，不可删除。")
		frappe.delete_doc("HBOS Specification", spec_name, force=1)
		_commit()
		return spec_name
	except Exception:
		_rollback()
		raise


def _normalize_spec_items(items):
	"""把前端传来的项目明细规范为子表行（字段名对齐 HBOS Specification Item）。"""
	if not items:
		return []
	rows = []
	for it in items or []:
		if not isinstance(it, dict):
			continue
		rows.append({
			"item": it.get("item") or it.get("test_item"),
			"item_name": it.get("item_name") or it.get("test_item"),
			"method_sop": it.get("method_sop") or it.get("method"),
			"limits_type": it.get("limits_type") or "记录型",
			"lower_limit": it.get("lower_limit"),
			"upper_limit": it.get("upper_limit"),
			"unit": it.get("unit"),
			"significant_digits": it.get("significant_digits"),
			"remark": it.get("remark"),
		})
	return rows


# ---------------------------------------------------------------------------
# 检验结果台账聚合查询（只读投影，对齐前端 ResultLedgerView 双模式）
# ---------------------------------------------------------------------------

LEDGER_SAMPLE_FIELDS = [
	"name", "material_name", "material_code", "batch_no", "sample_type",
	"sample_source", "specification", "spec_version", "priority", "status",
	"requestor", "received_date", "test_due_date", "creation", "remarks", "oos_locked",
]
LEDGER_RESULT_FIELDS = [
	"name", "sample", "item_name", "result_value", "result_text", "raw_value", "unit",
	"verdict", "result_status", "limits_type", "lower_limit", "upper_limit", "analyst",
	"submitted_at", "reviewer", "reviewed_at", "approver", "approved_at",
	"superseded_by", "creation",
]
LEDGER_REVISION_FIELDS = [
	"name", "result", "field_changed", "old_value", "new_value",
	"changed_by", "changed_at", "change_reason",
]


def _ledger_groups(samples):
	"""按 样品类型 → 样品种类 聚合批次数（对齐前端样品表左侧分组列表）。"""
	type_map = {}
	for s in samples:
		t = s.get("sample_type") or "未分类"
		m = s.get("material_name") or s.get("name") or "未知物料"
		if t not in type_map:
			type_map[t] = {}
		type_map[t][m] = type_map[t].get(m, 0) + 1
	return [
		{"type": t, "items": [{"material": m, "count": c} for m, c in mats.items()]}
		for t, mats in type_map.items()
	]


@frappe.whitelist()
def get_result_ledger(sample_type=None, material=None):
	"""检验结果台账聚合查询（只读）：返回 样品 + 检验项目受控记录 + 修订链 + COA 报告日期，
	对齐前端 ResultLedgerView 双模式渲染所需数据，避免前端多路 get_list 拼接。

	- samples: 样品主信息（含 report_date 派生自已发布 COA）
	- results: 检验项目受控记录（含 limits_text / display 服务端派生，superseded 链保留由前端过滤）
	- revisions: 修订记录
	- coas: {sample: 报告日期}
	- groups: 样品表左侧分组（类型 → 样品种类 → 批次数）
	"""
	_check_action("get_result_ledger")
	try:
		filters = {}
		if sample_type:
			filters["sample_type"] = sample_type
		if material:
			filters["material_name"] = material

		samples = frappe.get_all(
			"HBOS Sample",
			filters=filters,
			fields=LEDGER_SAMPLE_FIELDS,
			order_by="creation asc",
		)
		sample_names = [s["name"] for s in samples]

		coa_map = {}
		if sample_names:
			for c in frappe.get_all(
				"HBOS COA",
				filters={"sample": ["in", sample_names], "report_status": "已发布"},
				fields=["sample", "published_at"],
			):
				if c["published_at"]:
					coa_map[c["sample"]] = str(c["published_at"])[:10]

		results = []
		revisions = []
		if sample_names:
			results = frappe.get_all(
				"HBOS Test Result",
				filters={"sample": ["in", sample_names]},
				fields=LEDGER_RESULT_FIELDS,
				order_by="creation asc",
			)
			if results:
				revisions = frappe.get_all(
					"HBOS Result Revision",
					filters={"result": ["in", [r["name"] for r in results]]},
					fields=LEDGER_REVISION_FIELDS,
					order_by="changed_at desc",
				)

		# 服务端派生字段（前端可直接消费）
		for s in samples:
			s["report_date"] = coa_map.get(s["name"], "")
		for r in results:
			doc = frappe._dict(r)
			r["limits_text"] = _limits_text(doc) if r.get("limits_type") else ""
			r["display"] = _result_display_value(doc)

		return {
			"samples": samples,
			"results": results,
			"revisions": revisions,
			"coas": coa_map,
			"groups": _ledger_groups(samples),
			"meta": {"total_samples": len(samples)},
		}
	except Exception:
		_rollback()
		raise


# ---------------------------------------------------------------------------
# 合规审计日志查询（只读，对齐前端 合规审计日志 页）
# ---------------------------------------------------------------------------

LEDGER_AUDIT_FIELDS = [
	"name", "log_type", "doctype_target", "doc_name", "action_text",
	"field_changed", "old_value", "new_value", "reason", "user",
	"created_at", "checksum",
]


@frappe.whitelist()
def get_audit_log(log_type=None, doctype_target=None, user=None,
				  keyword=None, from_date=None, to_date=None, limit=500, offset=0):
	"""合规审计日志查询（只读）：分页返回审计事件流，支持类型/对象/操作人/关键字/时间筛选。
	返回 events（当前页）与 total（满足筛选的全部条数，供前端真分页，保证历史可逐页看全）。"""
	_check_action("get_audit_log")
	try:
		filters = []
		or_filters = []
		if log_type:
			filters.append(["log_type", "=", log_type])
		if doctype_target:
			filters.append(["doctype_target", "=", doctype_target])
		if user:
			filters.append(["user", "=", user])
		if from_date:
			filters.append(["created_at", ">=", from_date + " 00:00:00"])
		if to_date:
			filters.append(["created_at", "<=", to_date + " 23:59:59"])
		if keyword:
			kw = f"%{keyword}%"
			or_filters.extend([
				["doc_name", "like", kw],
				["action_text", "like", kw],
				["checksum", "like", kw],
			])
		def _conds(arr):
			parts, ps = [], []
			for item in arr:
				fld, op, val = item[0], str(item[1]), item[2]
				op_sql = "LIKE" if op.lower() == "like" else op if op in (">=", "<=", ">", "<", "=") else "="
				parts.append("`{}` {} %s".format(fld, op_sql))
				ps.append(val)
			return parts, ps

		and_parts, a_ps = _conds(filters)
		or_parts, o_ps = _conds(or_filters)
		where = []
		if and_parts:
			where.append(" AND ".join(and_parts))
		if or_parts:
			where.append("( " + " OR ".join(or_parts) + " )")
		sql = "SELECT COUNT(*) FROM `tabHBOS Audit Log`"
		if where:
			sql += " WHERE " + " AND ".join(where)
		total = frappe.db.sql(sql, a_ps + o_ps)[0][0] or 0
		page_size = max(1, min(int(limit or 500), 500))
		start = max(0, int(offset or 0))
		rows = frappe.get_all(
			"HBOS Audit Log",
			filters=filters,
			or_filters=or_filters,
			fields=LEDGER_AUDIT_FIELDS,
			order_by="created_at desc",
			limit_page_length=page_size,
			limit_start=start,
		)
		return {"events": rows, "total": total}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def get_audit_targets():
	"""审计『对象』筛选抽屉：返回全部审计数据中出现过的对象类型（非仅当前页），
	供前端按业务板块分组的下拉（业务操作 / 报告与标准 / 质量主数据 / 留样管理等）。"""
	_check_action("get_audit_log")
	rows = frappe.db.sql(
		"SELECT DISTINCT doctype_target FROM `tabHBOS Audit Log`"
		" WHERE doctype_target IS NOT NULL AND doctype_target <> ''"
		" ORDER BY doctype_target", as_list=True)
	return [r[0] for r in rows]
