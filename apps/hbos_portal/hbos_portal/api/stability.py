from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely, normalize_limit
from hbos_portal.services.dispatcher import dispatch_provider


@frappe.whitelist()
def get_stability(
    app_id: str,
    section: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    month: str | None = None,
    condition: str | None = None,
    exec_status: str | None = None,
    stability_product: str | None = None,
    stability_test_item: str | None = None,
    condition_type: str | None = None,
    limit: int | str | None = 50,
    offset: int | str | None = 0,
) -> dict[str, object]:
    def _load() -> dict[str, object]:
        return dispatch_provider(
            app_id,
            "stability",
            section=section or None,
            keyword=keyword or None,
            status=status or None,
            month=month or None,
            condition=condition or None,
            exec_status=exec_status or None,
            stability_product=stability_product or None,
            stability_test_item=stability_test_item or None,
            condition_type=condition_type or None,
            limit=normalize_limit(limit),
            offset=max(0, int(offset or 0)),
        )

    return call_safely(_load)
