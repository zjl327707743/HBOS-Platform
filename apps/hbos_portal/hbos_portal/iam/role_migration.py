"""Bounded, read-only old-source mapping. Never run from install/migrate hooks.

Candidates are review hints. Apply uses existing preview/save_assignment with
current source versions, current rights and strong proof; this module writes
neither rules nor associations. Rollback of the implementation uses its flag.
"""
from __future__ import annotations

import frappe
from hbos_portal.iam import guards,policy,role_access


def dry_run(employee_names):
    if not isinstance(employee_names,list) or not employee_names or len(employee_names)>200 or any(not isinstance(name,str) or not name for name in employee_names):
        frappe.throw('请显式提供1至200个员工主键。',frappe.ValidationError)
    items=[]
    for name in sorted(set(employee_names)):
        employee=frappe.db.get_value('Employee',name,['name','user_id','department','company','status'],as_dict=True,for_update=True)
        if not employee:frappe.throw('员工不存在。',frappe.ValidationError)
        guards.require_capability('iam.access.read',department=employee.department or None,company=employee.company,target_user=employee.user_id or None)
        sources=[]
        for kind,subject in [('User',employee.user_id),('Department',employee.department)]:
            doc=policy.get_policy(kind,subject,for_update=True) if subject else None
            if doc:
                rules=[dict(name=row.name,**policy.rule_dict(row)) for row in doc.rules]
                value=dict(subject_type=kind,subject_name=subject,name=doc.name,version=doc.version,enabled=doc.enabled,rules=rules)
                sources.append({**value,'source_hash':role_access.digest(value)})
        native=frappe.db.sql("select role from `tabHas Role` where parenttype='User' and parent=%s order by role for update",(employee.user_id,),as_dict=True) if employee.user_id else []
        native_roles=[row.role for row in native]
        attendance=[rule for source in sources for rule in source['rules'] if rule['app_id']=='attendance']
        constraints=[dict(source=source['name'],rule=row['name'],effect=row['effect'],operation=row['operation_id'],scope_type=row['scope_type'],scope_ref=row['scope_ref'],valid_from=row['valid_from'],valid_until=row['valid_until'],qualification_ref=row['qualification_ref'])
                     for source in sources for row in source['rules'] if row['app_id']=='attendance']
        simple=bool(attendance) and all(row['scope_type']=='SELF' and row['operation_id'] in {'app.enter','attendance.read'} and not row['qualification_ref'] for row in attendance)
        reasons=[]
        if not employee.user_id:reasons.append('账号未开通；不创建账号或分配角色。')
        if employee.status!='Active':reasons.append('员工失效；不扩大可见。')
        if set(native_roles)&{'HR User','HR Manager','System Manager'}:reasons.append('原生HR来源不能推断为具名公司管理员。')
        if attendance and not simple:reasons.append('含有具名范围、其他动作或资格；须逐项核对，不猜成更宽角色。')
        if any(not source['enabled'] for source in sources):reasons.append('保留原有禁用策略。')
        if any(row['effect']=='deny' for row in attendance):reasons.append('保留原有deny及临时禁用来源。')
        if any(row['valid_from'] or row['valid_until'] for row in attendance):reasons.append('保留原始期限与时钟语义，不延长已过期许可。')
        existing=role_access.assignments('Employee',name) if role_access.enabled() else []
        items.append(dict(employee_id=name,source_hash=role_access.digest(dict(employee=employee,sources=sources,native_roles=native_roles)),
            sources=sources,constraints=constraints,native_roles=native_roles,
            candidate_role='staff' if simple and employee.user_id and employee.status=='Active' and not set(native_roles)&{'HR User','HR Manager','System Manager'} else '',
            candidate_only=True,write_required=False,current_assignment_version=policy.value(existing[0],'version',0) if existing else 0,
            reasons=reasons or ['保持当前来源；无部门默认不构成deny。']))
    return dict(items=items,source_hash=role_access.digest(items),changed=False,apply_path='preview_assignment → save_assignment',rollback='关闭新角色开关，原Rule按当前合法版本继续求值；不全库回灌。')
