from __future__ import annotations

from contextlib import contextmanager
import json
from urllib.parse import unquote

import frappe

from hbos_portal.iam import policy

WRITE_CAPABILITIES = {"iam.people.link", "iam.people.provision", "iam.people.create", "iam.people.transfer", "iam.people.disable", "iam.people.reset", "iam.departments.manage", "iam.access.manage", "iam.roles.edit", "iam.roles.publish", "iam.roles.assign"}


def isolated_root() -> bool:
    return policy.get_current_user() == "Administrator" and policy.enabled_flag("hbos_iam_test_site")


def require_post():
    request = getattr(frappe.local, "request", None) or getattr(frappe, "request", None)
    if not request or getattr(request, "method", "").upper() != "POST":
        frappe.throw("此操作只接受经过CSRF校验的POST请求。", frappe.PermissionError)


@contextmanager
def controlled_write():
    """Internal request-local authority; document flags or API payloads cannot set it."""
    previous = frappe.flags.get("hbos_iam_write_depth", 0)
    frappe.flags.hbos_iam_write_depth = previous + 1
    try:
        yield
    finally:
        frappe.flags.hbos_iam_write_depth = previous


def require_controlled_write():
    if not frappe.flags.get("hbos_iam_write_depth", 0):
        frappe.throw("请使用受控管理服务，不能直接修改权限记录。", frappe.PermissionError)


def _permitted(user, operation, kind, ref, app_id):
    # An explicit platform delegation may cover a business app. A native role never does.
    apps = [app_id] if app_id == "iam" else [app_id, "iam"]
    return any(policy.evaluate(user, app, operation, kind, ref)["allowed"] for app in apps)


def managed_departments(operation_id, app_id="iam") -> list[str]:
    user = policy.get_current_user()
    if not policy.enabled_flag("hbos_iam_enabled") or operation_id not in policy.MANAGEMENT:
        return []
    rows = frappe.get_all("Department", fields=["name", "company"], order_by="name", limit_page_length=0)
    if isolated_root():
        return [policy.value(row, "name") for row in rows]
    return [policy.value(row, "name") for row in rows if _permitted(user, operation_id, "DEPARTMENT", policy.value(row, "name"), app_id)]


def require_capability(operation_id, department=None, company=None, app_id="iam", target_user=None):
    user = policy.get_current_user()
    if not policy.enabled_flag("hbos_iam_enabled"):
        frappe.throw("此站点尚未启用IAM管理。", frappe.PermissionError)
    if operation_id not in policy.MANAGEMENT or app_id not in {app["id"] for app in policy.registered_apps()}:
        frappe.throw("管理能力未注册。", frappe.PermissionError)
    root = isolated_root()
    if target_user == user and operation_id in WRITE_CAPABILITIES and not root:
        frappe.throw("不能为自己审批或修改授权与账号状态。", frappe.PermissionError)
    if department:
        actual_company = frappe.db.get_value("Department", department, "company", for_update=True)
        if not actual_company or (company and company != actual_company):
            frappe.throw("部门或公司范围不一致。", frappe.PermissionError)
        if root or _permitted(user, operation_id, "DEPARTMENT", department, app_id):
            return
    elif company:
        if frappe.db.exists("Company", company) and (root or _permitted(user, operation_id, "COMPANY", company, app_id)):
            return
    elif root or managed_departments(operation_id, app_id):
        return
    frappe.throw("没有该目标范围的管理权限。", frappe.PermissionError)


def _managed_department(name):
    if name and policy.enabled_flag('hbos_iam_roles_enabled') and frappe.db.exists('DocType', 'HBOS IAM Role Assignment'):
        if frappe.db.get_value('HBOS IAM Role Assignment', {'app_id': 'attendance', 'subject_type': 'Department', 'subject_name': name}, 'name', for_update=True):
            return True
    return bool(name and frappe.db.exists("DocType", policy.POLICY) and frappe.db.get_value(policy.POLICY, {"subject_type": "Department", "subject_name": name}, "name", for_update=True))


def _managed_user(user):
    if user and policy.enabled_flag('hbos_iam_roles_enabled') and frappe.db.exists('DocType', 'HBOS IAM Role Assignment'):
        employees = frappe.db.sql('select name,user_id,department,company,status from `tabEmployee` where user_id=%s order by name for update', (user,), as_dict=True)
        from hbos_portal.iam import role_access
        if any(role_access.resolve(row) is not None for row in employees):
            return True
    if not user or not frappe.db.exists("DocType", policy.POLICY):
        return False
    if frappe.db.get_value(policy.POLICY, {"subject_type": "User", "subject_name": user}, "name", for_update=True):
        return True
    if not frappe.db.exists("DocType", "Employee"):
        return False
    employees = frappe.db.sql("select department from `tabEmployee` where user_id=%s for update", (user,), as_dict=True)
    # New department defaults preserve independent legacy sources; the old IAM
    # policy boundary remains authoritative for native-role bypass prevention.
    return any(frappe.db.get_value(policy.POLICY, {"subject_type":"Department","subject_name":policy.value(row,"department")}, "name", for_update=True) for row in employees if policy.value(row,"department"))


def guard_employee(doc, method=None):
    if frappe.flags.get("hbos_iam_write_depth", 0):
        return
    before = doc.get_doc_before_save()
    fields = ("user_id", "department", "company", "status")
    if before and all(doc.get(field) == before.get(field) for field in fields):
        return
    subjects = [item for item in (before, doc) if item]
    if any(_managed_user(item.get("user_id")) or _managed_department(item.get("department")) for item in subjects):
        frappe.throw("已纳管员工的账号关联、组织与状态请使用受控员工管理流程。", frappe.PermissionError)


def guard_user(doc, method=None):
    if frappe.flags.get("hbos_iam_write_depth", 0) or not _managed_user(doc.name):
        return
    before = doc.get_doc_before_save()
    if not before:
        return
    roles = lambda item: sorted(row.role for row in item.get("roles", []))
    if any(doc.get(field) != before.get(field) for field in ("enabled", "user_type")) or roles(doc) != roles(before):
        frappe.throw("已纳管账号的状态或原生角色请使用受控管理流程。", frappe.PermissionError)


def guard_user_permission(doc, method=None):
    if not frappe.flags.get("hbos_iam_write_depth", 0) and _managed_user(doc.user):
        frappe.throw("不能直接改写已纳管账号的原生授权范围。", frappe.PermissionError)


def _managed_identity(doc):
    """Use persisted current ownership, never a renamed or detached payload."""
    if policy.value(doc, "doctype") == "User":
        return _managed_user(policy.value(doc, "name"))
    if policy.value(doc, "doctype") == "Employee":
        current = frappe.db.get_value("Employee", policy.value(doc, "name"), ["user_id", "department"], as_dict=True, for_update=True)
        subjects = [item for item in (current, doc) if item]
        return any(_managed_user(policy.value(item, "user_id")) or _managed_department(policy.value(item, "department")) for item in subjects)
    return False


def identity_has_permission(doc, user=None, ptype=None, debug=False):
    # Returning True only leaves the original native permission decision in
    # place. IAM adds a targeted deny; it never grants native HR/Desk access.
    if ptype != "delete" or not policy.enabled_flag("hbos_iam_enabled"):
        return True
    return not _managed_identity(doc)


def guard_identity_delete(doc, method=None):
    # No public or controlled IAM delete command is approved in this release.
    # This also covers native Administrator/ignore_permissions paths, which
    # can bypass the native pre-delete permission check.
    if policy.enabled_flag("hbos_iam_enabled") and _managed_identity(doc):
        frappe.throw("已纳管的员工与账号须保留；本轮不开放删除，请使用受控停用流程。", frappe.PermissionError)


def guard_identity_rename(doc, method=None, old=None, new=None, merge=False):
    # before_validate is not run by native SQL rename/merge. Reject before
    # primary keys, dynamic links and historical foreign keys are rewritten.
    if policy.enabled_flag("hbos_iam_enabled") and _managed_identity(doc):
        frappe.throw("已纳管的员工与账号主键不可改名或合并。", frappe.PermissionError)


def _deny_managed_deletions(doctype, names):
    if doctype not in {"User", "Employee"}:
        return
    if isinstance(names, str):
        try:
            names = json.loads(names)
        except (ValueError, TypeError):
            names = None
    # The native bulk endpoint sorts json.loads(items): dictionaries would be
    # iterated as their keys. Do not let an ambiguous shape evade preflight.
    if not isinstance(names, (list, tuple)) or any(not isinstance(name, str) or not name for name in names):
        frappe.throw("删除请求必须明确列出对象主键。", frappe.PermissionError)
    for name in names:
        if isinstance(name, str) and name:
            guard_identity_delete({"doctype": doctype, "name": name})


def check_identity_request():
    """Preflight only fixed native deletion routes, before User logout can commit."""
    if not policy.enabled_flag("hbos_iam_enabled") or getattr(frappe.session, "user", None) in (None, "Guest"):
        return
    request = getattr(frappe.local, "request", None)
    if not request:
        return
    path = unquote(str(getattr(request, "path", "") or ""))
    args = frappe.local.form_dict or {}
    if str(getattr(request, "method", "")).upper() == "DELETE":
        for prefix in ("/api/resource/", "/api/v2/document/"):
            if path.startswith(prefix):
                parts = path[len(prefix):].split("/", 1)
                if len(parts) == 2:
                    _deny_managed_deletions(parts[0], [parts[1]])
    command = str(args.get("cmd") or "")
    # Frappe app dispatches form_dict.cmd before the path-based API handler.
    # A command on a different method path must not evade this preflight.
    if not command and path.startswith("/api/method/"):
        command = path[len("/api/method/"):]
    elif not command and path.startswith("/api/v2/method/"):
        command = path[len("/api/v2/method/"):]
    if command == "frappe.client.delete":
        _deny_managed_deletions(args.get("doctype"), [args.get("name")])
    elif command == "frappe.desk.reportview.delete_items":
        _deny_managed_deletions(args.get("doctype"), args.get("items"))


def check_identity_job(method=None, kwargs=None, transaction_type=None):
    # Core restores the stored job.user, not a caller-supplied identity inside
    # kwargs. No worker (including Administrator) may lend authority to delete
    # an IAM-managed identity. Old queued work is rechecked at execution time.
    if policy.enabled_flag("hbos_iam_enabled") and method == "frappe.desk.reportview.delete_bulk":
        args = kwargs or {}
        _deny_managed_deletions(args.get("doctype"), args.get("items"))


def check_authenticated_request():
    """Fixed post-native-auth checks, not an authentication provider dispatcher."""
    if not policy.enabled_flag("hbos_iam_enabled"):
        return
    check_identity_request()
    if "hb_attendance_app" in frappe.get_installed_apps():
        # Keep Portal independent of a business-app import when uninstalled.
        # An installed guard that cannot load must fail closed, never be skipped.
        frappe.get_attr("hb_attendance_app.hbos_attendance.portal.permissions.check_request")()
