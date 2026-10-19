from __future__ import annotations

import os

import frappe

from hb_inventory_app.hbos_inventory.portal.provider import get_provider


def _require_ci_authority() -> None:
    if os.environ.get("HBOS_PORTAL_INTEGRATION_CHECKS") != "1":
        raise RuntimeError(
            "Inventory Portal integration checks require HBOS_PORTAL_INTEGRATION_CHECKS=1"
        )


def run() -> dict[str, object]:
    _require_ci_authority()
    frappe.set_user("Administrator")

    if not frappe.db.exists("Page", "hbos-photo-intake"):
        raise AssertionError("Inventory current intake Page is missing")
    if not frappe.db.exists("Workspace", "仓库工作台"):
        raise AssertionError("Inventory current Workspace is missing")

    provider = get_provider()
    manifest = provider.manifest()

    if manifest["route"] != "/hbos/inventory":
        raise AssertionError("Inventory stable route mismatch")
    # 「保留 legacy 直到 hybrid/native UX 门禁通过」的旧断言已过时：
    # 概览 / 拍照识别 / 草稿复核 / 批次 / 单据 / 拣货 / 对账等页已前端化，
    # manifest 相应改为 hybrid（见 `portal/manifest.py`）。这里跟随现状断言，
    # 而不是把 manifest 退回 legacy —— 页面确实已经在前端了。
    if manifest["migration_mode"] != "hybrid":
        raise AssertionError("Inventory should be hybrid after native UX rollout")
    if manifest["capabilities"] != ["summary"]:
        raise AssertionError("P3-INV-2 must expose only the summary capability")

    # 基础路由必须解析回 SPA 自身（概览页已原生），不再跳去 Desk。
    resolved = provider.resolve_route("/hbos/inventory")
    if resolved != "/hbos/inventory":
        raise AssertionError("Inventory base route should stay inside the Portal SPA")

    summary = provider.summary()
    if summary.get("app_id") != "inventory":
        raise AssertionError("Inventory summary app id mismatch")
    metrics = list(summary.get("metrics") or [])
    if len(metrics) != 4:
        raise AssertionError("Inventory summary must expose four semantic metrics")
    expected_metric_ids = {
        "inventory_visible_warehouses",
        "inventory_stocked_items",
        "inventory_negative_bins",
        "inventory_projected_shortage_bins",
    }
    if {str(metric.get("id")) for metric in metrics} != expected_metric_ids:
        raise AssertionError("Inventory summary metric contract mismatch")

    return {
        "inventory_route": manifest["route"],
        "inventory_mode": manifest["migration_mode"],
        "inventory_capabilities": manifest["capabilities"],
        "inventory_resolved_route": resolved,
        "inventory_summary_status": summary["status"],
        "inventory_summary_metrics": len(metrics),
    }
