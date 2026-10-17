from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely
from hbos_portal.services.bootstrap import build_bootstrap


@frappe.whitelist()
def get_bootstrap() -> dict[str, object]:
    return call_safely(build_bootstrap)
