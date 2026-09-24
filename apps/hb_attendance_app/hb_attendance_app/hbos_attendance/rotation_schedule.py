"""HBOS three-day rotation schedule generator.

The algorithm is code; employee membership and phase anchors are business data in
HBOS Attendance Policy Assignment (policy_type=ROTATION_3DAY). No production
employee identities are stored in this module.
"""

from datetime import date, timedelta

from hb_attendance_app.hbos_attendance.policy_registry import get_rotation_assignments

ROTATION_CYCLE = ["早班", "晚班", "休息"]


def rotation_shift_for(anchor_shift, anchor_date, target_date):
    """Resolve target shift from an anchor shift/date using the 3-day cycle."""
    if isinstance(anchor_date, str):
        anchor_date = date.fromisoformat(anchor_date[:10])
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date[:10])
    days = (target_date - anchor_date).days
    base = ROTATION_CYCLE.index(anchor_shift)
    return ROTATION_CYCLE[(base + days) % len(ROTATION_CYCLE)]


def _versions_by_employee(rows):
    out = {}
    for row in rows or []:
        if not row.employee or not row.effective_from or row.anchor_shift not in ROTATION_CYCLE:
            continue
        out.setdefault(row.employee, []).append(row)
    for employee in out:
        out[employee].sort(key=lambda r: (str(r.effective_from), str(r.name)))
    return out


def _assignment_for_day(versions, target_date):
    chosen = None
    ds = target_date.isoformat()
    for row in versions:
        start = str(row.effective_from or "")[:10]
        end = str(row.effective_to or "")[:10]
        if start and start <= ds and (not end or ds <= end):
            chosen = row
    return chosen


def generate_rotation_schedule(end_date):
    """Generate ROTATION-owned schedules without overwriting human decisions.

    Rules:
    - assignment membership/phase comes from HBOS Attendance Policy Assignment;
    - only rows with source_type=ROTATION are replaced;
    - LEGACY / IMPORT / MANUAL / SWAP rows always win;
    - no commit here: the caller owns the transaction.
    """
    import frappe

    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date[:10])

    rows = get_rotation_assignments(end_date)
    by_employee = _versions_by_employee(rows)

    created = 0
    protected = 0
    for employee, versions in by_employee.items():
        start_date = min(
            date.fromisoformat(str(r.effective_from)[:10])
            for r in versions
            if r.effective_from
        )
        if start_date > end_date:
            continue

        frappe.db.delete(
            "HBOS Employee Schedule",
            {
                "employee": employee,
                "schedule_date": ["between", [start_date.isoformat(), end_date.isoformat()]],
                "source_type": "ROTATION",
            },
        )

        d = start_date
        while d <= end_date:
            assignment = _assignment_for_day(versions, d)
            if not assignment:
                d += timedelta(days=1)
                continue

            existing = frappe.db.get_value(
                "HBOS Employee Schedule",
                {"employee": employee, "schedule_date": d.isoformat()},
                ["name", "source_type"],
                as_dict=True,
            )
            if existing:
                protected += 1
                d += timedelta(days=1)
                continue

            anchor = date.fromisoformat(str(assignment.effective_from)[:10])
            shift = rotation_shift_for(assignment.anchor_shift, anchor, d)
            frappe.get_doc(
                {
                    "doctype": "HBOS Employee Schedule",
                    "employee": employee,
                    "schedule_date": d.isoformat(),
                    "shift_type": shift,
                    "leave_type": "",
                    "source_type": "ROTATION",
                    "source_ref": assignment.name,
                }
            ).insert(ignore_permissions=True)
            created += 1
            d += timedelta(days=1)

    return {
        "generated": created,
        "protected": protected,
        "until": end_date.isoformat(),
    }
