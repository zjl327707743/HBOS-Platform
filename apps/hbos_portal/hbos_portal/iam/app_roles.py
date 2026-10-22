"""Controlled cross-application native role grants for managed employees.

Why this exists
---------------
``guard_user()`` blocks every native role change on a managed identity. That
boundary stays. Business portals such as inventory still authorize through the
native ERPNext role (``Stock User`` / ``Stock Manager``) because the IAM policy
model has no inventory operations yet. Without a supported command an operator
cannot give a managed employee a legitimate warehouse duty at all.

What this command does (and does not)
-------------------------------------
* Only roles listed in ``REGISTRY`` can be granted. Unknown names, Role
  Profiles, System Manager / HR Manager and other high-privilege roles are
  rejected by construction; there is no generic "set any role" API.
* The operator needs ``iam.access.manage`` in the target employee's department
  and company. Because every registered role is native-GLOBAL (it cannot be
  bounded to a company/warehouse inside ERPNext), a page/API grant additionally
  requires an explicitly designated site-level grantor and an explicit
  ``acknowledged_global_scope`` confirmation. A restricted HR administrator can
  never grant a GLOBAL role merely because they manage that employee.
* The operator must pass the real password proof required by the existing
  command layer and may not grant to their own account.
* Only the registered roles are added/removed. Every other native role,
  account state and identity association is preserved.
* The write happens inside ``guards.controlled_write()`` so ``guard_user()``
  still blocks Desk/REST/Has Role/Role Profile bypasses, while this one
  audited command is allowed. The flag is request-local and never exposed.
* The grant is native Frappe authority: the role itself is global. The
  registry records that fact and the UI shows it. This round does not invent
  warehouse-level scope inside ERPNext.
"""
from __future__ import annotations

import hashlib
import json

import frappe

from hbos_portal.auth.onboarding import serialize
from hbos_portal.iam import audit, guards, policy

ASSIGNMENT = "HBOS IAM Role Assignment"

# Server-owned registry. Every grantable native role must be listed here with
# its real backend meaning. Adding a role is a reviewed code change.
REGISTRY = {
    "inventory": {
        "title": "仓储库存",
        "scope_note": "ERPNext 原生角色本身不区分公司或仓库。实际数据包络由该员工既有的 Company User Permission 限定在公司级；仓库级包络未实现。授予前必须能证明这一公司包络，否则拒绝。",
        "roles": {
            "Stock User": {
                "title": "仓储经办",
                "native_scope": "GLOBAL",
                "risk": "medium",
                "summary": "可进入仓储门户并读取库存主数据；同时含 Delivery Note、Delivery Trip 等单据的读写删权限。",
                "permissions_note": "已核对：Stock User 在 permlevel 0 上有 51 条 DocPerm，含 Bin/Warehouse/Stock Ledger Entry 读取，也含 Delivery Note 等写权限；不是只读角色。",
            },
        },
        "blocked": {
            "Stock Manager": "本轮不开放：除仓储读写外还含 Landed Cost Voucher、Asset Movement 等更广提交权限，需单独审批与范围方案。",
            "System Manager": "本轮不开放：平台级高权限。",
            "HR Manager": "本轮不开放：不属于仓储职责。",
            "Accounts Manager": "本轮不开放：不属于仓储职责。",
        },
    }
}


def _fail(message: str):
    frappe.throw(message, frappe.ValidationError)


def _app(app_id: str) -> dict:
    app = REGISTRY.get(app_id)
    if not app:
        _fail("应用未登记可授予的原生角色。")
    return app


GRANTORS_KEY = "hbos_native_role_grantors"


def grantors() -> list[str]:
    """Single source of truth for the site-level GLOBAL grantor list.

    The CLI writer in ``role_init`` imports this function; a divergent parser
    would either grant authority nobody can audit or silently ignore a
    configured grantor.
    """
    raw = frappe.conf.get(GRANTORS_KEY) or []
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(",")]
    if not isinstance(raw, (list, tuple)):
        return []
    return sorted({str(item).strip() for item in raw if str(item).strip()})


def _grantors() -> list[str]:
    return grantors()


def is_site_grantor(user: str | None = None) -> bool:
    current = user or policy.get_current_user()
    return bool(current) and current in _grantors()


def _has_global_role(app: dict) -> bool:
    return any(meta.get("native_scope") == "GLOBAL" for meta in app["roles"].values())


def company_envelope(employee: dict) -> dict | None:
    """Return the exact company envelope proven by a native User Permission.

    A GLOBAL native role is only acceptable when the target user already has one
    unambiguous Company User Permission for the employee's company. This does not
    create or widen that permission; missing/ambiguous scope means no grant.
    """
    user = policy.value(employee, "user_id")
    company = policy.value(employee, "company")
    rows = frappe.db.sql(
        "select name, allow, for_value, applicable_for, apply_to_all_doctypes "
        "from `tabUser Permission` where user=%s and allow='Company' order by name limit 3 for update",
        (user,),
        as_dict=True,
    )
    if len(rows) != 1:
        return None
    row = rows[0]
    if policy.value(row, "for_value") != company or policy.value(row, "applicable_for"):
        return None
    return {"company": company, "source": "User Permission", "name": policy.value(row, "name")}


def _assert_grant_authority(app: dict, acknowledged: bool, employee: dict | None = None):
    """GLOBAL native roles cannot be bounded; only a site-level grantor may grant."""
    if not _has_global_role(app):
        return
    if acknowledged is not True:
        frappe.throw(
            "该原生角色是 GLOBAL：无法限定在公司或仓库范围内。必须由站点级授权人显式确认后才能继续。",
            frappe.PermissionError,
        )
    if not is_site_grantor():
        frappe.throw(
            "受限管理员不能授予 GLOBAL 原生角色：它覆盖本部门员工之外的公司/仓库数据。"
            "请联系站点级授权人（hbos_native_role_grantors）处理。",
            frappe.PermissionError,
        )
    if employee is not None and company_envelope(employee) is None:
        frappe.throw(
            "无法证明该员工的公司范围包络（需唯一、明确的 Company User Permission）。"
            "在补齐可核验范围前，拒绝授予 GLOBAL 原生角色。",
            frappe.PermissionError,
        )


def _employee(employee_id: str) -> dict:
    if not isinstance(employee_id, str) or not employee_id:
        _fail("必须指定员工。")
    rows = frappe.db.sql(
        "select name, employee_name, employee_number, user_id, department, company, status, modified "
        "from `tabEmployee` where name=%s limit 2 for update",
        (employee_id,),
        as_dict=True,
    )
    if len(rows) != 1:
        _fail("员工不存在或存在冲突。")
    employee = rows[0]
    if policy.value(employee, "status") != "Active":
        _fail("员工档案已失效。")
    if not policy.value(employee, "user_id"):
        _fail("员工尚未开通账号，不能授予原生应用角色。")
    return employee


def _additions(employee: dict, app_id: str, roles) -> list[str]:
    app = _app(app_id)
    target = _normalize(app_id, roles)
    current = _current_app_roles(app, _native_roles(policy.value(employee, "user_id")))
    return sorted(set(target) - set(current))


def _native_roles(user: str) -> list[str]:
    rows = frappe.db.sql(
        "select role from `tabHas Role` where parenttype='User' and parent=%s order by role for update",
        (user,),
        as_dict=True,
    )
    return [policy.value(row, "role") for row in rows]


def _app_roles(app: dict) -> list[str]:
    return sorted(app["roles"])


def _current_app_roles(app: dict, native: list[str]) -> list[str]:
    return [role for role in _app_roles(app) if role in set(native)]


def _authorize(employee: dict, *, write: bool):
    operation = "iam.access.manage" if write else "iam.access.read"
    guards.require_capability(
        operation,
        department=policy.value(employee, "department"),
        company=policy.value(employee, "company"),
        app_id="iam",
        target_user=policy.value(employee, "user_id"),
    )
    if write and policy.get_current_user() == policy.value(employee, "user_id"):
        frappe.throw("不能给自己授予或撤销应用角色。", frappe.PermissionError)


def _version(employee: dict) -> str:
    # Role changes are written to the User, so the optimistic version is the
    # User.modified value (locked for update) rather than Employee.modified.
    return str(frappe.db.get_value("User", policy.value(employee, "user_id"), "modified", for_update=True))


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode()).hexdigest()


def describe(employee_id: str) -> dict:
    employee = _employee(employee_id)
    _authorize(employee, write=False)
    native = _native_roles(policy.value(employee, "user_id"))
    apps = []
    for app_id, app in REGISTRY.items():
        apps.append(
            {
                "app_id": app_id,
                "title": app["title"],
                "scope_note": app["scope_note"],
                "roles": [
                    {"role": role, "title": meta["title"], "native_scope": meta["native_scope"], "risk": meta["risk"], "summary": meta["summary"], "permissions_note": meta["permissions_note"]}
                    for role, meta in sorted(app["roles"].items())
                ],
                "blocked": [{"role": role, "reason": reason} for role, reason in sorted(app["blocked"].items())],
                "current": _current_app_roles(app, native),
            }
        )
    return {
        "employee": policy.value(employee, "name"),
        "user": policy.value(employee, "user_id"),
        "company": policy.value(employee, "company"),
        "department": policy.value(employee, "department"),
        "version": _version(employee),
        "native_roles": sorted(native),
        "apps": apps,
        "is_grantor": is_site_grantor(),
        "can_grant": is_site_grantor(),
        "grant_requirement": "本轮登记的原生角色均为 GLOBAL；只有站点级授权人显式确认、且员工已有唯一 Company User Permission 时才能授予。仓库级范围仍未实现。",
        "scope_envelope": company_envelope(employee),
    }


def _normalize(app_id: str, roles) -> list[str]:
    app = _app(app_id)
    if isinstance(roles, str):
        try:
            roles = json.loads(roles)
        except (ValueError, TypeError):
            _fail("角色清单格式无效。")
    if not isinstance(roles, list):
        _fail("角色清单无效。")
    allowed = set(app["roles"])
    result = []
    for role in roles:
        if not isinstance(role, str) or role not in allowed:
            _fail("角色不在本轮可授予清单内：" + str(role))
        if role not in result:
            result.append(role)
    return sorted(result)


def _plan(employee_id: str, app_id: str, roles, expected_version: str, acknowledged_global_scope: bool = False) -> dict:
    app = _app(app_id)
    employee = _employee(employee_id)
    _authorize(employee, write=True)
    target = _normalize(app_id, roles)
    user = policy.value(employee, "user_id")
    native = _native_roles(user)
    current = _current_app_roles(app, native)
    add = sorted(set(target) - set(current))
    remove = sorted(set(current) - set(target))
    # The company-envelope precondition is a *grant* condition. Applying it to
    # a removal would make a GLOBAL role impossible to revoke exactly when the
    # target's Company User Permission changed and revocation is most urgent.
    if add:
        _assert_grant_authority(app, acknowledged_global_scope, employee)
    version = _version(employee)
    if str(expected_version) != version:
        frappe.throw("员工资料或账号已变化，请重新读取后再预览。", frappe.TimestampMismatchError)
    after_roles = sorted((set(native) - set(remove)) | set(add))
    context = _digest(
        {
            "employee": employee_id,
            "user": user,
            "version": version,
            "app_id": app_id,
            "add": add,
            "remove": remove,
            "after": after_roles,
        }
    )
    return {
        "employee": employee_id,
        "user": user,
        "app_id": app_id,
        "current": current,
        "target": target,
        "add": add,
        "remove": remove,
        "unchanged": sorted(set(current) & set(target)),
        "other_roles_preserved": sorted(set(native) - set(current)),
        "changed": bool(add or remove),
        "version": version,
        "context_revision": context,
        "scope_note": app["scope_note"],
        "scope_envelope": company_envelope(employee),
    }


def preview(employee_id: str, app_id: str, roles, expected_version: str, acknowledged_global_scope: bool = False) -> dict:
    return _plan(employee_id, app_id, roles, expected_version, acknowledged_global_scope)


def save(employee_id: str, app_id: str, roles, expected_version: str, context_revision: str, request_id: str, acknowledged_global_scope: bool = False) -> dict:
    guards.require_post()
    if not isinstance(request_id, str) or not request_id:
        _fail("缺少请求编号。")
    if acknowledged_global_scope not in (True, False):
        _fail("确认字段格式无效。")
    app = _app(app_id)
    payload = {
        "employee": employee_id,
        "app_id": app_id,
        "roles": _normalize(app_id, roles),
        "expected_version": str(expected_version),
        "context_revision": str(context_revision or ""),
        "acknowledged_global_scope": acknowledged_global_scope is True,
    }

    from hbos_portal.iam.role_commands import _proof

    with serialize("iam-work", "site"):
        # Authorization is a precondition of replay: a repeated request must not
        # return historical success after the actor lost scope or grantor status.
        employee = _employee(employee_id)
        _authorize(employee, write=True)
        if _additions(employee, app_id, payload["roles"]):
            _assert_grant_authority(app, acknowledged_global_scope, employee)
        replayed = audit.replay(request_id, "app_role.save", "Employee", employee_id, payload)
        if replayed is not None:
            return {**replayed, "replayed": True}
        plan = _plan(employee_id, app_id, roles, expected_version, acknowledged_global_scope)
        if not context_revision or context_revision != plan["context_revision"]:
            frappe.throw("预览内容已变化，请重新预览。", frappe.TimestampMismatchError)
        _proof(consume=True)
        if not plan["changed"]:
            return {**plan, "changed": False}
        user = policy.value(employee, "user_id")
        # Lock and assert the version again inside the write transaction.
        locked_modified = frappe.db.get_value("User", user, "modified", for_update=True)
        if str(locked_modified) != plan["version"]:
            frappe.throw("账号在保存过程中发生变化，请重新读取。", frappe.TimestampMismatchError)
        user_doc = frappe.get_doc("User", user)
        current = {row.role for row in user_doc.roles}
        keep = [{"role": row.role} for row in user_doc.roles if row.role not in set(plan["remove"])]
        added = [{"role": role} for role in plan["add"] if role not in current]
        user_doc.set("roles", keep + added)
        # controlled_write() is the single request-local authority for an
        # approved IAM command. Both guard_user() (before_validate) and the User
        # on_update hook honour it; without it, every grant to a managed Website
        # User is rejected as an unexpected native role change (HTTP 409).
        with guards.controlled_write():
            user_doc.save(ignore_permissions=True)
            after = {
                "employee": employee_id,
                "user": user,
                "app_id": app_id,
                "roles": plan["target"],
                "added": plan["add"],
                "removed": plan["remove"],
            }
            audit.append_event(
                request_id,
                "app_role.save",
                "Employee",
                employee_id,
                payload,
                before={"app_roles": plan["current"], "other_roles": plan["other_roles_preserved"]},
                after={**after, "acknowledged_global_scope": acknowledged_global_scope is True},
                version=1,
                reason="受控跨应用原生角色调整（GLOBAL 范围已由站点级授权人确认）" if acknowledged_global_scope else "受控跨应用原生角色调整",
            )
    return {**plan, "changed": True, "after": plan["target"], "replayed": False}
