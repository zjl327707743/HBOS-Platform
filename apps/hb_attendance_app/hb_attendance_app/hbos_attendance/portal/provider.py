from __future__ import annotations

from hb_attendance_app.hbos_attendance.portal.access import build_access_context
from hb_attendance_app.hbos_attendance.portal.manifest import get_manifest
from hb_attendance_app.hbos_attendance.portal.routes import resolve_stable_route
from hb_attendance_app.hbos_attendance.portal.summary import get_summary_projection


class AttendancePortalProvider:
    """Thin legacy experience adapter; Attendance remains domain authority."""

    def manifest(self) -> dict[str, object]:
        return get_manifest()

    def access_context(self) -> dict[str, object]:
        import frappe

        user = frappe.session.user
        roles = frappe.get_roles(user) if user and user != "Guest" else []
        return build_access_context(user, roles)

    def summary(self) -> dict[str, object]:
        return get_summary_projection()

    def resolve_route(self, stable_path: str) -> str:
        return resolve_stable_route(stable_path)


def get_provider() -> AttendancePortalProvider:
    return AttendancePortalProvider()
