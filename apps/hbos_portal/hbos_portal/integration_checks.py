from __future__ import annotations

import os

import frappe

from hbos_portal.services.access import evaluate_access
from hbos_portal.services.bootstrap import build_bootstrap
from hbos_portal.services.registry import build_registry
from hbos_portal.services.routes import resolve_stable_route


def _require_ci_authority() -> None:
    if os.environ.get("HBOS_PORTAL_INTEGRATION_CHECKS") != "1":
        raise RuntimeError(
            "HBOS Portal integration checks require HBOS_PORTAL_INTEGRATION_CHECKS=1"
        )


def run() -> dict[str, object]:
    """Verify real Frappe Hook -> Registry -> Access -> Bootstrap integration.

    This function is intentionally not whitelisted and is guarded by an
    explicit CI environment variable.
    """

    _require_ci_authority()

    frappe.set_user("Administrator")

    registry = build_registry()
    if registry.failures:
        raise AssertionError(
            "Portal Registry failures: "
            + "; ".join(
                f"{item.provider_path}:{item.code}:{item.detail}"
                for item in registry.failures
            )
        )

    if "lims" not in registry.entries:
        raise AssertionError("LIMS provider was not discovered by Frappe hooks")
    if "attendance" not in registry.entries:
        raise AssertionError("Attendance provider was not discovered by Frappe hooks")
    if "inventory" not in registry.entries:
        raise AssertionError("Inventory provider was not discovered by Frappe hooks")

    entry = registry.entries["lims"]
    manifest = entry.manifest.to_dict()

    if manifest["route"] != "/hbos/lims":
        raise AssertionError("LIMS stable route mismatch")
    if manifest["capabilities"] != ["summary", "tasks", "search"]:
        raise AssertionError(
            "P3-LIMS-5 must expose summary/tasks/search and no unreviewed capability"
        )

    access = evaluate_access(entry)
    if not access.can_enter:
        raise AssertionError("Administrator must receive LIMS break-glass entry access")

    route_result = resolve_stable_route(
        "lims",
        "/hbos/lims/tasks?scope=mine&task=TASK-001",
    )
    if route_result["resolved_path"] != "/hbos-lims/tasks?scope=mine&task=TASK-001":
        raise AssertionError("LIMS stable route adapter mismatch")

    attendance_route = resolve_stable_route(
        "attendance",
        "/hbos/attendance",
    )
    if attendance_route["resolved_path"] != "/app/hbos-attendance-dashboard":
        raise AssertionError("Attendance stable route adapter mismatch")

    inventory_route = resolve_stable_route(
        "inventory",
        "/hbos/inventory",
    )
    if inventory_route["resolved_path"] != "/app/hbos-photo-intake":
        raise AssertionError("Inventory stable route adapter mismatch")

    bootstrap = build_bootstrap()
    app_ids = [
        app["manifest"]["id"]
        for app in bootstrap["apps"]
    ]
    if "lims" not in app_ids:
        raise AssertionError("Authenticated Portal bootstrap did not expose LIMS")
    if "attendance" not in app_ids:
        raise AssertionError("Authenticated Portal bootstrap did not expose Attendance")
    if "inventory" not in app_ids:
        raise AssertionError("Authenticated Portal bootstrap did not expose Inventory")

    return {
        "registry_entries": sorted(registry.entries),
        "registry_failures": len(registry.failures),
        "lims_route": manifest["route"],
        "lims_manifest_capabilities": manifest["capabilities"],
        "lims_access": access.can_enter,
        "lims_resolved_route": route_result["resolved_path"],
        "attendance_resolved_route": attendance_route["resolved_path"],
        "inventory_resolved_route": inventory_route["resolved_path"],
        "bootstrap_apps": app_ids,
        "user": bootstrap["user"]["id"],
    }
