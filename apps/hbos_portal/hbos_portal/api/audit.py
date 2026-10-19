from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely, normalize_limit
from hbos_portal.services.dispatcher import dispatch_provider


@frappe.whitelist()
def get_audit(
    app_id: str,
    log_type: str | None = None,
    doctype_target: str | None = None,
    user: str | None = None,
    keyword: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int | str | None = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    def _load() -> dict[str, object]:
        return dispatch_provider(
            app_id,
            "audit",
            log_type=log_type or None,
            doctype_target=doctype_target or None,
            user=user or None,
            keyword=keyword or None,
            from_date=from_date or None,
            to_date=to_date or None,
            limit=normalize_limit(limit),
            cursor=cursor or None,
        )

    return call_safely(_load)
