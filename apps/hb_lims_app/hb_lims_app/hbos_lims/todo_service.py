# -*- coding: utf-8 -*-
"""个人待办聚合服务。

待办不是第二套业务状态，而是当前用户在已有业务单据上的可执行动作投影。
本模块只负责查询、身份范围、跨模块收敛和统一返回契约；真正的业务动作仍由
原模块服务执行并再次校验权限与状态。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
from typing import Any, Iterable

import frappe

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.todo_contract import (
	TodoRule,
	TODO_RULES,
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
SUMMARY_CACHE_TTL_SECONDS = 30
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
		full_name=frappe.utils.get_fullname(user) or user,
		session_roles=roles,
		business_roles=business_roles_for_user(user, roles),
	)


def _today() -> str:
	return str(frappe.utils.today())


def _generated_at() -> str:
	return datetime.now(timezone.utc).astimezone().isoformat()


def _roles_hash(roles: tuple[str, ...]) -> str:
	payload = "|".join(roles or ())
	return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _summary_cache_key(user: str, business_roles: tuple[str, ...]) -> str:
	return "hbos:my-todo-summary:{}:{}".format(user, _roles_hash(business_roles))


def _cache_backend():
	cache = getattr(frappe, "cache", None)
	return cache() if callable(cache) else cache


def _summary_cache_get(key: str):
	cache = _cache_backend()
	return cache.get_value(key) if cache is not None else None


def _summary_cache_set(key: str, value: dict):
	cache = _cache_backend()
	if cache is not None:
		cache.set_value(key, value, expires_in_sec=SUMMARY_CACHE_TTL_SECONDS)


def _summary_cache_delete(key: str):
	cache = _cache_backend()
	if cache is not None:
		cache.delete_value(key)


def invalidate_my_todo_summary_cache(user: str | None = None) -> None:
	"""失效当前会话的摘要；缓存异常不得反向影响已成功业务动作。"""
	try:
		identity = _current_identity()
		if user and user != identity.user:
			roles = tuple(frappe.get_roles(user) or ())
			business_roles = business_roles_for_user(user, roles)
		else:
			business_roles = identity.business_roles
		_summary_cache_delete(_summary_cache_key(user or identity.user, business_roles))
	except Exception as exc:
		if hasattr(frappe, "log_error"):
			frappe.log_error(str(exc), "HBOS 我的待办摘要缓存失效失败")


def _row_value(row: Any, field: str, default=None):
	if isinstance(row, dict):
		return row.get(field, default)
	return getattr(row, field, default)


def _permission_error_types():
	types = [PermissionError]
	for owner in (frappe, getattr(frappe, "exceptions", None)):
		error_type = getattr(owner, "PermissionError", None)
		if isinstance(error_type, type) and error_type not in types:
			types.append(error_type)
	return tuple(types)


def _get_list(doctype: str, filters: dict | None, fields: list[str]) -> list[dict]:
	"""统一走 permission-aware get_list；无读权限按不可见处理而不是让聚合接口崩溃。"""
	try:
		return list(
			frappe.get_list(
				doctype,
				filters=filters or {},
				fields=fields,
				limit_page_length=0,
			)
		)
	except Exception as exc:
		if isinstance(exc, _permission_error_types()):
			return []
		raise


def _parent_names_from_filter(filters: dict | None) -> list[str]:
	parent_filter = (filters or {}).get("parent")
	if isinstance(parent_filter, (list, tuple)) and len(parent_filter) == 2:
		operator, values = parent_filter
		if operator == "in":
			return [str(value) for value in (values or ()) if value]
	if parent_filter:
		return [str(parent_filter)]
	return []


def _readable_parent_names(parent_doctype: str, parent_names: list[str]) -> list[str]:
	if not parent_names:
		return []
	has_permission = getattr(frappe, "has_permission", None)
	if callable(has_permission):
		readable = []
		for name in parent_names:
			try:
				if has_permission(parent_doctype, ptype="read", doc=name):
					readable.append(name)
			except Exception as exc:
				if not isinstance(exc, _permission_error_types()):
					raise
		return readable
	return [
		_row_value(row, "name")
		for row in _get_list(
			parent_doctype,
			{"name": ["in", parent_names]},
			["name"],
		)
	]


def _get_child_list(
	doctype: str,
	filters: dict | None,
	fields: list[str],
	*,
	parent_doctype: str,
) -> list[dict]:
	"""读取子表前按父单逐条校验读权限，再用 get_all 取已授权父单的行。"""
	parent_names = _parent_names_from_filter(filters)
	readable_parents = _readable_parent_names(parent_doctype, parent_names)
	if not readable_parents:
		return []
	get_all = getattr(frappe, "get_all", None)
	if not callable(get_all):
		return []
	child_filters = dict(filters or {})
	child_filters["parent"] = ["in", readable_parents]
	try:
		return list(
			get_all(
				doctype,
				filters=child_filters,
				fields=fields,
				limit_page_length=0,
			)
		)
	except Exception as exc:
		if isinstance(exc, _permission_error_types()):
			return []
		raise


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


def _route_params(
	rule: TodoRule,
	source_name: str,
	*,
	task_name: str | None = None,
	context: dict | None = None,
):
	params = {}
	context = context or {}
	for field in rule.route_param_fields:
		if field == "scope":
			params[field] = "mine"
		elif field in context:
			params[field] = context[field]
		elif field in ("task", "result", "sample", "usage", "disposal"):
			params[field] = task_name or source_name
		elif field == "timepoint":
			params[field] = source_name
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
	route_context: dict | None = None,
):
	source_name = _row_value(row, "name")
	serialized_due_at = due_at.isoformat() if isinstance(due_at, (date, datetime)) else due_at
	module = rule.module
	if module.startswith("testing"):
		module = "testing"
	elif module.startswith("stability"):
		module = "stability"
	elif module.startswith("retention"):
		module = "retention"
	return {
		"todo_key": make_todo_key(rule.source_doctype, source_name, rule.action),
		"module": module,
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
		"due_at": serialized_due_at,
		"is_overdue": _is_overdue(due_at),
		"route": rule.route,
		"route_params": _route_params(
			rule, source_name, task_name=task_name, context=route_context,
		),
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

	timepoint_names = sorted(by_timepoint)
	items = _get_child_list(
		"HBOS Stability Timepoint Item",
		{"parent": ["in", timepoint_names]},
		["parent", "stability_test_item"],
		parent_doctype="HBOS Stability Timepoint",
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
			"analyst", "reviewer", "modified",
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
		owner_type, roles = _result_owner_for(rule, identity, result)
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


def _result_owner_for(rule: TodoRule, identity: Identity, row: dict):
	owner_type, roles = _owner_for(rule, identity, row)
	if owner_type != "role":
		return owner_type, roles
	if rule.action == "review_result" and _row_value(row, "analyst") == identity.user:
		return None, ()
	previous_reviewer = _row_value(row, "reviewed_by") or _row_value(row, "reviewer")
	if rule.action == "approve_result" and previous_reviewer == identity.user:
		return None, ()
	return owner_type, roles


def _enrich_stability_schedule(rows: list[dict]) -> list[dict]:
	"""批量计算稳定性有效截止日；effective_* 不是数据库列。"""
	from hb_lims_app.hbos_lims.stability_service import _enrich_schedule

	return list(_enrich_schedule(rows) or ())


def _stability_timepoint_items(timepoint_names: list[str]) -> dict[str, list[dict]]:
	if not timepoint_names:
		return {}
	rows = _get_child_list(
		"HBOS Stability Timepoint Item",
		{"parent": ["in", timepoint_names]},
		["parent", "stability_test_item", "is_required"],
		parent_doctype="HBOS Stability Timepoint",
	)
	items: dict[str, list[dict]] = {}
	for row in rows:
		items.setdefault(_row_value(row, "parent"), []).append(row)
	return items


def _business_stability_coverage(timepoint_names: list[str]) -> dict[str, set[str]]:
	"""按业务任务对应的基础项目返回各时间点已覆盖的稳定性项目。"""
	if not timepoint_names:
		return {}
	samples = _get_list(
		"HBOS Sample",
		{
			"sample_source": "稳定性",
			"stability_timepoint": ["in", timepoint_names],
		},
		["name", "sample_source", "stability_timepoint"],
	)
	sample_names = sorted({
		_row_value(sample, "name")
		for sample in samples
		if _row_value(sample, "name")
	})
	if not sample_names:
		return {}
	task_rows = _get_list(
		"HBOS Sample Task",
		{"sample": ["in", sample_names]},
		["sample", "test_item"],
	)
	base_items = {
		_row_value(task, "test_item")
		for task in task_rows
		if _row_value(task, "test_item")
	}
	mapping_rows = _get_list(
		"HBOS Stability Test Item",
		{"base_test_item": ["in", sorted(base_items)]},
		["name", "base_test_item"],
	)
	mapping = {
		_row_value(row, "base_test_item"): _row_value(row, "name")
		for row in mapping_rows
	}
	items = _get_child_list(
		"HBOS Stability Timepoint Item",
		{"parent": ["in", timepoint_names]},
		["parent", "stability_test_item"],
		parent_doctype="HBOS Stability Timepoint",
	)
	items_by_timepoint: dict[str, set[str]] = {}
	for item in items:
		items_by_timepoint.setdefault(_row_value(item, "parent"), set()).add(
			_row_value(item, "stability_test_item")
		)

	sample_by_name = {
		_row_value(sample, "name"): sample
		for sample in samples
	}
	result: dict[str, set[str]] = {}
	for timepoint in timepoint_names:
		allowed_items = items_by_timepoint.get(timepoint, set()) & _business_stability_items_for_timepoint(timepoint)
		result[timepoint] = {
			mapping.get(_row_value(task, "test_item"))
			for task in task_rows
			if _row_value(sample_by_name.get(_row_value(task, "sample")), "stability_timepoint") == timepoint
			and mapping.get(_row_value(task, "test_item")) in allowed_items
			and mapping.get(_row_value(task, "test_item"))
		}
	return result


def _manual_result_items(result_rows: list[dict]) -> dict[str, set[str]]:
	items: dict[str, set[str]] = {}
	for row in result_rows:
		if _row_value(row, "source_test_result"):
			continue
		items.setdefault(_row_value(row, "timepoint"), set()).add(
			_row_value(row, "stability_test_item")
		)
	return items


def _collect_stability_todos(identity: Identity) -> list[dict]:
	timepoints = _get_list(
		"HBOS Stability Timepoint",
		{"status": ["in", ["待取样", "待检测", "检测中", "已完成"]]},
		[
			"name", "status", "sample_by", "test_by", "evaluator",
			"trend_conclusion", "modified", "stability_sample",
			"plan_sample_date", "plan_test_date",
		],
	)
	if not timepoints:
		return []
	enriched = _enrich_stability_schedule(timepoints)
	timepoint_names = [_row_value(row, "name") for row in enriched]
	items_by_timepoint = _stability_timepoint_items(timepoint_names)
	business_coverage = _business_stability_coverage(timepoint_names)
	result_rows = _get_list(
		"HBOS Stability Result",
		{"status": ["in", list(ACTIONABLE_RESULT_STATUSES)]},
		[
			"name", "timepoint", "stability_test_item", "item_snapshot", "status",
			"analyst", "submitted_by", "reviewed_by", "approved_by",
			"source_test_result", "modified",
		],
	)
	manual_items = _manual_result_items(result_rows)

	items: list[dict] = []
	for row in enriched:
		status = _row_value(row, "status")
		condition = None
		if status == "检测中":
			required = {
				_row_value(item, "stability_test_item")
				for item in items_by_timepoint.get(_row_value(row, "name"), ())
				if _row_value(item, "is_required", 1)
			}
			covered_by_business = business_coverage.get(_row_value(row, "name"), set())
			if required - manual_items.get(_row_value(row, "name"), set()) - covered_by_business:
				condition = "missing_manual_result"
		elif status == "已完成" and not _row_value(row, "trend_conclusion"):
			condition = "missing_trend_conclusion"
		rule = find_rule("stability_timepoint", status, condition=condition)
		if not rule:
			continue
		owner_type, roles = _owner_for(rule, identity, row)
		if not owner_type:
			continue
		if rule.action == "complete_sampling":
			due_at = _row_value(row, "effective_sample_due")
			overdue = bool(_row_value(row, "sample_overdue"))
		elif rule.action in ("start_testing", "record_result"):
			due_at = _row_value(row, "effective_test_due")
			overdue = bool(_row_value(row, "test_overdue"))
		else:
			due_at, overdue = None, False
		item = _make_item(
			rule, row, identity, owner_type, roles,
			title="稳定性时间点：{}".format(_row_value(row, "name")),
			status=status,
			due_at=due_at,
			modified_at=_row_value(row, "modified"),
			route_context={"timepoint": _row_value(row, "name")},
			description=rule.label,
		)
		item["is_overdue"] = overdue
		items.append(item)
	return items


def _collect_stability_result_todos(identity: Identity) -> list[dict]:
	result_rows = _get_list(
		"HBOS Stability Result",
		{"status": ["in", list(ACTIONABLE_RESULT_STATUSES)]},
		[
			"name", "timepoint", "stability_test_item", "item_snapshot", "status",
			"analyst", "submitted_by", "reviewed_by", "approved_by",
			"source_test_result", "modified",
		],
	)
	items: list[dict] = []
	for row in result_rows:
		if _row_value(row, "source_test_result"):
			continue
		rule = find_rule("stability_result", _row_value(row, "status"))
		if not rule:
			continue
		owner_type, roles = _result_owner_for(rule, identity, row)
		if not owner_type:
			continue
		items.append(
			_make_item(
				rule, row, identity, owner_type, roles,
				title="稳定性结果：{}".format(
					_row_value(row, "item_snapshot") or _row_value(row, "stability_test_item")
				),
				status=_row_value(row, "status"),
				due_at=None,
				modified_at=_row_value(row, "modified"),
				route_context={"timepoint": _row_value(row, "timepoint")},
				description=rule.label,
			)
		)
	return items


def _retention_sample_todos(identity: Identity) -> list[dict]:
	samples = _get_list(
		"HBOS Retention Sample",
		{"observed_flag": 1},
		[
			"name", "sample_name", "batch_no", "status", "next_obs_month",
			"next_obs_due_date", "modified",
		],
	)
	if not samples:
		return []
	observations = _get_list(
		"HBOS Retention Observation",
		{"retention_sample": ["in", [_row_value(row, "name") for row in samples]]},
		["name", "retention_sample", "obs_month", "observer", "reviewed_by", "modified"],
	)
	observed_keys = {
		(_row_value(row, "retention_sample"), _row_value(row, "obs_month"))
		for row in observations
	}
	items = []
	for sample in samples:
		month = _row_value(sample, "next_obs_month")
		if month is None or (_row_value(sample, "name"), month) in observed_keys:
			continue
		due_at = _row_value(sample, "next_obs_due_date")
		status = "已逾期" if _is_overdue(due_at) else "应观察"
		rule = find_rule("retention_sample", status)
		if not rule:
			continue
		owner_type, roles = _owner_for(rule, identity, sample)
		if not owner_type:
			continue
		items.append(
			_make_item(
				rule, sample, identity, owner_type, roles,
				title="留样观察：{}".format(
					_row_value(sample, "sample_name") or _row_value(sample, "name")
				),
				status=status,
				due_at=due_at,
				modified_at=_row_value(sample, "modified"),
				route_context={"sample": _row_value(sample, "name")},
				description=rule.label,
			)
		)
	return items


def _retention_observation_todos(identity: Identity) -> list[dict]:
	rows = _get_list(
		"HBOS Retention Observation",
		{"reviewed_by": ["is", "not set"]},
		[
			"name", "retention_sample", "obs_month", "observer", "reviewed_by", "modified",
		],
	)
	rule = find_rule("retention_observation", "待审核")
	if not rule:
		return []
	items = []
	for row in rows:
		owner_type, roles = _owner_for(rule, identity, row)
		if not owner_type:
			continue
		items.append(
			_make_item(
				rule, row, identity, owner_type, roles,
				title="留样观察待审核：{}".format(_row_value(row, "retention_sample")),
				status="待审核",
				modified_at=_row_value(row, "modified"),
				route_context={
					"sample": _row_value(row, "retention_sample"),
					"observation": _row_value(row, "name"),
				},
				description=rule.label,
			)
		)
	return items


def _retention_usage_todos(identity: Identity) -> list[dict]:
	statuses = [rule.status for rule in TODO_RULES if rule.module == "retention_usage"]
	rows = _get_list(
		"HBOS Retention Usage Apply",
		{"status": ["in", statuses]},
		[
			"name", "status", "applicant", "stock_confirm_by", "qc_approval",
			"qa_approval", "qm_approval", "executed_by", "modified",
		],
	)
	items = []
	for row in rows:
		rule = find_rule("retention_usage", _row_value(row, "status"))
		if not rule:
			continue
		owner_type, roles = _owner_for(rule, identity, row)
		if not owner_type:
			continue
		items.append(
			_make_item(
				rule, row, identity, owner_type, roles,
				title="留样使用申请：{}".format(_row_value(row, "name")),
				status=_row_value(row, "status"),
				modified_at=_row_value(row, "modified"),
				route_context={"usage": _row_value(row, "name")},
				description=rule.label,
			)
		)
	return items


def _retention_disposal_todos(identity: Identity) -> list[dict]:
	statuses = [rule.status for rule in TODO_RULES if rule.module == "retention_disposal"]
	rows = _get_list(
		"HBOS Retention Disposal Apply",
		{"status": ["in", sorted(set(statuses))]},
		[
			"name", "status", "disposal_type", "applicant", "deadline",
			"qc_supervisor_sign", "qc_manager_sign", "qa_review_sign",
			"qa_manager_sign", "qm_sign", "disposal_by", "monitor_by", "modified",
		],
	)
	items = []
	for row in rows:
		status = _row_value(row, "status")
		condition = None
		if status == "已批准":
			condition = (
				"continue_retention"
				if _row_value(row, "disposal_type") == "留样期满继续留样"
				else "not_applicable"
			)
		elif status == "待执行":
			if not _row_value(row, "disposal_by"):
				condition = "handler_missing"
			elif not _row_value(row, "monitor_by"):
				condition = "monitor_missing"
			else:
				continue
		rule = find_rule("retention_disposal", status, condition=condition)
		if not rule:
			continue
		owner_type, roles = _owner_for(rule, identity, row)
		if not owner_type:
			continue
		due_at = _row_value(row, "deadline") if rule.due_extractor == "deadline" else None
		items.append(
			_make_item(
				rule, row, identity, owner_type, roles,
				title="留样处理申请：{}".format(_row_value(row, "name")),
				status=status,
				due_at=due_at,
				modified_at=_row_value(row, "modified"),
				route_context={"disposal": _row_value(row, "name")},
				description=rule.label,
			)
		)
	return items


def _collect_retention_todos(identity: Identity) -> list[dict]:
	items = []
	items.extend(_retention_sample_todos(identity))
	items.extend(_retention_observation_todos(identity))
	items.extend(_retention_usage_todos(identity))
	items.extend(_retention_disposal_todos(identity))
	return items


def _collect_all(identity: Identity) -> list[dict]:
	items = []
	items.extend(_collect_testing_todos(identity))
	items.extend(_collect_stability_todos(identity))
	items.extend(_collect_stability_result_todos(identity))
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
	cache_key = _summary_cache_key(identity.user, identity.business_roles)
	cached = _summary_cache_get(cache_key)
	if cached is not None:
		return cached
	items = _collect_all(identity)
	response = {
		"summary": _summary(items),
		"user": {"name": identity.user, "full_name": identity.full_name},
		"generated_at": _generated_at(),
	}
	try:
		_summary_cache_set(cache_key, response)
	except Exception as exc:
		if hasattr(frappe, "log_error"):
			frappe.log_error(str(exc), "HBOS 我的待办摘要缓存写入失败")
	return response


def get_my_testing_task_names() -> list[str]:
	"""供待检任务看板 scope=mine 使用的当前会话任务名投影。"""
	identity = _current_identity()
	names = set()
	for item in _collect_testing_todos(identity):
		if item.get("source_doctype") == "HBOS Sample Task":
			names.add(item["source_name"])
		elif item.get("source_doctype") == "HBOS Test Result":
			task_name = (item.get("route_params") or {}).get("task")
			if task_name:
				names.add(task_name)
	return sorted(names)
