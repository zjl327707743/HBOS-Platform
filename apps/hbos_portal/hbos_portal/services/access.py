from __future__ import annotations

from hbos_portal.contracts.access import AccessContext
from hbos_portal.contracts.errors import PortalException
from hbos_portal.services.registry import RegistryEntry


# Provider capability names are public routing keys.  LIMS exposes narrower
# semantic access capabilities for the protected projections so a copied URL
# cannot reach a domain service that the current role cannot use.
SEMANTIC_ACCESS_REQUIREMENTS = {
    ("lims", "results"): "lims.results.read",
    ("lims", "ledger"): "lims.ledger.read",
    ("lims", "retains"): "lims.retention.read",
}


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


def require_provider_capability(entry: RegistryEntry, capability: str) -> AccessContext:
    access = require_app_access(entry)
    required = SEMANTIC_ACCESS_REQUIREMENTS.get((entry.manifest.id, capability))
    if required and required not in access.capabilities:
        raise PortalException(
            "FORBIDDEN",
            "你没有权限访问这个 LIMS 数据模块。",
        )
    return access
