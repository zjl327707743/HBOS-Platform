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
        {"view": "my-testing", "task": "TASK-001"},
    )
    if stable_link != "/hbos/lims/tasks?view=my-testing&task=TASK-001":
        raise AssertionError("LIMS Todo stable deep-link projection mismatch")

    resolved = resolve_stable_route(stable_link)
    if resolved != "/hbos-lims/tasks?view=my-testing&task=TASK-001":
        raise AssertionError("LIMS stable deep-link runtime mapping mismatch")

    task_payload = get_provider().my_tasks(limit=5, cursor=None)
    if not isinstance(task_payload.get("tasks"), list):
        raise AssertionError("LIMS Portal tasks provider returned invalid tasks payload")
    if "next_cursor" not in task_payload:
        raise AssertionError("LIMS Portal tasks provider omitted next_cursor")

    approval_payload = get_provider().my_tasks(
        limit=5,
        cursor=None,
        view="my-approval",
    )
    if approval_payload.get("view") != "my-approval":
        raise AssertionError("LIMS Portal task view was not preserved")
    if not isinstance(approval_payload.get("tasks"), list):
        raise AssertionError("LIMS Portal approval view returned invalid tasks payload")

    summary_payload = get_provider().summary()
    metrics = list(summary_payload.get("metrics") or [])
    if summary_payload.get("app_id") != "lims":
        raise AssertionError("LIMS Portal summary app_id mismatch")
    if len(metrics) != 4:
        raise AssertionError("LIMS Portal summary must expose four semantic metrics")
    expected_metric_links = {
        "my_testing": "/hbos/lims/tasks?view=my-testing",
        "in_testing": "/hbos/lims/tasks?view=my-testing&status=%E6%A3%80%E9%AA%8C%E4%B8%AD",
        "my_review": "/hbos/lims/tasks?view=my-review",
        "coa_publish": "/hbos/lims/tasks?view=my-approval",
    }
    metric_ids = {str(metric.get("id")) for metric in metrics}
    if metric_ids != set(expected_metric_links):
        raise AssertionError("LIMS Portal summary semantic metric IDs mismatch")
    for metric in metrics:
        metric_id = str(metric.get("id"))
        if metric.get("deep_link") != expected_metric_links[metric_id]:
            raise AssertionError(
                f"LIMS Portal summary deep link mismatch for {metric_id}"
            )

    search_payload = get_provider().search(
        query="HBOS-NO-MATCH",
        limit=5,
    )
    if not isinstance(search_payload.get("results"), list):
        raise AssertionError("LIMS Portal search provider returned invalid results payload")

    result_payload = get_provider().results(limit=5, cursor=None)
    if not isinstance(result_payload.get("results"), list):
        raise AssertionError("LIMS Portal result provider returned invalid results payload")
    if "next_cursor" not in result_payload:
        raise AssertionError("LIMS Portal result provider omitted next_cursor")

    return {
        "stable_link": stable_link,
        "resolved_path": resolved,
        "task_count": len(task_payload["tasks"]),
        "approval_task_count": len(approval_payload["tasks"]),
        "next_cursor": task_payload["next_cursor"],
        "summary_status": summary_payload["status"],
        "summary_metrics": len(metrics),
        "search_results": len(search_payload["results"]),
        "result_count": len(result_payload["results"]),
    }
