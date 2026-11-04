from __future__ import annotations

from collections.abc import Iterator
from typing import Any


LIST_BATCH_SIZE = 50


def read_permission_page(
    doctype: str, *, limit: int, offset: int, **query: Any,
) -> list[dict[str, Any]]:
    """Apply the page boundary in get_list, retaining native row permissions."""
    import frappe

    return list(frappe.get_list(
        doctype,
        **query,
        limit_start=offset,
        limit_page_length=max(1, min(int(limit), LIST_BATCH_SIZE)),
    ))


def iter_permission_rows(doctype: str, **query: Any) -> Iterator[dict[str, Any]]:
    """Traverse authorized rows in bounded pages, including full totals/KPIs.

    Callers provide a stable order ending in the unique name field. Counts
    deliberately use the same get_list permission path as displayed records.
    """
    offset = 0
    while True:
        rows = read_permission_page(doctype, limit=LIST_BATCH_SIZE, offset=offset, **query)
        yield from rows
        if len(rows) < LIST_BATCH_SIZE:
            return
        offset += len(rows)


def literal_keyword_query(
    doctype: str, *, keyword: str, search_fields: tuple[str, ...],
    linked_matches: dict[str, set[str]] | None = None, **query: Any,
) -> dict[str, Any]:
    """Keep the former literal substring meaning for SQL wildcard characters.

    Frappe escapes backslashes in LIKE values, so a manual backslash escape
    is not a portable literal-match contract. Only these special keywords
    need a bounded authorized candidate scan before database pagination.
    """
    if "%" not in keyword and "_" not in keyword:
        return query
    linked_matches = linked_matches or {}
    fields = list(dict.fromkeys(("name", *search_fields, *linked_matches)))
    needle = keyword.lower()
    names = [
        row["name"] for row in iter_permission_rows(doctype, **{**query, "fields": fields})
        if needle in " ".join(str(row.get(field) or "") for field in search_fields).lower()
        or any(row.get(field) in matches for field, matches in linked_matches.items())
    ]
    return {**query, "filters": {**query.get("filters", {}), "name": ["in", names]}}


def page_cursor(*, offset: int, count: int, total: int) -> str | None:
    next_offset = offset + count
    return str(next_offset) if count and next_offset < total else None


def permission_page_with_total(
    doctype: str, *, limit: int, offset: int, **query: Any,
) -> tuple[list[dict[str, Any]], int, str | None]:
    rows = read_permission_page(doctype, limit=limit, offset=offset, **query)
    total = sum(1 for _ in iter_permission_rows(doctype, **{**query, "fields": ["name"]}))
    return rows, total, page_cursor(offset=offset, count=len(rows), total=total)
