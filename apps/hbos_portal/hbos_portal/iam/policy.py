from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

import frappe

POLICY = "HBOS IAM Policy"
RULE = "HBOS IAM Rule"
SCOPE_TYPES = {"SELF", "DEPARTMENT", "COMPANY", "WAREHOUSE", "LAB_GROUP", "KNOWLEDGE_SPACE", "EQUIPMENT", "ALL"}
MANAGEMENT = {
    "iam.people.read": "查看员工", "iam.people.link": "关联账号", "iam.people.provision": "开通账号",
    "iam.people.create": "新增员工", "iam.people.transfer": "调整部门", "iam.people.disable": "停用账号",
    "iam.people.reset": "重置临时密码", "iam.departments.read": "查看部门", "iam.departments.manage": "安排部门应用",
    "iam.access.read": "查看应用安排", "iam.access.manage": "修改应用安排", "iam.audit.read": "查看变更记录",
    "iam.roles.read": "查看角色与发布版本", "iam.roles.edit": "保存角色草稿",
    "iam.roles.publish": "发布角色权限", "iam.roles.assign": "分配应用角色",
}


def current_read(function):
    """Bounded retry for a fixed read-only closure, never a business command.

    Authorization is inside the closure and runs again after rollback. No
    decisions, rows, proofs or permissions survive a failed transaction.
    """
    from time import sleep
    conflicts = tuple(kind for name in ("QueryDeadlockError", "QueryTimeoutError") if isinstance((kind := getattr(frappe, name, None)), type))
    for attempt in range(4):
        try:
            return function()
        except conflicts:
            frappe.db.rollback()
            if attempt == 3:
                raise
            sleep((0.025, 0.125, 0.5)[attempt])


def value(row: Any, key: str, default=None):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def _fail(message: str):
    frappe.throw(message, frappe.PermissionError)


def enabled_flag(name):
    return frappe.conf.get(name) in (True, 1, "1")


def get_current_user() -> str:
    # Session-derived identity. Every request already re-validates the account in
    # auth_hooks (accounts.check_request -> require_user), so a row lock here
    # only serialized all concurrent reads of the same account.
    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
        _fail("请使用有效账号登录。")
    return user


def resolve_employee(user: str, required: bool = True, *, lock: bool = False):
    if not user or user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
        _fail("账号未开通或已停用。")
    rows = frappe.db.sql(
        "select name,user_id,department,company,status,employee_number,modified from `tabEmployee` where user_id=%s order by name limit 2"
        + (" for update" if lock else ""), (user,), as_dict=True)
    if len(rows) > 1:
        _fail("员工关联存在冲突，请联系管理员核对。")
    if not rows:
        if required:
            _fail("尚未确认员工档案关联，暂不能使用考勤。")
        return None
    if value(rows[0], "status") != "Active":
        _fail("员工档案已失效。")
    return rows[0]


def get_policy(subject_type: str, subject_name: str, for_update: bool = False):
    if subject_type not in {"User", "Department"} or not isinstance(subject_name, str) or not subject_name:
        frappe.throw("策略对象无效。", frappe.ValidationError)
    if for_update:
        rows = frappe.db.sql("select name from `tabHBOS IAM Policy` where subject_type=%s and subject_name=%s order by name limit 2 for update", (subject_type, subject_name), as_dict=True)
    else:
        rows = frappe.get_all(POLICY, filters={"subject_type": subject_type, "subject_name": subject_name}, fields=["name"], limit_page_length=2)
    if len(rows) > 1:
        _fail("同一对象存在多份策略，已拒绝授权。")
    if not rows:
        return None
    name = value(rows[0], "name")
    return frappe.get_doc(POLICY, name, for_update=for_update)


def _operation(identifier, title, *, ordinary=True, integrated=True, scope_types=None, objects=None):
    return {"id": identifier, "title": title, "ordinary": ordinary, "integrated": integrated, "scope_types": scope_types or [], "objects": objects or []}


def registered_apps() -> list[dict]:
    """Server-owned registry, never accepted from a browser or inferred from a Role."""
    enabled = enabled_flag("hbos_iam_enabled")
    own_object = [{"scope_type": "SELF", "scope_ref": "", "label": "本人"}]
    apps = [
        {"id": "attendance", "title": "考勤管理", "integrated": enabled, "synthetic": False, "operations": [
            _operation("attendance.read", "查看自己的考勤", integrated=enabled, scope_types=["SELF"], objects=own_object),
            _operation("attendance.export", "导出考勤", integrated=False)]},
        {"id": "iam", "title": "管理中心", "integrated": enabled, "synthetic": False, "operations": [
            _operation(identifier, title, ordinary=False, integrated=enabled, scope_types=["DEPARTMENT", "COMPANY"]) for identifier, title in MANAGEMENT.items()]},
    ]
    if enabled_flag('hbos_iam_roles_enabled'):
        from hbos_portal.iam.role_access import OPERATIONS
        apps[0]['operations'].extend(_operation(identifier, title, ordinary=False, integrated=enabled and integrated,
            scope_types=['DEPARTMENT', 'COMPANY'] if minimum == 'DEPARTMENT' else ['COMPANY'])
            for identifier, (title, _, minimum, integrated) in OPERATIONS.items() if identifier != 'attendance.read')
    else:
        apps[1]['operations'] = [operation for operation in apps[1]['operations'] if not operation['id'].startswith('iam.roles.')]
    for identifier, title in [("inventory", "库存管理"), ("lims", "质量检验"), ("knowledge", "知识库"), ("twin", "数字孪生")]:
        apps.append({"id": identifier, "title": title, "integrated": False, "synthetic": False, "operations": []})
    demo = enabled and enabled_flag("hbos_iam_test_site") and enabled_flag("hbos_iam_demo_enabled")
    warehouses = [{"scope_type": "WAREHOUSE", "scope_ref": "synthetic-warehouse-" + suffix.lower(), "label": "合成" + suffix + "仓（规则验证）"} for suffix in ("A", "B")]
    if demo and enabled_flag("hbos_iam_demo_new_object_enabled"):
        warehouses.append({"scope_type": "WAREHOUSE", "scope_ref": "synthetic-warehouse-c", "label": "合成C仓（新增对象验证）"})
    apps.append({"id": "iam_demo", "title": "合成扩展验证", "integrated": demo, "synthetic": True, "operations": [
        _operation("iam_demo.read", "查看合成设备", integrated=demo, scope_types=["EQUIPMENT"], objects=[{"scope_type": "EQUIPMENT", "scope_ref": "synthetic-equipment", "label": "合成设备"}]),
        _operation("iam_demo.query", "查询合成仓对象（规则验证）", integrated=demo, scope_types=["WAREHOUSE"], objects=warehouses),
        _operation("iam_demo.update", "修改合成仓对象（规则验证）", integrated=demo, scope_types=["WAREHOUSE"], objects=warehouses),
    ]})
    return apps


def registration(app_id: str, operation_id: str):
    if not isinstance(operation_id, str):
        return None
    if operation_id.startswith('iam.roles.') and not enabled_flag('hbos_iam_roles_enabled'):
        return None
    app = next((item for item in registered_apps() if item["id"] == app_id), None)
    if not app or not app["integrated"]:
        return None
    if operation_id == "app.enter":
        return _operation("app.enter", "应用入口", ordinary=False, scope_types=list(SCOPE_TYPES))
    if operation_id in MANAGEMENT and app_id == "attendance":
        return _operation(operation_id, MANAGEMENT[operation_id], ordinary=False, scope_types=["DEPARTMENT", "COMPANY"])
    return next((item for item in app["operations"] if item["id"] == operation_id and item["integrated"]), None)


def _datetime(item):
    if not item:
        return None
    return item if isinstance(item, datetime) else datetime.fromisoformat(str(item))


def _now():
    from frappe.utils import now_datetime
    return now_datetime()


def active(rule, now):
    if value(rule, "qualification_ref"):
        # No authoritative qualification executor is integrated in this first release.
        return False
    try:
        start, end = _datetime(value(rule, "valid_from")), _datetime(value(rule, "valid_until"))
        return (not start or start <= now) and (not end or now < end)
    except (ValueError, TypeError):
        return False


def rule_dict(rule) -> dict:
    fields = ("app_id", "operation_id", "effect", "scope_type", "scope_ref", "include_descendants", "valid_from", "valid_until", "qualification_ref")
    return {key: value(rule, key) for key in fields}


def validate_rule(rule, *, root=False) -> dict:
    item = rule_dict(rule)
    app_id, operation, scope, ref = (item[key] for key in ("app_id", "operation_id", "scope_type", "scope_ref"))
    if ref is not None and not isinstance(ref, str):
        raise ValueError("范围对象必须是明确的字符串。")
    ref = ref or ""
    if any(not isinstance(item[key], str) for key in ("app_id", "operation_id", "effect", "scope_type")) or not isinstance(ref, str):
        raise ValueError("规则字段格式错误。")
    operation_meta = registration(app_id, operation)
    if not operation_meta or item["effect"] not in {"allow", "deny"} or scope not in SCOPE_TYPES:
        raise ValueError("工作或范围尚未接入，不能授权。")
    if item["include_descendants"] not in (None, False, 0, "0"):
        raise ValueError("本轮不开放自动包含下级部门。")
    if item["qualification_ref"]:
        raise ValueError("资格核验执行器尚未接入，不能以引用文字授予权限。")
    if scope == "ALL":
        if ref != "*" or not ((operation == "app.enter" and item["effect"] == "deny") or root):
            raise ValueError("全部对象只用于明确应用停用或受控隔离根配置。")
    elif scope == "SELF":
        if ref or (operation != "app.enter" and scope not in operation_meta["scope_types"]):
            raise ValueError("本人范围由当前员工关联解析，不接受其他人员编号。")
    elif scope in {"DEPARTMENT", "COMPANY"}:
        if not ref or (operation != "app.enter" and scope not in operation_meta["scope_types"]):
            raise ValueError("没有开放此对象范围。")
        if not frappe.db.exists("Department" if scope == "DEPARTMENT" else "Company", ref):
            raise ValueError("组织对象不存在。")
    else:
        objects = operation_meta["objects"]
        if operation == "app.enter":
            objects = [obj for app in registered_apps() if app["id"] == app_id for op in app["operations"] if op["integrated"] for obj in op["objects"]]
        if not any(obj["scope_type"] == scope and obj["scope_ref"] == ref for obj in objects):
            raise ValueError("对象尚未接入，不能授予。")
    try:
        start, end = _datetime(item["valid_from"]), _datetime(item["valid_until"])
        if start and end and start >= end:
            raise ValueError("有效期结束必须晚于开始。")
    except (ValueError, TypeError) as exc:
        raise ValueError("有效期格式或顺序无效。") from exc
    item.update(scope_ref=ref, include_descendants=0)
    return item


def _rules(kind, name, overrides=None, *, lock=True):
    # Read-only callers pass lock=False: the policy row lock serialized every
    # parallel management read on the same subject.
    doc = get_policy(kind, name, for_update=lock) if name else None
    override = overrides is not None and (kind, name) in overrides
    if doc and not value(doc, "enabled"):
        return [], doc
    rules = overrides[(kind, name)] if override else (value(doc, "rules", []) if doc else [])
    return [rule_dict(rule) for rule in rules], doc


def _matches(rule, scope_type, scope_ref, company=None):
    kind, ref = value(rule, "scope_type"), value(rule, "scope_ref") or ""
    if kind == "ALL":
        return ref == "*"
    if kind == "COMPANY" and scope_type == "DEPARTMENT":
        return bool(company and ref == company)
    return kind == scope_type and ref == scope_ref


def _decide(personal, department, app_id, operation_id, scope_type, scope_ref, now, company=None):
    """One object per decision: no action × scope Cartesian product and no role fallback."""
    relevant = lambda rows, op: [r for r in rows if r["app_id"] == app_id and r["operation_id"] == op]
    matching = lambda rows: [r for r in rows if active(r, now) and _matches(r, scope_type, scope_ref, company)]
    personal_gates, department_gates = relevant(personal, "app.enter"), relevant(department, "app.enter")
    if any(r["effect"] == "deny" for r in matching(personal_gates + department_gates)):
        return False, "应用已停用或此对象被入口限制。", "个人设置" if matching(personal_gates) else "部门安排"
    # An expired explicit personal allow does not silently restore a broader inherited grant.
    gates = personal_gates if any(r["effect"] == "allow" for r in personal_gates) else department_gates
    if not any(r["effect"] == "allow" for r in matching(gates)):
        expired = any(r["effect"] == "allow" and _matches(r, scope_type, scope_ref, company) and not active(r, now) for r in gates)
        return False, "此应用权限尚未生效或已过期，请核对有效期。" if expired else "所属部门尚未开通此应用，或该数据范围尚未获准。", "个人设置" if gates is personal_gates else "部门安排"
    own_rules, inherited = relevant(personal, operation_id), relevant(department, operation_id)
    if any(r["effect"] == "deny" for r in matching(own_rules + inherited)):
        return False, "此项工作在该对象范围受到限制。", "个人设置" if matching(own_rules) else "部门安排"
    allows = own_rules if any(r["effect"] == "allow" for r in own_rules) else inherited
    if not any(r["effect"] == "allow" for r in matching(allows)):
        expired = any(r["effect"] == "allow" and _matches(r, scope_type, scope_ref, company) and not active(r, now) for r in allows)
        return False, "此功能权限尚未生效或已过期，请核对有效期。" if expired else "该部门尚未开通此功能，或该数据范围尚未获准。", "个人设置" if allows is own_rules else "部门安排"
    return True, "", "个人设置" if allows is own_rules else "部门安排"


_MISSING = object()


def _evaluate(user, app_id, operation_id, scope_type, scope_ref, now=None, overrides=None, employee_context=None, *, company=_MISSING):
    rejected = lambda reason: {"allowed": False, "reason": reason, "source": "未开放"}
    if not isinstance(scope_type, str) or not isinstance(scope_ref, str):
        return rejected("对象范围格式无效。")
    meta = registration(app_id, operation_id)
    if not meta or operation_id == "app.enter" or scope_type not in meta["scope_types"]:
        return rejected("工作或对象范围尚未开放。")
    if not user or user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
        return rejected("账号未开通或已停用。")
    from hbos_portal.iam.temporary_passwords import status as password_status
    if password_status(user).get("pending"):
        return rejected("员工须先完成首次改密，当前尚不能使用此功能。")
    try:
        employee = resolve_employee(user, required=app_id == "attendance" and not operation_id.startswith("iam."))
    except frappe.PermissionError:
        return rejected("员工档案关联尚未确认或已失效。")
    if employee_context is not None:
        # Internal transfer projection only. The HTTP API never accepts this
        # context, and it cannot replace a User or an Employee association.
        if not employee or value(employee_context, "name") != value(employee, "name") or value(employee_context, "user_id") != user or value(employee_context, "company") != value(employee, "company"):
            return rejected("调岗预览的员工关联不一致。")
        employee = employee_context
    if scope_type == "SELF" and (scope_ref or not employee):
        return rejected("本人范围必须使用当前有效员工关联。")
    if scope_type in {"DEPARTMENT", "COMPANY"} and not frappe.db.exists("Department" if scope_type == "DEPARTMENT" else "Company", scope_ref):
        return rejected("组织对象不存在。")
    if scope_type not in {"SELF", "DEPARTMENT", "COMPANY"} and not any(obj["scope_type"] == scope_type and obj["scope_ref"] == scope_ref for obj in meta["objects"]):
        return rejected("未知对象，已拒绝访问。")
    own, _ = _rules("User", user, overrides)
    inherited, _ = _rules("Department", value(employee, "department"), overrides) if employee else ([], None)
    if operation_id.startswith("iam."):
        inherited = []  # Management delegation never comes from ordinary departmental defaults.
    try:
        for rule in own + inherited:
            if rule["app_id"] == app_id and rule["operation_id"] in {"app.enter", operation_id}:
                validate_rule(rule, root=True)
    except ValueError:
        return rejected("已有规则包含未知或未接入的对象与资格，请核对设置。")
    if app_id == 'attendance' and not operation_id.startswith('iam.') and enabled_flag('hbos_iam_roles_enabled'):
        from hbos_portal.iam.role_access import decide
        decision = decide(employee, operation_id, scope_type, scope_ref)
        if decision is not None:
            return decision
    if company is _MISSING:
        # Authorization never needs to freeze the organization row: a read uses
        # the current snapshot, and every write path locks the target first in
        # guards.require_capability(). Locking here made one management read
        # take 88 department row locks.
        company = frappe.db.get_value("Department", scope_ref, "company") if scope_type == "DEPARTMENT" else None
    allowed, reason, source = _decide(own, inherited, app_id, operation_id, scope_type, scope_ref or "", now or _now(), company)
    return {"allowed": allowed, "reason": reason, "source": source}


def allows(user, app_id, operation_id, scope_type, scope_ref, now=None, *, company=_MISSING) -> bool:
    """Authorization decision only.

    ``evaluate()`` additionally hashes the whole policy revision (~13ms of DB
    reads and row locks) on every call. That value is a response field, never
    part of the decision, so authorization hot paths must not pay for it.
    """
    return bool(_evaluate(user, app_id, operation_id, scope_type, scope_ref, now=now, company=company)["allowed"])


def evaluate(user, app_id, operation_id, scope_type, scope_ref, now=None, *, company=_MISSING):
    result = _evaluate(user, app_id, operation_id, scope_type, scope_ref, now=now, company=company)
    result["policy_revision"] = current_revision(user) if enabled_flag("hbos_iam_enabled") else ""
    return result


def revision_digests(user=None) -> dict:
    """Invalidation hints, never authorization or command preview revisions.

    Read the subject's native association and the policies the evaluator uses.
    Do not include unrelated User/Employee modified times or a whole Policy
    version: changing another app in the same policy must not invalidate SELF.
    Future role executors must extend this versioned dependency contract with
    assignment/template versions and paired scope/expiry, before registration.
    """
    user = user or getattr(frappe.session, "user", None)
    state = frappe.db.get_value("User", user, ["name", "enabled", "hbos_initial_password_pending", "hbos_temporary_password", "hbos_temporary_password_expires_at", "hbos_password_generation"], as_dict=True, for_update=True) if user else None
    employees = frappe.db.sql("select name,user_id,department,company,status,employee_number from `tabEmployee` where user_id=%s order by name limit 2 for update", (user,), as_dict=True) if user else []
    # Explicit projection excludes unrelated fields returned by test adapters.
    fields = ("name", "user_id", "department", "company", "status", "employee_number")
    association = [{key: value(row, key) for key in fields} for row in employees]
    own, own_doc = _rules("User", user) if user and user != "Guest" else ([], None)
    departments = {}
    inherited = []
    for department in sorted({value(row, "department") for row in employees if value(row, "department")}):
        rules, doc = _rules("Department", department)
        inherited.extend(rules)
        departments[department] = {"state": frappe.db.get_value("Department", department, ["name", "company", "disabled"], as_dict=True, for_update=True), "enabled": value(doc, "enabled", 1)}
    now = _now()
    def digest(payload):
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()
    revisions = {}
    for app in registered_apps():
        app_id = app["id"]
        rules = lambda rows: sorted(({**rule_dict(row), "active": active(row, now)} for row in rows if row["app_id"] == app_id), key=lambda row: json.dumps(row, sort_keys=True, default=str))
        # Only management delegations depend on the target organization set.
        delegated = [row for row in own if row["app_id"] == app_id and row["operation_id"] in MANAGEMENT]
        targets = {}
        for row in delegated:
            kind, ref = row["scope_type"], row["scope_ref"]
            if kind == "COMPANY":
                targets["company:" + ref] = frappe.db.get_value("Company", ref, "name", for_update=True)
                targets["members:" + ref] = frappe.get_all("Department", filters={"company": ref}, fields=["name", "company", "disabled"], order_by="name", limit_page_length=0)
            elif kind == "DEPARTMENT":
                targets["department:" + ref] = frappe.db.get_value("Department", ref, ["name", "company", "disabled"], as_dict=True, for_update=True)
        role_dependencies = None
        if app_id == 'attendance' and enabled_flag('hbos_iam_roles_enabled'):
            from hbos_portal.iam.role_access import revision_dependencies
            role_dependencies = revision_dependencies(user)
        revisions[app_id] = digest({"schema": 3 if role_dependencies is not None else 2, "role_extension": role_dependencies if role_dependencies is not None else "not_integrated", "enabled": enabled_flag("hbos_iam_enabled"), "subject": state, "association": association, "departments": departments, "personal_enabled": value(own_doc, "enabled", 1), "personal": rules(own), "inherited": rules(inherited), "registration": app, "delegation_targets": targets})
    return {"policy_revision": digest(revisions), "app_revisions": revisions}


def current_revision(user=None) -> str:
    return revision_digests(user)["policy_revision"]


def _target_context(subject_type, subject_name, app_id):
    """A command context locks only its target and related members, never all Site users."""
    now = _now()
    payload = {"schema": 1, "subject_type": subject_type, "subject_name": subject_name, "app_id": app_id,
               "registration": next((app for app in registered_apps() if app["id"] == app_id), None)}
    def fingerprint(kind, name):
        doc = get_policy(kind, name, for_update=True) if name else None
        return {"version": value(doc, "version", 0), "enabled": value(doc, "enabled", 1), "rules": [{**rule_dict(row), "active": active(row, now)} for row in value(doc, "rules", []) if value(row, "app_id") == app_id]}
    def user_context(user):
        state = frappe.db.get_value("User", user, ["name", "enabled", "modified"], as_dict=True, for_update=True)
        rows = frappe.db.sql("select name,user_id,department,company,status,modified from `tabEmployee` where user_id=%s order by name limit 2 for update", (user,), as_dict=True)
        context = {"user": state, "employees": rows, "personal": fingerprint("User", user), "departments": {}}
        for row in rows:
            department = value(row, "department")
            if department:
                context["departments"][department] = {"state": frappe.db.get_value("Department", department, ["name", "company", "modified"], as_dict=True, for_update=True), "policy": fingerprint("Department", department)}
        if app_id == 'attendance' and enabled_flag('hbos_iam_roles_enabled'):
            from hbos_portal.iam.role_access import revision_dependencies
            context['role_source'] = revision_dependencies(user)
        return context
    if subject_type == "User":
        payload["target"] = user_context(subject_name)
    else:
        payload["department"] = frappe.db.get_value("Department", subject_name, ["name", "company", "modified"], as_dict=True, for_update=True)
        payload["policy"] = fingerprint("Department", subject_name)
        employees = frappe.db.sql("select name,user_id,department,company,status,modified from `tabEmployee` where department=%s order by name for update", (subject_name,), as_dict=True)
        payload["members"] = employees
        payload["users"] = {user: user_context(user) for user in sorted({value(row, "user_id") for row in employees if value(row, "user_id")})}
    payload["demo"] = enabled_flag("hbos_iam_test_site") and enabled_flag("hbos_iam_demo_enabled")
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def effective_work(subject_type, subject_name, app_id, policy_overrides=None, employee_context=None, *, lock=True):
    app = next((item for item in registered_apps() if item["id"] == app_id), None)
    rules, doc = _rules(subject_type, subject_name, policy_overrides, lock=lock)
    now = _now()
    operations = []
    role_assignment = None
    role_summary = None
    if app_id == 'attendance' and enabled_flag('hbos_iam_roles_enabled'):
        from hbos_portal.iam import role_access as roles
        if subject_type == 'User':
            role_employee = employee_context or resolve_employee(subject_name, required=False)
            role_assignment = roles.resolve(role_employee) if role_employee else None
        else:
            defaults = roles.assignments('Department', subject_name, app_id)
            if defaults:
                default = defaults[0]
                role_summary = '已默认安排普通员工；成员能否使用仍按各自账号、发布功能和既有限制核验。' if default.enabled and default.mode == 'DIRECT' else '当前不默认开通角色；个人独立安排保持。'
    for op in app["operations"] if app else []:
        objects = op["objects"]
        if role_assignment is not None and not op['id'].startswith('iam.') and op['id'] != 'attendance.read':
            feature = next((row for row in role_assignment.get('features', []) if row['operation_id'] == op['id']), None)
            objects = [{**scope, 'label': scope['scope_ref']} for scope in role_assignment.get('responsibilities', [])] if feature else []
        if op["id"].startswith("iam."):
            objects = [{"scope_type": r["scope_type"], "scope_ref": r["scope_ref"], "label": r["scope_ref"]} for r in rules if r["operation_id"] == op["id"] and r["scope_type"] in {"DEPARTMENT", "COMPANY"}]
        scopes, sources, reasons = [], [], []
        for obj in objects:
            if subject_type == "User":
                result = _evaluate(subject_name, app_id, op["id"], obj["scope_type"], obj["scope_ref"], now=now, overrides=policy_overrides, employee_context=employee_context)
            else:
                decision = _decide([], rules, app_id, op["id"], obj["scope_type"], obj["scope_ref"], now)
                result = {"allowed": decision[0] and op["integrated"] and op["ordinary"], "reason": decision[1], "source": "部门安排"}
            if result["allowed"]:
                scopes.append({"scope_type": obj["scope_type"], "scope_ref": obj["scope_ref"], "label": obj["label"]})
            sources.append(result["source"])
            if result["reason"]:
                reasons.append(result["reason"])
        operations.append({"operation_id": op["id"], "label": op["title"], "ordinary": op["ordinary"], "available": bool(app["integrated"] and op["integrated"]), "allowed": bool(scopes), "scopes": scopes, "source": "、".join(dict.fromkeys(sources)) or "尚未安排", "reason": "；".join(dict.fromkeys(reasons)) if not scopes else ""})
    suspension_rules = list(rules)
    if subject_type == "User":
        try:
            employee = employee_context or resolve_employee(subject_name, required=False)
            inherited, _ = _rules("Department", value(employee, "department"), policy_overrides) if employee else ([], None)
            suspension_rules.extend(inherited)
        except frappe.PermissionError:
            pass
    suspended = any(r["app_id"] == app_id and r["operation_id"] == "app.enter" and r["effect"] == "deny" and r["scope_type"] == "ALL" and r["scope_ref"] == "*" and active(r, now) for r in suspension_rules)
    ordinary_ids = {op["id"] for op in app["operations"] if op["ordinary"] and op["integrated"]} if app else set()
    return {"subject_type": subject_type, "subject_name": subject_name, "app_id": app_id, "version": value(doc, "version", 0), "context_revision": _target_context(subject_type, subject_name, app_id), "operations": operations, "suspended": suspended, 'role_summary': role_summary, "permission_mode": ("personal" if role_assignment['source_mode'] == 'direct' else "department") if role_assignment is not None else "personal" if subject_type == "Department" or any(r["app_id"] == app_id and r["operation_id"] in ordinary_ids for r in rules) else "department"}


def preview_effective_work(subject_type, subject_name, app_id, rules):
    """Server-only validated draft projection. No writes and no session impersonation."""
    return effective_work(subject_type, subject_name, app_id, policy_overrides={(subject_type, subject_name): rules})
