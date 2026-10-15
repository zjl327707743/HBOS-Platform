"""Bounded work commands. Browser intentions are never an authorization result."""
from __future__ import annotations

import copy
import json
from datetime import datetime

import frappe

from hbos_portal.iam import audit, guards, policy

RULE_FIELDS = ("app_id", "operation_id", "effect", "scope_type", "scope_ref", "include_descendants", "valid_from", "valid_until", "qualification_ref")
STOP = {"operation_id": "app.enter", "effect": "deny", "scope_type": "ALL", "scope_ref": "*"}


def _invalid(message):
    frappe.throw(message, frappe.ValidationError)


def _conflict(message):
    frappe.local.response["http_status_code"] = 409
    frappe.throw(message, frappe.TimestampMismatchError)


def plain_rule(row):
    return {key: policy.value(row, key) for key in RULE_FIELDS}


def _rules(document):
    return [plain_rule(row) for row in (document.get("rules") if document else [])]


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


def _objects(scopes):
    return sorted({(str(item.get("scope_type", "")), str(item.get("scope_ref", ""))) for item in scopes})


def _app(app_id):
    result = next((app for app in policy.registered_apps() if app["id"] == app_id), None)
    if not result or not result["integrated"] or app_id == "iam":
        frappe.throw("这个应用尚未接入此管理功能，暂不能在此调整。", frappe.PermissionError)
    return result


def _target(subject_type, subject_name):
    if subject_type == "User":
        if not frappe.db.exists("User", subject_name):
            _invalid("账号不存在。")
        # No matching by names, email or externally supplied employee numbers.
        employees = frappe.db.sql("select name,department,company,status from `tabEmployee` where user_id=%s order by name limit 2 for update", (subject_name,), as_dict=True)
        if len(employees) != 1:
            frappe.throw("请先核对唯一员工档案关联。", frappe.PermissionError)
        target = employees[0]
    elif subject_type == "Department":
        if not frappe.db.exists("Department", subject_name):
            _invalid("部门不存在或尚未确认。")
        target = frappe.get_doc("Department", subject_name, for_update=True)
        if target.get("disabled"):
            frappe.throw("这个部门暂不能用于分配应用。", frappe.PermissionError)
    else:
        _invalid("只能安排明确的员工账号或部门。")
    return target


def _authorize(subject_type, subject_name, app_id, *, write=False):
    target = _target(subject_type, subject_name)
    operation = ("iam.departments.manage" if subject_type == "Department" else "iam.access.manage") if write else "iam.access.read"
    department = subject_name if subject_type == "Department" else policy.value(target, "department")
    guards.require_capability(operation, department=department, company=policy.value(target, "company"), app_id=app_id, target_user=subject_name if subject_type == "User" else None)
    return target


def _operation(app, operation_id):
    result = next((item for item in app["operations"] if item["id"] == operation_id), None)
    if not result or not result.get("ordinary") or not result.get("integrated"):
        frappe.throw("未接入、管理或重要操作不能由普通工作勾选授予。", frappe.PermissionError)
    return result


def normalize_changes(changes, app):
    if isinstance(changes, str):
        try:
            changes = json.loads(changes)
        except ValueError:
            _invalid("工作更改格式不正确。")
    if not isinstance(changes, list) or len(changes) > 30:
        _invalid("请提交有限的工作更改清单。")
    seen, result = set(), []
    for change in changes:
        if not isinstance(change, dict) or set(change) - {"operation_id", "enabled", "scopes"}:
            _invalid("只能提交明确的工作与对象，不能提交全量策略。")
        operation_id = change.get("operation_id")
        if operation_id in seen:
            _invalid("同一工作不能重复提交。")
        seen.add(operation_id)
        operation = _operation(app, operation_id)
        enabled, scopes = change.get("enabled"), change.get("scopes", [])
        if not isinstance(enabled, bool) or not isinstance(scopes, list):
            _invalid("工作选择或对象格式不正确。")
        if any(not isinstance(scope, dict) or set(scope) != {"scope_type", "scope_ref"} for scope in scopes):
            _invalid("对象范围字段不正确。")
        allowed = _objects(operation["objects"])
        requested = _objects(scopes)
        if len(requested) != len(scopes) or any(scope not in allowed for scope in requested) or (enabled and not requested) or (not enabled and requested):
            _invalid("请选择完整、明确且已开放的对象范围。")
        result.append({"operation_id": operation_id, "enabled": enabled, "scopes": [{"scope_type": kind, "scope_ref": ref} for kind, ref in requested]})
    return result


def _ordinary_ids(app):
    return {item["id"] for item in app["operations"] if item.get("ordinary") and item.get("integrated")}


def _stop(row, app_id):
    return row.get("app_id") == app_id and all(row.get(key) == value for key, value in STOP.items())


def _complex(row):
    return bool(row.get("valid_from") or row.get("valid_until") or row.get("qualification_ref") or row.get("include_descendants"))


def _grant_deadline(subject_type, target, app_id):
    """Intersect a complete same-app delegation gate/action, then union paths.

    Management is never department-inherited. Only currently active explicit
    personal paths participate; future allows cannot extend a grant. An already
    scheduled matching deny bounds every path even if its start is still ahead.
    """
    if guards.isolated_root():
        return None
    actor = policy.get_current_user()
    document = policy.get_policy("User", actor, for_update=True)
    operation = "iam.departments.manage" if subject_type == "Department" else "iam.access.manage"
    department = policy.value(target, "name") if subject_type == "Department" else policy.value(target, "department")
    company = policy.value(target, "company")
    now = frappe.utils.now_datetime()
    horizons = []
    for candidate in {app_id, "iam"}:
        rows = [row for row in _rules(document) if row["app_id"] == candidate and row["operation_id"] in {"app.enter", operation} and policy._matches(row, "DEPARTMENT", department, company)]
        if any(row.get("qualification_ref") or row.get("include_descendants") for row in rows):
            frappe.throw("此委派含有尚未支持的授予限制，请先核对。", frappe.PermissionError)
        cutoff = None
        blocked = False
        for row in rows:
            if row["effect"] != "deny":
                continue
            if policy.active(row, now):
                blocked = True
                break
            start = frappe.utils.get_datetime(row["valid_from"]) if row["valid_from"] else None
            if start and start > now:
                cutoff = min(cutoff, start) if cutoff else start
        if blocked:
            continue
        gates = [row for row in rows if row["operation_id"] == "app.enter" and row["effect"] == "allow" and policy.active(row, now)]
        actions = [row for row in rows if row["operation_id"] == operation and row["effect"] == "allow" and policy.active(row, now)]
        for gate in gates:
            for action in actions:
                limits = [frappe.utils.get_datetime(row["valid_until"]) for row in (gate, action) if row["valid_until"]]
                if cutoff:
                    limits.append(cutoff)
                horizons.append(min(limits) if limits else None)
    if not horizons:
        frappe.throw("缺少可用于授予此工作的具名委派期限。", frappe.PermissionError)
    return None if None in horizons else max(horizons)


def _new_rule(app_id, operation_id, effect, scope, deadline=None):
    return {"app_id": app_id, "operation_id": operation_id, "effect": effect, "scope_type": scope["scope_type"], "scope_ref": scope["scope_ref"], "include_descendants": 0, "valid_from": None, "valid_until": deadline if effect == "allow" else None, "qualification_ref": None}


def _entry_allows(subject_type, target, rows, app_id, scope):
    personal = [row for row in rows if row["app_id"] == app_id and row["operation_id"] == "app.enter"]
    inherited = []
    if subject_type == "User":
        inherited = [row for row in _rules(policy.get_policy("Department", policy.value(target, "department"), for_update=True)) if row["app_id"] == app_id and row["operation_id"] == "app.enter"]
    now = frappe.utils.now_datetime()
    matches = lambda row: policy.active(row, now) and policy._matches(row, scope["scope_type"], scope["scope_ref"], policy.value(target, "company"))
    if any(row["effect"] == "deny" and matches(row) for row in personal + inherited):
        return False
    effective = personal if any(row["effect"] == "allow" for row in personal) else inherited
    return any(row["effect"] == "allow" and matches(row) for row in effective)


def _operation_state(summary, operation_id):
    return next((item for item in summary["operations"] if item["operation_id"] == operation_id), {"allowed": False, "scopes": []})


def _summary_text(summary):
    if summary.get("suspended"):
        return "已停用这个应用，已有安排保留。"
    texts = []
    for operation in summary.get("operations", []):
        if not operation.get("available"):
            continue
        label = operation.get("label", operation["operation_id"])
        texts.append(label if operation.get("allowed") else "暂未安排" + label)
    return "；".join(texts) or "尚未接入此管理功能。"


def describe(summary):
    summary = copy.deepcopy(summary)
    summary["summary"] = _summary_text(summary)
    return summary


def _impact(subject_type, subject_name, app_id, after_rules):
    result = {"changed": 0, "personal_preserved": 0, "unavailable": 0, "employees": []}
    if subject_type != "Department":
        return result
    employees = frappe.db.sql("select name,employee_name,user_id,status from `tabEmployee` where department=%s order by name for update", (subject_name,), as_dict=True)
    for employee in employees:
        user = policy.value(employee, "user_id")
        if not user or policy.value(employee, "status") != "Active" or not frappe.db.get_value("User", user, "enabled", for_update=True):
            result["unavailable"] += 1
            result["employees"].append({"employee": policy.value(employee, "name"), "name": policy.value(employee, "employee_name"), "result": "暂不可用"})
            continue
        personal = policy.get_policy("User", user, for_update=True)
        has_personal = any(row["app_id"] == app_id for row in _rules(personal))
        if has_personal:
            result["personal_preserved"] += 1
        before = policy.effective_work("User", user, app_id)
        after = policy.effective_work("User", user, app_id, policy_overrides={("Department", subject_name): after_rules})
        # Sources/revision are not a business effect; compare actual paired work.
        changed = [(row["operation_id"], row["allowed"], _objects(row["scopes"])) for row in before["operations"]] != [(row["operation_id"], row["allowed"], _objects(row["scopes"])) for row in after["operations"]]
        result["changed"] += int(changed)
        result["employees"].append({"employee": policy.value(employee, "name"), "name": policy.value(employee, "employee_name"), "result": "普通安排将调整" if changed else "保持原安排", "personal_preserved": has_personal})
    return result


def build_plan(subject_type, subject_name, app_id, changes=None, kind="save"):
    target = _authorize(subject_type, subject_name, app_id, write=True)
    app = _app(app_id)
    before = policy.effective_work(subject_type, subject_name, app_id)
    document = policy.get_policy(subject_type, subject_name, for_update=True)
    original = _rules(document)
    rows = copy.deepcopy(original)
    ordinary = _ordinary_ids(app)
    touched = set()
    if kind == "save":
        changes = normalize_changes(changes or [], app)
        for change in changes:
            operation_id = change["operation_id"]
            current = _operation_state(before, operation_id)
            if change["enabled"] == bool(current["allowed"]) and _objects(change["scopes"]) == _objects(current["scopes"]):
                continue
            if before.get("suspended"):
                frappe.throw("请先重新启用这个应用并核对将恢复的权限。", frappe.PermissionError)
            if any(_complex(row) for row in original if row["app_id"] == app_id and row["operation_id"] == operation_id):
                frappe.throw("这项工作含有期限或特别限制，请先核对具名安排，普通勾选不会覆盖它。", frappe.PermissionError)
            touched.add(operation_id)
            rows = [row for row in rows if not (row["app_id"] == app_id and row["operation_id"] == operation_id)]
            operation = _operation(app, operation_id)
            deadline = _grant_deadline(subject_type, target, app_id) if change["enabled"] else None
            selected = _objects(change["scopes"])
            for scope in operation["objects"]:
                effect = "allow" if (scope["scope_type"], scope["scope_ref"]) in selected else "deny"
                rows.append(_new_rule(app_id, operation_id, effect, scope, deadline))
        if touched:
            # Coordinate only the needed entry gate. Never delete a stop deny.
            for change in changes:
                if change["operation_id"] in touched and change["enabled"]:
                    for scope in change["scopes"]:
                        if _entry_allows(subject_type, target, rows, app_id, scope):
                            continue
                        gate = _new_rule(app_id, "app.enter", "allow", scope, _grant_deadline(subject_type, target, app_id))
                        if not any(_json(row) == _json(gate) for row in rows):
                            rows.append(gate)
    elif kind == "restore":
        if subject_type != "User":
            _invalid("恢复部门安排只能用于一位员工。")
        touched = ordinary
        # app.enter allow is retained if a non-ordinary permission depends on it;
        # otherwise restoring ordinary work also restores its entry source.
        has_important = any(row["app_id"] == app_id and row["operation_id"] not in ordinary | {"app.enter"} for row in rows)
        rows = [row for row in rows if not (row["app_id"] == app_id and (row["operation_id"] in ordinary or _stop(row, app_id) or (row["operation_id"] == "app.enter" and not has_important)))]
    elif kind == "suspend":
        if subject_type != "User":
            _invalid("只能停用一位员工的一个应用。")
        if not any(_stop(row, app_id) for row in rows):
            rows.append({**_new_rule(app_id, "app.enter", "deny", {"scope_type": "ALL", "scope_ref": "*"}), **STOP})
    elif kind == "reenable":
        if subject_type != "User":
            _invalid("只能重新启用一位员工的一个应用。")
        if not any(_stop(row, app_id) for row in rows):
            if before.get("suspended"):
                frappe.throw("应用由部门安排停用，不能通过个人启用绕过。", frappe.PermissionError)
        rows = [row for row in rows if not _stop(row, app_id)]
    else:
        _invalid("未注册的工作命令。")
    after = policy.effective_work(subject_type, subject_name, app_id, policy_overrides={(subject_type, subject_name): rows})
    if kind == "reenable" and after.get("suspended"):
        frappe.throw("部门仍停用此应用，不能由个人重新启用绕过。", frappe.PermissionError)
    # An entry change must not unlock an untouched operation, including a hidden
    # export or an important action. Reenable explicitly previews ordinary work.
    for operation in after["operations"]:
        old = _operation_state(before, operation["operation_id"])
        gains = set(_objects(operation["scopes"])) - set(_objects(old["scopes"]))
        if kind == "save" and operation["operation_id"] not in touched and _objects(operation["scopes"]) != _objects(old["scopes"]):
            frappe.throw("应用入口变化会影响本次未修改的工作，已阻止自动保存。", frappe.PermissionError)
        if gains and operation["operation_id"] not in touched:
            registered = next((item for item in app["operations"] if item["id"] == operation["operation_id"]), {})
            if kind != "reenable" or not registered.get("ordinary"):
                frappe.throw("应用入口变化会启用本次未选择的工作，已阻止自动保存，请单独核对。", frappe.PermissionError)
    return {"before": describe(before), "after": describe(after), "changed": _json(original) != _json(rows), "context_revision": before["context_revision"], "impact": _impact(subject_type, subject_name, app_id, rows), "_rules": rows, "_version": int(document.version) if document else 0}


def preview_work(subject_type, subject_name, app_id, changes=None, kind="save"):
    result = build_plan(subject_type, subject_name, app_id, changes, kind)
    return {key: value for key, value in result.items() if not key.startswith("_")}


def commit_work(subject_type, subject_name, app_id, changes=None, expected_version=None, context_revision=None, request_id=None, kind="save"):
    guards.require_post()
    if not isinstance(request_id, str) or not 16 <= len(request_id) <= 100:
        _invalid("请提交独立的请求编号。")
    try:
        expected_version = int(expected_version)
    except (ValueError, TypeError):
        _invalid("缺少已读取的策略版本。")
    payload = {"app_id": app_id, "changes": changes or [], "kind": kind, "expected_version": expected_version, "context_revision": context_revision}
    from hbos_portal.auth.onboarding import serialize
    # Serialize IAM writers even when the target Policy does not yet exist.
    # Current DB row locks remain the final arbiter for native account revocation.
    with serialize("iam-work", "site"):
        actor = policy.get_current_user()
        frappe.db.sql("select name, enabled from `tabUser` where name=%s for update", (actor,))
        policy.get_policy("User", actor, for_update=True)
        policy.get_policy(subject_type, subject_name, for_update=True)
        _authorize(subject_type, subject_name, app_id, write=True)
        replayed = audit.replay(request_id, "work." + kind, subject_type, subject_name, payload)
        if replayed is not None:
            return {**replayed, "replayed": True}
        plan = build_plan(subject_type, subject_name, app_id, changes, kind)
        if expected_version != plan["_version"] or not context_revision or context_revision != plan["context_revision"]:
            _conflict("安排或其来源已变化，请刷新结果并保留草稿后重新核对。")
        if not plan["changed"]:
            return {**plan["before"], "changed": False, "replayed": False}
        savepoint = "iam_work_command"
        frappe.db.savepoint(savepoint)
        try:
            with guards.controlled_write():
                document = policy.get_policy(subject_type, subject_name, for_update=True)
                if not document:
                    document = frappe.get_doc({"doctype": policy.POLICY, "subject_type": subject_type, "subject_name": subject_name, "version": 1, "enabled": 1})
                else:
                    document.version += 1
                document.set("rules", plan["_rules"])
                document.save(ignore_permissions=True)
                _authorize(subject_type, subject_name, app_id, write=True)
                result = {**describe(policy.effective_work(subject_type, subject_name, app_id)), "changed": True, "replayed": False}
                audit.append_event(request_id, "work." + kind, subject_type, subject_name, payload, before=plan["before"], after=result, version=document.version)
            # Frappe commits the whole successful POST, including its event.
            return result
        except Exception:
            frappe.db.rollback(save_point=savepoint)
            raise
