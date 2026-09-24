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
    if manifest["capabilities"]:
        raise AssertionError("P3-INV-1 must not enable data capabilities")

    resolved = provider.resolve_route("/hbos/inventory")
    if resolved != "/app/hbos-photo-intake":
        raise AssertionError("Inventory current implementation route mismatch")

    return {
        "inventory_route": manifest["route"],
        "inventory_mode": manifest["migration_mode"],
        "inventory_capabilities": manifest["capabilities"],
        "inventory_resolved_route": resolved,
    }
