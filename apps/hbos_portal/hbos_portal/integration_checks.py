from __future__ import annotations

import os

import frappe

from hbos_portal.services.access import evaluate_access
from hbos_portal.services.bootstrap import build_bootstrap
from hbos_portal.services.dispatcher import dispatch_provider
from hbos_portal.services.registry import build_registry
from hbos_portal.services.routes import resolve_stable_route

ATTENDANCE_PAGE = "hbos-attendance-dashboard"
ATTENDANCE_WORKSPACE = "海滨考勤工作台"


def _require_ci_authority() -> None:
    if os.environ.get("HBOS_PORTAL_INTEGRATION_CHECKS") != "1":
        raise RuntimeError(
            "HBOS Portal integration checks require HBOS_PORTAL_INTEGRATION_CHECKS=1"
        )


def run() -> dict[str, object]:
    """Verify real Frappe Hook -> Registry -> Access -> Bootstrap integration.

    This function is intentionally not whitelisted and is guarded by an
    explicit CI environment variable.

    Scope: this branch registers exactly one Portal provider (attendance,
    migration_mode=legacy). LIMS / Inventory are out of scope here, so the
    gate only asserts the attendance surface.
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

    if "attendance" not in registry.entries:
        raise AssertionError("Attendance provider was not discovered by Frappe hooks")

    entry = registry.entries["attendance"]
    manifest = entry.manifest.to_dict()

    if manifest["route"] != "/hbos/attendance":
        raise AssertionError("Attendance stable route mismatch")
    if manifest["migration_mode"] != "legacy":
        raise AssertionError("Attendance must stay in legacy migration mode")
    if manifest["capabilities"] != ["summary"]:
        raise AssertionError(
            "Attendance must expose only the reviewed summary capability"
        )

    if not frappe.db.exists("Page", ATTENDANCE_PAGE):
        raise AssertionError(f"Page {ATTENDANCE_PAGE} is missing")
    if not frappe.db.exists("Workspace", ATTENDANCE_WORKSPACE):
        raise AssertionError(f"Workspace {ATTENDANCE_WORKSPACE} is missing")

    access = evaluate_access(entry)
    if not access.can_enter:
        raise AssertionError(
            "Administrator must receive Attendance break-glass entry access"
        )

    attendance_route = resolve_stable_route(
        "attendance",
        "/hbos/attendance",
    )
    if attendance_route["resolved_path"] != "/app/hbos-attendance-dashboard":
        raise AssertionError("Attendance stable route adapter mismatch")

    summary_dispatch = dispatch_provider("attendance", "summary")
    summary = summary_dispatch["data"]
    summary_metrics = list(summary.get("metrics") or [])
    if len(summary_metrics) != 4:
        raise AssertionError(
            "Portal dispatcher did not receive the four Attendance summary metrics"
        )

    bootstrap = build_bootstrap()
    app_ids = [app["manifest"]["id"] for app in bootstrap["apps"]]
    if "attendance" not in app_ids:
        raise AssertionError(
            "Authenticated Portal bootstrap did not expose Attendance"
        )

    return {
        "registry_entries": sorted(registry.entries),
        "registry_failures": len(registry.failures),
        "attendance_route": manifest["route"],
        "attendance_manifest_capabilities": manifest["capabilities"],
        "attendance_migration_mode": manifest["migration_mode"],
        "attendance_access": access.can_enter,
        "attendance_page_present": True,
        "attendance_workspace_present": True,
        "attendance_resolved_route": attendance_route["resolved_path"],
        "attendance_summary_metrics": len(summary_metrics),
        "bootstrap_apps": app_ids,
        "user": bootstrap["user"]["id"],
    }
