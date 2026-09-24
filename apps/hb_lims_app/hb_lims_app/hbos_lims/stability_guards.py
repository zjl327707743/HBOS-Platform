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
	if _privileged() or doc.flags.get("allow_system_fields"):
		return
	if not before:
		# 新建时没有 before 文档，仍须禁止通过通用 insert 伪造审批/状态。
		# 仅允许 DocType 自身声明的默认值（通常是“草稿”/0/1）进入初始文档。
		meta = frappe.get_meta(doc.doctype)
		for field in fields:
			value = doc.get(field)
			df = meta.get_field(field)
			default = df.default if df else None
			if str(value or "") != str(default or ""):
				frappe.throw(
					"字段「{}」为系统字段，只能通过业务操作（服务方法）设置，禁止通过直接新建写入。".format(field)
				)
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


def _table_signature(rows, child_doctype):
	"""子表内容指纹：按行内容排序拼接，用于判断「行是否被增删改」（行序变化不算）。"""
	if not rows:
		return ""
	fieldnames = [f.fieldname for f in frappe.get_meta(child_doctype).fields
				  if f.fieldname and f.fieldtype not in ("Section Break", "Column Break", "Tab Break")]
	lines = []
	for row in rows:
		lines.append("|".join(str(row.get(f) or "") for f in fieldnames))
	return "\n".join(sorted(lines))


def guard_child_table_frozen(doc, table_field):
	"""子表冻结守卫：服务专用写入的流水子表，行不得被非特权用户直接增删改（方案 8.3 / 8.6）。

	仅在文档已有前值（非首次插入）时生效；业务服务写入前须置 `allow_system_fields`。
	"""
	before = doc.get_doc_before_save()
	if not before or _privileged() or doc.flags.get("allow_system_fields"):
		return
	child_doctype = frappe.get_meta(doc.doctype).get_field(table_field).options
	if _table_signature(before.get(table_field), child_doctype) != \
			_table_signature(doc.get(table_field), child_doctype):
		frappe.throw("「{}」为服务专用写入的流水子表，禁止直接增删改（方案 8.6）。".format(table_field))


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

# ---- M2-R8C 结果与报告 ----

# Result：仅「草稿」可删（方案 8.3）
RESULT_DELETABLE_STATUSES = ("草稿",)
# Report：仅「草稿」可删
REPORT_DELETABLE_STATUSES = ("草稿",)

RESULT_SYSTEM_FIELDS = (
	"status", "is_current", "result_version_key", "revision_no", "supersedes",
	"stability_sample", "item_snapshot", "method_version", "spec_limit", "spec_version",
	"source_test_result",
	"result_baseline", "baseline_ref", "baseline_doctype", "baseline_name",
	"is_qualified", "is_significant_change", "significant_change_basis", "is_zero_month",
	"oos_flag", "oot_flag",
	"analyst", "submitted_by", "submitted_at", "reviewed_by", "reviewed_at",
	"approved_by", "approved_at", "return_reason", "void_reason",
)

# 注：`client_code` / `client` **不列入**系统字段守卫——它们由控制器按 `customer`
# 只读派生（方案 5.4.2），其防篡改由「派生不一致即拒绝」保证，见控制器 _sync_customer。
REPORT_SYSTEM_FIELDS = (
	"status", "report_period_key", "seq",
	"proposed_validity_months", "proposed_validity_date",
	"proposed_validity_type", "proposed_validity_basis",
	"drafted_by", "draft_date", "qa_review_by", "qa_review_date",
	"qa_approve_by", "approve_date", "reject_reason", "void_reason",
)

# ---- M2-R8D 变更 / 稳定性室 / 设备 / 故障 ----

# Change：草稿、已取消可删（方案 8.3）
CHANGE_DELETABLE_STATUSES = ("草稿", "已取消")
# Room Log：温湿度原始记录全状态禁删；Equipment：台账禁删（用「停用」）；Fault Ticket：待处理可删
ROOM_LOG_DELETABLE_STATUSES = ()
EQUIPMENT_DELETABLE_STATUSES = ()
FAULT_DELETABLE_STATUSES = ("待处理",)

CHANGE_SYSTEM_FIELDS = (
	"status", "supersedes",
	"qa_review_by", "qa_review_date", "approver_by", "approve_date", "reject_reason",
	"implement_record", "implement_by", "implement_date",
	"post_assessment", "post_assessment_result", "post_assess_by", "post_assess_date",
	"applicant", "apply_date",
)
ROOM_LOG_SYSTEM_FIELDS = (
	"room_date_period_key", "temp_min", "temp_max", "humidity_min", "humidity_max",
	"within_spec", "status",
)
FAULT_SYSTEM_FIELDS = ("status", "last_fault_date", "handler", "handle_date")

# 注：Equipment 的 `status` 是受控终止机制（方案 8.3 用「停用」代替删除），
# `last_fault_date` 由 `open_fault_ticket` 派生回写——两者均须经业务服务写入。
EQUIPMENT_SYSTEM_FIELDS = ("status", "last_fault_date")


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


def validate_customer_code(doc, method=None):
	"""Customer 命名规范强制校验（方案 5.4.2 ②a，注册在 `doc_events["Customer"]["validate"]`）。

	**仅当该客户已被稳定性专项报告引用时生效**，由此同时满足方案的两条要求：
	「validate 钩子强制校验」与「不改核心源码、**不干扰非稳定性客户**」。
	真正要防的是「在用客户被改名」破坏 `report_period_key`（键含 client_code）。
	"""
	from hb_lims_app.hbos_lims import stability_contract as stb
	if not frappe.db.exists("DocType", "HBOS Stability Report"):
		return
	if not doc.name or not frappe.db.exists("HBOS Stability Report", {"customer": doc.name}):
		return
	ok, err = stb.check_customer_code(doc.name)
	if not ok:
		frappe.throw(err)
