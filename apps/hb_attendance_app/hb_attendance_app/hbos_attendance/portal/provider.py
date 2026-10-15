from __future__ import annotations

from hb_attendance_app.hbos_attendance.portal.access import build_access_context
from hb_attendance_app.hbos_attendance.portal.manifest import get_manifest
from hb_attendance_app.hbos_attendance.portal.routes import resolve_stable_route
from hb_attendance_app.hbos_attendance.portal.summary import get_summary_projection


class AttendancePortalProvider:
    """Thin legacy experience adapter; Attendance remains domain authority."""

    def manifest(self) -> dict[str, object]:
        manifest = get_manifest()
        if _personal_allowed():
            return {**manifest, "route": "/hbos/attendance/me", "migration_mode": "native", "description": "查看本人当前和历史考勤", "capabilities": []}
        return manifest

    def access_context(self) -> dict[str, object]:
        import frappe

        user = frappe.session.user
        roles = frappe.get_roles(user) if user and user != "Guest" else []
        from hb_attendance_app.hbos_attendance.portal.permissions import legacy_hr
        if not (getattr(frappe, "conf", {}).get("hbos_iam_enabled") in (True, 1, "1")) or legacy_hr(user):
            return build_access_context(user, roles)
        return build_access_context(user, [], personal_allowed=_personal_allowed())

    def summary(self) -> dict[str, object]:
        import frappe
        from hb_attendance_app.hbos_attendance.portal.permissions import legacy_hr
        if (frappe.conf.get("hbos_iam_enabled") in (True, 1, "1")) and not legacy_hr():
            if not _personal_allowed():
                frappe.throw("尚未安排本人考勤。", frappe.PermissionError)
            return {"app_id": "attendance", "generated_at": "", "status": "normal", "metrics": []}
        return get_summary_projection()

    def resolve_route(self, stable_path: str) -> str:
        import frappe
        from hb_attendance_app.hbos_attendance.portal.permissions import legacy_hr
        if (frappe.conf.get("hbos_iam_enabled") in (True, 1, "1")) and not legacy_hr():
            if _personal_allowed() and stable_path in {"/hbos/attendance", "/hbos/attendance/", "/hbos/attendance/me"}:
                return "/hbos/attendance/me"
            frappe.throw("此考勤入口尚未向当前账号开放。", frappe.PermissionError)
        return resolve_stable_route(stable_path)


def get_provider() -> AttendancePortalProvider:
    return AttendancePortalProvider()


def _personal_allowed():
    import frappe
    if not (frappe.conf.get("hbos_iam_enabled") in (True, 1, "1")) or not frappe.db.exists("DocType", "HBOS IAM Policy"):
        return False
    from hbos_portal.iam.policy import evaluate
    return evaluate(frappe.session.user, "attendance", "attendance.read", "SELF", "")["allowed"]
