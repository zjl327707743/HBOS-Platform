from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely, normalize_limit
from hbos_portal.services.dispatcher import dispatch_provider


@frappe.whitelist()
def get_tasks(
    app_id: str,
    limit: int | str | None = 20,
    cursor: str | None = None,
) -> dict[str, object]:
    def _load() -> dict[str, object]:
        return dispatch_provider(
            app_id,
            "tasks",
            limit=normalize_limit(limit),
            cursor=cursor or None,
        )

    return call_safely(_load)
