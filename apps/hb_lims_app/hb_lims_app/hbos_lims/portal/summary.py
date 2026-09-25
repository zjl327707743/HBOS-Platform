from __future__ import annotations

from typing import Any


def _int_value(value: object) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def project_todo_summary(payload: dict[str, Any]) -> dict[str, object]:
    """Convert the permission-aware LIMS todo summary into Portal semantics."""

    summary = dict(payload.get("summary") or {})
    by_module = dict(summary.get("by_module") or {})

    total = _int_value(summary.get("total"))
    overdue = _int_value(summary.get("overdue"))
    testing = _int_value(by_module.get("testing"))
    stability = _int_value(by_module.get("stability"))

    task_link = "/hbos/lims/tasks?scope=mine"

    return {
        "app_id": "lims",
        "generated_at": str(payload.get("generated_at") or ""),
        "status": "attention" if overdue > 0 else "normal",
        "metrics": [
            {
                "id": "my_lims_work",
                "label": "我的 LIMS 待办",
                "value": total,
                "tone": "info" if total > 0 else "neutral",
                "deep_link": task_link,
            },
            {
                "id": "my_lims_overdue",
                "label": "LIMS 超期",
                "value": overdue,
                "tone": "critical" if overdue > 0 else "success",
                "deep_link": task_link,
            },
            {
                "id": "my_lims_testing",
                "label": "检验待办",
                "value": testing,
                "tone": "info" if testing > 0 else "neutral",
                "deep_link": task_link,
            },
            {
                "id": "my_lims_stability",
                "label": "稳定性待办",
                "value": stability,
                "tone": "warning" if stability > 0 else "neutral",
                "deep_link": task_link,
            },
        ],
    }


def get_summary_projection() -> dict[str, object]:
    from hb_lims_app.hbos_lims.todo_service import get_my_todo_summary

    return project_todo_summary(get_my_todo_summary())
