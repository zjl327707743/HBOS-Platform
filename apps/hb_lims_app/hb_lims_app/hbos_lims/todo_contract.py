# -*- coding: utf-8 -*-
"""个人待办纯契约。

本模块只包含规则与纯函数，不依赖 Frappe 运行时。业务查询、来源权限和
实际动作执行均由 ``todo_service`` 与原业务服务负责。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Mapping, Sequence

from hb_lims_app.hbos_lims import workflow_contract as wf


OwnerType = Literal["user", "role"]
ExecuteMode = Literal["direct", "route"]

LIMS_BUSINESS_ROLES = (
    wf.ROLE_ANALYST,
    wf.ROLE_REVIEWER,
    wf.ROLE_LIMS_QA,
    wf.ROLE_LIMS_QA_MANAGER,
    wf.ROLE_LIMS_QP,
    wf.ROLE_MANAGER,
)


@dataclass(frozen=True)
class TodoRule:
    module: str
    source_doctype: str
    status: str
    action: str
    permission_action: str
    permission_scope: str | None
    label: str
    allowed_roles: tuple[str, ...]
    assignment_field: str | None = None
    execute_mode: ExecuteMode = "route"
    due_extractor: str | None = None
    route: str = ""
    route_param_fields: tuple[str, ...] = ()
    condition: str | None = None


def _allowed_roles(action: str, scope: str | None = None) -> tuple[str, ...]:
    role_set = (
        wf.SCOPED_ACTION_ROLES.get((scope, action), set())
        if scope
        else wf.ACTION_ROLES.get(action, set())
    )
    return tuple(role for role in LIMS_BUSINESS_ROLES if role in role_set)


def _rule(
    module: str,
    source_doctype: str,
    status: str,
    action: str,
    label: str,
    *,
    permission_action: str | None = None,
    permission_scope: str | None = None,
    assignment_field: str | None = None,
    execute_mode: ExecuteMode = "route",
    due_extractor: str | None = None,
    route: str,
    route_param_fields: tuple[str, ...],
    condition: str | None = None,
) -> TodoRule:
    permission_action = permission_action or action
    return TodoRule(
        module=module,
        source_doctype=source_doctype,
        status=status,
        action=action,
        permission_action=permission_action,
        permission_scope=permission_scope,
        label=label,
        allowed_roles=_allowed_roles(permission_action, permission_scope),
        assignment_field=assignment_field,
        execute_mode=execute_mode,
        due_extractor=due_extractor,
        route=route,
        route_param_fields=route_param_fields,
        condition=condition,
    )


TODO_RULES = (
    _rule(
        "testing_task", "HBOS Sample Task", "已分配", "start_task", "开始检验",
        assignment_field="assignee", execute_mode="direct", due_extractor="due_date",
        route="/tasks", route_param_fields=("scope", "task"),
    ),
    _rule(
        "testing_result", "HBOS Test Result", "草稿", "submit_result", "提交结果",
        assignment_field="analyst", due_extractor="task_due_date",
        route="/tasks", route_param_fields=("scope", "task"),
    ),
    _rule(
        "testing_result", "HBOS Test Result", "已提交", "review_result", "复核结果",
        execute_mode="direct", due_extractor="task_due_date",
        route="/tasks", route_param_fields=("scope", "task"),
    ),
    _rule(
        "testing_result", "HBOS Test Result", "已复核", "approve_result", "批准结果",
        execute_mode="direct", due_extractor="task_due_date",
        route="/tasks", route_param_fields=("scope", "task"),
    ),
    _rule(
        "stability_timepoint", "HBOS Stability Timepoint", "待取样",
        "complete_sampling", "完成取样", assignment_field="sample_by",
        execute_mode="direct", due_extractor="effective_sample_due",
        route="/stability/schedule", route_param_fields=("timepoint",),
    ),
    _rule(
        "stability_timepoint", "HBOS Stability Timepoint", "待检测",
        "start_testing", "开始检测", assignment_field="test_by",
        execute_mode="direct", due_extractor="effective_test_due",
        route="/stability/schedule", route_param_fields=("timepoint",),
    ),
    _rule(
        "stability_timepoint", "HBOS Stability Timepoint", "检测中",
        "record_result", "录入结果", due_extractor="effective_test_due",
        route="/stability/results", route_param_fields=("timepoint",),
        condition="missing_manual_result",
    ),
    _rule(
        "stability_timepoint", "HBOS Stability Timepoint", "已完成",
        "eval_trend", "评价趋势", assignment_field="evaluator",
        route="/stability/results", route_param_fields=("timepoint",),
        condition="missing_trend_conclusion",
    ),
    _rule(
        "stability_result", "HBOS Stability Result", "草稿", "submit_result", "提交结果",
        permission_scope="HBOS Stability Result", assignment_field="analyst",
        route="/stability/results", route_param_fields=("timepoint", "result"),
    ),
    _rule(
        "stability_result", "HBOS Stability Result", "已提交", "review_result", "复核结果",
        permission_scope="HBOS Stability Result", execute_mode="direct",
        route="/stability/results", route_param_fields=("timepoint", "result"),
    ),
    _rule(
        "stability_result", "HBOS Stability Result", "已复核", "approve_result", "批准结果",
        permission_scope="HBOS Stability Result", execute_mode="direct",
        route="/stability/results", route_param_fields=("timepoint", "result"),
    ),
    _rule(
        "retention_sample", "HBOS Retention Sample", "应观察",
        "record_observation", "记录观察", due_extractor="next_obs_due_date",
        route="/retention/observations", route_param_fields=("sample",),
    ),
    _rule(
        "retention_sample", "HBOS Retention Sample", "已逾期",
        "record_observation", "记录观察", due_extractor="next_obs_due_date",
        route="/retention/observations", route_param_fields=("sample",),
    ),
    _rule(
        "retention_observation", "HBOS Retention Observation", "待审核",
        "review_observation", "审核观察", execute_mode="direct",
        route="/retention/observations", route_param_fields=("sample", "observation"),
    ),
    _rule(
        "retention_usage", "HBOS Retention Usage Apply", "草稿",
        "submit_usage_apply", "提交申请", permission_action="create_usage_apply",
        assignment_field="applicant", execute_mode="direct",
        route="/retention/usage", route_param_fields=("usage",),
    ),
    _rule(
        "retention_usage", "HBOS Retention Usage Apply", "待库存确认",
        "confirm_stock", "库存确认", permission_action="usage_confirm",
        execute_mode="direct", route="/retention/usage", route_param_fields=("usage",),
    ),
    _rule(
        "retention_usage", "HBOS Retention Usage Apply", "待QC批准",
        "approve_usage", "QC 批准", permission_action="usage_qc",
        execute_mode="direct", route="/retention/usage", route_param_fields=("usage",),
    ),
    _rule(
        "retention_usage", "HBOS Retention Usage Apply", "待QA批准",
        "approve_usage", "QA 批准", permission_action="usage_qa",
        execute_mode="direct", route="/retention/usage", route_param_fields=("usage",),
    ),
    _rule(
        "retention_usage", "HBOS Retention Usage Apply", "待QM批准",
        "approve_usage", "QM 批准", permission_action="usage_qm",
        execute_mode="direct", route="/retention/usage", route_param_fields=("usage",),
    ),
    _rule(
        "retention_usage", "HBOS Retention Usage Apply", "已批准",
        "execute_usage", "执行使用", permission_action="usage_execute",
        execute_mode="direct", route="/retention/usage", route_param_fields=("usage",),
    ),
    _rule(
        "retention_disposal", "HBOS Retention Disposal Apply", "草稿",
        "submit_disposal_apply", "提交申请", permission_action="create_disposal_apply",
        assignment_field="applicant", execute_mode="direct",
        route="/retention/disposal", route_param_fields=("disposal",),
    ),
    _rule(
        "retention_disposal", "HBOS Retention Disposal Apply", "待QC主管审核",
        "approve_disposal", "QC 主管审核", permission_action="disposal_qc",
        execute_mode="direct", route="/retention/disposal", route_param_fields=("disposal",),
    ),
    _rule(
        "retention_disposal", "HBOS Retention Disposal Apply", "待QC负责人审核",
        "approve_disposal", "QC 负责人审核", permission_action="disposal_qc",
        execute_mode="direct", route="/retention/disposal", route_param_fields=("disposal",),
    ),
    _rule(
        "retention_disposal", "HBOS Retention Disposal Apply", "待QA审核",
        "approve_disposal", "QA 审核", permission_action="disposal_qa",
        execute_mode="direct", route="/retention/disposal", route_param_fields=("disposal",),
    ),
    _rule(
        "retention_disposal", "HBOS Retention Disposal Apply", "待QA负责人审核",
        "approve_disposal", "QA 负责人审核", permission_action="disposal_qa",
        execute_mode="direct", route="/retention/disposal", route_param_fields=("disposal",),
    ),
    _rule(
        "retention_disposal", "HBOS Retention Disposal Apply", "待QM批准",
        "approve_disposal", "QM 批准", permission_action="disposal_qm",
        execute_mode="direct", route="/retention/disposal", route_param_fields=("disposal",),
    ),
    _rule(
        "retention_disposal", "HBOS Retention Disposal Apply", "已批准",
        "continue_retention", "执行续留", permission_action="disposal_handler",
        execute_mode="direct", route="/retention/disposal", route_param_fields=("disposal",),
        condition="continue_retention",
    ),
    _rule(
        "retention_disposal", "HBOS Retention Disposal Apply", "待执行",
        "dispose_handle", "执行处理", permission_action="disposal_handler",
        execute_mode="direct", due_extractor="deadline",
        route="/retention/disposal", route_param_fields=("disposal",),
        condition="handler_missing",
    ),
    _rule(
        "retention_disposal", "HBOS Retention Disposal Apply", "待执行",
        "dispose_monitor", "监督处理", permission_action="disposal_monitor",
        execute_mode="direct", due_extractor="deadline",
        route="/retention/disposal", route_param_fields=("disposal",),
        condition="monitor_missing",
    ),
)


def business_roles_for_user(user: str, roles: Sequence[str]) -> tuple[str, ...]:
    if user == "Administrator":
        return ()
    role_set = set(roles or ())
    return tuple(role for role in LIMS_BUSINESS_ROLES if role in role_set)


def resolve_owner_type(
    current_user: str,
    assigned_user: str | None,
    role_match: bool,
) -> OwnerType | None:
    assigned_user = (assigned_user or "").strip()
    if assigned_user:
        return "user" if assigned_user == current_user else None
    return "role" if role_match else None


def find_rule(module: str, status: str, condition: str | None = None) -> TodoRule | None:
    matches = [
        rule for rule in TODO_RULES
        if rule.module == module and rule.status == status
    ]
    if condition is not None:
        return next((rule for rule in matches if rule.condition == condition), None)
    return next((rule for rule in matches if rule.condition is None), None)


def current_action(
    module: str,
    status: str,
    *,
    source_test_result: str | None = None,
) -> str | None:
    if module == "stability_result" and source_test_result:
        return None
    rule = find_rule(module, status)
    return rule.action if rule else None


def testing_task_is_covered(
    base_test_item: str,
    mapping: Mapping[str, str],
    timepoint_items: set[str],
) -> bool:
    mapped_item = mapping.get(base_test_item)
    return bool(mapped_item and mapped_item in timepoint_items)


def make_todo_key(source_doctype: str, source_name: str, action: str) -> str:
    return f"{source_doctype}:{source_name}:{action}"


def deduplicate_todos(items: Sequence[dict]) -> list[dict]:
    by_key: dict[str, dict] = {}
    order: list[str] = []
    for item in items:
        key = item["todo_key"]
        if key not in by_key:
            order.append(key)
            by_key[key] = item
            continue
        if by_key[key].get("owner_type") != "user" and item.get("owner_type") == "user":
            by_key[key] = item
    return [by_key[key] for key in order]


def _date_sort_value(value) -> date:
    if not value:
        return date.max
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def sort_todos(items: Sequence[dict]) -> list[dict]:
    priority_rank = {"加急": 4, "紧急": 4, "高": 3, "中": 2, "普通": 1, "低": 0}
    ordered = list(items)
    ordered.sort(key=lambda item: str(item.get("modified_at") or ""), reverse=True)
    ordered.sort(key=lambda item: priority_rank.get(item.get("priority"), 1), reverse=True)
    ordered.sort(key=lambda item: _date_sort_value(item.get("due_at")))
    ordered.sort(key=lambda item: bool(item.get("is_overdue")), reverse=True)
    return ordered
