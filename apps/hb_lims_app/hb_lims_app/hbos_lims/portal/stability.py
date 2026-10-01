from __future__ import annotations

from typing import Any


def _rows(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in (value or {}).get("rows", [])]


def _limit(value: int | str | None, default: int = 50) -> int:
    try:
        return max(1, min(int(value or default), 50))
    except (TypeError, ValueError):
        return default


def get_stability_projection(
    *,
    section: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    month: str | None = None,
    condition: str | None = None,
    exec_status: str | None = None,
    stability_product: str | None = None,
    stability_test_item: str | None = None,
    condition_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, object]:
    """稳定性 Portal 只读投影，所有数据均经稳定性服务角色校验。"""
    from hb_lims_app.hbos_lims import stability_service

    current = section or "workbench"
    page_size = _limit(limit)
    dashboard: dict[str, Any] = {}
    schedule: dict[str, Any] = {"rows": [], "summary": {}}
    samples: dict[str, Any] = {"rows": []}
    results: dict[str, Any] = {"rows": []}
    products: dict[str, Any] = {"rows": []}
    test_items: dict[str, Any] = {"rows": []}
    trend: dict[str, Any] | None = None

    if current in {"workbench", "schedule", "samples", "results"}:
        dashboard = dict(stability_service.get_stability_dashboard() or {})
    if current in {"workbench", "schedule"}:
        schedule = dict(stability_service.get_stability_schedule(
            month=month or None,
            condition=condition or None,
            exec_status=exec_status or None,
            keyword=keyword or None,
            limit=page_size,
        ) or {})
    if current == "samples":
        samples = dict(stability_service.get_stability_samples(
            keyword=keyword or None,
            status=status or None,
            stability_product=stability_product or None,
            limit=page_size,
            offset=max(0, int(offset or 0)),
        ) or {})
    if current == "results":
        results = dict(stability_service.get_stability_results(
            stability_test_item=stability_test_item or None,
            status=status or None,
            limit=page_size,
        ) or {})
    if current == "trend":
        products = dict(stability_service.get_stability_products(
            keyword=keyword or None,
            include_inactive=0,
        ) or {})
        test_items = dict(stability_service.get_stability_master(
            "HBOS Stability Test Item", keyword=None, include_inactive=0,
        ) or {})
        if stability_product and stability_test_item:
            trend = dict(stability_service.get_stability_trend(
                stability_product=stability_product,
                stability_test_item=stability_test_item,
                condition_type=condition_type or None,
            ) or {})

    schedule_rows = _rows(schedule)
    sample_rows = _rows(samples)
    result_rows = _rows(results)
    product_rows = _rows(products)
    return {
        "section": current,
        "dashboard": dashboard,
        "schedule": {"rows": schedule_rows, "summary": schedule.get("summary") or {}},
        "samples": {"rows": sample_rows, "total": len(sample_rows)},
        "results": {"rows": result_rows, "total": len(result_rows)},
        "products": {"rows": product_rows, "total": len(product_rows)},
        "test_items": {"rows": _rows(test_items), "total": len(_rows(test_items))},
        "trend": trend,
        "scope": dashboard.get("scope") or "当前账号可查看的稳定性数据",
    }
