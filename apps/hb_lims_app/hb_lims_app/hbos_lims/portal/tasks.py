from __future__ import annotations

from typing import Any

from hb_lims_app.hbos_lims.portal.routes import build_stable_deep_link

_PRIORITY_MAP = {
    "加急": "critical",
    "紧急": "critical",
    "高": "high",
    "高优先级": "high",
    "中": "normal",
    "普通": "normal",
    "常规": "normal",
    "低": "low",
}


def normalize_priority(value: object) -> str:
    return _PRIORITY_MAP.get(str(value or "").strip(), "normal")


def normalize_cursor(cursor: str | None) -> int:
    if cursor in (None, ""):
        return 0
    try:
        value = int(str(cursor))
    except (TypeError, ValueError) as exc:
        raise ValueError("LIMS task cursor must be a non-negative integer") from exc
    if value < 0:
        raise ValueError("LIMS task cursor must be a non-negative integer")
    return value


def project_todo(item: dict[str, Any]) -> dict[str, object]:
    todo_key = str(item.get("todo_key") or "").strip()
    if not todo_key:
        raise ValueError("LIMS todo projection requires todo_key")

    route = str(item.get("route") or "").strip()
    if not route:
        raise ValueError("LIMS todo projection requires route")

    owner_type = str(item.get("owner_type") or "")
    assignment_type = "direct" if owner_type == "user" else "role_pool"

    return {
        "task_id": f"lims:{todo_key}",
        "app_id": "lims",
        "category": str(item.get("module") or "testing"),
        "title": str(item.get("title") or item.get("action_label") or "LIMS 待办"),
        "description": str(item.get("description") or ""),
        "action": str(item.get("action") or ""),
        "action_label": str(item.get("action_label") or ""),
        "priority": normalize_priority(item.get("priority")),
        "due_at": item.get("due_at"),
        "overdue": bool(item.get("is_overdue")),
        "assignment_type": assignment_type,
        "deep_link": build_stable_deep_link(
            route,
            dict(item.get("route_params") or {}),
        ),
        "modified_at": item.get("modified_at"),
    }


def get_task_projection(
    *,
    limit: int = 20,
    cursor: str | None = None,
) -> dict[str, object]:
    from hb_lims_app.hbos_lims.todo_service import get_my_todos

    offset = normalize_cursor(cursor)
    response = get_my_todos(limit=limit, offset=offset)
    raw_items = list(response.get("items") or [])
    tasks = [project_todo(dict(item)) for item in raw_items]
    total = int(response.get("total") or 0)
    next_offset = offset + len(raw_items)

    return {
        "tasks": tasks,
        "next_cursor": str(next_offset) if next_offset < total else None,
        "total": total,
    }
