"""Company-bounded adapters for the existing policy and calculation engines."""
from __future__ import annotations

from datetime import timedelta
import frappe
from hbos_portal.api.iam_roles import _call
from hbos_portal.auth.onboarding import serialize
from hbos_portal.iam import audit, guards, role_access
from hb_attendance_app.hbos_attendance.portal import role_scope, personal

OPERATIONS = {'generate':'attendance.schedule.generate','recalculate':'attendance.rules.recalculate'}
POLICY_FIELDS = ('policy_type','effective_from','effective_to','enabled','anchor_shift','group_name','remarks')


def _bound(action):
    operation='attendance.rules.manage' if action=='manage' else OPERATIONS.get(action)
    if not operation:
        frappe.throw('计算操作未登记。',frappe.PermissionError)
    bound=role_scope.context(operation)
    if bound is None:
        frappe.throw('此角色计算入口未向当前账号开放。',frappe.PermissionError)
    return bound


def _plan(action, employees, date_from, date_to):
    if action not in OPERATIONS:frappe.throw('计算操作未登记。',frappe.PermissionError)
    bound=_bound(action)
    names=frappe.parse_json(employees) if isinstance(employees,str) else employees
    if not isinstance(names,list) or not names or len(names)>200 or any(not isinstance(name,str) or not name for name in names) or len(set(names))!=len(names):
        frappe.throw('请选择1至200名范围内员工。',frappe.ValidationError)
    start,end,_,_=personal.bounded_request(date_from,date_to)
    if (end-start).days>30:
        frappe.throw('一次计算最多31天。',frappe.ValidationError)
    for name in names:
        role_scope.context(OPERATIONS[action],employee=name)
    # Pairing consumes one day of context on each side. Reject the selected
    # unknown range; unrelated unknown people never prevent this selection.
    pad=timedelta(days=1) if action=='recalculate' else timedelta(0)
    roster=role_scope.historical_employees(bound,start-pad,end+pad)
    selected=[row for row in roster if row.name in names and row.status=='Active']
    if len(selected)!=len(names):
        frappe.throw('所选员工期间存在无法证明的归属或已失效，未计算。',frappe.PermissionError)
    from hb_attendance_app.hbos_attendance.portal.record_lists import approved_sources
    for key,doctype,metadata in [('feishu-leave','HBOS Leave Record',{'approval_status':'已通过'}),('feishu-rest-leave','HBOS Rest Leave Record',{'approval_status':'已通过','verify_status':'已核实'})]:
        _,_,complete=approved_sources(bound,selected,key,dict(doctype=doctype,metadata_filters=metadata),start-pad,end+pad)
        if not complete:
            frappe.throw('计算来源的完整期间或引用归属缺少依据，须先核对；本次未计算。',frappe.PermissionError)
    params=dict(names=tuple(sorted(names)),start=start-pad,end=end+pad,departments=tuple(bound['departments']) or ('',))
    sources={}
    specs={
        'Employee':"name in %(names)s",
        'Employee Checkin':"employee in %(names)s and time>=%(start)s and time<date_add(%(end)s,interval 1 day)",
        'Attendance':"employee in %(names)s and attendance_date between %(start)s and %(end)s",
        'HBOS Employee Schedule':"employee in %(names)s and schedule_date between %(start)s and %(end)s",
        'HBOS Attendance Policy Assignment':"employee in %(names)s",
        'HBOS Employee Shift':"employee in %(names)s",
        'HBOS Shift Rule':"department in %(departments)s",
        'HBOS Leave Record':"employee in %(names)s and start_date<=%(end)s and end_date>=%(start)s and approval_status='已通过'",
        'HBOS Rest Leave Record':"employee in %(names)s and start_date<=%(end)s and end_date>=%(start)s and approval_status='已通过' and verify_status='已核实'",
    }
    for doctype,predicate in specs.items():
        fields={'Employee':'name,modified,department,company,status,employee_number,hbos_fixed_shift,hbos_fixed_shift_code',
                'Employee Checkin':'name,employee,time,log_type,hbos_terminal_sn,hbos_check_type'}.get(doctype,'*')
        sources[doctype]=frappe.db.sql(f'select {fields} from `tab{doctype}` where '+predicate+' order by name for update',params,as_dict=True)
    # Validate all fixed family references before the native engine resolves a
    # legacy pointer. No cross-company family can influence a result.
    allowed_rules={row.name for row in sources['HBOS Shift Rule']}
    codes={row.rule_code for row in sources['HBOS Shift Rule'] if row.rule_code}
    for item in sources['HBOS Employee Shift']+sources['Employee']:
        pointer=item.get('shift_rule') or item.get('hbos_fixed_shift')
        code=item.get('rule_code') or item.get('hbos_fixed_shift_code')
        if pointer and pointer not in allowed_rules or code and code not in codes:
            frappe.throw('员工班次引用不在当前公司范围内，须先核对。',frappe.PermissionError)
    if codes:
        family=frappe.db.sql('select department from `tabHBOS Shift Rule` where rule_code in %s order by name for update',(tuple(codes),),as_dict=True)
        if any(row.department not in bound['departments'] for row in family):
            frappe.throw('规则族跨越当前公司，须先核对。',frappe.PermissionError)
    for row in sources['Attendance']:
        if row.company and row.company!=next(item.company for item in selected if item.name==row.employee):
            frappe.throw('考勤记录公司不一致，须先核对。',frappe.PermissionError)
    fingerprint=role_access.digest(dict(action=action,employees=selected,start=start,end=end,sources=sources))
    return bound,selected,start,end,fingerprint


@frappe.whitelist(methods=['GET'])
def calculation_employees(action='recalculate', search='', **kwargs):
    def run():
        role_scope.check_fields({'action','search'})
        bound=_bound(action)
        if not isinstance(search,str) or len(search)>80:frappe.throw('查询内容过长。',frappe.ValidationError)
        params=dict(search='%'+search+'%')
        predicate=role_scope.employee_predicate(bound,'tabEmployee',params)
        return dict(scope=bound['scope_label'],items=frappe.db.sql(f"select name,employee_name,employee_number,department from `tabEmployee` where {predicate} and status='Active' and (employee_name like %(search)s or employee_number like %(search)s) order by employee_number,name limit 200",params,as_dict=True))
    return _call(run,read_only=True)


@frappe.whitelist(methods=['GET'])
def preview_calculation(action, employees, date_from, date_to, **kwargs):
    def run():
        role_scope.check_fields({'action','employees','date_from','date_to'})
        bound,rows,start,end,fingerprint=_plan(action,employees,date_from,date_to)
        return dict(scope=bound['scope_label'],employees=[dict(name=row.name,employee_name=row.employee_name) for row in rows],date_from=str(start),date_to=str(end),expected_inputs=fingerprint,warning='保留原生更正和人工考勤；仅重建所选范围的自动结果。' if action=='recalculate' else '仅生成所选员工与日期的轮转排班；人工、导入和历史排班优先。')
    return _call(run,read_only=True)


@frappe.whitelist(methods=['POST'])
def execute_calculation(action, employees, date_from, date_to, expected_inputs, request_id, **kwargs):
    def run():
        role_scope.check_fields({'action','employees','date_from','date_to','expected_inputs','request_id'})
        guards.require_post()
        with serialize('attendance-calculation','company'):
            # Replay rechecks every selected employee's current authority.
            bound,rows,start,end,fingerprint=_plan(action,employees,date_from,date_to)
            subject=rows[0].name
            payload=dict(action=action,employees=employees,date_from=date_from,date_to=date_to,expected_version=expected_inputs)
            replay=audit.replay(request_id,OPERATIONS[action],'Employee',subject,payload)
            if replay is not None:return {**replay,'replayed':True}
            if fingerprint!=expected_inputs:
                frappe.local.response['http_status_code']=409
                frappe.throw('员工、排班或计算来源已变化，请重新预览。',frappe.ValidationError)
            from hb_attendance_app.hbos_attendance.policy_registry import employee_bound
            with employee_bound([row.name for row in rows]):
                if action=='generate':
                    from hb_attendance_app.hbos_attendance.rotation_schedule import generate_rotation_schedule
                    result=generate_rotation_schedule(str(end),employees=[row.name for row in rows],start_date=str(start))
                else:
                    from hb_attendance_app.hbos_attendance.api import _regenerate_attendance_impl
                    result=_regenerate_attendance_impl(str(start),str(end),employee_scope=rows,rule_departments=bound['departments'])
            result={**result,'changed':True}
            audit.append_event(request_id,OPERATIONS[action],'Employee',subject,payload,after=result)
            return result
    return _call(run)


def _policy_employee(employee):
    bound=role_scope.context('attendance.rules.manage',employee=employee)
    if bound is None:frappe.throw('当前账号未开通规则配置。',frappe.PermissionError)
    return bound


@frappe.whitelist(methods=['GET'])
def get_employee_policies(employee, **kwargs):
    def run():
        role_scope.check_fields({'employee'})
        _policy_employee(employee)
        from hb_attendance_app.hbos_attendance.policy_registry import POLICY_TYPES
        rows=frappe.db.sql('select name,employee,modified,'+','.join(POLICY_FIELDS)+' from `tabHBOS Attendance Policy Assignment` where employee=%s order by effective_from,name for update',(employee,),as_dict=True)
        return dict(items=rows,policy_types=list(POLICY_TYPES))
    return _call(run,read_only=True)


@frappe.whitelist(methods=['POST'])
def save_employee_policy(employee, settings, expected_version, request_id, name=None, **kwargs):
    def run():
        role_scope.check_fields({'employee','settings','expected_version','request_id','name'})
        guards.require_post()
        with serialize('attendance-calculation','company'):
            _policy_employee(employee)
            values=frappe.parse_json(settings) if isinstance(settings,str) else settings
            if not isinstance(values,dict) or set(values)-set(POLICY_FIELDS):frappe.throw('规则配置字段无效。',frappe.PermissionError)
            payload=dict(name=name,employee=employee,settings=values,expected_version=expected_version)
            replay=audit.replay(request_id,'attendance.rules.manage','Employee',employee,payload)
            if replay is not None:return {**replay,'replayed':True}
            if not isinstance(values.get('remarks',''),str) or len(values.get('remarks',''))>500 or values.get('enabled',1) not in (0,1,False,True):
                frappe.throw('规则说明或启用状态无效。',frappe.ValidationError)
            if name:
                doc=frappe.get_doc('HBOS Attendance Policy Assignment',name,for_update=True)
                if doc.employee!=employee:frappe.throw('配置不属于所选员工。',frappe.PermissionError)
                if str(doc.modified)!=str(expected_version):
                    frappe.local.response['http_status_code']=409
                    frappe.throw('规则配置已变化，请刷新。',frappe.ValidationError)
                doc.update(values)
                doc.save(ignore_permissions=True)
            else:
                if expected_version not in (None,''):frappe.throw('新增规则不接受旧版本。',frappe.ValidationError)
                doc=frappe.get_doc(dict(doctype='HBOS Attendance Policy Assignment',employee=employee,source_type='MANUAL',**values)).insert(ignore_permissions=True)
            result=dict(name=doc.name,changed=True)
            audit.append_event(request_id,'attendance.rules.manage','Employee',employee,payload,after=result)
            return result
    return _call(run)
