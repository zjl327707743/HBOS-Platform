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
_correction_cancel = ContextVar('attendance_role_correction_cancel', default=None)


class HistoricalEmployees(list):
    def __init__(self):
        super().__init__()
        self.coverage={'complete':True,'rejected_ranges':[]}


def check_fields(allowed):
    if set(getattr(frappe.local,'form_dict',{}) or {}) - set(allowed) - {'cmd'}:
        frappe.throw('此范围接口不接受额外员工、部门或身份参数。',frappe.PermissionError)


@contextmanager
def report_execution(key, employees, *, bound=None, date_from=None, date_to=None, coverage=None, include_leave=True):
    if key not in {'monthly','checkins','results'}:
        raise ValueError('Unintegrated scoped report')
    leave_names=None
    if key=='monthly' and include_leave:
        if bound is None or date_from is None or date_to is None:raise ValueError('Missing temporal report context')
        from hb_attendance_app.hbos_attendance.portal.record_lists import approved_sources
        leave_names,_,complete=approved_sources(bound,employees,'feishu-leave',dict(doctype='HBOS Leave Record',metadata_filters={'approval_status':'已通过'}),date_from,date_to)
        if not complete and coverage is not None:
            coverage.update(complete=False,rejected_ranges=[dict(date_from=str(date_from),date_to=str(date_to),reason='部分请假记录的完整期间归属缺少依据，未读取相应请假。')])
    token=_report.set(dict(key=key, employees=tuple(row.name for row in employees),departments={row.name:row.department for row in employees},leave_names=leave_names))
    try:
        yield
    finally:
        _report.reset(token)


def report_sql(query,*args,**kwargs):
    if _report.get() is not None:query=str(query).rstrip().rstrip(';')+' for update'
    return frappe.db.sql(query,*args,**kwargs)


def current_rows(doctype,**kwargs):
    allowed={'Employee','HBOS Shift Rule','HBOS Employee Shift','HBOS Employee Schedule','HBOS Attendance Policy Assignment','HBOS Leave Record','HBOS Rest Leave Record','HBOS Overtime Record'}
    if doctype not in allowed:raise ValueError('Unknown current-read source')
    # Use the native builder, predicates and escaping; only the read mode changes.
    query=frappe.db.get_all(doctype,run=False,**kwargs)
    return frappe.db.sql(str(query).rstrip().rstrip(';')+' for update',as_dict=True)


def report_predicate(alias, params):
    bound=_report.get()
    if bound is None:return None
    if alias not in {'a','ec','lr'}:raise ValueError('Unknown report source')
    params['iam_employees']=bound['employees'] or ('',)
    predicate=f'{alias}.employee in %(iam_employees)s'
    if alias=='lr':
        if bound.get('leave_names') is None:raise ValueError('Unproved leave source')
        params['iam_leave_names']=tuple(bound['leave_names']) or ('',)
        predicate+=' and lr.name in %(iam_leave_names)s'
    return predicate


def temporal_report_rows(rows):
    bound=_report.get()
    if bound is not None:
        for row in rows:
            employee=row.get('employee')
            if employee in bound['departments']:row['department']=bound['departments'][employee]
    return rows


def scoped_report_sources(sources):
    bound=_report.get()
    if bound is None:return False
    allowed={'monthly':{'Employee','Attendance','Employee Checkin','HBOS Leave Record'},
             'checkins':{'Employee','Employee Checkin','HBOS Shift Rule'},'results':{'Employee','Attendance','Employee Checkin'}}
    if not set(sources).issubset(allowed[bound['key']]):
        frappe.throw('该报表来源尚未接入角色范围。',frappe.PermissionError)
    return True


def context(operation, *, department=None, employee=None, rule=None):
    requested_department=department
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
    companies=[]
    for scope in resolved.get('responsibilities', []):
        if scope['scope_type']=='DEPARTMENT':
            if policy.evaluate(user,'attendance',operation,'DEPARTMENT',scope['scope_ref'])['allowed']:
                departments.append(scope['scope_ref'])
        elif policy.evaluate(user,'attendance',operation,'COMPANY',scope['scope_ref'])['allowed']:
            companies.append(scope['scope_ref'])
            departments.extend(row.name for row in frappe.db.sql('select name from `tabDepartment` where company=%s and disabled=0 order by name for update',(scope['scope_ref'],),as_dict=True))
    departments=sorted(set(departments))
    if not departments and not companies:
        frappe.throw('当前发布角色没有此功能的具名负责范围。',frappe.PermissionError)
    if rule:
        department=frappe.db.get_value('HBOS Shift Rule',rule,'department',for_update=True)
    if employee:
        department=frappe.db.get_value('Employee',employee,'department',for_update=True)
        company=frappe.db.get_value('Employee',employee,'company',for_update=True)
        if not company or department and company!=frappe.db.get_value('Department',department,'company',for_update=True):
            frappe.throw('员工与部门公司归属不一致，须先核对。',frappe.PermissionError)
        if company not in companies and department not in departments:
            frappe.throw('员工不在当前具名负责范围内。',frappe.PermissionError)
    if rule and not department or department and department not in departments and not (employee and company in companies):
        frappe.throw('该员工、班次或部门不在当前具名负责范围内。',frappe.PermissionError)
    label='部门：'+requested_department if requested_department else '、'.join(('公司：' if row['scope_type']=='COMPANY' else '负责部门：')+row['scope_ref'] for row in resolved['responsibilities'])
    return dict(user=user,departments=[requested_department] if requested_department else departments,companies=companies if not requested_department else [],operation=operation,scope_label=label)


def current_company_predicate(alias):
    if alias not in {'e','emp','tabEmployee'}:
        raise ValueError('Unknown employee source')
    return f'{alias}.company=(select company from `tabDepartment` iam_department where iam_department.name={alias}.department)'


def employee_predicate(bound,alias,params):
    if alias not in {'e','emp','tabEmployee'}:raise ValueError('Unknown employee source')
    params.update(iam_departments=tuple(bound['departments']) or ('',),iam_companies=tuple(bound.get('companies',[])) or ('',))
    return f"(({alias}.department in %(iam_departments)s or {alias}.company in %(iam_companies)s) and ({current_company_predicate(alias)} or (coalesce({alias}.department,'')='' and {alias}.company in %(iam_companies)s)))"


def attribution_allowed(bound,attribution):
    if not attribution:return False
    department,company=attribution
    if department and company!=frappe.db.get_value('Department',department,'company',for_update=True):return False
    return company in bound.get('companies',[]) or department in bound['departments']


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
    from frappe.utils import get_datetime, get_system_timezone
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    frozen=getattr(frappe,'conf',{}).get('hbos_iam_role_native_clock_zone')
    if not frozen or frozen != get_system_timezone():
        return None  # A Site clock change needs its own proven cutover plan.
    try:
        native_zone=ZoneInfo(frozen)
    except (ValueError,ZoneInfoNotFoundError):
        return None
    def native_time(value):
        return get_datetime(value).replace(tzinfo=native_zone).astimezone(ZoneInfo('Asia/Shanghai')).replace(tzinfo=None)
    if not frappe.get_meta('Employee').track_changes or not employee.creation or native_time(employee.creation)>start:
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
            stamp=native_time(version.creation)
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
    params={}
    predicate=employee_predicate(bound,'tabEmployee',params)
    names={row.name for row in frappe.db.sql('select name from `tabEmployee` where '+predicate+' order by name for update',params,as_dict=True)}
    # A JSON match is a candidate search only, never proof or authorization.
    versions=frappe.db.sql("select docname,data from `tabVersion` where ref_doctype='Employee' and (data like %s or data like %s) order by name for update",('%"department"%','%"company"%'),as_dict=True)
    for version in versions:
        try: changes=json.loads(version.data or '{}').get('changed',[])
        except (TypeError,ValueError): continue
        if any(isinstance(row,list) and len(row)==3 and (row[0]=='department' and any(department in row[1:] for department in departments) or row[0]=='company' and any(company in row[1:] for company in bound.get('companies',[]))) for row in changes):
            names.add(version.docname)
    employees=HistoricalEmployees()
    if not names:return employees
    for employee in frappe.db.sql('select name,employee_number,employee_name,department,company,status,creation from `tabEmployee` where name in %(names)s order by name for update',{'names':tuple(names)},as_dict=True):
        attribution=_historical_department(employee,start,end)
        if attribution is None:
            employees.coverage['complete']=False
            continue  # No business row/count for this employee is read.
        department,company=attribution
        if attribution_allowed(bound,attribution):
            stated=frappe.db.sql("select distinct company from `tabAttendance` where employee=%s and attendance_date between %s and %s and docstatus<2 and coalesce(company,'')<>'' for update",(employee.name,start.date(),end.date()),as_dict=True)
            if any(item.company!=company for item in stated):
                employees.coverage['complete']=False
                continue
            employees.append(frappe._dict({**employee,'department':department or '', 'company':company}))
    if not employees.coverage['complete']:
        employees.coverage['rejected_ranges']=[dict(scope=bound.get('scope_label','负责范围'),date_from=start.date().isoformat(),date_to=end.date().isoformat(),reason='部分历史归属缺少依据或期间发生调岗，未读取对应记录；结果仅含可证归属的数据。')]
        if not employees:
            frappe.throw('此历史范围缺少可证部门归属，已拒绝读取对应记录；本人历史查询保持。',frappe.PermissionError)
    return employees
