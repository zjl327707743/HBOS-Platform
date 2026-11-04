from __future__ import annotations

import frappe

from hbos_portal.iam import audit


@frappe.whitelist()
def list_events(subject_type=None, subject_name=None, page=1, page_size=20, date_from=None, date_to=None, operation=None, result=None):
    return {"ok": True, "data": audit.list_events(subject_type, subject_name, page, page_size, date_from, date_to, operation, result), "error": None}


@frappe.whitelist()
def get_event(name):
    return {"ok": True, "data": audit.get_event(name), "error": None}
