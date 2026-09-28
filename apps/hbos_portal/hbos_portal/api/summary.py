from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely
from hbos_portal.services.dispatcher import dispatch_provider


@frappe.whitelist()
def get_summary(app_id: str) -> dict[str, object]:
    return call_safely(
        lambda: dispatch_provider(app_id, "summary")
    )
