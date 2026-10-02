from __future__ import annotations

from collections.abc import Mapping
from typing import Any

INVENTORY_LINK = "/hbos/inventory"


def _number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def project_inventory_summary(
    visible_warehouses: list[str],
    bins: list[Mapping[str, Any]],
) -> dict[str, object]:
    """Project permission-scoped ERPNext Bin facts into Portal semantics.

    Quantities are never added across items because their stock UOMs may differ.
    The projection therefore exposes counts only.
    """

    stocked_items: set[str] = set()
    negative_bins = 0
    projected_shortage_bins = 0

    for row in bins:
        item_code = str(row.get("item_code") or "").strip()
        actual_qty = _number(row.get("actual_qty"))
        projected_qty = _number(row.get("projected_qty"))

        if item_code and actual_qty != 0:
            stocked_items.add(item_code)
        if actual_qty < 0:
            negative_bins += 1
        if projected_qty < 0:
            projected_shortage_bins += 1

    needs_attention = negative_bins > 0 or projected_shortage_bins > 0

    return {
        "app_id": "inventory",
        "generated_at": "",
        "status": "attention" if needs_attention else "normal",
        "metrics": [
            {
                "id": "inventory_visible_warehouses",
                "label": "可见货位",
                "value": len(visible_warehouses),
                "tone": "info" if visible_warehouses else "neutral",
                "deep_link": INVENTORY_LINK,
            },
            {
                "id": "inventory_stocked_items",
                "label": "有库存物料",
                "value": len(stocked_items),
                "tone": "info" if stocked_items else "neutral",
                "deep_link": INVENTORY_LINK,
            },
            {
                "id": "inventory_negative_bins",
                "label": "负库存项",
                "value": negative_bins,
                "tone": "critical" if negative_bins else "success",
                "deep_link": INVENTORY_LINK,
            },
            {
                "id": "inventory_projected_shortage_bins",
                "label": "预计短缺项",
                "value": projected_shortage_bins,
                "tone": "warning" if projected_shortage_bins else "success",
                "deep_link": INVENTORY_LINK,
            },
        ],
    }


def _load_permission_aware_inventory() -> tuple[list[str], list[dict[str, object]]]:
    import frappe

    # frappe.get_list applies role and User Permission filters for the session
    # user. We first obtain that user's visible leaf warehouses, then explicitly
    # constrain Bin to the same set so no broader inventory scope can leak into
    # Portal through an aggregate.
    warehouses = [
        str(name)
        for name in frappe.get_list(
            "Warehouse",
            filters={"is_group": 0, "disabled": 0},
            pluck="name",
            order_by="name",
            limit_page_length=0,
        )
        if name
    ]

    if not warehouses:
        return [], []

    rows = frappe.get_list(
        "Bin",
        filters={"warehouse": ["in", warehouses]},
        fields=["warehouse", "item_code", "actual_qty", "projected_qty"],
        limit_page_length=0,
    )

    return warehouses, [dict(row) for row in rows]


def get_summary_projection() -> dict[str, object]:
    warehouses, bins = _load_permission_aware_inventory()
    return project_inventory_summary(warehouses, bins)
