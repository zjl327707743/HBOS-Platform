"""Read-only target and preservation manifest with no User names or hashes."""
from __future__ import annotations

import hashlib
import json

import frappe


def fingerprint(rows) -> str:
    canonical = json.dumps(sorted((list(row) for row in rows), key=lambda row: str(row)), default=str, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def inspect() -> dict:
    users = frappe.db.sql("SELECT name,enabled,user_type,username FROM `tabUser` ORDER BY name")
    credentials = frappe.db.sql("SELECT name,fieldname,password,encrypted FROM `__Auth` WHERE doctype='User' ORDER BY name,fieldname")
    roles = frappe.db.sql("SELECT parent,role FROM `tabHas Role` WHERE parenttype='User' ORDER BY parent,role")
    permissions = frappe.db.sql("SELECT user,allow,for_value,apply_to_all_doctypes,applicable_for FROM `tabUser Permission` ORDER BY user,allow,for_value")
    associations = []
    identity_installed = bool(frappe.db.exists("DocType", "HBOS External Identity"))
    identities = frappe.db.sql("SELECT provider,tenant_key,app_id,id_type,external_id,user,enabled FROM `tabHBOS External Identity`") if identity_installed else []
    for table, field in [("Employee", "user_id"), ("Employee Checkin", "employee"), ("Attendance", "employee")]:
        if frappe.db.exists("DocType", table):
            associations.extend((table, *row) for row in frappe.db.sql(f"SELECT name,`{field}` FROM `tab{table}` ORDER BY name"))
    return {"site": frappe.local.site, "database_fingerprint": hashlib.sha256(str(frappe.conf.db_name).encode()).hexdigest(),
        "installed_apps": frappe.get_installed_apps(), "user_count": len(users),
        "user_fingerprint": fingerprint(users), "credential_fingerprint": fingerprint(credentials),
        "role_fingerprint": fingerprint(roles), "permission_fingerprint": fingerprint(permissions),
        "business_association_fingerprint": fingerprint(associations),
        "identity_fingerprint": fingerprint(identities), "identity_table_present": identity_installed,
        "business_counts": {doctype: frappe.db.count(doctype) for doctype in ["Employee", "Employee Checkin", "Attendance"] if frappe.db.exists("DocType", doctype)},
        "encryption_key_present": bool(frappe.conf.get("encryption_key")),
        "legacy_feishu_social_keys": len([row for row in frappe.get_all("Social Login Key", filters={"enable_social_login": 1}, fields=["name", "provider_name", "authorize_url"]) if any(s in str(row).lower() for s in ["feishu", "larksuite"])]),
        "csrf_enabled": not bool(frappe.conf.get("ignore_csrf"))}
