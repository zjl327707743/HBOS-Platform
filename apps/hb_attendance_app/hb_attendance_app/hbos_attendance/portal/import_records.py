"""Read only native import batches with immutable company/source provenance."""
import json

import frappe
from frappe.utils import getdate
from hbos_portal.iam import policy
from hb_attendance_app.hbos_attendance.portal import imports,personal,role_scope
from hb_attendance_app.hbos_attendance.import_contract import MONTHLY_SUMMARY

READ='attendance.record.import_log.read'
STAGING='attendance.report.staging.read'
NOTE='仅包含来源和完整期间归属可核验的批次；未核验的历史批次未纳入。'


def _clean(filters,allowed):
    value=frappe.parse_json(filters) if isinstance(filters,str) else (filters or {})
    if not isinstance(value,dict) or set(value)-allowed:
        frappe.throw('导入记录筛选字段无效。',frappe.PermissionError)
    return {key:item for key,item in value.items() if item not in ('',None)}


def _approved(operation,clean):
    bound=role_scope.context(operation,department=clean.get('department'))
    if bound is None:return None
    start,end,_,_=personal.bounded_request(clean.get('from_date'),clean.get('to_date'))
    companies=set(bound.get('companies',[]))
    companies.update(frappe.db.get_value('Department',name,'company',for_update=True) for name in bound['departments'])
    params=dict(companies=tuple(sorted(companies-{'',None})) or ('',),start=str(start),end=str(end))
    rows=frappe.db.sql("""select name,operation,after_json from `tabHBOS IAM Change Event`
        where operation in ('attendance.import.preview','attendance.import.execute','attendance.import.monthly')
        and json_valid(after_json) and json_unquote(json_extract(after_json,'$.company')) in %(companies)s
        and json_unquote(json_extract(after_json,'$.date_from'))<=%(end)s
        and json_unquote(json_extract(after_json,'$.date_to'))>=%(start)s
        order by creation desc,name desc limit 1001 for update""",params,as_dict=True)
    if len(rows)>1000:frappe.throw('匹配批次超过单次核验上限，请缩小日期范围。',frappe.ValidationError)
    seen=set();approved=[]
    for row in rows:
        manifest=json.loads(row.after_json)
        name=manifest.get('log_name')
        if not name or name in seen:continue
        seen.add(name)
        if clean.get('import_log') and clean['import_log']!=name:continue
        if manifest.get('source_operation')!=row.operation:continue
        names=manifest.get('employee_names')
        if not isinstance(names,list) or not names or len(names)>200:continue
        # Native metadata only, followed by temporal proof, before business JSON.
        try:people=role_scope.historical_employees(bound,getdate(manifest['date_from']),getdate(manifest['date_to']))
        except frappe.PermissionError:continue
        allowed={person.name:person for person in people if person.name in names}
        if operation==READ and set(allowed)!=set(names):continue
        if clean.get('employee'):
            allowed={key:value for key,value in allowed.items() if key==clean['employee']}
        if not allowed:continue
        if imports._log_hash(name)!=manifest.get('log_hash'):continue
        approved.append((name,manifest,allowed))
    if clean.get('import_log') and not approved:
        frappe.throw('该批次不存在可核验的当前范围来源。',frappe.PermissionError)
    if clean.get('employee') and not any(clean['employee'] in people for _,_,people in approved):
        # A guessed employee never turns into an empty successful scope query.
        role_scope.context(operation,employee=clean['employee'])
    return bound,start,end,approved


def get_list(spec,filters,limit,start):
    if role_scope.context(READ) is None:return None
    def run():
        role_scope.check_fields({'key','filters','limit','start','fieldname'})
        clean=_clean(filters,{'from_date','to_date','import_type','import_status','import_log'})
        bound,date_from,date_to,approved=_approved(READ,clean)
        names=tuple(name for name,_,_ in approved) or ('',)
        params=dict(names=names);predicate='name in %(names)s'
        for field in spec['filters']:
            if clean.get(field):predicate+=f' and `{field}`=%({field})s';params[field]=clean[field]
        fields=','.join('`'+column['fieldname']+'`' for column in spec['columns'])
        rows=frappe.db.sql(f'select {fields} from `tab{imports.LOG}` where {predicate} order by creation desc,name desc for update',params,as_dict=True)
        return dict(key='import-log',doctype=imports.LOG,title=spec['title'],hint=NOTE,columns=spec['columns'],
            filter_fields=spec['filters'],rows=rows[start:start+limit],total=len(rows),limit=limit,start=start,
            scope=bound['scope_label'],date_from=str(date_from),date_to=str(date_to),coverage=dict(complete=False))
    return policy.current_read(run)


def filter_options(spec,fieldname,filters):
    if role_scope.context(READ) is None:return None
    if fieldname not in spec['filters']:frappe.throw('字段不可筛选。',frappe.ValidationError)
    # Same verified rows and predicates as the list, before de-duplication.
    role_scope.check_fields({'key','fieldname','filters'})
    result=get_list(spec,filters,1000,0)
    return [dict(value=value,label=value) for value in sorted({str(row[fieldname]) for row in result['rows'] if row.get(fieldname)})]


def staging(filters,limit,start):
    role_scope.check_fields({'filters','limit','start'})
    clean=_clean(filters,{'from_date','to_date','employee','department','import_log'})
    bound,date_from,date_to,approved=_approved(STAGING,clean)
    module=frappe.get_module('hb_attendance_app.hbos_attendance.report.hbos_月度汇总暂存（对账）.hbos_月度汇总暂存（对账）')
    from hb_attendance_app.hbos_attendance.api import EXEMPT_NUMS
    data=[]
    for name,manifest,people in approved:
        if manifest.get('mode')!='monthly' or manifest['source_operation']!='attendance.import.monthly':continue
        # JSON_TABLE evaluates the exact approved employee predicate in SQL.
        # Unapproved department records never cross the database boundary.
        records=frappe.db.sql("""select json_extract(l.monthly_summary_staging,concat('$.records[',j.ord-1,']')) as record
            from `tabHBOS Attendance Import Log` l,
            json_table(l.monthly_summary_staging,'$.records[*]' columns(
                ord for ordinality,employee varchar(140) path '$.employee')) j
            where l.name=%s and j.employee in %s for update""",(name,tuple(people)),as_dict=True)
        for item in records:
            record=json.loads(item.record)
            if record.get('employee_number') in EXEMPT_NUMS:continue
            employee=people[record['employee']]
            record['department']=employee.department
            data.append(dict(import_log=name,import_type=MONTHLY_SUMMARY,period_start=manifest['date_from'],period_end=manifest['date_to'],
                **{field:record.get(field) for field in ('employee','employee_name','employee_number','department','expected_days','actual_days','leave_hours','pay_hours','late_count','early_count','absent_days')},
                storage_note='月度汇总暂存；不写入打卡或考勤结果。'))
    return dict(report='staging',columns=module._columns(),data=data[start:start+limit],total=len(data),limit=limit,start=start,
        coverage=dict(complete=False,rejected_ranges=[dict(date_from=str(date_from),date_to=str(date_to),reason=NOTE)]))
