from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely
from hbos_portal.services.routes import resolve_stable_route


@frappe.whitelist()
def resolve_route(app_id: str, stable_path: str) -> dict[str, object]:
    return call_safely(
        lambda: resolve_stable_route(app_id, stable_path)
    )
