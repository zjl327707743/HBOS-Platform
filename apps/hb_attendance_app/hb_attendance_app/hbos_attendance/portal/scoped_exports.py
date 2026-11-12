"""Current-authority exports using existing renderers and native private File."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import frappe
from hbos_portal.api.iam_roles import _call
from hbos_portal.auth.accounts import no_store
from hbos_portal.auth.onboarding import serialize
from hbos_portal.iam import audit, guards, policy
from hb_attendance_app.hbos_attendance.portal import personal, role_scope, export_scope
from hb_attendance_app.hbos_attendance.report_data import _clean_filters

KINDS={key:'attendance.export.'+key for key in ('monthly','exceptions','roster')}


def _authorize(kind,filters):
    if kind not in KINDS:frappe.throw('导出类型未登记。',frappe.PermissionError)
    clean=_clean_filters(filters)
    if set(clean)-{'from_date','to_date','month','year','employee','department'}:
        frappe.throw('导出不接受身份、公司或外部服务选项。',frappe.PermissionError)
    bound=role_scope.context(KINDS[kind])
    if bound is None or len(bound.get('companies',[]))!=1:
        frappe.throw('导出需要当前角色的明确公司范围。',frappe.PermissionError)
    company=bound['companies'][0]
    if clean.get('department'):
        bound=role_scope.context(KINDS[kind],department=clean['department'])
    today=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    if kind=='roster':
        if any(clean.get(field) and clean[field]!=today for field in ('from_date','to_date')) or clean.get('month') or clean.get('year'):
            frappe.throw('班次人员表使用当前配置，请按今日日期导出。',frappe.ValidationError)
        clean.update(from_date=today,to_date=today)
        params={}
        predicate=role_scope.employee_predicate(bound,'tabEmployee',params)
        people=role_scope.HistoricalEmployees()
        people.extend(frappe.db.sql('select name,employee_name,employee_number,company,department from `tabEmployee` where status=\'Active\' and '+predicate+' order by name for update',params,as_dict=True))
        for row in people:row['department']=row.department or ''
    else:
        if clean.get('month') or clean.get('year'):
            from calendar import monthrange
            from datetime import date
            first=date(int(clean.get('year')),int(clean.get('month')),1)
            clean.update(from_date=first.isoformat(),to_date=first.replace(day=monthrange(first.year,first.month)[1]).isoformat())
            clean.pop('month',None);clean.pop('year',None)
        start,end,_,_=personal.bounded_request(clean.get('from_date'),clean.get('to_date') or today)
        clean.update(from_date=str(start),to_date=str(end))
        people=role_scope.historical_employees(bound,start,end)
    coverage=people.coverage
    if clean.get('employee'):
        if clean['employee'] not in {row.name for row in people}:
            frappe.throw('该员工不在本次可证导出范围内。',frappe.PermissionError)
        people=[row for row in people if row.name==clean['employee']]
    if not people or len(people)>1000:frappe.throw('请将导出限定到1至1000名员工。',frappe.ValidationError)
    # Roster uses all versions in the named company, including historical
    # disabled departments. Cross-company fixed references must never fall back
    # silently to a built-in label.
    departments=[row.name for row in frappe.db.sql('select name from `tabDepartment` where company=%s order by name for update',(company,),as_dict=True)]
    if kind=='roster':
        params=dict(names=tuple(row.name for row in people))
        refs=frappe.db.sql('select employee,rule_code,shift_rule from `tabHBOS Employee Shift` where employee in %(names)s order by name for update',params,as_dict=True)
        refs+=frappe.db.sql('select name as employee,hbos_fixed_shift_code as rule_code,hbos_fixed_shift as shift_rule from `tabEmployee` where name in %(names)s order by name for update',params,as_dict=True)
        for row in refs:
            if row.rule_code:
                rules=frappe.db.sql('select department from `tabHBOS Shift Rule` where rule_code=%s order by name for update',(row.rule_code,),as_dict=True)
            elif row.shift_rule:
                rules=frappe.db.sql('select department from `tabHBOS Shift Rule` where name=%s for update',(row.shift_rule,),as_dict=True)
            else:continue
            if not rules or any(rule.department not in departments for rule in rules):
                frappe.throw('员工班次来源跨公司或已失效，须先核对。',frappe.PermissionError)
    scope=bound['scope_label']
    clean.pop('department',None)  # Temporal roster already enforces it.
    manifest=dict(actor=policy.get_current_user(),kind=kind,source_operation=KINDS[kind],company=company,scope=scope,employee_names=[row.name for row in people],departments=departments,date_from=clean['from_date'],date_to=clean['to_date'],coverage=coverage)
    manifest['source_hash']=_source_hash(manifest,people)
    return manifest,people,clean


def _source_hash(manifest,people):
    from hbos_portal.iam.role_access import digest
    params=dict(names=tuple(manifest['employee_names']),start=manifest['date_from'],end=manifest['date_to'],departments=tuple(manifest['departments']) or ('',))
    sources={}
    specs={
        'Employee':('name,employee_name,employee_number,department,company,status,hbos_fixed_shift,hbos_fixed_shift_code','name in %(names)s'),
        'HBOS Attendance Policy Assignment':('name,employee,policy_type,enabled,effective_from,effective_to,remarks','employee in %(names)s'),
    }
    if manifest['kind']=='roster':
        specs.update({
            'HBOS Shift Rule':('name,rule_code,rule_name,department,shift_type,start_time,end_time,late_after,effective_from,status','department in %(departments)s'),
            'HBOS Employee Shift':('name,employee,rule_code,shift_rule,is_primary','employee in %(names)s'),
        })
    else:
        specs.update({
            'Attendance':('name,employee,company,attendance_date,status,shift,late_entry,early_exit,working_hours,docstatus','employee in %(names)s and attendance_date between %(start)s and %(end)s'),
            'Employee Checkin':('name,employee,time,log_type','employee in %(names)s and date(time) between %(start)s and %(end)s'),
        })
        if manifest['kind']=='monthly':
            from hb_attendance_app.hbos_attendance.portal.record_lists import approved_sources
            from frappe.utils import getdate
            ids,_,_=approved_sources(dict(companies=[manifest['company']],departments=manifest['departments']),people,'feishu-leave',dict(doctype='HBOS Leave Record',metadata_filters={'approval_status':'已通过'}),getdate(params['start']),getdate(params['end']))
            params['leaves']=tuple(ids) or ('',)
            specs['HBOS Leave Record']=('name,employee,department,start_date,end_date,leave_type,leave_days,approval_status','name in %(leaves)s')
    for doctype,(fields,predicate) in specs.items():
        sources[doctype]=frappe.db.sql(f'select {fields} from `tab{doctype}` where '+predicate+' order by name for update',params,as_dict=True)
    return digest(sources)


def _result(event,manifest):
    return dict(event_name=event,file_id=manifest['file_id'],scope=manifest['scope'],date_from=manifest['date_from'],date_to=manifest['date_to'],coverage=manifest['coverage'],download_url='/api/method/hb_attendance_app.hbos_attendance.portal.scoped_exports.download_export?event_name='+event)


def _file(manifest):
    file=frappe.get_doc('File',manifest['file_id'],for_update=True)
    if not file.is_private or file.owner!=policy.get_current_user():
        frappe.throw('文件不属于当前导出账号。',frappe.PermissionError)
    from hb_attendance_app.hbos_attendance.portal.artifacts import private_content
    content=private_content(file)
    if hashlib.sha256(content).hexdigest()!=manifest['file_hash']:
        frappe.throw('文件内容来源已变化，下载已拒绝。',frappe.PermissionError)
    return file,content


def _manifest(event_name):
    row=frappe.db.get_value(audit.EVENT,event_name,['name','actor','operation','after_json'],as_dict=True,for_update=True)
    if not row or row.actor!=policy.get_current_user() or row.operation not in KINDS.values():
        frappe.throw('导出文件不存在或当前账号无权下载。',frappe.PermissionError)
    try:
        manifest=json.loads(row.after_json)
        kind=next(key for key,value in KINDS.items() if value==row.operation)
        if manifest.get('source_operation')!=row.operation:raise ValueError()
        if manifest['settings'].get('from_date')!=manifest['date_from'] or manifest['settings'].get('to_date')!=manifest['date_to']:raise ValueError()
        current,_,_=_authorize(kind,manifest['settings'])
        if current['company']!=manifest['company'] or current['source_hash']!=manifest.get('source_hash') or not set(manifest['employee_names']).issubset(current['employee_names']):raise ValueError()
    except (KeyError,TypeError,ValueError,StopIteration,frappe.ValidationError):
        frappe.throw('员工范围或文件源数据已变化，下载已拒绝；请核对当前授权后重新生成。',frappe.PermissionError)
    return manifest


@frappe.whitelist(methods=['POST'])
def create_export(kind, filters, request_id, **kwargs):
    def run():
        no_store();guards.require_post()
        role_scope.check_fields({'kind','filters','request_id'})
        with serialize('attendance-export',policy.get_current_user()):
            manifest,people,clean=_authorize(kind,filters)
            payload=dict(kind=kind,settings=_clean_filters(filters))
            subject=people[0].name
            replay=audit.replay(request_id,KINDS[kind],'Employee',subject,payload)
            if replay is not None:
                event=frappe.db.get_value(audit.EVENT,{'request_id':request_id},'name',for_update=True)
                current=_manifest(event);_file(current)
                return {**_result(event,current),'replayed':True}
            from hb_attendance_app.hbos_attendance.policy_registry import employee_bound
            with employee_bound(manifest['employee_names']),export_scope.execution(manifest):
                if kind=='roster':
                    from hb_attendance_app.hbos_attendance.roster_export import export_shift_roster
                    url=export_shift_roster()
                else:
                    export=frappe.get_module('hb_attendance_app.hbos_attendance.report.月度考勤汇总.export')
                    renderer=export.export_xlsx if kind=='monthly' else export.export_exceptions
                    with role_scope.report_execution('monthly',people,bound=dict(companies=[manifest['company']],departments=manifest['departments']),date_from=clean['from_date'],date_to=clean['to_date'],coverage=manifest['coverage'],include_leave=kind=='monthly'):url=renderer(**clean)
            file=frappe.get_doc('File',{'file_url':url})
            content=file.get_content(encodings=())
            content=content.encode() if isinstance(content,str) else content
            manifest={key:value for key,value in manifest.items() if key not in {'departments','kind','actor'}}
            manifest.update(file_id=file.name,file_hash=hashlib.sha256(content).hexdigest(),settings=clean,changed=True)
            event=audit.append_event(request_id,KINDS[kind],'Employee',subject,payload,after=manifest)
            return _result(event.name,manifest)
    return _call(run)


@frappe.whitelist(methods=['GET'])
def download_export(event_name, **kwargs):
    no_store()
    role_scope.check_fields({'event_name'})
    manifest=_manifest(event_name)
    file,content=_file(manifest)
    frappe.local.response.update(type='download',filename=file.file_name,filecontent=content,display_content_as='attachment')
