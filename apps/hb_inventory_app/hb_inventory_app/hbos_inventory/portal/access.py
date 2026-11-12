from __future__ import annotations

from collections.abc import Sequence

APP_ID = "inventory"
READ_CAPABILITY = "inventory.read"
INVENTORY_PORTAL_ROLES = frozenset({
    "Stock User",
    "Stock Manager",
    "System Manager",
})


def build_access_context(
    user: str | None,
    roles: Sequence[str] | None,
) -> dict[str, object]:
    normalized_user = str(user or "").strip()
    role_set = {str(role) for role in (roles or ())}

    can_enter = bool(
        normalized_user
        and normalized_user != "Guest"
        and (
            normalized_user == "Administrator"
            or bool(role_set.intersection(INVENTORY_PORTAL_ROLES))
        )
    )

    return {
        "app_id": APP_ID,
        "can_enter": can_enter,
        "capabilities": [READ_CAPABILITY] if can_enter else [],
        "scopes": {},
    }
