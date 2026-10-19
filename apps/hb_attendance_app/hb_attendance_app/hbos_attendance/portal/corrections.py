"""Bounded adapter for the installed HRMS Attendance Request lifecycle."""
from __future__ import annotations

from contextlib import contextmanager

import frappe

from hbos_portal.api.iam_roles import _call
from hbos_portal.auth.onboarding import serialize
from hbos_portal.iam import audit, guards, policy
from hb_attendance_app.hbos_attendance.portal import personal, role_scope

_cancel = role_scope._correction_cancel
FIELDS=('employee','company','from_date','to_date','half_day','half_day_date','reason','explanation','shift','include_holidays')


def _operation(action):
    if action not in {'create','submit','cancel','amend'}:
        frappe.throw('更正操作未登记。',frappe.PermissionError)
    return 'attendance.correction.'+action


def _employee(employee, action, start=None, end=None):
    bound=role_scope.context(_operation(action),employee=employee)
    if bound is None:
        frappe.throw('此角色更正入口尚未向当前账号开放。',frappe.PermissionError)
    row=frappe.db.get_value('Employee',employee,['name','employee_name','department','company','status','modified'],as_dict=True,for_update=True)
    if not row or row.status!='Active':
        frappe.throw('员工不存在、已失效或不在可管理范围内。',frappe.PermissionError)
    if start is not None:
        if employee not in {item.name for item in role_scope.historical_employees(bound,start,end)}:
            frappe.throw('此更正期间缺少员工在负责范围内的历史归属依据。',frappe.PermissionError)
        # HRMS selects these linked sources by Employee/date. Reject an
        # inconsistent native Company before its validators read or update it.
        predicates={
            'Attendance':'attendance_date between %(start)s and %(end)s and docstatus<2',
            'Leave Application':'from_date<=%(end)s and to_date>=%(start)s and docstatus=1',
            'Shift Assignment':'start_date<=%(end)s and (end_date>=%(start)s or end_date is null) and docstatus=1',
        }
        for doctype,predicate in predicates.items():
            if not frappe.db.has_column(doctype,'company'):continue
            linked=frappe.db.sql(f'select name,company from `tab{doctype}` where employee=%(employee)s and '+predicate+' order by name for update',dict(employee=employee,start=start,end=end),as_dict=True)
            if any(item.company and item.company!=row.company for item in linked):
                frappe.throw('已有业务记录与员工公司归属不一致，须先核对；本次未更正。',frappe.PermissionError)
    return row


def _request(name, action):
    row=frappe.db.get_value('Attendance Request',name,['name','employee','company','from_date','to_date','modified','docstatus'],as_dict=True,for_update=True)
    if not row:
        frappe.throw('更正申请不存在或无权操作。',frappe.PermissionError)
    start,end,_,_=personal.bounded_request(str(row.from_date),str(row.to_date))
    employee=_employee(row.employee,action,start,end)
    if row.company!=employee.company:
        frappe.throw('更正申请与员工公司归属不一致，须先核对。',frappe.PermissionError)
    return frappe.get_doc('Attendance Request',name,for_update=True),employee


def _dto(doc):
    return dict(name=doc.name,docstatus=doc.docstatus,modified=str(doc.modified),amended_from=doc.amended_from,**{key:doc.get(key) for key in FIELDS})


def _version(actual,expected):
    if str(actual)!=str(expected or ''):
        frappe.local.response['http_status_code']=409
        frappe.throw('员工或更正申请已变化，请重新核对。',frappe.ValidationError)


def _settings(raw,employee):
    raw=frappe.parse_json(raw) if isinstance(raw,str) else raw
    if not isinstance(raw,dict) or set(raw)-set(FIELDS) or raw.get('employee') not in (None,employee.name) or raw.get('company') not in (None,employee.company):
        frappe.throw('更正只接受当前员工的明确字段，不接受其他身份或公司。',frappe.PermissionError)
    if raw.get('reason') not in {'On Duty','Work From Home'} or not isinstance(raw.get('explanation'),str) or not 5<=len(raw['explanation'].strip())<=500:
        frappe.throw('请选择原生更正原因，并填写5至500字的事实说明。',frappe.ValidationError)
    for flag in ('half_day','include_holidays'):
        if raw.get(flag,0) not in (0,1,False,True):
            frappe.throw('更正选项格式无效。',frappe.ValidationError)
    start,end,_,_=personal.bounded_request(raw.get('from_date'),raw.get('to_date'))
    if (end-start).days>30:
        frappe.throw('一次更正最多31天，请按实际期间分别办理。',frappe.ValidationError)
    shift=raw.get('shift')
    if shift and not frappe.db.exists('Shift Assignment',{'employee':employee.name,'shift_type':shift,'docstatus':1,'start_date':['<=',start],'end_date':['>=',end]}):
        frappe.throw('所选班次不是该员工在此期间的原生排班。',frappe.PermissionError)
    return {key:raw.get(key) for key in FIELDS if key in raw and key not in {'employee','company'}} | {'employee':employee.name,'company':employee.company},start,end


@frappe.whitelist(methods=['GET'])
def list_correction_employees(action='create', search='', **kwargs):
    def run():
        role_scope.check_fields({'action','search'})
        bound=role_scope.context(_operation(action))
        if bound is None:
            frappe.throw('此更正功能未向当前账号开放。',frappe.PermissionError)
        if not isinstance(search,str) or len(search)>80:
            frappe.throw('查询内容过长。',frappe.ValidationError)
        return dict(items=frappe.db.sql("select name,employee_name,employee_number,department from `tabEmployee` where company=(select company from `tabDepartment` iam_department where iam_department.name=tabEmployee.department) and status='Active' and department in %(departments)s and (employee_name like %(search)s or employee_number like %(search)s) order by employee_number,name limit 50",{'departments':tuple(bound['departments']),'search':'%'+search+'%'},as_dict=True))
    return _call(run,read_only=True)


@frappe.whitelist(methods=['GET'])
def list_corrections(employee, action='create', **kwargs):
    def run():
        role_scope.check_fields({'employee','action'})
        row=_employee(employee,action)
        params={'employee':employee,'company':row.company,'state':{'create':0,'submit':0,'cancel':1,'amend':2}[action]}
        state="(docstatus=2 or (docstatus=0 and coalesce(amended_from,'')<>''))" if action=='amend' else 'docstatus=%(state)s'
        names=frappe.db.sql('select name from `tabAttendance Request` where employee=%(employee)s and company=%(company)s and '+state+' order by modified desc,name limit 50 for update',params,as_dict=True)
        return dict(items=[_dto(_request(item.name,action)[0]) for item in names])
    return _call(run,read_only=True)


@frappe.whitelist(methods=['GET'])
def get_correction_context(employee=None, request_name=None, action='create', **kwargs):
    def run():
        role_scope.check_fields({'employee','request_name','action'})
        if request_name:
            doc,row=_request(request_name,action)
            if employee and employee!=row.name:
                frappe.throw('员工与申请不一致。',frappe.PermissionError)
            return dict(employee={**row,'modified':str(row.modified)},request=_dto(doc))
        if action!='create':
            frappe.throw('请选择已有更正申请。',frappe.ValidationError)
        row=_employee(employee,action)
        return dict(employee={**row,'modified':str(row.modified)},request=None,reasons=[dict(value='On Duty',label='因公出勤'),dict(value='Work From Home',label='居家工作')])
    return _call(run,read_only=True)


@frappe.whitelist(methods=['POST'])
def create_correction(employee, settings, expected_employee_version, request_id, **kwargs):
    def run():
        role_scope.check_fields({'employee','settings','expected_employee_version','request_id'})
        guards.require_post()
        with serialize('attendance-correction',employee):
            row=_employee(employee,'create')
            values,start,end=_settings(settings,row)
            _employee(employee,'create',start,end)
            payload=dict(settings=values,expected_employee_version=expected_employee_version)
            replay=audit.replay(request_id,_operation('create'),'Employee',employee,payload)
            if replay is not None:return {**replay,'replayed':True}
            _version(row.modified,expected_employee_version)
            doc=frappe.get_doc(dict(doctype='Attendance Request',**values)).insert(ignore_permissions=True)
            result=dict(name=doc.name,employee=employee,docstatus=doc.docstatus,changed=True)
            audit.append_event(request_id,_operation('create'),'Employee',employee,payload,after=result)
            return result
    return _call(run)


@frappe.whitelist(methods=['POST'])
def update_correction(request_name, settings, expected_version, request_id, **kwargs):
    def run():
        role_scope.check_fields({'request_name','settings','expected_version','request_id'})
        guards.require_post()
        link=frappe.db.get_value('Attendance Request',request_name,['employee','amended_from'],as_dict=True,for_update=True)
        if not link:frappe.throw('申请不存在或无权操作。',frappe.PermissionError)
        action='amend' if link.amended_from else 'create'
        doc,row=_request(request_name,action)
        values,start,end=_settings(settings,row)
        _employee(row.name,action,start,end)
        with serialize('attendance-correction',row.name):
            payload=dict(name=request_name,settings=values,expected_version=expected_version)
            replay=audit.replay(request_id,_operation(action),'Employee',row.name,payload)
            if replay is not None:return {**replay,'replayed':True}
            _version(doc.modified,expected_version)
            if doc.docstatus!=0:
                frappe.throw('只有草稿可修改；已提交内容须先取消并创建修订。',frappe.ValidationError)
            doc.update(values)
            doc.save(ignore_permissions=True)
            result=dict(name=doc.name,employee=row.name,docstatus=doc.docstatus,changed=True)
            audit.append_event(request_id,_operation(action),'Employee',row.name,payload,after=result)
            return result
    return _call(run)


@contextmanager
def _cancel_scope(doc):
    token=_cancel.set((policy.get_current_user(),doc.name,doc.employee))
    try:yield
    finally:_cancel.reset(token)


def cancel_native_attendance(doc):
    """Return False outside the server's authorized native-cancel adapter."""
    if _cancel.get()!=(policy.get_current_user(),doc.name,doc.employee):return False
    from frappe.utils import getdate
    _employee(doc.employee,'cancel',getdate(doc.from_date),getdate(doc.to_date))
    rows=frappe.db.sql('select name,employee,company,attendance_date from `tabAttendance` where attendance_request=%s and docstatus=1 order by name for update',(doc.name,),as_dict=True)
    if any(row.employee!=doc.employee or row.company and row.company!=doc.company or not getdate(doc.from_date)<=getdate(row.attendance_date)<=getdate(doc.to_date) for row in rows):
        frappe.throw('申请关联的考勤归属不一致，已拒绝整个取消。',frappe.PermissionError)
    for row in rows:
        attendance=frappe.get_doc('Attendance',row.name,for_update=True)
        attendance.flags.ignore_permissions=True
        attendance.cancel()  # Native validation, workflow, status and comments.
    return True


@frappe.whitelist(methods=['POST'])
def transition_correction(request_name, action, expected_version, request_id, **kwargs):
    def run():
        role_scope.check_fields({'request_name','action','expected_version','request_id'})
        guards.require_post()
        if action not in {'submit','cancel','amend'}:
            frappe.throw('更正状态操作未登记。',frappe.PermissionError)
        doc,row=_request(request_name,action)
        with serialize('attendance-correction',row.name):
            payload=dict(name=request_name,action=action,expected_version=expected_version)
            replay=audit.replay(request_id,_operation(action),'Employee',row.name,payload)
            if replay is not None:return {**replay,'replayed':True}
            _version(doc.modified,expected_version)
            expected={'submit':0,'cancel':1,'amend':2}[action]
            if doc.docstatus!=expected:
                frappe.throw('请按原生草稿、提交、取消、修订顺序办理。',frappe.ValidationError)
            before=dict(name=doc.name,docstatus=doc.docstatus)
            doc.flags.ignore_permissions=True
            if action=='submit':doc.submit()
            elif action=='cancel':
                with _cancel_scope(doc):doc.cancel()
            else:
                original=doc
                doc=frappe.copy_doc(original)
                doc.docstatus=0
                doc.amended_from=original.name
                doc.insert(ignore_permissions=True)
            result=dict(name=doc.name,employee=row.name,docstatus=doc.docstatus,changed=True)
            audit.append_event(request_id,_operation(action),'Employee',row.name,payload,before=before,after=result)
            return result
    return _call(run)
