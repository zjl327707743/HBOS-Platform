from __future__ import annotations

from typing import Any

from hb_lims_app.hbos_lims.portal.results import _result_row


def _cursor(value: str | None) -> int:
    if value in (None, ""):
        return 0
    try:
        offset = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("LIMS ledger cursor must be a non-negative integer") from exc
    if offset < 0:
        raise ValueError("LIMS ledger cursor must be a non-negative integer")
    return offset


def _sample_text(sample: dict[str, Any]) -> str:
    return " ".join(
        str(sample.get(field) or "")
        for field in ("name", "material_name", "material_code", "batch_no", "sample_type", "status")
    ).lower()


def _result_text(result: dict[str, object]) -> str:
    return " ".join(
        str(result.get(field) or "")
        for field in ("result_name", "sample", "batch_no", "material_name", "item_name", "analyst")
    ).lower()


def get_ledger_projection(
    *,
    sample_type: str | None = None,
    material: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    verdict: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    """Project the existing permission-guarded result ledger for Portal.

    The LIMS service remains the only authority for visibility and derived
    values. This adapter only filters and shapes read-only data for the SPA.
    """
    from hb_lims_app.hbos_lims import lims_service

    payload = lims_service.get_result_ledger(
        sample_type=sample_type or None,
        material=material or None,
    )
    raw_samples = [dict(row) for row in payload.get("samples") or []]
    sample_map = {str(row.get("name")): row for row in raw_samples}
    result_rows = [
        _result_row(dict(row), sample_map)
        for row in payload.get("results") or []
    ]
    needle = str(keyword or "").strip().lower()
    result_rows = [
        row for row in result_rows
        if (not status or str(row.get("result_status") or "") == str(status))
        and (not verdict or str(row.get("verdict") or "") == str(verdict))
        and (not needle or _result_text(row).find(needle) >= 0)
    ]
    result_by_sample: dict[str, list[dict[str, object]]] = {}
    for row in result_rows:
        result_by_sample.setdefault(str(row.get("sample") or ""), []).append(row)

    filtered_samples: list[dict[str, Any]] = []
    for sample in raw_samples:
        sample_name = str(sample.get("name") or "")
        sample_match = not needle or needle in _sample_text(sample)
        has_result = bool(result_by_sample.get(sample_name))
        if needle and not sample_match and not has_result:
            continue
        if (status or verdict) and not has_result:
            continue
        filtered_samples.append(sample)

    offset = _cursor(cursor)
    page_size = max(1, min(int(limit or 50), 100))
    page_samples = filtered_samples[offset:offset + page_size]
    page_names = {str(sample.get("name") or "") for sample in page_samples}
    page_results = [row for row in result_rows if str(row.get("sample") or "") in page_names]
    page_result_names = {str(row.get("result_name") or "") for row in page_results}
    revisions = [
        dict(revision)
        for revision in payload.get("revisions") or []
        if str(revision.get("result") or "") in page_result_names
    ]
    next_offset = offset + len(page_samples)

    return {
        "samples": page_samples,
        "results": page_results,
        "revisions": revisions,
        "coas": {
            str(sample.get("name")): payload.get("coas", {}).get(str(sample.get("name")), "")
            for sample in page_samples
        },
        "groups": payload.get("groups") or [],
        "total_samples": len(filtered_samples),
        "next_cursor": str(next_offset) if next_offset < len(filtered_samples) else None,
    }
