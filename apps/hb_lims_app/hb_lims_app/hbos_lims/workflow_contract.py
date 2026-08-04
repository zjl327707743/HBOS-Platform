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

# 角色
ROLE_MANAGER = "LIMS Manager"
ROLE_ANALYST = "LIMS Analyst"
ROLE_REVIEWER = "LIMS Reviewer"
ROLE_SYSTEM = "System Manager"

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
	TASK_APPROVED: set(),
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
