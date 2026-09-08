# -*- coding: utf-8 -*-
"""LIMS 检验流程状态机契约（零 Frappe 依赖，可离线单测）。

业务口径来自《海滨药业LIMS系统开发方案》模块 3 检验流程管理：
样品登记 → 任务分配 → 检验执行 → 数据录入 → 自动判定 → 复核 → 放行。
OOS 触发：判定不合格 → OOS候选 → OOS锁定（禁止放行）。
"""

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
}

# 动作 -> 允许角色（动作语义见 lims_service）
ACTION_ROLES = {
	"register_sample": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"generate_tasks": {ROLE_MANAGER, ROLE_SYSTEM},
	"assign_task": {ROLE_MANAGER, ROLE_SYSTEM},
	"start_task": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"submit_result": {ROLE_ANALYST, ROLE_MANAGER, ROLE_SYSTEM},
	"review_result": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"approve_result": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"revise_result": {ROLE_MANAGER, ROLE_SYSTEM},
	"confirm_oos": {ROLE_MANAGER, ROLE_SYSTEM},
	"release_sample": {ROLE_REVIEWER, ROLE_MANAGER, ROLE_SYSTEM},
	"reject_sample": {ROLE_MANAGER, ROLE_SYSTEM},
	# 质量标准管理（Manager 维护主数据）
	"create_specification": {ROLE_MANAGER, ROLE_SYSTEM},
	"update_specification": {ROLE_MANAGER, ROLE_SYSTEM},
	"delete_specification": {ROLE_MANAGER, ROLE_SYSTEM},
	"activate_specification": {ROLE_MANAGER, ROLE_SYSTEM},
	"obsolete_specification": {ROLE_MANAGER, ROLE_SYSTEM},
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


def action_allowed(action, actor_role):
	"""角色是否允许执行指定动作。"""
	return actor_role in ACTION_ROLES.get(action, set())


def is_final_state(flow, state):
	"""是否为终态（不可再流转）。"""
	table = FLOW_TRANSITIONS.get(flow)
	return bool(table) and not table.get(state)
