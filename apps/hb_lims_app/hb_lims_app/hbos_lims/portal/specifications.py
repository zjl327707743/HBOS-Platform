from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _cursor(value: str | None) -> int:
    if value in (None, ""):
        return 0
    try:
        offset = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("LIMS specification cursor must be a non-negative integer") from exc
    if offset < 0:
        raise ValueError("LIMS specification cursor must be a non-negative integer")
    return offset


def _as_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    as_dict = getattr(row, "as_dict", None)
    if callable(as_dict):
        return dict(as_dict())
    return {key: getattr(row, key) for key in dir(row) if not key.startswith("_")}


def _limits_text(item: dict[str, Any]) -> str:
    kind = str(item.get("limits_type") or "")
    lower = item.get("lower_limit")
    upper = item.get("upper_limit")
    if kind == "记录型":
        return "记录型"
    if kind == "上限" and upper is not None:
        return f"≤ {upper}"
    if kind == "下限" and lower is not None:
        return f"≥ {lower}"
    if lower is not None and upper is not None:
        return f"{lower} - {upper}"
    return "—"


def _project_item(row: Any) -> dict[str, object]:
    item = _as_dict(row)
    return {
        "item": str(item.get("item") or ""),
        "item_name": str(item.get("item_name") or item.get("item") or ""),
        "method_sop": str(item.get("method_sop") or ""),
        "limits_type": str(item.get("limits_type") or ""),
        "lower_limit": item.get("lower_limit"),
        "upper_limit": item.get("upper_limit"),
        "limits_text": _limits_text(item),
        "unit": str(item.get("unit") or ""),
        "significant_digits": item.get("significant_digits"),
        "remark": str(item.get("remark") or ""),
    }


def _project_spec(row: Any, *, include_items: bool = False) -> dict[str, object]:
    item = _as_dict(row)
    projected: dict[str, object] = {
        "specification_id": str(item.get("name") or ""),
        "spec_code": str(item.get("spec_code") or ""),
        "spec_name": str(item.get("spec_name") or ""),
        "material_code": str(item.get("material_code") or ""),
        "material_name": str(item.get("material_name") or ""),
        "version": str(item.get("version") or ""),
        "supersedes": str(item.get("supersedes") or ""),
        "effective_date": item.get("effective_date"),
        "status": str(item.get("status") or ""),
        "standard_source": str(item.get("standard_source") or ""),
        "storage_condition": str(item.get("storage_condition") or ""),
        "retain_sample_qty": str(item.get("retain_sample_qty") or ""),
        "remarks": str(item.get("remarks") or ""),
        "items": [],
    }
    if include_items:
        projected["items"] = [_project_item(child) for child in (item.get("items") or [])]
    return projected


SPECIFICATION_FIELDS = [
    "name", "spec_code", "spec_name", "material_code", "material_name", "version",
    "supersedes", "effective_date", "status", "standard_source", "storage_condition",
    "retain_sample_qty", "remarks", "creation", "modified",
]


def get_specification_projection(
    *,
    specification_id: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
) -> dict[str, object]:
    """Expose permission-filtered quality standards as a read-only DTO."""
    import frappe

    page_size = max(1, min(int(limit or 50), 50))
    filters: dict[str, object] = {"name": specification_id} if specification_id else {}
    if status and not specification_id:
        filters["status"] = status
    query: dict[str, object] = {
        "fields": SPECIFICATION_FIELDS,
        "filters": filters,
        "order_by": "creation desc",
        "limit_page_length": 1 if specification_id else page_size + 1,
    }
    if keyword and not specification_id:
        query["or_filters"] = [
            [field, "like", f"%{keyword}%"]
            for field in ("name", "spec_code", "spec_name", "material_code", "material_name", "version")
        ]
    rows = frappe.get_list(
        "HBOS Specification",
        **query,
    )
    projected = [_project_spec(row) for row in rows if _as_dict(row).get("name")]

    if specification_id:
        selected = next((row for row in projected if row["specification_id"] == specification_id), None)
        if selected is None:
            return {"specifications": [], "total": 0, "next_cursor": None, "detail": None}
        detail = _project_spec(
            frappe.get_doc("HBOS Specification", specification_id),
            include_items=True,
        )
        return {
            "specifications": [detail],
            "total": 1,
            "next_cursor": None,
            "detail": detail,
        }

    needle = str(keyword or "").strip().lower()
    filtered = [
        row for row in projected
        if (not status or row["status"] == str(status))
        and (
            not needle
            or needle in " ".join(
                str(row.get(field) or "")
                for field in ("specification_id", "spec_code", "spec_name", "material_code", "material_name", "version")
            ).lower()
        )
    ]
    offset = _cursor(cursor)
    page = filtered[offset:offset + page_size]
    next_offset = offset + len(page)
    return {
        "specifications": page,
        "total": len(filtered),
        "next_cursor": str(next_offset) if next_offset < len(filtered) else None,
        "detail": None,
    }
