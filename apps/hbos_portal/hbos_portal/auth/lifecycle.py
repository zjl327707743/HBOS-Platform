"""Explicitly enabled member suspension, with no destructive network fallback."""
from __future__ import annotations

from urllib.parse import quote

import frappe


def member_suspended(member: dict, open_id: str) -> bool:
    # A missing member/permission/department is not proof of offboarding.
    # Only explicit, authenticated status flags can suspend a local User.
    return member.get("open_id") == open_id and any(
        member.get("status", {}).get(key) is True
        for key in ("is_frozen", "is_resigned", "is_unjoin", "is_exited")
    )


def sync_disabled_members() -> dict:
    from hbos_portal.auth.accounts import audit
    from hbos_portal.auth.feishu import load_settings, _tenant_token, _unwrap_feishu_payload, CONTACT_USER_URL
    import requests

    if not frappe.conf.get("hbos_feishu_disable_sync_enabled"):
        return {"status": "DISABLED", "checked": 0, "suspended": 0, "failed": 0}
    settings = load_settings()
    if not settings.configured:
        return {"status": "CONFIG_REQUIRED", "checked": 0, "suspended": 0, "failed": 1}
    summary = {"status": "COMPLETE", "checked": 0, "suspended": 0, "failed": 0}
    try:
        token = _tenant_token(settings)
    except Exception:
        # No provider payload, credential or identity is written to logs.
        audit("member_sync_unavailable", "Administrator", status="Failed")
        return {"status": "UNAVAILABLE", "checked": 0, "suspended": 0, "failed": 1}
    rows = frappe.get_all("HBOS External Identity", filters={"provider": "feishu", "tenant_key": settings.tenant_key, "app_id": settings.app_id, "enabled": 1}, fields=["user", "external_id"])
    for row in rows:
        if row.user in {"Guest", "Administrator"}:
            continue  # The native emergency administrator is never suspended.
        summary["checked"] += 1
        try:
            payload = _unwrap_feishu_payload(requests.get(CONTACT_USER_URL + quote(row.external_id, safe=""), params={"user_id_type": "open_id"}, headers={"Authorization": f"Bearer {token}"}, timeout=10))
            if member_suspended(payload.get("user") or {}, row.external_id):
                doc = frappe.get_doc("User", row.user)
                if doc.enabled:
                    doc.enabled = 0
                    doc.save(ignore_permissions=True)
                    audit("feishu_member_suspended", row.user)
                    summary["suspended"] += 1
        except Exception:
            summary["failed"] += 1
            audit("member_sync_check_failed", row.user, status="Failed")
    if summary["failed"]:
        summary["status"] = "PARTIAL_FAILURE"
    return summary
