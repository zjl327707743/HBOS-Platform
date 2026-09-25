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
    if manifest["migration_mode"] != "legacy":
        raise AssertionError("Inventory must remain legacy until hybrid/native UX gate")
    if manifest["capabilities"] != ["summary"]:
        raise AssertionError("P3-INV-2 must expose only the summary capability")

    resolved = provider.resolve_route("/hbos/inventory")
    if resolved != "/app/hbos-photo-intake":
        raise AssertionError("Inventory current implementation route mismatch")

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
