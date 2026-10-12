from __future__ import annotations

from typing import Any

from hb_lims_app.hbos_lims.portal.routes import build_stable_deep_link
from hb_lims_app.hbos_lims.todo_contract import PORTAL_TASK_VIEW_ACTIONS, business_roles_for_user
from hb_lims_app.hbos_lims.workflow_contract import action_allowed

_PRIORITY_MAP = {
    "加急": "critical",
    "紧急": "critical",
    "高": "high",
    "高优先级": "high",
    "中": "normal",
    "普通": "normal",
    "常规": "normal",
    "低": "low",
    "critical": "critical",
    "high": "high",
    "normal": "normal",
    "low": "low",
}

_PRIORITY_FILTER_MAP = {
    "critical": "加急",
    "high": "高",
    "normal": "常规",
    "low": "低",
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


def normalize_view(view: str | None) -> str | None:
    value = str(view or "").strip()
    if not value:
        return None
    if value not in PORTAL_TASK_VIEW_ACTIONS:
        raise ValueError("LIMS task view is not supported")
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
        "status": str(item.get("status") or ""),
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


def get_pending_coa_todos() -> list[dict[str, object]]:
    """Project permission-aware, SoD-safe COA publish tasks.

    COA publication is a quality credential action and is intentionally kept
    separate from the ordinary result approval task. The final write check
    remains in ``lims_service.publish_coa``.
    """
    import frappe

    user = str(getattr(getattr(frappe, "session", None), "user", "") or "")
    roles = tuple(frappe.get_roles(user) or ()) if user and user != "Guest" else ()
    business_roles = business_roles_for_user(user, roles)
    if not any(action_allowed("publish_coa", role) for role in business_roles):
        return []

    from hb_lims_app.hbos_lims.todo_service import _get_list, _row_value

    rows = _get_list(
        "HBOS COA",
        {"report_status": "已审核"},
        ["name", "sample", "material_name", "batch_no", "qa_reviewer", "modified"],
    )
    tasks: list[dict[str, object]] = []
    for row in rows:
        # Publisher must differ from the QA reviewer; hide self-reviewed COA
        # from the approval queue before the write endpoint enforces it again.
        if _row_value(row, "qa_reviewer") == user:
            continue
        coa_name = str(_row_value(row, "name") or "").strip()
        if not coa_name:
            continue
        sample = str(_row_value(row, "sample") or coa_name)
        material = str(_row_value(row, "material_name") or sample)
        tasks.append(
            {
                "todo_key": f"HBOS COA:{coa_name}:publish_coa",
                "module": "quality",
                "source_doctype": "HBOS COA",
                "source_name": coa_name,
                "title": f"{material} · COA",
                "description": f"发布 COA：{sample}",
                "action": "publish_coa",
                "action_label": "发布 COA",
                "status": "已审核",
                "owner_type": "role",
                "priority": "常规",
                "due_at": None,
                "is_overdue": False,
                "route": "/tasks",
                "route_params": {
                    "scope": "mine",
                    "view": "my-approval",
                    "coa": coa_name,
                },
                "modified_at": _row_value(row, "modified"),
            }
        )
    return tasks


def get_task_projection(
    *,
    limit: int = 20,
    cursor: str | None = None,
    view: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    keyword: str | None = None,
) -> dict[str, object]:
    from hb_lims_app.hbos_lims import todo_service

    offset = normalize_cursor(cursor)
    selected_view = normalize_view(view)
    # The current todo service caps one response at 200. The adapter filters
    # the permission-aware result set before paging so view counts and cursors
    # describe the same collection as the UI.
    priority_filter = _PRIORITY_FILTER_MAP.get(str(priority or "").strip(), priority)
    response = todo_service.get_my_todos(
        limit=200,
        offset=0,
        status=status or None,
        priority=priority_filter or None,
        keyword=keyword or None,
    )
    raw_items = list(response.get("items") or [])
    raw_items.extend(get_pending_coa_todos())

    normalized_priority = normalize_priority(priority) if priority else None
    normalized_keyword = str(keyword or "").strip().lower()

    def matches_filters(item: dict[str, object]) -> bool:
        if status and str(item.get("status") or "") != str(status):
            return False
        if normalized_priority and normalize_priority(item.get("priority")) != normalized_priority:
            return False
        if normalized_keyword:
            searchable = " ".join(
                str(item.get(field) or "")
                for field in ("title", "description", "source_name", "action_label")
            ).lower()
            if normalized_keyword not in searchable:
                return False
        return True

    raw_items = [item for item in raw_items if matches_filters(item)]
    if selected_view:
        allowed_actions = PORTAL_TASK_VIEW_ACTIONS[selected_view]
        raw_items = [item for item in raw_items if item.get("action") in allowed_actions]

    tasks = [project_todo(dict(item)) for item in raw_items]
    total = len(tasks)
    page = tasks[offset:offset + max(int(limit), 1)]
    next_offset = offset + len(page)

    return {
        "tasks": page,
        "next_cursor": str(next_offset) if next_offset < total else None,
        "total": total,
        "view": selected_view,
    }
