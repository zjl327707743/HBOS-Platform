from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely, normalize_limit
from hbos_portal.services.dispatcher import dispatch_provider


@frappe.whitelist()
def get_retention(
    app_id: str,
    section: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    active: str | None = None,
    limit: int | str | None = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    def _load() -> dict[str, object]:
        return dispatch_provider(
            app_id,
            "retains",
            section=section or None,
            keyword=keyword or None,
            status=status or None,
            active=active or None,
            limit=normalize_limit(limit),
            cursor=cursor or None,
        )

    return call_safely(_load)
