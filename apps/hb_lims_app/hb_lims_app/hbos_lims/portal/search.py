from __future__ import annotations

from typing import Any
from urllib.parse import quote


def project_result_row(row: dict[str, Any]) -> dict[str, object]:
    name = str(row.get("name") or "").strip()
    if not name:
        raise ValueError("LIMS search result requires a result name")

    item_name = str(row.get("item_name") or "检验结果").strip()
    sample = str(row.get("sample") or "").strip()
    verdict = str(row.get("verdict") or "").strip()
    status = str(row.get("result_status") or "").strip()

    subtitle_parts = [part for part in (sample, verdict) if part]

    return {
        "app_id": "lims",
        "entity_type": "test_result",
        "entity_id": name,
        "title": f"{item_name} · {name}",
        "subtitle": " · ".join(subtitle_parts),
        "status": status,
        "deep_link": f"/hbos/lims/results/{quote(name, safe='')}",
    }


def _permission_error_types(frappe_module: object) -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = [PermissionError]
    for owner in (frappe_module, getattr(frappe_module, "exceptions", None)):
        error_type = getattr(owner, "PermissionError", None)
        if isinstance(error_type, type) and error_type not in types:
            types.append(error_type)
    return tuple(types)


def search_results(*, query: str, limit: int = 20) -> dict[str, object]:
    import frappe

    q = str(query or "").strip()
    if not q:
        return {"results": []}

    normalized_limit = min(max(int(limit or 20), 1), 50)
    like = f"%{q}%"

    try:
        rows = frappe.get_list(
            "HBOS Test Result",
            fields=[
                "name",
                "sample",
                "item_name",
                "verdict",
                "result_status",
                "modified",
            ],
            or_filters=[
                ["name", "like", like],
                ["sample", "like", like],
                ["item_name", "like", like],
            ],
            order_by="modified desc",
            limit_page_length=normalized_limit,
        )
    except Exception as exc:
        if isinstance(exc, _permission_error_types(frappe)):
            return {"results": []}
        raise

    return {
        "results": [project_result_row(dict(row)) for row in rows],
    }
