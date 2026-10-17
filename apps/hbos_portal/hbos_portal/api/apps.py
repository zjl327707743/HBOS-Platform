from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely
from hbos_portal.services.access import require_app_access, require_authenticated_user
from hbos_portal.services.dispatcher import get_entry


@frappe.whitelist()
def get_app(app_id: str) -> dict[str, object]:
    def _load() -> dict[str, object]:
        require_authenticated_user()
        entry = get_entry(app_id)
        access = require_app_access(entry)
        return {
            "manifest": entry.manifest.to_dict(),
            "access": access.to_dict(),
        }

    return call_safely(_load)
