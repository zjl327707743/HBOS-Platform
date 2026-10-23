"""Preserve HRMS lifecycle; only its child cancel permission is adapted."""
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest


class ScopedAttendanceRequest(AttendanceRequest):
    def on_cancel(self):
        from hb_attendance_app.hbos_attendance.portal.role_scope import _correction_cancel
        if _correction_cancel.get() is None:
            return super().on_cancel()
        from hb_attendance_app.hbos_attendance.portal.corrections import cancel_native_attendance
        if not cancel_native_attendance(self):
            return super().on_cancel()
