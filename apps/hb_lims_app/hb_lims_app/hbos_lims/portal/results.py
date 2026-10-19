from __future__ import annotations

from typing import Any

def _cursor(value: str | None) -> int:
    if value in (None, ""):
        return 0
    try:
        offset = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("LIMS result cursor must be a non-negative integer") from exc
    if offset < 0:
        raise ValueError("LIMS result cursor must be a non-negative integer")
    return offset


def _result_row(row: dict[str, Any], samples: dict[str, dict[str, Any]]) -> dict[str, object]:
    sample_name = str(row.get("sample") or "")
    sample = samples.get(sample_name, {})
    return {
        "result_name": str(row.get("name") or ""),
        "sample": sample_name,
        "batch_no": str(sample.get("batch_no") or ""),
        "material_name": str(sample.get("material_name") or ""),
        "item_name": str(row.get("item_name") or "检验项目"),
        "result_value": row.get("result_value"),
        "result_text": str(row.get("result_text") or ""),
        "raw_value": str(row.get("raw_value") or ""),
        "unit": str(row.get("unit") or ""),
        "verdict": str(row.get("verdict") or ""),
        "result_status": str(row.get("result_status") or ""),
        "limits_type": str(row.get("limits_type") or ""),
        "limits_text": str(row.get("limits_text") or ""),
        "lower_limit": row.get("lower_limit"),
        "upper_limit": row.get("upper_limit"),
        "significant_digits": row.get("significant_digits"),
        "analyst": str(row.get("analyst") or ""),
        "submitted_at": row.get("submitted_at"),
        "reviewer": str(row.get("reviewer") or ""),
        "reviewed_at": row.get("reviewed_at"),
        "approver": str(row.get("approver") or ""),
        "approved_at": row.get("approved_at"),
        "superseded_by": str(row.get("superseded_by") or ""),
        "display": str(row.get("display") or ""),
    }


def _matches(row: dict[str, object], keyword: str | None, status: str | None, verdict: str | None) -> bool:
    if status and str(row.get("result_status") or "") != str(status):
        return False
    if verdict and str(row.get("verdict") or "") != str(verdict):
        return False
    needle = str(keyword or "").strip().lower()
    if not needle:
        return True
    searchable = " ".join(
        str(row.get(field) or "")
        for field in ("result_name", "sample", "batch_no", "material_name", "item_name", "analyst", "reviewer")
    ).lower()
    return needle in searchable


def get_result_projection(
    *,
    result_id: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    verdict: str | None = None,
) -> dict[str, object]:
    """Expose the existing permission-guarded result ledger as a Portal DTO.

    The projection is read-only. Result writes stay in ``lims_service`` so its
    workflow, SoD, signature and audit checks remain the only write authority.
    """
    from hb_lims_app.hbos_lims import lims_service

    payload = lims_service.get_result_ledger()
    sample_rows = {str(row.get("name")): dict(row) for row in payload.get("samples") or []}
    rows: list[dict[str, object]] = []
    for raw_row in payload.get("results") or []:
        row = _result_row(dict(raw_row), sample_rows)
        if row.get("result_name"):
            rows.append(row)

    if result_id:
        selected = next((row for row in rows if row["result_name"] == result_id), None)
        if not selected:
            return {"results": [], "total": 0, "next_cursor": None, "detail": None}
        revisions = [
            dict(revision)
            for revision in payload.get("revisions") or []
            if str(revision.get("result") or "") == result_id
        ]
        sample = sample_rows.get(str(selected.get("sample") or ""), {})
        return {
            "results": [selected],
            "total": 1,
            "next_cursor": None,
            "detail": {
                "result": selected,
                "sample": sample,
                "revisions": revisions,
                "signature_chain": {
                    "analyst": selected.get("analyst"),
                    "submitted_at": selected.get("submitted_at"),
                    "reviewer": selected.get("reviewer"),
                    "reviewed_at": selected.get("reviewed_at"),
                    "approver": selected.get("approver"),
                    "approved_at": selected.get("approved_at"),
                },
            },
        }

    filtered = [row for row in rows if _matches(row, keyword, status, verdict)]
    offset = _cursor(cursor)
    page_size = max(1, min(int(limit or 50), 100))
    page = filtered[offset:offset + page_size]
    next_offset = offset + len(page)
    return {
        "results": page,
        "total": len(filtered),
        "next_cursor": str(next_offset) if next_offset < len(filtered) else None,
        "detail": None,
    }
