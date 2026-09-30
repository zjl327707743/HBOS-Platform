"""Owned temporary users for real HTTP session checks on designated test Sites."""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

import frappe


def _path() -> Path:
    return Path(frappe.get_site_path("private", "hbos-http-synthetic.json"))


def prepare() -> dict:
    if not frappe.conf.get("hbos_account_test_site") or _path().exists():
        raise RuntimeError("Requires designated test Site and no outstanding owned fixture")
    original = frappe.in_test
    frappe.in_test = True
    try:
        user = "account-http-" + secrets.token_hex(6) + "@example.test"
        password = secrets.token_urlsafe(40)
        frappe.get_doc({"doctype": "User", "email": user, "first_name": "HTTP合成验证", "user_type": "Website User", "enabled": 1, "send_welcome_email": 0}).insert(ignore_permissions=True)
        from frappe.utils.password import update_password
        update_password(user, password)
        frappe.db.commit()
        fd = os.open(_path(), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump({"user": user, "password": password}, handle)
        return {"created": True, "scope": "synthetic_test_site_only"}
    finally:
        frappe.in_test = original


def change_enabled(enabled: int = 0) -> dict:
    if not frappe.conf.get("hbos_account_test_site"):
        raise RuntimeError("Not a test Site")
    fixture = json.loads(_path().read_text())
    doc = frappe.get_doc("User", fixture["user"])
    if doc.first_name != "HTTP合成验证" or not doc.name.endswith("@example.test"):
        raise RuntimeError("Unexpected fixture")
    doc.enabled = int(enabled)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"enabled": doc.enabled}


def cleanup() -> dict:
    if not frappe.conf.get("hbos_account_test_site") or not _path().exists():
        raise RuntimeError("Not an owned test fixture")
    fixture = json.loads(_path().read_text())
    doc = frappe.get_doc("User", fixture["user"])
    if doc.first_name != "HTTP合成验证" or not doc.name.endswith("@example.test"):
        raise RuntimeError("Unexpected fixture")
    frappe.in_test = True
    frappe.delete_doc("User", doc.name, force=True, ignore_permissions=True)
    frappe.db.commit()
    _path().unlink()
    return {"removed": True}
