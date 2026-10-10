from __future__ import annotations

import frappe

from hbos_portal.auth.accounts import digest, validate_auth_paths


def active_user_key(provider: str, tenant: str, app: str, user: str) -> str:
    return digest("\x1f".join((provider, tenant, app, user)))


def migrate_identity_constraints() -> None:
    validate_auth_paths()
    if not frappe.db.exists('Role', 'HBOS Account Handover Manager'):
        frappe.get_doc({'doctype': 'Role', 'role_name': 'HBOS Account Handover Manager', 'desk_access': 1}).insert(ignore_permissions=True)
    rows = frappe.get_all("HBOS External Identity", fields=["name", "provider", "tenant_key", "app_id", "user", "enabled"], limit_page_length=0)
    seen = set()
    for row in rows:
        key = active_user_key(row.provider, row.tenant_key, row.app_id, row.user) if row.enabled else None
        if key and key in seen:
            frappe.throw("同一用户存在多条有效飞书绑定；请先执行冲突 dry-run 核对，禁止自动合并。")
        seen.add(key)
        frappe.db.set_value("HBOS External Identity", row.name, "active_user_key", key, update_modified=False)
    # Frappe's standard credential resolver supports these aliases only when
    # the native setting is enabled. Existing passwords and roles are untouched.
    frappe.db.set_single_value("System Settings", "allow_login_using_user_name", 1)
    ensure_portal_assets()


def ensure_portal_assets() -> None:
    for app in ("hbos_portal", "hb_attendance_app", "hb_inventory_app", "hb_lims_app", "hb_knowledge_app", "hb_twin_app"):
        if app in frappe.get_installed_apps():
            _ensure_app_assets(app)


def _ensure_app_assets(app: str) -> None:
    from pathlib import Path

    source = Path(frappe.get_app_path(app, "public"))
    if not source.is_dir():
        return
    assets = Path(frappe.local.sites_path).resolve() / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    link = assets / app
    if link.is_symlink():
        if link.resolve() != source.resolve():
            frappe.throw("Portal 资产指向未知目录，未覆盖；请检查正式挂载配置。")
    elif link.exists():
        frappe.throw("Portal 资产为未知非链接目录，未覆盖；请先备份核对。")
    else:
        link.symlink_to(source, target_is_directory=True)


def guard_social_login(doc, method=None) -> None:
    if doc.enable_social_login and any(word in " ".join(str(doc.get(k) or "") for k in ["name", "provider_name", "authorize_url"]).lower() for word in ["feishu", "larksuite"]):
        frappe.throw("请使用 HBOS 飞书入口；不能启用按邮箱自动接管的历史 Social Login Key。")
