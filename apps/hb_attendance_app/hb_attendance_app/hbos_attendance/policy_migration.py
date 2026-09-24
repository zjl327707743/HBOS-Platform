"""Private migration helpers for attendance policy assignments.

This module contains no production identities. A seed JSON is exported from the
legacy deployment before upgrade and imported locally after the clean candidate is
installed. The seed file must never be committed.
"""

import json
from pathlib import Path

import frappe

from hb_attendance_app.hbos_attendance.policy_registry import POLICY_TYPES, clear_policy_cache


def import_policy_seed(path):
    """Import a private JSON policy seed from a local administrator-controlled path.

    Intended for bench execute only; this function is deliberately not whitelisted.
    Rows are idempotently upserted by employee + policy_type + effective_from.
    """
    seed_path = Path(path).expanduser().resolve()
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    rows = payload.get("assignments") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("policy seed must be a list or assignments object")

    summary = {"total": len(rows), "created": 0, "updated": 0, "unmatched": 0, "invalid": 0}
    for row in rows:
        if not isinstance(row, dict):
            summary["invalid"] += 1
            continue
        employee_number = str(row.get("employee_number") or "").strip()
        policy_type = str(row.get("policy_type") or "").strip()
        if not employee_number or policy_type not in POLICY_TYPES:
            summary["invalid"] += 1
            continue

        employee = frappe.db.get_value(
            "Employee", {"employee_number": employee_number}, "name"
        )
        if not employee:
            summary["unmatched"] += 1
            continue

        effective_from = row.get("effective_from") or None
        key = {
            "employee": employee,
            "policy_type": policy_type,
            "effective_from": effective_from,
        }
        existing = frappe.db.get_value(
            "HBOS Attendance Policy Assignment", key, "name"
        )
        doc = (
            frappe.get_doc("HBOS Attendance Policy Assignment", existing)
            if existing
            else frappe.new_doc("HBOS Attendance Policy Assignment")
        )
        doc.employee = employee
        doc.policy_type = policy_type
        doc.enabled = 1 if row.get("enabled", 1) else 0
        doc.effective_from = effective_from
        doc.effective_to = row.get("effective_to") or None
        doc.group_name = row.get("group_name") or ""
        doc.anchor_shift = row.get("anchor_shift") or ""
        doc.source_type = "MIGRATED"
        doc.remarks = row.get("remarks") or ""
        doc.save(ignore_permissions=True)
        summary["updated" if existing else "created"] += 1

    clear_policy_cache()
    frappe.db.commit()
    return summary
