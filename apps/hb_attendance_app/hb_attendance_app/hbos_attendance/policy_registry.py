"""Attendance policy membership registry.

Code owns policy *types*; Frappe business data owns which employees belong to them.
No real employee IDs/names are stored in this module.
"""

from collections.abc import Set
from datetime import date

POLICY_ADMIN = "ADMIN"
POLICY_FOOD = "FOOD"
POLICY_SAFETY = "SAFETY"
POLICY_EXEMPT = "EXEMPT"
POLICY_LATE_EXEMPT = "LATE_EXEMPT"
POLICY_ANOMALY_HIDDEN = "ANOMALY_HIDDEN"
POLICY_SPECIAL_SHIFT = "SPECIAL_SHIFT"
POLICY_FOUR_SHIFT = "FOUR_SHIFT"
POLICY_ROTATION_3DAY = "ROTATION_3DAY"

POLICY_TYPES = (
    POLICY_ADMIN,
    POLICY_FOOD,
    POLICY_SAFETY,
    POLICY_EXEMPT,
    POLICY_LATE_EXEMPT,
    POLICY_ANOMALY_HIDDEN,
    POLICY_SPECIAL_SHIFT,
    POLICY_FOUR_SHIFT,
    POLICY_ROTATION_3DAY,
)


def _day_string(day=None):
    if day is None:
        return date.today().isoformat()
    if hasattr(day, "isoformat"):
        return day.isoformat()
    return str(day)[:10]


def _frappe():
    try:
        import frappe
        return frappe
    except Exception:
        return None


def clear_policy_cache():
    frappe = _frappe()
    if frappe is None:
        return
    try:
        if hasattr(frappe.local, "hbos_attendance_policy_cache"):
            frappe.local.hbos_attendance_policy_cache = {}
    except Exception:
        pass


def get_policy_numbers(policy_type, day=None):
    """Return employee_number set for an enabled policy at a business date.

    The query is request-local cached. Offline/unit-test imports return an empty set
    rather than embedding production identities in source code.
    """
    if policy_type not in POLICY_TYPES:
        raise ValueError("unsupported attendance policy: %s" % policy_type)

    frappe = _frappe()
    if frappe is None:
        return set()

    ds = _day_string(day)
    key = (policy_type, ds)
    try:
        cache = getattr(frappe.local, "hbos_attendance_policy_cache", None)
        if cache is None:
            cache = {}
            frappe.local.hbos_attendance_policy_cache = cache
        if key in cache:
            return set(cache[key])
    except Exception:
        cache = None

    try:
        rows = frappe.db.sql(
            """
            SELECT emp.employee_number
            FROM \`tabHBOS Attendance Policy Assignment\` p
            JOIN \`tabEmployee\` emp ON emp.name = p.employee
            WHERE p.enabled = 1
              AND p.policy_type = %s
              AND (p.effective_from IS NULL OR p.effective_from = '' OR p.effective_from <= %s)
              AND (p.effective_to IS NULL OR p.effective_to = '' OR p.effective_to >= %s)
              AND emp.status = 'Active'
              AND IFNULL(emp.employee_number, '') != ''
            """,
            (policy_type, ds, ds),
            as_dict=True,
        )
        result = {str(r.employee_number) for r in rows if r.employee_number}
    except Exception:
        # During initial migrate the table may not exist yet. Do not fall back to
        # hard-coded production identities; an empty policy set is safer and visible.
        result = set()

    if cache is not None:
        cache[key] = frozenset(result)
    return result


def get_rotation_assignments(day=None):
    """Return active ROTATION_3DAY assignment rows for schedule generation."""
    frappe = _frappe()
    if frappe is None:
        return []
    ds = _day_string(day)
    return frappe.db.get_all(
        "HBOS Attendance Policy Assignment",
        filters={
            "enabled": 1,
            "policy_type": POLICY_ROTATION_3DAY,
            "effective_from": ["<=", ds],
        },
        fields=[
            "name", "employee", "employee_number", "group_name",
            "anchor_shift", "effective_from", "effective_to",
        ],
        order_by="employee, effective_from asc, creation asc",
    )


class PolicySet(Set):
    """Read-only set-like compatibility facade backed by Frappe policy data."""

    def __init__(self, policy_type):
        self.policy_type = policy_type

    def _members(self):
        return get_policy_numbers(self.policy_type)

    def __contains__(self, item):
        return str(item or "") in self._members()

    def __iter__(self):
        return iter(sorted(self._members()))

    def __len__(self):
        return len(self._members())

    def __repr__(self):
        return "PolicySet(%r)" % self.policy_type

    def __and__(self, other):
        return set(self) & set(other)

    def __or__(self, other):
        return set(self) | set(other)
