from __future__ import annotations

from collections.abc import Sequence

APP_ID = "attendance"
READ_CAPABILITY = "attendance.read"
ATTENDANCE_PORTAL_ROLES = frozenset({
    "HR User",
    "HR Manager",
    "System Manager",
})


def build_access_context(
    user: str | None,
    roles: Sequence[str] | None,
) -> dict[str, object]:
    """Translate current Attendance authority into Portal semantic access.

    P3-ATT-1 intentionally exposes only the existing HR/management surface.
    Ordinary employee access will be enabled only after a native personal
    attendance experience and its authorization contract are ready.
    """

    normalized_user = str(user or "").strip()
    role_set = {str(role) for role in (roles or ())}

    can_enter = bool(
        normalized_user
        and normalized_user != "Guest"
        and (
            normalized_user == "Administrator"
            or bool(role_set.intersection(ATTENDANCE_PORTAL_ROLES))
        )
    )

    return {
        "app_id": APP_ID,
        "can_enter": can_enter,
        "capabilities": [READ_CAPABILITY] if can_enter else [],
        "scopes": {},
    }
