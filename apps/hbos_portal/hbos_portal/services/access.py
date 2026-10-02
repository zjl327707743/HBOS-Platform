from __future__ import annotations

from hbos_portal.contracts.access import AccessContext
from hbos_portal.contracts.errors import PortalException
from hbos_portal.services.registry import RegistryEntry


def require_authenticated_user() -> str:
    import frappe

    user = frappe.session.user
    if not user or user == "Guest":
        raise PortalException(
            "UNAUTHENTICATED",
            "请先登录 HBOS。",
        )
    return user


def evaluate_access(entry: RegistryEntry) -> AccessContext:
    value = entry.provider.access_context()
    return AccessContext.from_mapping(
        value,
        expected_app_id=entry.manifest.id,
    )


def require_app_access(entry: RegistryEntry) -> AccessContext:
    access = evaluate_access(entry)
    if not access.can_enter:
        raise PortalException(
            "FORBIDDEN",
            "你没有权限进入这个应用。",
        )
    return access
