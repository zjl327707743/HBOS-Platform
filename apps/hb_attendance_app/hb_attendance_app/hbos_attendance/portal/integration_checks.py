from __future__ import annotations

import os

import frappe

from hb_attendance_app.hbos_attendance.portal.provider import get_provider


def _require_ci_authority() -> None:
    if os.environ.get("HBOS_PORTAL_INTEGRATION_CHECKS") != "1":
        raise RuntimeError(
            "Attendance Portal integration checks require HBOS_PORTAL_INTEGRATION_CHECKS=1"
        )


def run() -> dict[str, object]:
    _require_ci_authority()

    frappe.set_user("Administrator")

    if not frappe.db.exists("Page", "hbos-attendance-dashboard"):
        raise AssertionError("Attendance current Desk dashboard Page is missing")
    if not frappe.db.exists("Workspace", "海滨考勤工作台"):
        raise AssertionError("Attendance current Workspace is missing")

    provider = get_provider()
    manifest = provider.manifest()
    if manifest["route"] != "/hbos/attendance":
        raise AssertionError("Attendance stable route mismatch")
    if manifest["migration_mode"] != "legacy":
        raise AssertionError("Attendance must remain legacy until native UX gate")
    if manifest["capabilities"] != ["summary"]:
        raise AssertionError("P3-ATT-2 must enable summary only")

    resolved = provider.resolve_route("/hbos/attendance")
    if resolved != "/app/hbos-attendance-dashboard":
        raise AssertionError("Attendance current implementation route mismatch")

    summary_payload = provider.summary()
    metrics = list(summary_payload.get("metrics") or [])
    if summary_payload.get("app_id") != "attendance":
        raise AssertionError("Attendance summary app_id mismatch")
    if len(metrics) != 4:
        raise AssertionError("Attendance summary must expose four HR metrics")
    if any(metric.get("deep_link") != "/hbos/attendance/dashboard" for metric in metrics):
        raise AssertionError("Attendance summary must use stable HBOS deep links")

    return {
        "attendance_route": manifest["route"],
        "attendance_mode": manifest["migration_mode"],
        "attendance_capabilities": manifest["capabilities"],
        "attendance_resolved_route": resolved,
        "attendance_summary_status": summary_payload["status"],
        "attendance_summary_metrics": len(metrics),
    }
