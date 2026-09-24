from __future__ import annotations

import os

from hb_lims_app.hbos_lims.portal.provider import get_provider
from hb_lims_app.hbos_lims.portal.routes import (
    build_stable_deep_link,
    resolve_stable_route,
)


def _require_ci_authority() -> None:
    if os.environ.get("HBOS_PORTAL_INTEGRATION_CHECKS") != "1":
        raise RuntimeError(
            "LIMS Portal integration checks require HBOS_PORTAL_INTEGRATION_CHECKS=1"
        )


def run() -> dict[str, object]:
    """Verify the LIMS-owned internal-route -> stable-link -> runtime-route chain."""

    _require_ci_authority()

    stable_link = build_stable_deep_link(
        "/tasks",
        {"scope": "mine", "task": "TASK-001"},
    )
    if stable_link != "/hbos/lims/tasks?scope=mine&task=TASK-001":
        raise AssertionError("LIMS Todo stable deep-link projection mismatch")

    resolved = resolve_stable_route(stable_link)
    if resolved != "/hbos-lims/tasks?scope=mine&task=TASK-001":
        raise AssertionError("LIMS stable deep-link runtime mapping mismatch")

    task_payload = get_provider().my_tasks(limit=5, cursor=None)
    if not isinstance(task_payload.get("tasks"), list):
        raise AssertionError("LIMS Portal tasks provider returned invalid tasks payload")
    if "next_cursor" not in task_payload:
        raise AssertionError("LIMS Portal tasks provider omitted next_cursor")

    summary_payload = get_provider().summary()
    metrics = list(summary_payload.get("metrics") or [])
    if summary_payload.get("app_id") != "lims":
        raise AssertionError("LIMS Portal summary app_id mismatch")
    if len(metrics) != 4:
        raise AssertionError("LIMS Portal summary must expose four semantic metrics")
    if any(metric.get("deep_link") != "/hbos/lims/tasks?scope=mine" for metric in metrics):
        raise AssertionError("LIMS Portal summary must expose stable HBOS deep links")

    return {
        "stable_link": stable_link,
        "resolved_path": resolved,
        "task_count": len(task_payload["tasks"]),
        "next_cursor": task_payload["next_cursor"],
        "summary_status": summary_payload["status"],
        "summary_metrics": len(metrics),
    }
