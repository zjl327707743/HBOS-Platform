# -*- coding: utf-8 -*-
"""个人待办聚合服务。

待办不是第二套业务状态，而是当前用户在已有业务单据上的可执行动作投影。
本模块只负责查询、身份范围、跨模块收敛和统一返回契约；真正的业务动作仍由
原模块服务执行并再次校验权限与状态。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

import frappe

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.todo_contract import (
	TodoRule,
	business_roles_for_user,
	deduplicate_todos,
	find_rule,
	make_todo_key,
	sort_todos,
	testing_task_is_covered,
)


TODO_DOCTYPES = (
	"HBOS Sample Task",
	"HBOS Test Result",
)
ACTIVE_TASK_STATUSES = ("已分配", "检验中", "已提交", "已复核")
ACTIONABLE_RESULT_STATUSES = ("草稿", "已提交", "已复核")
MODULE_LABELS = {
	"testing": "检验业务",
	"stability": "稳定性",
	"retention": "留样",
	"quality": "质量",
	"compliance": "合规",
}


@dataclass(frozen=True)
class Identity:
	user: str
	full_name: str
	session_roles: tuple[str, ...]
	business_roles: tuple[str, ...]


def _current_identity() -> Identity:
	"""只读取 Frappe 当前会话，不接受调用方传入 user/roles。"""
	user = str(frappe.session.user)
	roles = tuple(frappe.get_roles(user) or ())
	return Identity(
		user=user,
		full_name=frappe.get_fullname(user) or user,
		session_roles=roles,
		business_roles=business_roles_for_user(user, roles),
	)


def _today() -> str:
	return date.today().isoformat()


def _generated_at() -> str:
	return datetime.now(timezone.utc).astimezone().isoformat()


def _row_value(row: Any, field: str, default=None):
	if isinstance(row, dict):
		return row.get(field, default)
	return getattr(row, field, default)


def _get_list(doctype: str, filters: dict | None, fields: list[str]) -> list[dict]:
	"""统一走 permission-aware get_list，不使用 get_all 或 SQL 绕过权限。"""
	return list(
		frappe.get_list(
			doctype,
			filters=filters or {},
			fields=fields,
			limit_page_length=0,
		)
	)


def _allowed_by_action(rule: TodoRule, identity: Identity) -> bool:
	return _action_allowed(
		rule.permission_action,
		identity.session_roles,
		scope=rule.permission_scope,
	)


def _action_allowed(
	action: str,
	business_roles: tuple[str, ...],
	scope: str | None = None,
) -> bool:
	return any(wf.action_allowed(action, role, scope=scope) for role in business_roles)


def _matching_business_roles(rule: TodoRule, identity: Identity) -> tuple[str, ...]:
	return tuple(
		role
		for role in identity.business_roles
		if wf.action_allowed(
			rule.permission_action,
			role,
			scope=rule.permission_scope,
		)
	)


def _owner_for(
	rule: TodoRule,
	identity: Identity,
	row: dict,
) -> tuple[str | None, tuple[str, ...]]:
	if not _allowed_by_action(rule, identity):
		return None, ()
	assigned = _row_value(row, rule.assignment_field) if rule.assignment_field else None
	assigned = str(assigned).strip() if assigned else ""
	if assigned:
		return ("user", ()) if assigned == identity.user else (None, ())
	matching_roles = _matching_business_roles(rule, identity)
	if matching_roles:
		return "role", matching_roles
	return None, ()


def _date_value(value) -> date | None:
	if not value:
		return None
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	try:
		return date.fromisoformat(str(value)[:10])
	except (TypeError, ValueError):
		return None


def _is_overdue(value) -> bool:
	due = _date_value(value)
	today = _date_value(_today())
	return bool(due and today and due < today)


def _route_params(rule: TodoRule, source_name: str, *, task_name: str | None = None):
	params = {}
	for field in rule.route_param_fields:
		if field == "scope":
			params[field] = "mine"
		elif field in ("task", "result", "sample", "usage", "disposal"):
			params[field] = task_name or source_name
	return params


def _make_item(
	rule: TodoRule,
	row: dict,
	identity: Identity,
	owner_type: str,
	roles: tuple[str, ...],
	*,
	title: str,
	status: str,
	priority=None,
	due_at=None,
	modified_at=None,
	task_name: str | None = None,
	description: str | None = None,
):
	source_name = _row_value(row, "name")
	return {
		"todo_key": make_todo_key(rule.source_doctype, source_name, rule.action),
		"module": "testing" if rule.module.startswith("testing") else rule.module,
		"source_doctype": rule.source_doctype,
		"source_name": source_name,
		"title": title,
		"description": description or rule.label,
		"action": rule.action,
		"action_label": rule.label,
		"status": status,
		"owner_type": owner_type,
		"owner_name": identity.full_name if owner_type == "user" else "角色待处理",
		"assignee": identity.user if owner_type == "user" else None,
		"candidate_roles": list(roles),
		"priority": priority or "常规",
		"due_at": due_at,
		"is_overdue": _is_overdue(due_at),
		"route": rule.route,
		"route_params": _route_params(rule, source_name, task_name=task_name),
		"modified_at": modified_at,
		"execute_mode": rule.execute_mode,
	}


def _serialize_todo(candidate: dict) -> dict:
	"""补齐稳定的展示字段，provider 不重复实现序列化口径。"""
	item = dict(candidate)
	item["module_label"] = MODULE_LABELS.get(item.get("module"), item.get("module"))
	item["status_label"] = item.get("status")
	item["owner_label"] = (
		"指派给我" if item.get("owner_type") == "user" else "角色待处理"
	)
	return item


def _business_stability_items_for_timepoint(timepoint_name: str) -> set[str]:
	"""复用稳定性服务的项目粒度守卫；保留包装函数便于离线测试与缓存。"""
	from hb_lims_app.hbos_lims.stability_service import (
		_business_stability_items_for_timepoint as coverage,
	)

	return set(coverage(timepoint_name) or ())


def _stability_coverage(
	samples: Iterable[dict],
	task_rows: Iterable[dict],
) -> dict[str, set[str]]:
	stable_samples = {
		_row_value(sample, "name"): sample
		for sample in samples
		if _row_value(sample, "sample_source") == "稳定性"
		and _row_value(sample, "stability_timepoint")
	}
	if not stable_samples:
		return {}

	by_timepoint: dict[str, set[str]] = {}
	for sample in stable_samples.values():
		timepoint = _row_value(sample, "stability_timepoint")
		by_timepoint.setdefault(timepoint, set())
		if timepoint not in by_timepoint:
			by_timepoint[timepoint] = set()

	timepoint_names = sorted(by_timepoint)
	items = _get_list(
		"HBOS Stability Timepoint Item",
		{"parent": ["in", timepoint_names]},
		["parent", "stability_test_item"],
	)
	items_by_timepoint: dict[str, set[str]] = {}
	for item in items:
		items_by_timepoint.setdefault(_row_value(item, "parent"), set()).add(
			_row_value(item, "stability_test_item")
		)

	base_items = {
		_row_value(task, "test_item")
		for task in task_rows
		if _row_value(task, "test_item")
	}
	mappings = _get_list(
		"HBOS Stability Test Item",
		{"base_test_item": ["in", sorted(base_items)]},
		["name", "base_test_item"],
	)
	mapping = {
		_row_value(item, "base_test_item"): _row_value(item, "name")
		for item in mappings
	}

	result: dict[str, set[str]] = {}
	for timepoint in timepoint_names:
		covered = _business_stability_items_for_timepoint(timepoint)
		result[timepoint] = {
			_row_value(task, "test_item")
			for task in task_rows
			if _row_value(task, "sample") in stable_samples
			and _row_value(stable_samples[_row_value(task, "sample")], "stability_timepoint")
			== timepoint
			and testing_task_is_covered(
				_row_value(task, "test_item"), mapping,
				items_by_timepoint.get(timepoint, set()) & covered,
			)
		}
	return result


def _collect_testing_todos(identity: Identity) -> list[dict]:
	task_rows = _get_list(
		"HBOS Sample Task",
		{"status": ["in", list(ACTIVE_TASK_STATUSES)]},
		[
			"name", "sample", "test_item", "item_name", "assignee", "due_date",
			"priority", "status", "result", "modified",
		],
	)
	sample_names = sorted(
		{_row_value(row, "sample") for row in task_rows if _row_value(row, "sample")}
	)
	samples = _get_list(
		"HBOS Sample",
		{"name": ["in", sample_names]} if sample_names else {"name": ["in", [""]]},
		["name", "material_name", "batch_no", "sample_source", "stability_timepoint"],
	)
	sample_by_name = {_row_value(row, "name"): row for row in samples}
	coverage = _stability_coverage(samples, task_rows)

	items: list[dict] = []
	for task in task_rows:
		sample = sample_by_name.get(_row_value(task, "sample"))
		if not sample:
			continue
		timepoint = _row_value(sample, "stability_timepoint")
		if (
			_row_value(sample, "sample_source") == "稳定性"
			and timepoint
			and _row_value(task, "test_item") in coverage.get(timepoint, set())
		):
			continue
		if _row_value(task, "status") != "已分配":
			continue
		rule = find_rule("testing_task", _row_value(task, "status"))
		if not rule:
			continue
		owner_type, roles = _owner_for(rule, identity, task)
		if not owner_type:
			continue
		items.append(
			_make_item(
				rule, task, identity, owner_type, roles,
				title="{} · {}".format(
					_row_value(sample, "material_name") or _row_value(task, "sample"),
					_row_value(task, "item_name") or _row_value(task, "test_item"),
				),
				status=_row_value(task, "status"),
				priority=_row_value(task, "priority"),
				due_at=_row_value(task, "due_date"),
				modified_at=_row_value(task, "modified"),
				task_name=_row_value(task, "name"),
				description="开始检验：{}".format(_row_value(task, "item_name") or "检验项目"),
			)
		)

	task_by_name = {_row_value(task, "name"): task for task in task_rows}
	result_rows = _get_list(
		"HBOS Test Result",
		{"result_status": ["in", list(ACTIONABLE_RESULT_STATUSES)]},
		[
			"name", "task", "sample", "test_item", "item_name", "result_status",
			"analyst", "modified",
		],
	)
	for result in result_rows:
		task = task_by_name.get(_row_value(result, "task"))
		sample = sample_by_name.get(_row_value(result, "sample"))
		if not task or not sample:
			continue
		rule = find_rule("testing_result", _row_value(result, "result_status"))
		if not rule:
			continue
		owner_type, roles = _owner_for(rule, identity, result)
		if not owner_type:
			continue
		items.append(
			_make_item(
				rule, result, identity, owner_type, roles,
				title="{} · {}".format(
					_row_value(sample, "material_name") or _row_value(result, "sample"),
					_row_value(result, "item_name") or _row_value(result, "test_item"),
				),
				status=_row_value(result, "result_status"),
				priority=_row_value(task, "priority"),
				due_at=_row_value(task, "due_date"),
				modified_at=_row_value(result, "modified") or _row_value(task, "modified"),
				task_name=_row_value(task, "name"),
				description="{}：{}".format(rule.label, _row_value(result, "item_name") or "检验结果"),
			)
		)
	return items


def _collect_stability_todos(_identity: Identity) -> list[dict]:
	return []


def _collect_retention_todos(_identity: Identity) -> list[dict]:
	return []


def _collect_all(identity: Identity) -> list[dict]:
	items = []
	items.extend(_collect_testing_todos(identity))
	items.extend(_collect_stability_todos(identity))
	items.extend(_collect_retention_todos(identity))
	return [_serialize_todo(item) for item in sort_todos(deduplicate_todos(items))]


def _as_bool(value) -> bool:
	return value is True or str(value).lower() in {"1", "true", "yes", "on"}


def _matches_filters(
	items: list[dict],
	*,
	module: str | None = None,
	owner_type: str | None = None,
	status: str | None = None,
	priority: str | None = None,
	overdue=False,
	keyword: str | None = None,
) -> list[dict]:
	keyword = str(keyword).strip().lower() if keyword else ""
	result = []
	for item in items:
		if module and item.get("module") != module:
			continue
		if owner_type and item.get("owner_type") != owner_type:
			continue
		if status and item.get("status") != status:
			continue
		if priority and item.get("priority") != priority:
			continue
		if _as_bool(overdue) and not item.get("is_overdue"):
			continue
		if keyword:
			searchable = " ".join(
				str(item.get(field) or "")
				for field in ("title", "description", "source_name", "action_label")
			).lower()
			if keyword not in searchable:
				continue
		result.append(item)
	return result


def _summary(items: list[dict]) -> dict:
	by_module = {module: 0 for module in ("testing", "stability", "retention", "quality", "compliance")}
	for item in items:
		if item.get("module") in by_module:
			by_module[item["module"]] += 1
	return {
		"total": len(items),
		"assigned_to_me": sum(item.get("owner_type") == "user" for item in items),
		"role_pending": sum(item.get("owner_type") == "role" for item in items),
		"overdue": sum(bool(item.get("is_overdue")) for item in items),
		"by_module": by_module,
	}


@frappe.whitelist()
def get_my_todos(
	module=None,
	owner_type=None,
	status=None,
	priority=None,
	overdue=False,
	keyword=None,
	limit=50,
	offset=0,
):
	identity = _current_identity()
	all_items = _collect_all(identity)
	filtered = _matches_filters(
		all_items,
		module=module,
		owner_type=owner_type,
		status=status,
		priority=priority,
		overdue=overdue,
		keyword=keyword,
	)
	try:
		limit = min(max(int(limit), 1), 200)
		offset = max(int(offset), 0)
	except (TypeError, ValueError):
		limit, offset = 50, 0
	return {
		"items": filtered[offset:offset + limit],
		"total": len(filtered),
		"limit": limit,
		"offset": offset,
		"filtered_summary": _summary(filtered),
		"user": {"name": identity.user, "full_name": identity.full_name},
		"generated_at": _generated_at(),
	}


@frappe.whitelist()
def get_my_todo_summary():
	identity = _current_identity()
	items = _collect_all(identity)
	return {
		"summary": _summary(items),
		"user": {"name": identity.user, "full_name": identity.full_name},
		"generated_at": _generated_at(),
	}
