from __future__ import annotations

from typing import Any

from hb_lims_app.hbos_lims.portal.pagination import (
    iter_permission_rows,
    literal_keyword_query,
    page_cursor,
    permission_page_with_total,
    read_permission_page,
)


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


def _sample_rows(
    *, keyword: str | None, status: str | None, page_size: int, offset: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import frappe

    filters = {"status": status} if status else {}
    query: dict[str, Any] = {
        "fields": SAMPLE_FIELDS,
        "filters": filters,
        "order_by": "retention_date desc, modified desc, name desc",
    }
    needle = str(keyword or "").strip()
    if needle:
        # Product names participate in the same SQL OR as sample fields. The
        # lookup itself is permission-filtered and may span multiple pages.
        product_query = literal_keyword_query(
            "HBOS Retention Product", keyword=needle, search_fields=("product_name",),
            fields=["name"], filters={"product_name": ["like", f"%{needle}%"]}, order_by="name asc",
        )
        matching_products = {
            str(row["name"]) for row in iter_permission_rows("HBOS Retention Product", **product_query)
        }
        query["or_filters"] = [
            [field, "like", f"%{needle}%"]
            for field in ("name", "sample_name", "material_code", "batch_no", "storage_location")
        ]
        if matching_products:
            query["or_filters"].append(["retention_product", "in", sorted(matching_products)])
        query = literal_keyword_query(
            "HBOS Retention Sample", **query, keyword=needle,
            search_fields=("name", "sample_name", "material_code", "batch_no", "storage_location"),
            linked_matches={"retention_product": matching_products},
        )
    raw = read_permission_page("HBOS Retention Sample", **query, limit=page_size, offset=offset)
    facts = list(iter_permission_rows("HBOS Retention Sample", **{
        **query, "fields": ["name", "status", "observed_flag", "retention_due_date"],
    }))
    product_names = sorted({str(row["retention_product"]) for row in raw if row.get("retention_product")})
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
    rows: list[dict[str, Any]] = []
    for raw_row in raw:
        row = dict(raw_row)
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
        rows.append(projected)
    return rows, facts


def _product_rows(
    *, keyword: str | None, active: str | None, page_size: int, offset: int,
) -> tuple[list[dict[str, Any]], int, str | None]:
    filters = {}
    if active in {"启用", "停用"}:
        filters["is_active"] = 1 if active == "启用" else 0
    query: dict[str, Any] = {
        "fields": PRODUCT_FIELDS,
        "filters": filters,
        "order_by": "modified desc, name desc",
    }
    needle = str(keyword or "").strip()
    if needle:
        query["or_filters"] = [
            [field, "like", f"%{needle}%"]
            for field in ("name", "product_code", "product_name", "category", "obs_rule", "storage_condition")
        ]
        query = literal_keyword_query(
            "HBOS Retention Product", **query, keyword=needle,
            search_fields=("name", "product_code", "product_name", "category", "obs_rule", "storage_condition"),
        )
    raw, total, next_cursor = permission_page_with_total(
        "HBOS Retention Product", **query, limit=page_size, offset=offset,
    )
    rows: list[dict[str, Any]] = []
    for raw_row in raw:
        row = dict(raw_row)
        is_active = bool(row.get("is_active"))
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
        rows.append(projected)
    return rows, total, next_cursor


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
    offset = _cursor(cursor)
    sample_page, sample_facts = _sample_rows(keyword=keyword, status=status, page_size=page_size, offset=offset)
    product_page, product_total, product_cursor = _product_rows(
        keyword=keyword, active=active, page_size=page_size, offset=offset,
    )
    observations = retention_service.get_observation_plan()
    usage_status = status if section == "usage" else None
    disposal_status = status if section == "disposal" else None
    usages = retention_service.list_usage_applies(status=usage_status or None)
    disposals = retention_service.list_disposal_applies(status=disposal_status or None)

    sample_total = len(sample_facts)
    sample_cursor = page_cursor(offset=offset, count=len(sample_page), total=sample_total)
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
            1 for row in sample_facts
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
            "in_stock": sum(1 for row in sample_facts if row.get("status") in {"在库", "部分使用"}),
            "observed": sum(1 for row in sample_facts if row.get("observed_flag")),
            "near_due_30": near_due,
            "pending_usage": pending_usage,
            "pending_disposal": pending_disposal,
            "due_observation": due_observation,
        },
        "section": section or "workbench",
    }
