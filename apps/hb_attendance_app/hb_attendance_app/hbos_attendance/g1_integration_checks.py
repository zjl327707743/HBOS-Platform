"""Destructive G1 integration checks for an isolated CI site only.

This module is deliberately not whitelisted.  It may only run when
HBOS_G1_INTEGRATION_CHECKS=1 is present in the process environment.
"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from unittest.mock import patch

import frappe

SMOKE_EMPLOYEE = "HBOS-G1-SMOKE-EMP"
SMOKE_EMPLOYEE_NUMBER = "G1-SMOKE-001"
ROLLBACK_ROW = "HBOS-ATT-G1-ROLLBACK"
OUTSIDE_ROW = "HBOS-ATT-G1-OUTSIDE"
IDEMPOTENT_ROW = "HBOS-ATT-G1-IDEMPOTENT"


def _guard():
    if os.environ.get("HBOS_G1_INTEGRATION_CHECKS") != "1":
        raise RuntimeError(
            "G1 integration checks are destructive and may run only with "
            "HBOS_G1_INTEGRATION_CHECKS=1 on an isolated site."
        )


def _delete_smoke_rows():
    frappe.db.sql(
        """DELETE FROM `tabAttendance`
           WHERE name IN (%s, %s, %s)""",
        (ROLLBACK_ROW, OUTSIDE_ROW, IDEMPOTENT_ROW),
    )
    if frappe.db.table_exists("HBOS Attendance Policy Assignment"):
        frappe.db.delete(
            "HBOS Attendance Policy Assignment",
            {"employee": SMOKE_EMPLOYEE},
        )
    frappe.db.sql("DELETE FROM `tabEmployee` WHERE name = %s", (SMOKE_EMPLOYEE,))


def _insert_smoke_employee():
    now = frappe.utils.now_datetime()
    frappe.db.sql(
        """INSERT INTO `tabEmployee`
           (name, employee_name, employee_number, status, owner, modified_by,
            creation, modified, docstatus)
           VALUES (%s,%s,%s,'Active','Administrator','Administrator',%s,%s,0)""",
        (
            SMOKE_EMPLOYEE,
            "HBOS G1 Smoke Employee",
            SMOKE_EMPLOYEE_NUMBER,
            now,
            now,
        ),
    )


def _insert_attendance(name, day, status="Present"):
    now = frappe.utils.now_datetime()
    frappe.db.sql(
        """INSERT INTO `tabAttendance`
           (name, employee, attendance_date, status, owner, modified_by,
            creation, modified, docstatus)
           VALUES (%s,%s,%s,%s,'Administrator','Administrator',%s,%s,0)""",
        (name, SMOKE_EMPLOYEE, day, status, now, now),
    )


def _exists(doctype, name):
    return bool(frappe.db.exists(doctype, name))


def _check_regeneration_rollback():
    from hb_attendance_app.hbos_attendance import api

    _insert_attendance(ROLLBACK_ROW, "2026-01-02")
    _insert_attendance(OUTSIDE_ROW, "2026-01-20")
    frappe.db.commit()

    def fail_after_delete(_start, _end):
        frappe.db.sql(
            "DELETE FROM `tabAttendance` WHERE name = %s",
            (ROLLBACK_ROW,),
        )
        raise RuntimeError("G1 injected regeneration failure")

    with patch.object(api, "_regenerate_attendance_impl", fail_after_delete):
        try:
            api.regenerate_attendance("2026-01-01", "2026-01-10")
        except RuntimeError as exc:
            if "G1 injected" not in str(exc):
                raise
        else:
            raise AssertionError("injected regeneration failure did not propagate")

    if not _exists("Attendance", ROLLBACK_ROW):
        raise AssertionError("target-range Attendance was not restored by rollback")
    if not _exists("Attendance", OUTSIDE_ROW):
        raise AssertionError("out-of-range Attendance changed during rollback test")


def _check_regeneration_idempotency():
    from hb_attendance_app.hbos_attendance import api

    def deterministic_impl(_start, _end):
        frappe.db.sql(
            "DELETE FROM `tabAttendance` WHERE name = %s",
            (IDEMPOTENT_ROW,),
        )
        _insert_attendance(IDEMPOTENT_ROW, "2026-02-02")
        return {"generated": 1}

    with patch.object(api, "_regenerate_attendance_impl", deterministic_impl):
        first = api.regenerate_attendance("2026-02-01", "2026-02-05")
        second = api.regenerate_attendance("2026-02-01", "2026-02-05")

    count = frappe.db.count("Attendance", {"name": IDEMPOTENT_ROW})
    if count != 1:
        raise AssertionError(f"idempotent regeneration left {count} rows")
    if first != second:
        raise AssertionError("same regeneration input returned different deterministic result")


def _check_policy_seed_idempotency():
    from hb_attendance_app.hbos_attendance.policy_migration import import_policy_seed

    payload = {
        "assignments": [
            {
                "employee_number": SMOKE_EMPLOYEE_NUMBER,
                "policy_type": "ADMIN",
                "enabled": 1,
                "effective_from": "2026-01-01",
                "effective_to": None,
                "remarks": "G1 isolated migration rehearsal",
            }
        ]
    }
    fd, seed_path = tempfile.mkstemp(prefix="hbos-g1-policy-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        first = import_policy_seed(seed_path)
        second = import_policy_seed(seed_path)
        count = frappe.db.count(
            "HBOS Attendance Policy Assignment",
            {
                "employee": SMOKE_EMPLOYEE,
                "policy_type": "ADMIN",
                "effective_from": "2026-01-01",
            },
        )
        if count != 1:
            raise AssertionError(f"policy seed import is not idempotent: {count} rows")
        if first.get("created") != 1:
            raise AssertionError(f"first policy import did not create exactly one row: {first}")
        if second.get("updated") != 1:
            raise AssertionError(f"second policy import did not update exactly one row: {second}")
    finally:
        with suppress(FileNotFoundError):
            os.unlink(seed_path)


def run():
    """Run the G1 DB transaction and private-seed rehearsal checks."""
    _guard()
    frappe.set_user("Administrator")
    _delete_smoke_rows()
    frappe.db.commit()
    try:
        _insert_smoke_employee()
        frappe.db.commit()
        _check_regeneration_rollback()
        _check_regeneration_idempotency()
        _check_policy_seed_idempotency()
        return {
            "ok": True,
            "rollback": "pass",
            "idempotency": "pass",
            "policy_seed": "pass",
        }
    finally:
        _delete_smoke_rows()
        frappe.db.commit()
