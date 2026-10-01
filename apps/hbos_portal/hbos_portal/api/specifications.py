from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely, normalize_limit
from hbos_portal.services.dispatcher import dispatch_provider


@frappe.whitelist()
def get_specifications(
    app_id: str,
    specification_id: str | None = None,
    limit: int | str | None = 50,
    cursor: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
) -> dict[str, object]:
    def _load() -> dict[str, object]:
        return dispatch_provider(
            app_id,
            "specifications",
            specification_id=specification_id or None,
            limit=normalize_limit(limit),
            cursor=cursor or None,
            keyword=keyword or None,
            status=status or None,
        )

    return call_safely(_load)
