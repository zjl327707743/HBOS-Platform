from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _cursor(value: str | None) -> int:
    if value in (None, ""):
        return 0
    try:
        offset = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("LIMS COA cursor must be a non-negative integer") from exc
    if offset < 0:
        raise ValueError("LIMS COA cursor must be a non-negative integer")
    return offset


def _value(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(key, default)
    return getattr(row, key, default)


def _as_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    as_dict = getattr(row, "as_dict", None)
    if callable(as_dict):
        return dict(as_dict())
    return {key: getattr(row, key) for key in dir(row) if not key.startswith("_")}


def _project_item(row: Any) -> dict[str, object]:
    item = _as_dict(row)
    return {
        "test_item": str(item.get("test_item") or ""),
        "item_name": str(item.get("item_name") or item.get("test_item") or ""),
        "method_sop": str(item.get("method_sop") or ""),
        "standard": str(item.get("standard") or ""),
        "result": str(item.get("result") or ""),
        "verdict": str(item.get("verdict") or ""),
        "remark": str(item.get("remark") or ""),
    }


def _project_coa(row: Any, *, include_items: bool = False) -> dict[str, object]:
    item = _as_dict(row)
    projected: dict[str, object] = {
        "coa_id": str(item.get("name") or ""),
        "sample": str(item.get("sample") or ""),
        "batch_no": str(item.get("batch_no") or ""),
        "material_code": str(item.get("material_code") or ""),
        "material_name": str(item.get("material_name") or ""),
        "spec_version": str(item.get("spec_version") or ""),
        "report_status": str(item.get("report_status") or ""),
        "qa_reviewer": str(item.get("qa_reviewer") or ""),
        "qa_reviewed_at": item.get("qa_reviewed_at"),
        "published_by": str(item.get("published_by") or ""),
        "published_at": item.get("published_at"),
        "pdf_attachment": str(item.get("pdf_attachment") or ""),
        "remarks": str(item.get("remarks") or ""),
        "items": [],
    }
    if include_items:
        projected["items"] = [_project_item(child) for child in (item.get("items") or [])]
    return projected


COA_FIELDS = [
    "name", "sample", "batch_no", "material_code", "material_name", "spec_version",
    "report_status", "qa_reviewer", "qa_reviewed_at", "published_by", "published_at",
    "pdf_attachment", "remarks", "creation", "modified",
]


def get_coa_projection(
    *,
    coa_id: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
) -> dict[str, object]:
    """Expose permission-filtered COA records as a read-only Portal DTO."""
    import frappe

    page_size = max(1, min(int(limit or 50), 50))
    filters: dict[str, object] = {"name": coa_id} if coa_id else {}
    if status and not coa_id:
        filters["report_status"] = status
    query: dict[str, object] = {
        "fields": COA_FIELDS,
        "filters": filters,
        "order_by": "creation desc",
        "limit_page_length": 1 if coa_id else page_size + 1,
    }
    if keyword and not coa_id:
        query["or_filters"] = [
            [field, "like", f"%{keyword}%"]
            for field in ("name", "sample", "batch_no", "material_name", "spec_version")
        ]
    rows = frappe.get_list(
        "HBOS COA",
        **query,
    )
    projected = [_project_coa(row) for row in rows if _value(row, "name")]

    if coa_id:
        selected = next((row for row in projected if row["coa_id"] == coa_id), None)
        if selected is None:
            return {"coas": [], "total": 0, "next_cursor": None, "detail": None}
        detail = _project_coa(frappe.get_doc("HBOS COA", coa_id), include_items=True)
        return {"coas": [detail], "total": 1, "next_cursor": None, "detail": detail}

    needle = str(keyword or "").strip().lower()
    filtered = [
        row for row in projected
        if (not status or row["report_status"] == str(status))
        and (
            not needle
            or needle in " ".join(
                str(row.get(field) or "")
                for field in ("coa_id", "sample", "batch_no", "material_name", "spec_version")
            ).lower()
        )
    ]
    offset = _cursor(cursor)
    page = filtered[offset:offset + page_size]
    next_offset = offset + len(page)
    return {
        "coas": page,
        "total": len(filtered),
        "next_cursor": str(next_offset) if next_offset < len(filtered) else None,
        "detail": None,
    }
