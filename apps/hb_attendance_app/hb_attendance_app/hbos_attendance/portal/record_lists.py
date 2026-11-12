"""Temporal executors for the existing employee-linked Attendance list specs."""
from __future__ import annotations

from datetime import datetime, time
import frappe
from hb_attendance_app.hbos_attendance.portal import personal, role_scope
from hb_attendance_app.hbos_attendance.report_data import _clean_filters

SPECS={
    'feishu-leave':('attendance.record.leave.read','start_date','end_date'),
    'feishu-overtime':('attendance.record.overtime.read','start_time','end_time'),
    'feishu-rest-leave':('attendance.record.rest_leave.read','start_date','end_date'),
}


def approved_sources(bound, people, key, spec, start, end):
    _,first,last=SPECS[key]
    by_name={row.name:row for row in people}
    params=dict(employees=tuple(by_name) or ('',),start=start,end=end)
    # Attribution metadata only. Full rows and counts are queried only after
    # their entire event interval and referenced overtime dates are proved.
    reference=',overtime_dates' if key=='feishu-rest-leave' else ''
    predicate=f'employee in %(employees)s and date({first})<=%(end)s and date({last})>=%(start)s'
    for field,value in spec.get('metadata_filters',{}).items():
        if field not in {'approval_status','verify_status'}:raise ValueError('Unknown metadata filter')
        predicate+=f' and {field}=%(meta_{field})s'
        params['meta_'+field]=value
    rows=frappe.db.sql(f'select name,employee,department,{first} as event_start,{last} as event_end'+reference+f' from `tab{spec["doctype"]}` where '+predicate+' order by name for update',params,as_dict=True)
    names=[];departments={};complete=getattr(people,'coverage',{'complete':True})['complete']
    from frappe.utils import get_datetime
    for row in rows:
        try:
            lower=get_datetime(row.event_start)
            upper=get_datetime(row.event_end)
            if first.endswith('_date'):upper=datetime.combine(upper.date(),time.max)
            attribution=role_scope._historical_department(by_name[row.employee],lower,upper)
            valid=lower<=upper and role_scope.attribution_allowed(bound,attribution) and (not row.department or row.department==attribution[0])
            if valid and key=='feishu-rest-leave' and row.overtime_dates:
                from hb_attendance_app.hbos_attendance.rest_leave import parse_overtime_dates
                references=parse_overtime_dates(row.overtime_dates,lower.year)
                if not references:valid=False
                for day in references:
                    day=get_datetime(str(day))
                    origin=role_scope._historical_department(by_name[row.employee],datetime.combine(day.date(),time.min),datetime.combine(day.date(),time.max))
                    if not role_scope.attribution_allowed(bound,origin):valid=False
        except (ValueError,TypeError):valid=False
        if valid:
            names.append(row.name);departments[row.name]=attribution[0]
        else:complete=False
    return names,departments,complete


def selection(key, spec, filters):
    operation,first,last=SPECS[key]
    clean=_clean_filters(filters)
    if set(clean)-set(spec['filters'])-{'from_date','to_date','employee','department'}:
        frappe.throw('记录列表不接受未登记筛选。',frappe.PermissionError)
    bound=role_scope.context(operation,department=clean.get('department'))
    if bound is None:return None
    from zoneinfo import ZoneInfo
    today=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    start,end,_,_=personal.bounded_request(clean.get('from_date'),clean.get('to_date') or today)
    people=role_scope.historical_employees(bound,start,end)
    by_name={row.name:row for row in people}
    if clean.get('employee'):
        if clean['employee'] not in by_name:
            frappe.throw('员工不在此期间的负责范围内。',frappe.PermissionError)
        by_name={clean['employee']:by_name[clean['employee']]}
    names,departments,complete=approved_sources(bound,list(by_name.values()),key,spec,start,end)
    complete=complete and people.coverage['complete']
    filters={field:value for field,value in clean.items() if field in spec['filters']}
    filters['name']=['in',names or ['']]
    return dict(filters=filters,departments=departments,scope=bound['scope_label'],date_from=str(start),date_to=str(end),coverage={'complete':complete,'rejected_ranges':[] if complete else [dict(date_from=str(start),date_to=str(end),reason='部分记录的历史或引用归属缺少依据，未读取这些记录。')]})


def get_list(key,spec,filters,limit,start):
    if getattr(frappe,'conf',{}).get('hbos_iam_roles_enabled') not in (True,1,'1'):return None
    from hbos_portal.iam import policy
    def run():
        role_scope.check_fields({'key','filters','limit','start'})
        selected=selection(key,spec,filters)
        if selected is None:return None
        fields=[column['fieldname'] for column in spec['columns']]
        rows=role_scope.current_rows(spec['doctype'],filters=selected['filters'],fields=fields,order_by=spec['order_by'],limit_page_length=limit,limit_start=start)
        for row in rows:row['department']=selected['departments'][row.name]
        total=len(role_scope.current_rows(spec['doctype'],filters=selected['filters'],fields=['name'],limit_page_length=0))
        role_scope.context(SPECS[key][0])
        return dict(key=key,doctype=spec['doctype'],title=spec['title'],hint=spec['hint'],columns=spec['columns'],filter_fields=spec['filters'],rows=rows,total=total,limit=limit,start=start,**{field:selected[field] for field in ('scope','date_from','date_to','coverage')})
    return policy.current_read(run)


def filter_options(key,spec,fieldname,filters):
    if getattr(frappe,'conf',{}).get('hbos_iam_roles_enabled') not in (True,1,'1'):return None
    from hbos_portal.iam import policy
    def run():
        role_scope.check_fields({'key','fieldname','filters'})
        if fieldname not in spec['filters']:frappe.throw('字段不可筛选。',frappe.ValidationError)
        selected=selection(key,spec,filters)
        if selected is None:return None
        rows=role_scope.current_rows(spec['doctype'],filters=selected['filters'],fields=[fieldname])
        values=sorted({str(row.get(fieldname)) for row in rows if row.get(fieldname)})[:200]
        return [dict(value=value,label=value) for value in values]
    return policy.current_read(run)
