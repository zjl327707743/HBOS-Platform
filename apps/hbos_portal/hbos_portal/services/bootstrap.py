from __future__ import annotations

from hbos_portal.portal.constants import CONTRACT_VERSION
from hbos_portal.services.access import evaluate_access, require_authenticated_user
from hbos_portal.services.branding import get_branding, get_user_identity
from hbos_portal.services.registry import build_registry


def build_bootstrap() -> dict[str, object]:
    import frappe

    user = require_authenticated_user()
    registry = build_registry()

    apps: list[dict[str, object]] = []
    for entry in registry.ordered_entries():
        try:
            access = evaluate_access(entry)
        except Exception:
            # Provider access failure is isolated from the rest of bootstrap.
            frappe.log_error(
                title=f"HBOS Portal access provider failed: {entry.manifest.id}",
                message=frappe.get_traceback(),
            )
            continue

        if not access.can_enter:
            continue

        apps.append(
            {
                "manifest": entry.manifest.to_dict(),
                "access": {
                    "can_enter": True,
                },
            }
        )

    return {
        "contract_version": CONTRACT_VERSION,
        "generated_at": frappe.utils.now_datetime().isoformat(),
        "user": get_user_identity(user),
        "branding": get_branding(),
        "apps": apps,
        "preferences": {
            "reduce_motion": None,
            "density": "comfortable",
        },
    }
