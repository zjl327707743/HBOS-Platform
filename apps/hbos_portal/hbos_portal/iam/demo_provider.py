"""Explicitly synthetic registration probe; no identity injection HTTP adapter."""
from __future__ import annotations

import frappe

from hbos_portal.iam import policy


def require_isolated_site():
    if frappe.local.site != "iam-r4-b.localhost" or not policy.enabled_flag("hbos_iam_test_site"):
        frappe.throw("Synthetic validation is restricted to the named isolated Site.", frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def get_demo_object(scope_ref="synthetic-equipment", operation_id="iam_demo.read", **kwargs):
    require_isolated_site()
    if not policy.enabled_flag("hbos_iam_demo_enabled"):
        frappe.throw("The synthetic module is disabled.", frappe.PermissionError)
    if set(kwargs) - {"cmd"} or set(frappe.local.form_dict or {}) - {"cmd", "scope_ref", "operation_id"}:
        frappe.throw("Unsupported synthetic request fields.", frappe.PermissionError)
    user = policy.get_current_user()
    definition = policy.registration("iam_demo", operation_id)
    obj = next((item for item in (definition or {}).get("objects", []) if item["scope_ref"] == scope_ref), None)
    if not obj or not definition.get("ordinary") or not policy.allows(user, "iam_demo", operation_id, obj["scope_type"], scope_ref):
        frappe.throw("The current account has no access to this synthetic object.", frappe.PermissionError)
    return {"synthetic": True, "id": obj["scope_ref"], "operation_id": operation_id, "label": obj["label"]}
