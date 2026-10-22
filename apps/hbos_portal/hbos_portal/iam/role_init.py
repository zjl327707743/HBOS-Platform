"""Controlled role initialization and initial management delegation (CLI only).

Trust boundary
--------------
These functions are called by the local trusted operator through
``bench --site <site> hbos_portal init-roles`` / ``delegate-admin``. They are
*not* whitelisted HTTP endpoints and do not accept a web session. The CLI
operator identity and reason are recorded in the IAM change log; the CLI does
not claim that a browser user completed password/MFA re-authentication.

What initialization does
------------------------
* Validates the exact site, company list and the three attendance role keys.
* Creates only missing role definitions, with server-computed draft features
  and management scopes limited to the explicitly named companies.
* Never publishes a role (drafts are not an execution source), never assigns a
  role to an employee, never grants a native ERPNext/HRMS role, never enables a
  feature flag, and never runs from install/migrate hooks.

Repeated execution keeps existing roles untouched (no duplicate, no overwrite
of published content) and is safe to run again.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
from contextlib import contextmanager

import frappe

from hbos_portal.auth.onboarding import serialize
from hbos_portal.iam import audit, guards, policy, role_access as roles
from hbos_portal.iam.app_roles import GRANTORS_KEY, grantors as _site_grantors

TARGET_ROLES = ("staff", "clerk", "admin")
ACTOR_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@:-]{2,139}")


def _fail(message: str):
    frappe.throw(message, frappe.ValidationError)


def _validate_actor(actor: str, reason: str) -> tuple[str, str]:
    if not isinstance(actor, str) or not ACTOR_PATTERN.fullmatch(actor.strip()):
        _fail("必须填写本机操作者标识（3-140 位字母、数字或 _ . @ : -）。")
    if not isinstance(reason, str) or len(reason.strip()) < 8:
        _fail("必须填写至少 8 个字符的执行原因。")
    return actor.strip(), reason.strip()[:300]


def _validate_scope(companies, role_keys) -> tuple[list[str], list[str]]:
    companies = list(companies or [])
    role_keys = list(role_keys or TARGET_ROLES)
    if not companies:
        _fail("必须显式指定至少一个公司。")
    if len(set(companies)) != len(companies):
        _fail("公司清单存在重复项。")
    for company in companies:
        if not isinstance(company, str) or not company.strip():
            _fail("公司标识无效。")
        if not frappe.db.exists("Company", company):
            _fail(f"公司不存在：{company}")
    if not role_keys:
        _fail("必须显式指定至少一个考勤角色。")
    if len(set(role_keys)) != len(role_keys):
        _fail("角色清单存在重复项。")
    unknown = [key for key in role_keys if key not in TARGET_ROLES]
    if unknown:
        _fail("未知角色：" + ", ".join(unknown) + "；只允许 staff / clerk / admin。")
    return companies, role_keys


def _existing_role(app_id: str, role_key: str):
    rows = frappe.db.sql(
        "select name from `tabHBOS IAM App Role` where app_id=%s and role_key=%s order by name limit 2 for update",
        (app_id, role_key),
        as_dict=True,
    )
    if len(rows) > 1:
        _fail(f"角色 {role_key} 存在重复定义，拒绝继续。")
    return policy.value(rows[0], "name") if rows else ""


def plan_initialize(companies, role_keys=TARGET_ROLES) -> dict:
    """Read-only plan: which role definitions are missing and would be created."""
    companies, role_keys = _validate_scope(companies, role_keys)
    plan = []
    for key in role_keys:
        existing = _existing_role("attendance", key)
        plan.append(
            {
                "role_key": key,
                "title": roles.BLUEPRINTS[key][0],
                "boundary_kind": roles.BLUEPRINTS[key][1],
                "companies": companies,
                "existing": existing,
                "action": "keep" if existing else "create",
            }
        )
    return {
        "site": frappe.local.site,
        "operation": "role.initialize",
        "dry_run": True,
        "companies": companies,
        "roles": plan,
        "changed": any(row["action"] == "create" for row in plan),
        "publishes": False,
        "assigns": False,
        "grants_native_roles": False,
    }


def initialize(companies, role_keys=TARGET_ROLES, *, actor: str, reason: str, dry_run: bool = True) -> dict:
    """Create missing attendance role definitions. Never publishes or assigns."""
    actor, reason = _validate_actor(actor, reason)
    companies, role_keys = _validate_scope(companies, role_keys)
    if dry_run:
        plan = plan_initialize(companies, role_keys)
        plan.update(actor=actor, reason=reason, dry_run=True)
        return plan

    created, kept = [], []
    with serialize("iam-work", "site"):
        with guards.controlled_write():
            for key in role_keys:
                existing = _existing_role("attendance", key)
                if existing:
                    kept.append({"role_key": key, "name": existing})
                    continue
                features = roles.normalize_features(
                    [
                        {"operation_id": row["operation_id"], "scope_binding": row["scope_binding"]}
                        for row in roles.registry(key)
                        if row["allowed"]
                    ],
                    key,
                )
                role = frappe.get_doc(
                    {
                        "doctype": roles.ROLE,
                        "app_id": "attendance",
                        "role_key": key,
                        "title": roles.BLUEPRINTS[key][0],
                        "boundary_kind": roles.BLUEPRINTS[key][1],
                        "enabled": 1,
                        "draft_version": 1,
                        "draft_features": features,
                        "management_scopes": [
                            {"scope_type": "COMPANY", "scope_ref": company, "include_descendants": 0}
                            for company in sorted(set(companies))
                        ],
                    }
                ).insert(ignore_permissions=True)
                payload = {
                    "operation": "role.initialize",
                    "site": frappe.local.site,
                    "role_key": key,
                    "companies": sorted(set(companies)),
                    "operator": actor,
                }
                audit.append_event(
                    f"cli-init-{key}-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}-{frappe.generate_hash(length=6)}",
                    "role.initialize",
                    roles.ROLE,
                    role.name,
                    payload,
                    before={},
                    after={
                        "role_key": key,
                        "name": role.name,
                        "draft_version": role.draft_version,
                        "published_release": role.published_release or "",
                        "companies": sorted(set(companies)),
                        "operator": actor,
                        "site": frappe.local.site,
                    },
                    version=role.draft_version,
                    reason=f"{actor}: {reason}",
                )
                created.append({"role_key": key, "name": role.name})
            # One transaction: all missing roles are created or none is.
            frappe.db.commit()

    result = {
        "site": frappe.local.site,
        "operation": "role.initialize",
        "dry_run": False,
        "actor": actor,
        "companies": companies,
        "created": created,
        "kept": kept,
        "changed": bool(created),
        "publishes": False,
        "assigns": False,
        "grants_native_roles": False,
    }
    # Idempotent repeat: every requested role already exists.
    return result


def _management_rules(company: str) -> list[dict]:
    app_id = "iam"
    rules = [{"app_id": app_id, "operation_id": "app.enter", "effect": "allow", "scope_type": "COMPANY", "scope_ref": company, "include_descendants": 0, "valid_from": None, "valid_until": None, "qualification_ref": None}]
    for operation in policy.MANAGEMENT:
        rules.append(
            {
                "app_id": app_id,
                "operation_id": operation,
                "effect": "allow",
                "scope_type": "COMPANY",
                "scope_ref": company,
                "include_descendants": 0,
                "valid_from": None,
                "valid_until": None,
                "qualification_ref": None,
            }
        )
    return rules


def _rule_key(row) -> tuple:
    return (
        policy.value(row, "app_id"),
        policy.value(row, "operation_id"),
        policy.value(row, "effect"),
        policy.value(row, "scope_type"),
        policy.value(row, "scope_ref") or "",
    )


def plan_delegate_admin(user: str, company: str) -> dict:
    """Read-only plan for the first, named, audited management delegation."""
    if not isinstance(user, str) or not user or user == "Administrator":
        _fail("必须指定一个非 Administrator 的具名合成管理账号。")
    if not frappe.db.exists("User", user) or not frappe.db.get_value("User", user, "enabled"):
        _fail("指定账号不存在或已停用。")
    if not company or not frappe.db.exists("Company", company):
        _fail("必须指定一个已存在的公司范围。")
    native = {row.role for row in frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, fields=["role"])}
    forbidden = native & {"System Manager", "Administrator"}
    if forbidden:
        _fail("该账号已持有 " + ", ".join(sorted(forbidden)) + "，不能作为受限管理账号；请改用普通合成账号。")
    existing = policy.get_policy("User", user)
    if existing is not None and not policy.value(existing, "enabled"):
        _fail("该账号已有停用策略，拒绝隐式启用。")
    before = [_rule_key(row) for row in (existing.rules if existing else [])]
    desired = _management_rules(company)
    missing = [row for row in desired if (row["app_id"], row["operation_id"], row["effect"], row["scope_type"], row["scope_ref"]) not in before]
    return {
        "site": frappe.local.site,
        "operation": "iam.delegate",
        "dry_run": True,
        "user": user,
        "company": company,
        "existing_policy": policy.value(existing, "name") if existing else "",
        "existing_rules": len(before),
        "missing_rules": missing,
        "changed": bool(missing),
    }


def delegate_admin(user: str, company: str, *, actor: str, reason: str, dry_run: bool = True) -> dict:
    """Grant an explicit, company-scoped IAM management policy to one named user.

    This is the only bootstrap delegation path in this round. It does not grant
    attendance business data, does not grant native roles, and does not touch
    feature flags. The CLI operator and reason are audited.
    """
    actor, reason = _validate_actor(actor, reason)
    plan = plan_delegate_admin(user, company)
    if dry_run:
        plan.update(actor=actor, reason=reason, dry_run=True)
        return plan
    if not plan["changed"]:
        plan.update(dry_run=False, changed=False, actor=actor)
        return plan

    with serialize("iam-work", "site"):
        with guards.controlled_write():
            existing = policy.get_policy("User", user, for_update=True)
            before = [_rule_key(row) for row in (existing.rules if existing else [])]
            if existing:
                doc = existing
                doc.version = int(doc.version or 0) + 1
            else:
                doc = frappe.get_doc({"doctype": policy.POLICY, "subject_type": "User", "subject_name": user, "version": 1, "enabled": 1, "rules": []})
            missing = [row for row in _management_rules(company) if (row["app_id"], row["operation_id"], row["effect"], row["scope_type"], row["scope_ref"]) not in before]
            for row in missing:
                doc.append("rules", row)
            doc.save(ignore_permissions=True)
            audit.append_event(
                f"cli-delegate-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}-{frappe.generate_hash(length=6)}",
                "iam.delegate",
                "User",
                user,
                {"site": frappe.local.site, "company": company, "operator": actor, "added": len(missing)},
                before={"rules": len(before)},
                after={"policy": doc.name, "version": doc.version, "rules": len(doc.rules), "company": company, "operator": actor, "site": frappe.local.site},
                version=doc.version,
                reason=f"{actor}: {reason}",
            )
            frappe.db.commit()
    plan.update(dry_run=False, changed=True, version=doc.version, added=len(missing), actor=actor)
    return plan


def _grantors() -> list[str]:
    # Shared parser with the runtime authorization check in iam.app_roles.
    return _site_grantors()


@contextmanager
def _site_config_lock():
    """Serialize read-modify-write of site_config.json across CLI runs.

    Two concurrent operators would otherwise each read the old file and the
    second ``os.replace`` would silently drop the first grantor change.
    """
    path = frappe.get_site_path("site_config.json")
    with open(path + ".lock", "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield path
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _write_site_config(values: dict, path: str | None = None) -> None:
    path = path or frappe.get_site_path("site_config.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(values, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.chmod(tmp, os.stat(path).st_mode & 0o777)
    os.replace(tmp, path)


def plan_native_role_grantor(user: str, *, revoke: bool = False) -> dict:
    if not isinstance(user, str) or not user or user == "Administrator":
        _fail("必须指定一个非 Administrator 的具名站点级授权账号。")
    if not frappe.db.exists("User", user) or not frappe.db.get_value("User", user, "enabled"):
        _fail("指定账号不存在或已停用。")
    current = _grantors()
    target = [item for item in current if item != user] if revoke else sorted(set(current) | {user})
    return {
        "site": frappe.local.site,
        "operation": "native_role.grantor",
        "dry_run": True,
        "user": user,
        "revoke": bool(revoke),
        "before": current,
        "after": target,
        "changed": target != current,
    }


def set_native_role_grantor(user: str, *, actor: str, reason: str, revoke: bool = False, dry_run: bool = True) -> dict:
    """Add/remove a named site-level grantor for GLOBAL native roles.

    Site-level grantor status is deliberately separate from iam.access.manage:
    a department/company manager must never gain authority over GLOBAL native
    roles merely because they can manage an employee.
    """
    actor, reason = _validate_actor(actor, reason)
    plan = plan_native_role_grantor(user, revoke=revoke)
    if dry_run or not plan["changed"]:
        plan.update(dry_run=True if dry_run else False, actor=actor)
        return plan
    with _site_config_lock() as path:
        with open(path, encoding="utf-8") as handle:
            config = json.load(handle)
        # Re-read under the lock so a concurrent writer cannot be overwritten.
        current = _grantors()
        target = [item for item in current if item != user] if revoke else sorted(set(current) | {user})
        if target == current:
            plan.update(dry_run=False, actor=actor, changed=False, after=current)
            return plan
        before_file = dict(config)
        plan["before"], plan["after"] = current, target
        config[GRANTORS_KEY] = target
        try:
            # The audit row is inserted before the file is replaced, so an
            # active grantor can never exist without a matching record; a file
            # failure rolls the row back with the transaction.
            audit.append_event(
                f"cli-grantor-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}-{frappe.generate_hash(length=6)}",
                "native_role.grantor",
                "User",
                user,
                {"site": frappe.local.site, "operator": actor, "revoke": bool(revoke), "after": target},
                before={"grantors": current},
                after={"grantors": target, "operator": actor, "site": frappe.local.site, "revoke": bool(revoke)},
                version=1,
                reason=f"{actor}: {reason}",
            )
            _write_site_config(config, path)
            frappe.db.commit()
        except Exception:
            _write_site_config(before_file, path)
            frappe.db.rollback()
            raise
    frappe.conf[GRANTORS_KEY] = plan["after"]
    plan.update(dry_run=False, actor=actor, changed=True)
    return plan
