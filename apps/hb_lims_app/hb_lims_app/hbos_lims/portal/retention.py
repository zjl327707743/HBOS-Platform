from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SAMPLE_FIELDS = [
    "name", "retention_product", "sample_name", "material_code", "batch_no",
    "category", "status", "source", "retention_date", "expiry_date",
    "retention_due_date", "retention_qty", "qty_uom", "package_count",
    "package_spec", "current_qty", "reserved_qty", "observed_flag", "obs_year",
    "obs_selected_reason", "next_obs_month", "next_obs_due_date",
    "storage_condition", "storage_location", "retained_by", "remarks",
    "modified",
]

PRODUCT_FIELDS = [
    "name", "product_code", "product_name", "category", "is_active",
    "retention_qty_rule", "full_test_qty", "full_test_qty_uom", "default_uom",
    "is_liquid", "is_outsource", "storage_condition", "obs_rule", "modified",
]


def _cursor(value: str | None) -> int:
    if value in (None, ""):
        return 0
    try:
        offset = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("LIMS retention cursor must be a non-negative integer") from exc
    if offset < 0:
        raise ValueError("LIMS retention cursor must be a non-negative integer")
    return offset


def _text(row: Mapping[str, Any], *fields: str) -> str:
    return " ".join(str(row.get(field) or "") for field in fields).lower()


def _page(rows: list[dict[str, Any]], *, limit: int, cursor: str | None) -> tuple[list[dict[str, Any]], int, str | None]:
    offset = _cursor(cursor)
    page_size = max(1, min(int(limit or 50), 50))
    page = rows[offset:offset + page_size]
    next_offset = offset + len(page)
    return page, len(rows), str(next_offset) if next_offset < len(rows) else None


def _sample_rows(*, keyword: str | None, status: str | None, page_size: int) -> list[dict[str, Any]]:
    import frappe

    filters = {"status": status} if status else {}
    query: dict[str, Any] = {
        "fields": SAMPLE_FIELDS,
        "filters": filters,
        "order_by": "retention_date desc, modified desc",
        "limit_page_length": page_size + 1,
    }
    if keyword:
        query["or_filters"] = [
            [field, "like", f"%{keyword}%"]
            for field in ("name", "sample_name", "material_code", "batch_no", "storage_location")
        ]
    raw = frappe.get_list("HBOS Retention Sample", **query)
    product_names = [str(row.get("retention_product") or "") for row in raw if row.get("retention_product")]
    products: dict[str, Any] = {}
    if product_names:
        product_query: dict[str, Any] = {
            "fields": ["name", "product_code", "product_name", "category", "default_uom", "obs_rule", "storage_condition"],
            "filters": {"name": ["in", product_names]},
            "limit_page_length": len(product_names),
        }
        products = {
            str(row.get("name")): row
            for row in frappe.get_list("HBOS Retention Product", **product_query)
        }
    needle = str(keyword or "").strip().lower()
    rows: list[dict[str, Any]] = []
    for raw_row in raw:
        row = dict(raw_row)
        if status and str(row.get("status") or "") != status:
            continue
        product = products.get(str(row.get("retention_product") or ""), {})
        projected = {
            "name": str(row.get("name") or ""),
            "retention_product": str(row.get("retention_product") or ""),
            "product_code": str(product.get("product_code") or ""),
            "product_name": str(product.get("product_name") or ""),
            "sample_name": str(row.get("sample_name") or ""),
            "material_code": str(row.get("material_code") or ""),
            "batch_no": str(row.get("batch_no") or ""),
            "category": str(row.get("category") or product.get("category") or ""),
            "status": str(row.get("status") or ""),
            "source": str(row.get("source") or ""),
            "retention_date": row.get("retention_date"),
            "expiry_date": row.get("expiry_date"),
            "retention_due_date": row.get("retention_due_date"),
            "retention_qty": row.get("retention_qty") or 0,
            "qty_uom": str(row.get("qty_uom") or product.get("default_uom") or ""),
            "package_count": row.get("package_count") or 0,
            "package_spec": str(row.get("package_spec") or ""),
            "current_qty": row.get("current_qty") or 0,
            "reserved_qty": row.get("reserved_qty") or 0,
            "available_qty": (row.get("current_qty") or 0) - (row.get("reserved_qty") or 0),
            "observed_flag": row.get("observed_flag") or 0,
            "obs_year": row.get("obs_year"),
            "obs_selected_reason": str(row.get("obs_selected_reason") or ""),
            "next_obs_month": row.get("next_obs_month"),
            "next_obs_due_date": row.get("next_obs_due_date"),
            "obs_rule": str(product.get("obs_rule") or ""),
            "storage_condition": str(row.get("storage_condition") or product.get("storage_condition") or ""),
            "storage_location": str(row.get("storage_location") or ""),
            "retained_by": str(row.get("retained_by") or ""),
            "remarks": str(row.get("remarks") or ""),
        }
        if needle and needle not in _text(projected, "name", "product_name", "sample_name", "batch_no", "material_code", "storage_location"):
            continue
        rows.append(projected)
    return rows


def _product_rows(*, keyword: str | None, active: str | None, page_size: int) -> list[dict[str, Any]]:
    import frappe

    filters = {}
    if active in {"启用", "停用"}:
        filters["is_active"] = 1 if active == "启用" else 0
    query: dict[str, Any] = {
        "fields": PRODUCT_FIELDS,
        "filters": filters,
        "order_by": "modified desc",
        "limit_page_length": page_size + 1,
    }
    if keyword:
        query["or_filters"] = [
            [field, "like", f"%{keyword}%"]
            for field in ("name", "product_code", "product_name", "category", "obs_rule", "storage_condition")
        ]
    raw = frappe.get_list("HBOS Retention Product", **query)
    needle = str(keyword or "").strip().lower()
    rows: list[dict[str, Any]] = []
    for raw_row in raw:
        row = dict(raw_row)
        is_active = bool(row.get("is_active"))
        if active in {"启用", "停用"} and (is_active != (active == "启用")):
            continue
        projected = {
            "name": str(row.get("name") or ""),
            "product_code": str(row.get("product_code") or ""),
            "product_name": str(row.get("product_name") or ""),
            "category": str(row.get("category") or ""),
            "is_active": 1 if is_active else 0,
            "retention_qty_rule": str(row.get("retention_qty_rule") or ""),
            "full_test_qty": row.get("full_test_qty"),
            "full_test_qty_uom": str(row.get("full_test_qty_uom") or ""),
            "default_uom": str(row.get("default_uom") or ""),
            "is_liquid": 1 if row.get("is_liquid") else 0,
            "is_outsource": 1 if row.get("is_outsource") else 0,
            "storage_condition": str(row.get("storage_condition") or ""),
            "obs_rule": str(row.get("obs_rule") or ""),
        }
        if needle and needle not in _text(projected, "name", "product_code", "product_name", "category", "obs_rule", "storage_condition"):
            continue
        rows.append(projected)
    return rows


def get_retention_projection(
    *,
    section: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    active: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    """Project permission-aware retention data for the Portal workbench.

    The retention service remains the authority for observation, usage and
    disposal visibility. This adapter only joins read fields and never writes
    workflow state or exposes Frappe Desk routes.
    """
    from hb_lims_app.hbos_lims import retention_service

    page_size = max(1, min(int(limit or 50), 50))
    samples = _sample_rows(keyword=keyword, status=status, page_size=page_size)
    products = _product_rows(keyword=keyword, active=active, page_size=page_size)
    observations = retention_service.get_observation_plan()
    usage_status = status if section == "usage" else None
    disposal_status = status if section == "disposal" else None
    usages = retention_service.list_usage_applies(status=usage_status or None)
    disposals = retention_service.list_disposal_applies(status=disposal_status or None)

    sample_page, sample_total, sample_cursor = _page(samples, limit=limit, cursor=cursor)
    product_page, product_total, product_cursor = _page(products, limit=limit, cursor=cursor)
    observation_rows = list(observations.get("rows") or [])
    usage_rows = list(usages.get("rows") or [])
    disposal_rows = list(disposals.get("rows") or [])
    pending_usage = sum(1 for row in usage_rows if str(row.get("status") or "") not in {"已执行", "已驳回", "已取消"})
    pending_disposal = sum(1 for row in disposal_rows if str(row.get("status") or "") not in {"已完成", "已驳回", "已取消"})
    due_observation = sum(1 for row in observation_rows if str(row.get("due") or "") in {"应观察", "已逾期", "待审核"})
    near_due = 0
    try:
        import frappe
        today = frappe.utils.getdate(frappe.utils.today())
        import datetime
        horizon = today + datetime.timedelta(days=30)
        near_due = sum(
            1 for row in samples
            if row.get("retention_due_date") and today <= frappe.utils.getdate(row["retention_due_date"]) <= horizon
        )
    except Exception:
        near_due = 0

    return {
        "samples": sample_page,
        "samples_total": sample_total,
        "samples_next_cursor": sample_cursor,
        "products": product_page,
        "products_total": product_total,
        "products_next_cursor": product_cursor,
        "observations": observation_rows,
        "observation_completeness": observations.get("completeness") or [],
        "usage": {"rows": usage_rows, "total": usages.get("total", len(usage_rows))},
        "disposal": {"rows": disposal_rows, "total": disposals.get("total", len(disposal_rows))},
        "summary": {
            "sample_total": sample_total,
            "in_stock": sum(1 for row in samples if row.get("status") in {"在库", "部分使用"}),
            "observed": sum(1 for row in samples if row.get("observed_flag")),
            "near_due_30": near_due,
            "pending_usage": pending_usage,
            "pending_disposal": pending_disposal,
            "due_observation": due_observation,
        },
        "section": section or "workbench",
    }
