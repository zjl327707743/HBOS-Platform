from __future__ import annotations

from typing import Any

from hb_lims_app.hbos_lims.portal.routes import build_stable_deep_link


def _int_value(value: object) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _task_link(view: str, *, status: str | None = None) -> str:
    params: dict[str, object] = {"view": view}
    if status:
        params["status"] = status
    return build_stable_deep_link("/tasks", params)


def project_todo_summary(payload: dict[str, Any]) -> dict[str, object]:
    """Convert permission-aware LIMS facts into the approved KPI contract."""

    summary = dict(payload.get("summary") or {})
    semantic = dict(payload.get("semantic") or {})
    overdue = _int_value(summary.get("overdue"))
    pending_testing = _int_value(semantic.get("pending_testing"))
    in_testing = _int_value(semantic.get("in_testing"))
    pending_review = _int_value(semantic.get("pending_review"))
    pending_coa = _int_value(semantic.get("pending_coa_publish"))

    return {
        "app_id": "lims",
        "generated_at": str(payload.get("generated_at") or ""),
        "scope_label": str(payload.get("scope_label") or "我的 LIMS 工作范围"),
        "status": "attention" if overdue > 0 else "normal",
        "metrics": [
            {
                "id": "my_testing",
                "label": "待检",
                "value": pending_testing,
                "tone": "info" if pending_testing > 0 else "neutral",
                "deep_link": _task_link("my-testing"),
            },
            {
                "id": "in_testing",
                "label": "检验中",
                "value": in_testing,
                "tone": "info" if in_testing > 0 else "neutral",
                "deep_link": _task_link("my-testing", status="检验中"),
            },
            {
                "id": "my_review",
                "label": "待复核",
                "value": pending_review,
                "tone": "warning" if pending_review > 0 else "neutral",
                "deep_link": _task_link("my-review"),
            },
            {
                "id": "coa_publish",
                "label": "待发布 COA",
                "value": pending_coa,
                "tone": "critical" if pending_coa > 0 else "success",
                "deep_link": _task_link("my-approval"),
            },
        ],
    }


def _scope_label() -> str:
    """Return a non-sensitive, read-only label for the current LIMS scope."""
    import frappe

    from hb_lims_app.hbos_lims import workflow_contract as wf
    from hb_lims_app.hbos_lims.todo_contract import business_roles_for_user

    user = str(getattr(getattr(frappe, "session", None), "user", "") or "")
    roles = tuple(frappe.get_roles(user) or ()) if user and user != "Guest" else ()
    business_roles = business_roles_for_user(user, roles)
    if wf.ROLE_MANAGER in business_roles:
        return "LIMS 管理范围"
    if any(role in business_roles for role in (wf.ROLE_LIMS_QA, wf.ROLE_LIMS_QA_MANAGER, wf.ROLE_LIMS_QP)):
        return "质量审批范围"
    if wf.ROLE_REVIEWER in business_roles:
        return "复核范围"
    if wf.ROLE_ANALYST in business_roles:
        return "检验范围"
    return "我的 LIMS 工作范围"


def _semantic_counts(items: list[dict[str, object]]) -> dict[str, int]:
    return {
        "pending_testing": sum(item.get("action") == "start_task" for item in items),
        "in_testing": sum(
            item.get("action") == "submit_result"
            and item.get("status") == "草稿"
            for item in items
        ),
        "pending_review": sum(item.get("action") == "review_result" for item in items),
        "pending_coa_publish": sum(item.get("action") == "publish_coa" for item in items),
    }


def get_summary_projection() -> dict[str, object]:
    from hb_lims_app.hbos_lims.todo_service import get_my_todo_summary
    from hb_lims_app.hbos_lims.todo_service import get_my_todos
    from hb_lims_app.hbos_lims.portal.tasks import get_pending_coa_todos

    payload = dict(get_my_todo_summary())
    task_payload = get_my_todos(limit=200, offset=0)
    items = list(task_payload.get("items") or [])
    items.extend(get_pending_coa_todos())
    payload["semantic"] = _semantic_counts(items)
    payload["scope_label"] = _scope_label()
    return project_todo_summary(payload)
