"""Fresh, named role bounds for explicitly integrated Attendance executors.

This does not relax native all-row reports, File, Prepared Report or workers.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, time

import frappe

_report = ContextVar('attendance_role_report', default=None)


class HistoricalEmployees(list):
    def __init__(self):
        super().__init__()
        self.coverage={'complete':True,'rejected_ranges':[]}


def check_fields(allowed):
    if set(getattr(frappe.local,'form_dict',{}) or {}) - set(allowed) - {'cmd'}:
        frappe.throw('此范围接口不接受额外员工、部门或身份参数。',frappe.PermissionError)


@contextmanager
def report_execution(key, employees):
    if key not in {'monthly','checkins','results'}:
        raise ValueError('Unintegrated scoped report')
    token=_report.set(dict(key=key, employees=tuple(row.name for row in employees)))
    try:
        yield
    finally:
        _report.reset(token)


def report_predicate(alias, params):
    bound=_report.get()
    if bound is None:return None
    if alias not in {'a','ec','lr'}:raise ValueError('Unknown report source')
    params['iam_employees']=bound['employees'] or ('',)
    return f'{alias}.employee in %(iam_employees)s'


def scoped_report_sources(sources):
    bound=_report.get()
    if bound is None:return False
    allowed={'monthly':{'Employee','Attendance','Employee Checkin','HBOS Leave Record'},
             'checkins':{'Employee','Employee Checkin','HBOS Shift Rule'},'results':{'Employee','Attendance','Employee Checkin'}}
    if not set(sources).issubset(allowed[bound['key']]):
        frappe.throw('该报表来源尚未接入角色范围。',frappe.PermissionError)
    return True


def context(operation, *, department=None, employee=None, rule=None):
    if getattr(frappe,'conf',{}).get('hbos_iam_roles_enabled') not in (True,1,'1'):
        return None
    from hbos_portal.iam import policy, role_access as roles
    if not roles.enabled():
        return None
    user=policy.get_current_user()
    subject=policy.resolve_employee(user, required=False)
    resolved=roles.resolve(subject) if subject else None
    if resolved is None:
        return None
    departments=[]
    for scope in resolved.get('responsibilities', []):
        if scope['scope_type']=='DEPARTMENT':
            if policy.evaluate(user,'attendance',operation,'DEPARTMENT',scope['scope_ref'])['allowed']:
                departments.append(scope['scope_ref'])
        elif policy.evaluate(user,'attendance',operation,'COMPANY',scope['scope_ref'])['allowed']:
            departments.extend(row.name for row in frappe.db.sql('select name from `tabDepartment` where company=%s and disabled=0 order by name for update',(scope['scope_ref'],),as_dict=True))
    departments=sorted(set(departments))
    if not departments:
        frappe.throw('当前发布角色没有此功能的具名负责范围。',frappe.PermissionError)
    if rule:
        department=frappe.db.get_value('HBOS Shift Rule',rule,'department',for_update=True)
    if employee:
        department=frappe.db.get_value('Employee',employee,'department',for_update=True)
    if (employee or rule) and not department or department and department not in departments:
        frappe.throw('该员工、班次或部门不在当前具名负责范围内。',frappe.PermissionError)
    return dict(user=user,departments=[department] if department else departments,operation=operation)


def require(operation, **target):
    bound=context(operation,**target)
    if bound is None:
        if getattr(frappe,'conf',{}).get('hbos_iam_enabled') in (True,1,'1'):
            from hb_attendance_app.hbos_attendance.portal.permissions import legacy_hr
            if not legacy_hr(for_update=True):
                frappe.throw('此业务入口尚未向当前账号开放。',frappe.PermissionError)
        frappe.only_for(['HR User','HR Manager','System Manager'])
    return bound


def _historical_department(employee, start, end):
    """Native Employee creation + complete tracked Version chain, never today's dept alone.

    An unprovable period or a transition inside it is refused. SELF is separate.
    """
    from frappe.utils import get_datetime
    if not frappe.get_meta('Employee').track_changes or not employee.creation or get_datetime(employee.creation)>start:
        return None
    department,company=employee.department,employee.company
    versions=frappe.db.sql("select creation,data from `tabVersion` where ref_doctype='Employee' and docname=%s order by creation desc,name desc for update",(employee.name,),as_dict=True)
    for version in versions:
        try:
            changes=json.loads(version.data or '{}').get('changed',[])
        except (TypeError,ValueError):
            return None
        for change in changes:
            if not isinstance(change,list) or len(change)!=3 or change[0] not in {'department','company'}:
                continue
            field,old,new=change
            stamp=get_datetime(version.creation)
            if stamp<=start:
                continue
            current=department if field=='department' else company
            if current!=new or stamp<=end:
                return None
            if field=='department':department=old
            else:company=old
    return department,company


def historical_employees(bound, start, end):
    """Select candidates from current membership and tracked native history.

    Only metadata is loaded before temporal attribution; no business row/count is
    read until the whole requested period has an authorizing attribution.
    """
    if not bound:
        raise ValueError('Missing role bound')
    from frappe.utils import get_datetime
    start=datetime.combine(start,time.min) if not isinstance(start,datetime) else start
    end=datetime.combine(end,time.max) if not isinstance(end,datetime) else end
    departments=bound['departments']
    names={row.name for row in frappe.db.sql('select name from `tabEmployee` where department in %(departments)s order by name for update',{'departments':tuple(departments)},as_dict=True)}
    # A JSON match is a candidate search only, never proof or authorization.
    versions=frappe.db.sql("select docname,data from `tabVersion` where ref_doctype='Employee' and data like %s order by name for update",('%"department"%',),as_dict=True)
    for version in versions:
        try: changes=json.loads(version.data or '{}').get('changed',[])
        except (TypeError,ValueError): continue
        if any(isinstance(row,list) and len(row)==3 and row[0]=='department' and any(department in row[1:] for department in departments) for row in changes):
            names.add(version.docname)
    employees=HistoricalEmployees()
    if not names:return employees
    for employee in frappe.db.sql('select name,employee_number,employee_name,department,company,status,creation from `tabEmployee` where name in %(names)s order by name for update',{'names':tuple(names)},as_dict=True):
        attribution=_historical_department(employee,start,end)
        if attribution is None:
            employees.coverage['complete']=False
            continue  # No business row/count for this employee is read.
        department,company=attribution
        if department in departments:
            actual_company=frappe.db.get_value('Department',department,'company',for_update=True)
            if actual_company!=company:
                employees.coverage['complete']=False
                continue
            employees.append(frappe._dict({**employee,'department':department,'company':company}))
    if not employees.coverage['complete']:
        employees.coverage['rejected_ranges']=[dict(department=department,date_from=start.date().isoformat(),date_to=end.date().isoformat(),reason='部分历史归属缺少依据或期间发生调岗，未读取对应记录；结果仅含可证归属的数据。') for department in departments]
        if not employees:
            frappe.throw('此历史范围缺少可证部门归属，已拒绝读取对应记录；本人历史查询保持。',frappe.PermissionError)
    return employees
