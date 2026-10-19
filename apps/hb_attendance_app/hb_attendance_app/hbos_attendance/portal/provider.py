from __future__ import annotations

from hb_attendance_app.hbos_attendance.portal.access import build_access_context
from hb_attendance_app.hbos_attendance.portal.manifest import get_manifest
from hb_attendance_app.hbos_attendance.portal.routes import resolve_stable_route
from hb_attendance_app.hbos_attendance.portal.summary import get_summary_projection


class AttendancePortalProvider:
    """Thin legacy experience adapter; Attendance remains domain authority."""

    def manifest(self) -> dict[str, object]:
        manifest = get_manifest()
        managed = _role_context()
        if managed is not None:
            return {**manifest, 'route': _role_route(managed), 'migration_mode': 'native', 'description': '按已发布角色与具名范围使用考勤', 'capabilities': []}
        if _personal_allowed():
            return {**manifest, "route": "/hbos/attendance/me", "migration_mode": "native", "description": "查看本人当前和历史考勤", "capabilities": []}
        return manifest

    def access_context(self) -> dict[str, object]:
        import frappe

        user = frappe.session.user
        roles = frappe.get_roles(user) if user and user != "Guest" else []
        managed = _role_context()
        if managed is not None:
            return {'app_id':'attendance','can_enter':bool(managed),'capabilities':['attendance.role.managed',*managed], 'scopes':{}}
        from hb_attendance_app.hbos_attendance.portal.permissions import legacy_hr
        if not (getattr(frappe, "conf", {}).get("hbos_iam_enabled") in (True, 1, "1")) or legacy_hr(user):
            return build_access_context(user, roles)
        return build_access_context(user, [], personal_allowed=_personal_allowed())

    def summary(self) -> dict[str, object]:
        import frappe
        from hb_attendance_app.hbos_attendance.portal.permissions import legacy_hr
        managed = _role_context()
        if managed is not None:
            if not managed:
                frappe.throw('当前角色没有可用考勤功能。', frappe.PermissionError)
            return {'app_id':'attendance','generated_at':'','status':'normal','metrics':[]}
        if (frappe.conf.get("hbos_iam_enabled") in (True, 1, "1")) and not legacy_hr():
            if not _personal_allowed():
                frappe.throw("尚未安排本人考勤。", frappe.PermissionError)
            return {"app_id": "attendance", "generated_at": "", "status": "normal", "metrics": []}
        return get_summary_projection()

    def resolve_route(self, stable_path: str) -> str:
        import frappe
        from hb_attendance_app.hbos_attendance.portal.permissions import legacy_hr
        managed = _role_context()
        if managed is not None:
            if stable_path in {'/hbos/attendance','/hbos/attendance/'} and managed:
                return _role_route(managed)
            if any(stable_path == path and operation in managed for operation,path in ROLE_ROUTES.items()):
                return stable_path
            frappe.throw('此考勤页面未包含在当前发布角色中。', frappe.PermissionError)
        if (frappe.conf.get("hbos_iam_enabled") in (True, 1, "1")) and not legacy_hr():
            if _personal_allowed() and stable_path in {"/hbos/attendance", "/hbos/attendance/", "/hbos/attendance/me"}:
                return "/hbos/attendance/me"
            frappe.throw("此考勤入口尚未向当前账号开放。", frappe.PermissionError)
        return resolve_stable_route(stable_path)


def get_provider() -> AttendancePortalProvider:
    return AttendancePortalProvider()


ROLE_ROUTES = {
    **{'attendance.export.'+kind:'/hbos/attendance/exports' for kind in ('monthly','exceptions','roster')},
    **{'attendance.record.'+operation+'.read':'/hbos/attendance/list/'+slug for operation,slug in [('leave','feishu-leave'),('overtime','feishu-overtime'),('rest_leave','feishu-rest-leave')]},
    **{op:'/hbos/attendance/shifts' for op in ('attendance.shift.read','attendance.shift.manage','attendance.shift.status','attendance.shift.delete','attendance.schedule.read','attendance.schedule.bind')},
    **{op:'/hbos/attendance/rules' for op in ('attendance.rules.manage','attendance.rules.recalculate','attendance.schedule.generate')},
    **{'attendance.correction.'+action:'/hbos/attendance/corrections' for action in ('create','submit','cancel','amend')},
    'attendance.department.records.read':'/hbos/attendance/employees',
    'attendance.company.read':'/hbos/attendance',
    'attendance.read':'/hbos/attendance/me',
    'attendance.department.board.read':'/hbos/attendance/board',
    'attendance.report.monthly.read':'/hbos/attendance/report/monthly',
    'attendance.report.checkins.read':'/hbos/attendance/report/checkins',
    'attendance.report.results.read':'/hbos/attendance/report/results',
}


def _role_context():
    import frappe
    if frappe.conf.get('hbos_iam_roles_enabled') not in (True,1,'1'):
        return None
    from hbos_portal.iam import policy, role_access as roles
    employee=policy.resolve_employee(policy.get_current_user(),required=False)
    resolved=roles.resolve(employee) if employee else None
    if resolved is None:return None
    result=[]
    for feature in resolved.get('features',[]):
        scopes=[dict(scope_type='SELF',scope_ref='')] if feature['scope_binding']=='SELF' else resolved.get('responsibilities',[])
        if any(policy.evaluate(policy.get_current_user(),'attendance',feature['operation_id'],scope['scope_type'],scope['scope_ref'])['allowed'] for scope in scopes):
            result.append(feature['operation_id'])
    return result


def _role_route(capabilities):
    priority=('attendance.company.read','attendance.department.board.read','attendance.department.records.read','attendance.read')
    return next((ROLE_ROUTES[operation] for operation in (*priority,*ROLE_ROUTES) if operation in capabilities), '/hbos/attendance')


def _personal_allowed():
    import frappe
    if not (frappe.conf.get("hbos_iam_enabled") in (True, 1, "1")) or not frappe.db.exists("DocType", "HBOS IAM Policy"):
        return False
    from hbos_portal.iam.policy import evaluate
    return evaluate(frappe.session.user, "attendance", "attendance.read", "SELF", "")["allowed"]
