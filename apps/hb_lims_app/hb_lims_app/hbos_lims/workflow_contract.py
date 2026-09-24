# -*- coding: utf-8 -*-
"""LIMS 检验流程状态机契约（零 Frappe 依赖，可离线单测）。

业务口径来自《海滨药业LIMS系统开发方案》模块 3 检验流程管理：
样品登记 → 任务分配 → 检验执行 → 数据录入 → 自动判定 → 复核 → 放行。
OOS 触发：判定不合格 → OOS候选 → OOS锁定（禁止放行）。
"""

# M2-R8A 稳定性流程转移表由 stability_contract 单一持有，此处只做合并引用
# （R7 时期 retention 转移表在两处重复定义，此处不再重复，避免双源漂移）
from hb_lims_app.hbos_lims import stability_contract as stb_contract

# 流程类型
FLOW_SAMPLE = "sample"
FLOW_TASK = "task"
FLOW_RESULT = "result"
FLOW_RETENTION = "retention"
FLOW_USAGE_APPLY = "usage_apply"
FLOW_DISPOSAL_APPLY = "disposal_apply"

# 样品状态
SAMPLE_DRAFT = "草稿"
SAMPLE_REGISTERED = "已登记"
SAMPLE_TESTING = "检验中"
SAMPLE_TESTED = "检验完成"
SAMPLE_RELEASED = "已放行"
SAMPLE_REJECTED = "已拒绝"
SAMPLE_OOS = "OOS锁定"

# 任务状态
TASK_PENDING = "待分配"
TASK_ASSIGNED = "已分配"
TASK_TESTING = "检验中"
TASK_SUBMITTED = "已提交"
TASK_REVIEWED = "已复核"
TASK_APPROVED = "已批准"
TASK_OOS_CANDIDATE = "OOS候选"
TASK_OOS_LOCKED = "OOS锁定"

# 结果状态
RESULT_DRAFT = "草稿"
RESULT_SUBMITTED = "已提交"
RESULT_REVIEWED = "已复核"
RESULT_APPROVED = "已批准"
RESULT_REVISED = "已修订"

# 系统字段（状态 / 签署 / 版本链）：只能由业务服务（lims_service 中带
# `doc.flags.allow_system_fields = True` 的保存）或 System Manager / Administrator 修改；
# 表单直改、frappe.client.set_value 等低层写入由控制器守卫拦截
# （实现见 guards.guard_system_fields）。命名带 DocType 前缀，避免与稳定性板块
# stability_guards 中的同名常量混淆。
HBOS_SAMPLE_SYSTEM_FIELDS = ("status", "oos_locked")

HBOS_SAMPLE_TASK_SYSTEM_FIELDS = ("status", "assignee", "assigned_by", "assigned_date", "result")

HBOS_TEST_RESULT_SYSTEM_FIELDS = (
	"result_status", "is_oos_candidate", "superseded_by",
	"submitted_signature", "submitted_at",
	"reviewer", "reviewed_signature", "reviewed_at",
	"approver", "approved_signature", "approved_at",
)

HBOS_COA_SYSTEM_FIELDS = (
	"report_status", "qa_reviewer", "qa_reviewed_at",
	"published_by", "published_at", "pdf_attachment",
)

HBOS_SPECIFICATION_SYSTEM_FIELDS = ("status", "effective_date")

# 留样状态（M2-R7，方案 6.1 rev6）
RET_IN_STOCK = "在库"
RET_PARTIAL_USED = "部分使用"
RET_EXHAUSTED = "已用尽"
RET_PENDING = "待处理"
RET_DESTROYED = "已销毁"
RET_TRANSFERRED = "已转出"

RETENTION_TRANSITIONS = {
	RET_IN_STOCK: {RET_PARTIAL_USED, RET_PENDING, RET_TRANSFERRED},
	RET_PARTIAL_USED: {RET_PARTIAL_USED, RET_EXHAUSTED, RET_PENDING, RET_TRANSFERRED},
	RET_EXHAUSTED: {RET_PENDING, RET_TRANSFERRED},
	# 回退按进入待处理前的状态快照恢复（rev6）
	RET_PENDING: {RET_DESTROYED, RET_IN_STOCK, RET_PARTIAL_USED},
	RET_DESTROYED: set(),
	RET_TRANSFERRED: set(),
}

# 使用申请状态（方案 6.1 FLOW_USAGE_APPLY）
USE_DRAFT = "草稿"
USE_WAIT_STOCK = "待库存确认"
USE_WAIT_QC = "待QC批准"
USE_WAIT_QA = "待QA批准"
USE_WAIT_QM = "待QM批准"
USE_APPROVED = "已批准"
USE_EXECUTED = "已执行"
USE_REJECTED = "已驳回"
USE_CANCELLED = "已取消"

# 处理申请状态（方案 6.1 FLOW_DISPOSAL_APPLY；QA 负责人层由 qa_manager_required 决定）
DSP_DRAFT = "草稿"
DSP_WAIT_QC_SUP = "待QC主管审核"
DSP_WAIT_QC_LEAD = "待QC负责人审核"
DSP_WAIT_QA_REVIEW = "待QA审核"
DSP_WAIT_QA_LEAD = "待QA负责人审核"
DSP_WAIT_QM = "待QM批准"
DSP_APPROVED = "已批准"
DSP_WAIT_EXECUTE = "待执行"
DSP_DONE = "已完成"
DSP_REJECTED = "已驳回"
DSP_CANCELLED = "已取消"

USAGE_APPLY_TRANSITIONS = {
	USE_DRAFT: {USE_WAIT_STOCK, USE_CANCELLED},
	USE_WAIT_STOCK: {USE_WAIT_QC, USE_REJECTED},
	USE_WAIT_QC: {USE_WAIT_QA, USE_REJECTED},
	USE_WAIT_QA: {USE_WAIT_QM, USE_REJECTED},
	USE_WAIT_QM: {USE_APPROVED, USE_REJECTED},
	USE_APPROVED: {USE_EXECUTED, USE_CANCELLED},  # rev6 逃生口：已批准→已取消（Manager、释放预占）
	USE_EXECUTED: set(),
	USE_REJECTED: set(),
	USE_CANCELLED: set(),
}

DISPOSAL_APPLY_TRANSITIONS = {
	DSP_DRAFT: {DSP_WAIT_QC_SUP, DSP_CANCELLED},
	DSP_WAIT_QC_SUP: {DSP_WAIT_QC_LEAD, DSP_REJECTED},
	DSP_WAIT_QC_LEAD: {DSP_WAIT_QA_REVIEW, DSP_REJECTED},
	# 双路径：5 级经 QA 负责人；4 级（qa_manager_required=0）跳过直达 QM（rev3/6.5）
	DSP_WAIT_QA_REVIEW: {DSP_WAIT_QA_LEAD, DSP_WAIT_QM, DSP_REJECTED},
	DSP_WAIT_QA_LEAD: {DSP_WAIT_QM, DSP_REJECTED},
	DSP_WAIT_QM: {DSP_APPROVED, DSP_REJECTED},
	DSP_APPROVED: {DSP_WAIT_EXECUTE},
	DSP_WAIT_EXECUTE: {DSP_DONE, DSP_CANCELLED},  # rev6 逃生口：待执行→已取消（Manager）
	DSP_DONE: set(),
	DSP_REJECTED: set(),
	DSP_CANCELLED: set(),
}

# 角色
ROLE_MANAGER = "LIMS Manager"
ROLE_ANALYST = "LIMS Analyst"
ROLE_REVIEWER = "LIMS Reviewer"
ROLE_SYSTEM = "System Manager"
ROLE_LIMS_QA = "LIMS QA"
# M2-R8A 新增两角色（Owner 2026-09-16 确认采纳方案 6.2；QM ≠ QP、QA 经理 ≠ QA 审核人）
ROLE_LIMS_QA_MANAGER = "LIMS QA Manager"   # QA 经理：一般变更批准
ROLE_LIMS_QP = "LIMS QP"                   # 质量受权人：重大变更批准 / 方案与报告作废

# 状态转移表（current -> allowed targets）
SAMPLE_TRANSITIONS = {
	SAMPLE_DRAFT: {SAMPLE_REGISTERED, SAMPLE_REJECTED},
	SAMPLE_REGISTERED: {SAMPLE_TESTING, SAMPLE_REJECTED, SAMPLE_OOS},
	SAMPLE_TESTING: {SAMPLE_TESTED, SAMPLE_OOS},
	SAMPLE_TESTED: {SAMPLE_RELEASED, SAMPLE_REJECTED},
	SAMPLE_RELEASED: set(),
	SAMPLE_REJECTED: set(),
	SAMPLE_OOS: set(),
}

TASK_TRANSITIONS = {
	TASK_PENDING: {TASK_ASSIGNED},
	TASK_ASSIGNED: {TASK_TESTING},
	TASK_TESTING: {TASK_SUBMITTED, TASK_OOS_CANDIDATE},
	TASK_SUBMITTED: {TASK_REVIEWED, TASK_OOS_CANDIDATE},
	TASK_REVIEWED: {TASK_APPROVED, TASK_OOS_CANDIDATE},
	TASK_APPROVED: {TASK_SUBMITTED},  # 已批准结果修订后回退待复核
	TASK_OOS_CANDIDATE: {TASK_OOS_LOCKED, TASK_TESTING},  # 人工确认锁定，或解除 OOS 回到检验
	TASK_OOS_LOCKED: set(),
}

RESULT_TRANSITIONS = {
	RESULT_DRAFT: {RESULT_SUBMITTED, RESULT_REVISED},
	RESULT_SUBMITTED: {RESULT_REVIEWED, RESULT_REVISED},
	RESULT_REVIEWED: {RESULT_APPROVED, RESULT_REVISED},
	RESULT_APPROVED: set(),
	RESULT_REVISED: set(),
}

FLOW_TRANSITIONS = {
	FLOW_SAMPLE: SAMPLE_TRANSITIONS,
	FLOW_RETENTION: RETENTION_TRANSITIONS,
	FLOW_USAGE_APPLY: USAGE_APPLY_TRANSITIONS,
	FLOW_DISPOSAL_APPLY: DISPOSAL_APPLY_TRANSITIONS,
	FLOW_TASK: TASK_TRANSITIONS,
	FLOW_RESULT: RESULT_TRANSITIONS,
	# M2-R8A 稳定性（R8B~R8D 的 Sample/Timepoint/Result/Report/Change/Fault 按子轮增量并入）
	**stb_contract.STABILITY_FLOW_TRANSITIONS,
}

# 动作 -> 允许角色（动作语义见 lims_service）
ACTION_ROLES = {
	"register_sample": {ROLE_ANALYST, ROLE_MANAGER},
	"generate_tasks": {ROLE_MANAGER},
	"assign_task": {ROLE_MANAGER},
	"start_task": {ROLE_ANALYST, ROLE_MANAGER},
	"submit_result": {ROLE_ANALYST, ROLE_MANAGER},
	"review_result": {ROLE_REVIEWER, ROLE_MANAGER},
	"approve_result": {ROLE_REVIEWER, ROLE_MANAGER},
	"revise_result": {ROLE_MANAGER},
	"confirm_oos": {ROLE_MANAGER},
	"release_sample": {ROLE_REVIEWER, ROLE_MANAGER},
	"reject_sample": {ROLE_MANAGER},
	"create_coa": {ROLE_REVIEWER, ROLE_MANAGER},
	"review_coa": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_MANAGER},
	"publish_coa": {ROLE_LIMS_QA, ROLE_MANAGER},
	# 质量标准管理（Manager 维护主数据）
	"create_specification": {ROLE_MANAGER},
	"update_specification": {ROLE_MANAGER},
	"delete_specification": {ROLE_MANAGER},
	"activate_specification": {ROLE_MANAGER},
	"obsolete_specification": {ROLE_MANAGER},
	# 检验结果台账聚合查询（只读，所有 LIMS 角色 + System）
	"get_result_ledger": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	# 留样板块 R7A（方案 6.3 动作矩阵，角色方案 B）
	"register_retention": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"adjust_stock": {ROLE_MANAGER, ROLE_SYSTEM},
	# 留样板块 R7B 观察管理（矩阵：录入 Analyst/Reviewer/Manager；审核 Reviewer/QA/Manager；选取 Reviewer/Manager）
	"select_obs_batch": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"cancel_obs_batch": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"record_observation": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"review_observation": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	# 留样板块 R7C 使用/处理审批（QC 线 Reviewer / QA 线 LIMS QA / QM Manager；逃生口仅 Manager）
	"create_usage_apply": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"usage_confirm": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"usage_qc": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"usage_qa": {ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	"usage_qm": {ROLE_MANAGER, ROLE_SYSTEM},
	"usage_execute": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"usage_reject": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	"usage_cancel": {ROLE_MANAGER, ROLE_SYSTEM},
	"create_disposal_apply": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"disposal_qc": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"disposal_qa": {ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	"disposal_qm": {ROLE_MANAGER, ROLE_SYSTEM},
	"disposal_handler": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"disposal_monitor": {ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	"disposal_cancel": {ROLE_MANAGER, ROLE_SYSTEM},
	"transfer_out": {ROLE_MANAGER, ROLE_SYSTEM},
	# 留样板块只读聚合（4 报表口径 + 台账，LIMS 全角色 + System）
	"get_retention_dashboard": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	"get_retention_ledger": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	"get_observation_plan": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	"get_disposal_quarterly": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	# 合规审计日志查询（只读，Reviewer / Manager / System 可读）
	"get_audit_log": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	# ---- M2-R8A 稳定性板块（方案 6.3.1 / 6.3.2 动作矩阵逐行落地）----
	# 通知单提出方为 QA 线（方案 5.2.1 `qa_applicant`），建档动作同权限
	"create_notice": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	# 6.3.1 FLOW_STB_NOTICE
	"register_review": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"submit_notice": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"confirm_notice_qc": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"approve_notice": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"reject_notice": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"cancel_notice": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"close_notice": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	# 6.3.2 FLOW_STB_PROTOCOL
	"submit_protocol": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	# 方案 5.2.2 定义 qa_review_by / qa_approve_by 两个签署位，6.4 要求
	# 「QA 审核人 ≠ QA 批准人」——审核为状态不变的准入动作（同 register_review 模式），
	# 角色取 6.3.6 review_report 行口径
	"review_protocol": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
						ROLE_MANAGER, ROLE_SYSTEM},
	"approve_protocol": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"reject_protocol": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"void_protocol": {ROLE_LIMS_QP, ROLE_MANAGER, ROLE_SYSTEM},
	# 主数据维护（对齐既有 create_specification 惯例：Manager 维护主数据）
	"manage_stability_master": {ROLE_MANAGER, ROLE_SYSTEM},
	# 稳定性只读聚合（工作台 / 通知单台账）
	"get_stability_dashboard": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
								ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_notices": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							  ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_notice_detail": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
									ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	# 主数据与方案的只读接口（前端「考察申请与方案」建档与各 tab 数据源）
	"get_stability_master": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							 ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_products": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							   ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_protocols": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
								ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_audit": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	# ---- M2-R8B 稳定性样品与时间点（方案 6.3.3 / 6.3.4 动作矩阵逐行落地）----
	# 注：`adjust_stock` / `transfer_out` 与 R7 留样同名（方案 6.3.3 即如此命名），
	#     两者角色集一致（Manager + System）；此处沿用既有条目，不再重复注册。
	"register_stability_sample": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"review_sample_storage": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_MANAGER, ROLE_SYSTEM},
	"record_sampling": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"return_sample": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"mark_for_disposal": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
						  ROLE_MANAGER, ROLE_SYSTEM},
	"cancel_disposal": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
						ROLE_MANAGER, ROLE_SYSTEM},
	"dispose_sample": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"generate_timepoints": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"complete_sampling": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"import_zero_month_result": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"start_testing": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	# 系统触发动作（门禁 10/20：角色豁免、动作名不豁免）——由服务内部调用，用户不可直接调用
	# 注：三者均**无 @frappe.whitelist**（非公开入口）；complete_testing 由 approve_result
	#     在全部必检项目获批后自动调用，reopen_timepoint 由 void_result 调用。
	"complete_testing": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
						 ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"reopen_timepoint": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
						 ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"cancel_timepoint": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
						 ROLE_MANAGER, ROLE_SYSTEM},
	"append_conditions": {ROLE_REVIEWER, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"apply_delay": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"approve_delay": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
					  ROLE_MANAGER, ROLE_SYSTEM},
	"reject_delay": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
					 ROLE_MANAGER, ROLE_SYSTEM},
	"approve_extra_sampling": {ROLE_MANAGER, ROLE_SYSTEM},
	# R8B 只读
	"get_stability_samples": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							  ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_sample_detail": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
									ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_schedule": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							   ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_timepoint_detail": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
									   ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_delays": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							 ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	# ---- M2-R8C 稳定性结果与报告（方案 6.3.5 / 6.3.6）----
	# 注：`submit_result` / `review_result` / `approve_result` / `revise_result` 与 R3 检验流程
	#     同名但角色不同，见 SCOPED_ACTION_ROLES（按 DocType 作用域覆盖，避免互相放宽）。
	"void_result": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"return_result": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"record_result": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"mark_superseded": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
						ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"eval_trend": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"create_stability_report": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"save_report_draft": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"submit_report": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"review_report": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
					  ROLE_MANAGER, ROLE_SYSTEM},
	"approve_report": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"reject_report": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"void_report": {ROLE_LIMS_QP, ROLE_MANAGER, ROLE_SYSTEM},
	# R8C 只读
	"get_stability_results": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							  ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_result_detail": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
									ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_trend": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_reports": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							  ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_report_detail": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
									ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_validity_advice": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
									  ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_customer_scan": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
									ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	# ---- M2-R8D 变更、稳定性室与设备（方案 6.3.7 / 6.3.8）----
	"create_change": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
					  ROLE_MANAGER, ROLE_SYSTEM},
	"submit_change": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"review_change": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	# 一般变更批准 QA 经理专属（S7：无 Manager 兜底）；重大变更批准 QP 专属
	"approve_change_general": {ROLE_LIMS_QA_MANAGER, ROLE_SYSTEM},
	"approve_change_major": {ROLE_LIMS_QP, ROLE_SYSTEM},
	"reject_change": {ROLE_LIMS_QA_MANAGER, ROLE_LIMS_QP, ROLE_MANAGER, ROLE_SYSTEM},
	"cancel_change": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
					  ROLE_MANAGER, ROLE_SYSTEM},
	"implement_change": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"assess_change": {ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"reopen_change": {ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	"log_room_env": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"manage_equipment": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"open_fault_ticket": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"start_fault_handling": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"submit_fault_assessment": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"return_fault_handling": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"close_fault_ticket": {ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER,
						   ROLE_MANAGER, ROLE_SYSTEM},
	# R8D 只读
	"get_stability_changes": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
							  ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_change_detail": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
									ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_room_logs": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
								ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_equipments": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
								 ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
	"get_stability_fault_tickets": {ROLE_ANALYST, ROLE_REVIEWER, ROLE_LIMS_QA,
									ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_LIMS_QP, ROLE_SYSTEM},
}

# 同名但角色不同的动作：按 DocType 作用域覆盖（见 action_allowed 文档）
SCOPED_ACTION_ROLES = {
	("HBOS Stability Result", "submit_result"):
		{ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	("HBOS Stability Result", "review_result"):
		{ROLE_REVIEWER, ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	("HBOS Stability Result", "approve_result"):
		{ROLE_LIMS_QA, ROLE_LIMS_QA_MANAGER, ROLE_MANAGER, ROLE_SYSTEM},
	("HBOS Stability Result", "revise_result"):
		{ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
}


def can_transition(flow, current, target):
	"""状态转移合法性（纯状态表检查，不含角色）。"""
	table = FLOW_TRANSITIONS.get(flow)
	if not table:
		return False
	allowed = table.get(current)
	if allowed is None:
		return False
	return target in allowed


def action_allowed(action, actor_role, scope=None):
	"""角色是否允许执行指定动作。

	`scope`（DocType 名）用于同名但角色不同的动作。

	治理约束：System Manager 是技术运维角色，不是质量业务批准角色。
	即使历史 ACTION_ROLES 里仍保留 ROLE_SYSTEM 作为兼容记录，它也只能执行
	`get_*` 只读动作；任何状态、签署、主数据、处置等写动作必须持有明确 LIMS 业务角色。
	真正的技术 break-glass 仅保留给内建 Administrator，并由字段守卫/审计单独处理。
	"""
	if actor_role == ROLE_SYSTEM and not str(action or "").startswith("get_"):
		return False
	if scope:
		scoped = SCOPED_ACTION_ROLES.get((scope, action))
		if scoped is not None:
			return actor_role in scoped
	return actor_role in ACTION_ROLES.get(action, set())


def is_final_state(flow, state):
	"""是否为终态（不可再流转）。"""
	table = FLOW_TRANSITIONS.get(flow)
	return bool(table) and not table.get(state)
