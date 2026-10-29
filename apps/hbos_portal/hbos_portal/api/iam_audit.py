from __future__ import annotations

import frappe

from hbos_portal.iam import audit


@frappe.whitelist()
def list_events(subject_type=None, subject_name=None, page=1, page_size=20):
    return {"ok": True, "data": audit.list_events(subject_type, subject_name, page, page_size), "error": None}
