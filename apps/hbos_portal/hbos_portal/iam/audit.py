from __future__ import annotations

import hashlib
import json
import re

import frappe

from hbos_portal.iam import guards, policy

EVENT = "HBOS IAM Change Event"
# Only configuration, lifecycle state and minimal command results. No arbitrary response bodies.
SAFE_KEYS = {
    "settings", "access_state", "permission_mode", "changes",
    "subject_type", "subject_name", "employee", "employee_id", "user", "user_id", "department", "department_id", "company",
    "app_id", "operation_id", "operation", "effect", "scope_type", "scope_ref", "include_descendants", "valid_from", "valid_until", "qualification_ref",
    "name", "version", "expected_version", "context_revision", "policy_revision", "enabled", "status", "relation_status", "account_status",
    "rules", "operations", "scopes", "source", "allowed", "available", "ordinary", "label", "reason", "result", "changed", "ok",
    "suspended", "before", "after", "before_version", "after_version", "revision", "target", "linked", "created", "reused", "first_password_required",
    "temporary_password_state", "pending", "temporary", "expires_at", "generation", "can_claim", "following_changed", "personal_unchanged", "unavailable",
    "impact", "count", "request_id", "request_hash", "message", "code", "error", "success", "employee_status", "account_created", "policy_name", "summary", "replayed",
}
SECRET_KEY = re.compile(r"password(?!_state)|token|proof|secret|cookie|authorization|(^|_)sid($|_)|checkin|attendance_records", re.I)


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def request_hash(operation, subject_type, subject_name, payload):
    return hashlib.sha256(_canonical({"operation": operation, "subject_type": subject_type, "subject_name": subject_name, "payload": payload}).encode()).hexdigest()


def _request_id(request_id):
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,139}", request_id):
        frappe.throw("request_id格式无效。", frappe.ValidationError)


def safe_snapshot(value, depth=0):
    if depth > 10:
        frappe.throw("变更记录过深。", frappe.ValidationError)
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            if SECRET_KEY.search(str(key)) and key not in {"temporary_password_state", "first_password_required"}:
                continue
            if key in SAFE_KEYS:
                result[key] = safe_snapshot(child, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > 1000:
            frappe.throw("变更记录过大。", frappe.ValidationError)
        return [safe_snapshot(item, depth + 1) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:1000]


def _conflict():
    frappe.local.response["http_status_code"] = 409
    frappe.throw("请求编号已被使用或内容发生变化，请重新核对。", frappe.ValidationError)


def replay(request_id, operation, subject_type, subject_name, payload):
    _request_id(request_id)
    actor = policy.get_current_user()
    rows = frappe.db.sql("select name,actor,request_hash,operation,subject_type,subject_name,after_json from `tabHBOS IAM Change Event` where request_id=%s limit 2 for update", (request_id,), as_dict=True)
    if not rows:
        return None
    expected = request_hash(operation, subject_type, subject_name, payload)
    row = rows[0]
    if len(rows) != 1 or policy.value(row, "actor") != actor or policy.value(row, "request_hash") != expected or policy.value(row, "operation") != operation or policy.value(row, "subject_type") != subject_type or policy.value(row, "subject_name") != subject_name:
        _conflict()
    # Authorization is deliberately a caller precondition and rechecked at every command.
    try:
        return safe_snapshot(json.loads(policy.value(row, "after_json") or "{}"))
    except (TypeError, ValueError):
        _conflict()


def append_event(request_id, operation, subject_type, subject_name, payload, before=None, after=None, version=0, result="success", reason=""):
    _request_id(request_id)
    if replay(request_id, operation, subject_type, subject_name, payload) is not None:
        _conflict()  # A command must return replay before making any mutation.
    from frappe.utils import now_datetime
    with guards.controlled_write():
        doc = frappe.get_doc({"doctype": EVENT, "actor": policy.get_current_user(), "request_id": request_id,
            "request_hash": request_hash(operation, subject_type, subject_name, payload), "subject_type": subject_type,
            "subject_name": subject_name, "operation": operation, "before_json": _canonical(safe_snapshot(before or {})),
            "after_json": _canonical(safe_snapshot(after or {})), "version": version, "result": result,
            "reason": str(reason)[:300], "occurred_at": now_datetime()})
        doc.insert(ignore_permissions=True)
    return doc


def list_events(subject_type=None, subject_name=None, page=1, page_size=20):
    guards.require_capability("iam.audit.read")
    try:
        page, page_size = int(page), int(page_size)
        if page < 1 or page > 10000 or page_size < 1 or page_size > 50:
            raise ValueError
    except (ValueError, TypeError):
        frappe.throw("分页参数无效。", frappe.ValidationError)
    departments = guards.managed_departments("iam.audit.read")
    # Resolve authorized subjects before list and count; never count the unscoped log.
    employees = frappe.db.sql("select name,user_id from `tabEmployee` where department in %(departments)s order by name for update", {"departments": tuple(departments)}, as_dict=True) if departments else []
    allowed = {("Department", name) for name in departments} | {("User", policy.value(row, "user_id")) for row in employees if policy.value(row, "user_id")} | {("Employee", policy.value(row, "name")) for row in employees}
    if subject_type or subject_name:
        if not subject_type or not subject_name or (subject_type, subject_name) not in allowed:
            if not guards.isolated_root():
                frappe.throw("没有该对象的审计读取权限。", frappe.PermissionError)
        allowed = {(subject_type, subject_name)}
    if not allowed and not guards.isolated_root():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    conditions, params = [], {}
    if not guards.isolated_root() or subject_type:
        for index, (kind, name) in enumerate(sorted(allowed)):
            conditions.append(f"(subject_type=%(kind{index})s and subject_name=%(name{index})s)")
            params[f"kind{index}"], params[f"name{index}"] = kind, name
    where = " where " + " or ".join(conditions) if conditions else ""
    count = frappe.db.sql("select count(*) from `tabHBOS IAM Change Event`" + where, params)[0][0]
    params.update(limit=page_size, offset=(page - 1) * page_size)
    fields = "name, actor, request_id, subject_type, subject_name, operation, version, result, reason, occurred_at"
    rows = frappe.db.sql("select " + fields + " from `tabHBOS IAM Change Event`" + where + " order by occurred_at desc, name desc limit %(limit)s offset %(offset)s", params, as_dict=True)
    return {"items": rows, "total": count, "page": page, "page_size": page_size}
