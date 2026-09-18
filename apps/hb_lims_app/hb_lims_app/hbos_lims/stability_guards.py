# -*- coding: utf-8 -*-
"""M2-R8 稳定性板块：控制器层写入守卫（方案 6.1 / 7.7 / 8.6）。

两层保护，与 R7 `HBOS Retention Sample._guard_system_fields` 同一模式：
1. 系统字段守卫——状态、签署、版本链等系统字段只能由业务服务（带
   `allow_system_fields` 标记）或 System Manager / Administrator 修改；
   表单直改、`frappe.client.set_value` 等低层写入一律拦截。
2. 冻结快照守卫——`snapshot_frozen=1` 后快照字段只读（方案 7.7）。

低层直写（`frappe.db.set_value` / 裸 SQL）绕过 validate 是设计已知项，
其后果由 8.6 运行期一致性扫描检出（见方案 8.6，R8B 起落地）。
"""

import frappe

NOTICE_SYSTEM_FIELDS = (
	"status", "snapshot_frozen", "version", "supersedes",
	"register_review_by", "register_review_date",
	"qa_applicant", "apply_date",
	"qc_manager_confirm_by", "qc_manager_confirm_date",
	"approver_by", "approve_date",
	"reject_reason", "reject_by", "reject_date",
	"cancel_reason", "cancel_by", "cancel_date",
)

PROTOCOL_SYSTEM_FIELDS = (
	"status", "snapshot_frozen", "version", "supersedes",
	"drafted_by", "draft_date",
	"qa_review_by", "qa_review_date",
	"qa_approve_by", "approve_date", "effective_date",
	"reject_reason", "reject_by", "reject_date",
	"void_reason", "void_by", "void_date",
)


def _privileged():
	if frappe.session.user == "Administrator":
		return True
	return "System Manager" in frappe.get_roles()


def guard_system_fields(doc, fields):
	"""系统字段守卫：非特权用户且未经服务授权时，系统字段不得变化。"""
	before = doc.get_doc_before_save()
	if not before or _privileged() or doc.flags.get("allow_system_fields"):
		return
	for field in fields:
		if str(before.get(field) or "") != str(doc.get(field) or ""):
			frappe.throw(
				"字段「{}」为系统字段，只能通过业务操作（服务方法）修改，禁止直接编辑。".format(field)
			)


def guard_snapshot_frozen(doc, fields, flag_field="snapshot_frozen"):
	"""冻结快照守卫：快照已冻结时，快照字段只读（方案 7.7）。"""
	before = doc.get_doc_before_save()
	if not before or not before.get(flag_field):
		return
	if doc.flags.get("allow_system_fields"):
		return
	for field in fields:
		if str(before.get(field) or "") != str(doc.get(field) or ""):
			frappe.throw(
				"字段「{}」已随快照冻结，批准后不可修改；如需变更请生成新版本（方案 7.7）。".format(field)
			)


# 删除拦截允许状态（方案 8.3 主 DocType 删除拦截表）；None = 全部禁删
NOTICE_DELETABLE_STATUSES = ("草稿", "已驳回", "已取消")
PROTOCOL_DELETABLE_STATUSES = ("草稿",)
MASTER_DELETABLE_STATUSES = None
# Stability Sample：全生命周期禁删（方案 8.3）
SAMPLE_DELETABLE_STATUSES = ()
# Stability Timepoint：仅「待取样」可删（且要求无取样/检测/延期记录，由控制器另判）
TIMEPOINT_DELETABLE_STATUSES = ("待取样",)

# ---- M2-R8B 样品与时间点的系统字段（只允许业务服务写入，方案 8.6） ----

SAMPLE_SYSTEM_FIELDS = (
	"status", "current_qty", "start_date", "condition_snapshot",
	"need_evaluation", "evaluated_by", "evaluation_date",
	"stored_by", "reviewed_by", "reviewed_date",
	"pre_disposal_status", "disposal_mark_reason",
	"disposal_marked_by", "disposal_marked_date",
	"disposal_cancel_reason", "disposal_cancelled_by", "disposal_cancelled_date",
)

TIMEPOINT_SYSTEM_FIELDS = (
	"status", "sample_cond_point_key", "time_point_label",
	"plan_sample_date", "plan_test_date", "delay_limit_days",
	"is_full_test", "sample_by", "test_by",
	"extra_approver_by", "extra_approve_date", "cancel_reason",
)


def _audit_delete_block(doctype, doc_name, action_text, reason):
	"""删除拦截审计独立提交（方案 8.7）：不随 frappe.throw 的回滚丢失。"""
	from hb_lims_app.hbos_lims.lims_service import audit_log
	try:
		audit_log("删除拦截", doctype, doc_name, action_text=action_text,
				  reason=reason, commit=True)
	except Exception as exc:
		frappe.log_error("删除拦截审计写入失败：{}".format(exc), "HBOS Stability 删除审计")


def guard_delete(doc, doctype, deletable_statuses):
	"""删除拦截（方案 8.3）：受控状态的记录禁止删除，抛错前先独立提交审计（8.7）。

	主数据一律禁删（`deletable_statuses=None`），改用 `is_active=0` 停用。
	"""
	status = doc.get("status")
	if deletable_statuses is not None and status in deletable_statuses:
		return
	_audit_delete_block(doctype, doc.name,
						"删除拦截：{}（状态 {}）".format(doc.name, status or "无状态"),
						"受控记录不允许删除（方案 8.3）；主数据请用「停用」代替删除")
	frappe.throw("「{}」当前状态（{}）不允许删除（方案 8.3）；主数据请用「停用」代替删除。".format(
		doc.name, status or "无状态"))
