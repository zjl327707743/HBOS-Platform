from __future__ import annotations


def _cursor(value: str | None) -> int:
    if value in (None, ""):
        return 0
    try:
        offset = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("LIMS audit cursor must be a non-negative integer") from exc
    if offset < 0:
        raise ValueError("LIMS audit cursor must be a non-negative integer")
    return offset


def get_audit_projection(
    *,
    log_type: str | None = None,
    doctype_target: str | None = None,
    user: str | None = None,
    keyword: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, object]:
    """Expose the existing reviewer/quality guarded audit stream read-only."""
    from hb_lims_app.hbos_lims import lims_service

    offset = _cursor(cursor)
    page_size = max(1, min(int(limit or 50), 100))
    payload = lims_service.get_audit_log(
        log_type=log_type or None,
        doctype_target=doctype_target or None,
        user=user or None,
        keyword=keyword or None,
        from_date=from_date or None,
        to_date=to_date or None,
        limit=page_size,
        offset=offset,
    )
    events = [dict(event) for event in payload.get("events") or []]
    total = int(payload.get("total") or 0)
    next_offset = offset + len(events)
    return {
        "events": events,
        "total": total,
        "next_cursor": str(next_offset) if next_offset < total else None,
        "targets": list(lims_service.get_audit_targets() or []),
    }
