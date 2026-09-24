"""HBOS attendance policy compatibility names.

Production identities are no longer hard-coded in source. These set-like objects
resolve membership from HBOS Attendance Policy Assignment business data.
"""

from hb_attendance_app.hbos_attendance.policy_registry import (
    POLICY_ADMIN,
    POLICY_ANOMALY_HIDDEN,
    POLICY_EXEMPT,
    POLICY_FOOD,
    POLICY_LATE_EXEMPT,
    POLICY_SAFETY,
    PolicySet,
)

ADMIN_NUMS = PolicySet(POLICY_ADMIN)
FOOD_NUMS = PolicySet(POLICY_FOOD)
SAFETY_NUMS = PolicySet(POLICY_SAFETY)
EXEMPT_NUMS = PolicySet(POLICY_EXEMPT)
LATE_EXEMPT_NUMS = PolicySet(POLICY_LATE_EXEMPT)
ANOMALY_HIDDEN_NUMS = PolicySet(POLICY_ANOMALY_HIDDEN)
