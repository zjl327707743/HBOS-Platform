from __future__ import annotations

import os

from hb_attendance_app.hbos_attendance.portal.provider import get_provider


def _require_ci_authority() -> None:
    if os.environ.get("HBOS_PORTAL_INTEGRATION_CHECKS") != "1":
        raise RuntimeError(
            "Attendance Portal integration checks require HBOS_PORTAL_INTEGRATION_CHECKS=1"
        )


def run() -> dict[str, object]:
    _require_ci_authority()

    provider = get_provider()
    manifest = provider.manifest()
    if manifest["route"] != "/hbos/attendance":
        raise AssertionError("Attendance stable route mismatch")
    if manifest["migration_mode"] != "legacy":
        raise AssertionError("Attendance must remain legacy until native UX gate")
    if manifest["capabilities"]:
        raise AssertionError("P3-ATT-1 must not enable data capabilities")

    resolved = provider.resolve_route("/hbos/attendance")
    if resolved != "/app/hbos-attendance-dashboard":
        raise AssertionError("Attendance current implementation route mismatch")

    return {
        "attendance_route": manifest["route"],
        "attendance_mode": manifest["migration_mode"],
        "attendance_capabilities": manifest["capabilities"],
        "attendance_resolved_route": resolved,
    }
