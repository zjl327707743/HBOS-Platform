from __future__ import annotations

import json
from pathlib import Path

import frappe

from hbos_portal.auth.accounts import require_user, no_store
from hbos_portal.services.registry import build_registry
from hbos_portal.services.access import evaluate_access
from hbos_portal.services.diagnostic_context import diagnostic_user_context


@frappe.whitelist(methods=["GET"])
def get_diagnostics(user: str | None = None) -> dict:
    no_store()
    administrator = require_user()
    if administrator != "Administrator" and "System Manager" not in frappe.get_roles(administrator):
        frappe.throw("应用诊断仅管理员可查看。", frappe.PermissionError)
    subject = user or administrator
    require_user(subject)
    rows = []
    with diagnostic_user_context(subject):
        registry = build_registry()
        for entry in registry.ordered_entries():
            try:
                access = evaluate_access(entry)
                rows.append({"app_id": entry.manifest.id, "title": entry.manifest.title,
                    "provider": "registered", "route": entry.manifest.route,
                    "visible": access.can_enter, "capabilities": list(access.capabilities),
                    "reason": "available" if access.can_enter else "permission_denied"})
            except Exception:
                rows.append({"app_id": entry.manifest.id, "provider": "access_failed", "visible": False, "reason": "provider_failed"})
        failures = [{"code": failure.code} for failure in registry.failures]
    path = Path(frappe.get_app_path("hbos_portal", "public", "portal", "build-info.json"))
    build = json.loads(path.read_text()) if path.is_file() else {"status": "production_bundle_missing"}
    return {"subject": subject, "apps": rows, "installed_apps": frappe.get_installed_apps(), "failures": failures, "build": build}
