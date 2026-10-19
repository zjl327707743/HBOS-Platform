"""Published application roles: paired features/scopes, with legacy restrictions.

No positive Rule projection is created. Drafts are never an execution source.
"""
from __future__ import annotations

import hashlib
import json

import frappe

from hbos_portal.iam import policy

ROLE = 'HBOS IAM App Role'
RELEASE = 'HBOS IAM Role Release'
FEATURE = 'HBOS IAM Role Feature'
ASSIGNMENT = 'HBOS IAM Role Assignment'
SCOPE = 'HBOS IAM Role Scope'
BLUEPRINTS = {
    'staff': ('普通员工', 'SELF'),
    'clerk': ('部门考勤员', 'DEPARTMENT'),
    'admin': ('考勤管理员', 'COMPANY'),
}
# An entry becomes publishable only when its actual executor is integrated.
OPERATIONS = {
    'attendance.read': ('查看自己的考勤', 'self', 'SELF', True),
    'attendance.department.board.read': ('查看部门考勤面板', 'board', 'DEPARTMENT', True),
    'attendance.department.records.read': ('查看部门员工考勤', 'records', 'DEPARTMENT', True),
    'attendance.company.read': ('查看全公司考勤', 'company', 'COMPANY', True),
    'attendance.shift.read': ('查看班次与规则', 'schedule', 'COMPANY', True),
    'attendance.shift.manage': ('维护班次规则', 'schedule', 'COMPANY', True),
    'attendance.shift.status': ('停用班次规则', 'schedule', 'COMPANY', True),
    'attendance.shift.delete': ('删除班次规则', 'schedule', 'COMPANY', True),
    'attendance.schedule.read': ('查看员工排班', 'schedule', 'COMPANY', True),
    'attendance.schedule.bind': ('安排员工班次', 'schedule', 'COMPANY', True),
    'attendance.schedule.import': ('导入员工排班', 'import', 'COMPANY', False),
    'attendance.schedule.generate': ('生成轮班排班', 'rules', 'COMPANY', True),
    'attendance.import.preview': ('预览考勤导入', 'import', 'COMPANY', False),
    'attendance.import.execute': ('提交考勤导入', 'import', 'COMPANY', False),
    'attendance.import.monthly': ('导入月度考勤', 'import', 'COMPANY', False),
    'attendance.correction.create': ('登记考勤更正', 'correction', 'COMPANY', True),
    'attendance.correction.submit': ('提交考勤更正', 'correction', 'COMPANY', True),
    'attendance.correction.cancel': ('取消考勤更正', 'correction', 'COMPANY', True),
    'attendance.correction.amend': ('修订考勤更正', 'correction', 'COMPANY', True),
    'attendance.rules.recalculate': ('重新计算考勤', 'rules', 'COMPANY', True),
    'attendance.rules.manage': ('配置员工考勤规则', 'rules', 'COMPANY', True),
    'attendance.report.checkins.read': ('查看打卡流水报表', 'reports', 'DEPARTMENT', True),
    'attendance.report.results.read': ('查看考勤结果报表', 'reports', 'DEPARTMENT', True),
    'attendance.report.monthly.read': ('查看月度考勤汇总', 'reports', 'DEPARTMENT', True),
    'attendance.report.staging.read': ('查看月度对账暂存', 'reports', 'DEPARTMENT', False),
    'attendance.record.import_log.read': ('查看导入日志', 'reports', 'COMPANY', False),
    'attendance.record.leave.read': ('查看请假记录', 'reports', 'COMPANY', True),
    'attendance.record.overtime.read': ('查看加班记录', 'reports', 'COMPANY', True),
    'attendance.record.rest_leave.read': ('查看调休记录', 'reports', 'COMPANY', True),
    'attendance.export.monthly': ('导出月度考勤', 'export', 'COMPANY', True),
    'attendance.export.exceptions': ('导出考勤异常', 'export', 'COMPANY', True),
    'attendance.export.roster': ('导出班次人员表', 'export', 'COMPANY', True),
}
BINDINGS = {'SELF': 'SELF', 'DEPARTMENT': 'RESPONSIBLE_DEPARTMENTS', 'COMPANY': 'RESPONSIBLE_COMPANIES'}


def enabled():
    return policy.enabled_flag('hbos_iam_enabled') and policy.enabled_flag('hbos_iam_roles_enabled')


def require_available():
    if not enabled() or any(not frappe.db.exists('DocType', name) for name in (ROLE, RELEASE, FEATURE, ASSIGNMENT, SCOPE)):
        frappe.throw('角色实现尚未启用或模型未就绪。', frappe.PermissionError)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(',', ':')).encode()).hexdigest()


def feature_dict(row):
    return {key: policy.value(row, key) for key in ('operation_id', 'scope_binding')}


def scope_dict(row):
    return {'scope_type': policy.value(row, 'scope_type'), 'scope_ref': policy.value(row, 'scope_ref'), 'include_descendants': int(policy.value(row, 'include_descendants') or 0)}


def document(doctype, name):
    children = {ROLE: [('draft_features', FEATURE), ('management_scopes', SCOPE)],
                RELEASE: [('features', FEATURE)], ASSIGNMENT: [('responsibilities', SCOPE)]}
    if doctype not in children:
        raise ValueError('Unknown role parent')
    doc = frappe.get_doc(doctype, name, for_update=True)
    # Parent current-read alone does not refresh a pre-existing RR snapshot of
    # child rows. Every authorizing child set uses a matching locking read too.
    for field, table in children[doctype]:
        rows = frappe.db.sql(f'select * from `tab{table}` where parenttype=%s and parent=%s and parentfield=%s order by idx,name for update',
                             (doctype, name, field), as_dict=True)
        doc.set(field, rows)
    return doc


def registry(role_key=None):
    boundary = BLUEPRINTS.get(role_key, ('', 'COMPANY'))[1]
    result = []
    for operation, (title, group, minimum, integrated) in OPERATIONS.items():
        allowed = minimum == 'SELF' or boundary == 'COMPANY' or boundary == 'DEPARTMENT' and minimum == 'DEPARTMENT'
        binding = 'SELF' if minimum == 'SELF' else BINDINGS[boundary]
        result.append(dict(operation_id=operation, title=title, group=group, allowed=allowed,
                           scope_binding=binding, integrated=integrated,
                           reason='' if integrated else '此功能的角色范围接入尚未完成'))
    return result


def normalize_features(rows, role_key, *, publishing=False):
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except (ValueError, TypeError):
            rows = None
    if not isinstance(rows, list) or len(rows) > len(OPERATIONS) or role_key not in BLUEPRINTS:
        frappe.throw('角色功能清单无效。', frappe.ValidationError)
    choices = {row['operation_id']: row for row in registry(role_key)}
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'operation_id', 'scope_binding'}:
            frappe.throw('功能只接受已登记的操作与成对范围。', frappe.ValidationError)
        choice = choices.get(row.get('operation_id'))
        if not choice or not choice['allowed'] or row.get('scope_binding') != choice['scope_binding'] or row['operation_id'] in seen:
            frappe.throw('功能未知、重复或超过该角色范围上限。', frappe.PermissionError)
        if publishing and not choice['integrated']:
            frappe.throw('含有尚未完成范围接入的功能，不能发布。', frappe.PermissionError)
        seen.add(row['operation_id'])
        result.append(feature_dict(row))
    return sorted(result, key=lambda row: row['operation_id'])


def normalize_scopes(rows, boundary, companies):
    if rows is None and boundary == 'SELF':
        rows = []
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except (ValueError, TypeError):
            rows = None
    if not isinstance(rows, list) or len(rows) > 100:
        frappe.throw('请提交明确且有界的负责范围。', frappe.ValidationError)
    if boundary == 'SELF':
        if rows:
            frappe.throw('普通员工范围固定为本人。', frappe.PermissionError)
        return []
    if not rows or boundary == 'COMPANY' and len(rows) != 1:
        frappe.throw('请明确选择负责部门或一个负责公司。', frappe.ValidationError)
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - {'scope_type', 'scope_ref', 'include_descendants'}:
            frappe.throw('范围字段不在受控清单内。', frappe.ValidationError)
        if row.get('scope_type') != boundary or row.get('include_descendants') not in (None, 0, False) or not isinstance(row.get('scope_ref'), str) or not row['scope_ref']:
            frappe.throw('负责范围不符合角色上限，不默认包含下级。', frappe.PermissionError)
        ref = row['scope_ref']
        if boundary == 'COMPANY':
            company = frappe.db.get_value('Company', ref, 'name', for_update=True)
        else:
            department = frappe.db.get_value('Department', ref, ['name', 'company', 'disabled', 'is_group'], as_dict=True, for_update=True)
            company = policy.value(department, 'company')
            if not department or policy.value(department, 'disabled') or policy.value(department, 'is_group'):
                frappe.throw('负责部门已失效或需要重新核对。', frappe.PermissionError)
        if not company or company not in companies or (boundary, ref) in seen:
            frappe.throw('负责范围重复、失效或不属于角色管理域。', frappe.PermissionError)
        seen.add((boundary, ref))
        result.append(dict(scope_type=boundary, scope_ref=ref, include_descendants=0))
    return sorted(result, key=lambda row: row['scope_ref'])


def assignments(subject_type, subject_name, app_id='attendance'):
    rows = frappe.db.sql('select name from `tabHBOS IAM Role Assignment` where subject_type=%s and subject_name=%s and app_id=%s order by name for update', (subject_type, subject_name, app_id), as_dict=True)
    if app_id == 'attendance' and len(rows) > 1:
        frappe.throw('考勤角色关联存在冲突，已拒绝授权。', frappe.PermissionError)
    return [document(ASSIGNMENT, row.name) for row in rows]


def management_companies(role):
    rows = [scope_dict(row) for row in role.management_scopes]
    if not rows or any(row['scope_type'] != 'COMPANY' or not row['scope_ref'] or row['include_descendants'] for row in rows):
        frappe.throw('角色本身的管理范围未确认。', frappe.PermissionError)
    return sorted({row['scope_ref'] for row in rows})


_UNSET = object()


def preserves_legacy_personal(employee):
    """An unset new association never overwrites an existing independent source."""
    user=policy.value(employee,'user_id')
    if not user:return False
    rules,doc=policy._rules('User',user)
    stored=policy.value(doc,'rules',[]) if doc else []
    if any(policy.value(row,'app_id')=='attendance' and policy.value(row,'operation_id')!='app.enter' and not str(policy.value(row,'operation_id') or '').startswith('iam.') for row in stored):
        return True
    # Existing un-managed native HR remains on its original executor until an
    # explicit personal association opts it in. Old IAM management still wins.
    if doc or policy.get_policy('Department',policy.value(employee,'department'),for_update=True):
        return False
    native=frappe.db.sql("select role from `tabHas Role` where parenttype='User' and parent=%s order by role for update",(user,),as_dict=True)
    return bool({policy.value(row,'role') for row in native}&{'HR User','HR Manager','System Manager'})


def resolve(employee, app_id='attendance', *, own_override=_UNSET, default_override=_UNSET):
    """None means this subject is still on the exact legacy evaluator."""
    if not enabled() or app_id != 'attendance':
        return None
    require_available()
    own = assignments('Employee', policy.value(employee, 'name'), app_id)
    own = own[0] if own else None
    if own_override is not _UNSET:
        own = own_override
    if not own and preserves_legacy_personal(employee):
        return None
    inherited = None
    if not own or own.mode == 'FOLLOW_DEPARTMENT':
        department = policy.value(employee, 'department')
        inherited = assignments('Department', department, app_id) if department else []
        inherited = inherited[0] if inherited else None
        if default_override is not _UNSET:
            inherited = default_override
    selected = inherited if not own or own.mode == 'FOLLOW_DEPARTMENT' else own
    if not own and not selected:
        return None
    result = {'managed': True, 'assignment': policy.value(own, 'name') or policy.value(selected, 'name'),
              'assignment_version': policy.value(own, 'version', 0), 'default_version': policy.value(inherited, 'version', 0),
              'source_mode': 'department' if selected is inherited else 'direct', 'source_ref': policy.value(employee, 'department') if selected is inherited else policy.value(employee, 'name'),
              'role': None, 'release': None, 'features': [], 'responsibilities': [], 'reason': '尚未关联有效角色。'}
    if not selected or not selected.enabled or selected.mode != 'DIRECT' or not selected.role:
        return result
    if selected.review_required:
        return {**result, 'reason': '负责范围待复核。'}
    role = document(ROLE, selected.role)
    result.update(role=role.name, role_key=role.role_key, title=role.title, boundary_kind=role.boundary_kind)
    if own and not own.enabled:
        return {**result, 'reason': '个人角色安排尚未启用。'}
    if role.app_id != app_id or not role.enabled or not role.published_release:
        return {**result, 'reason': '角色未发布或已停用。'}
    if policy.value(employee, 'company') not in management_companies(role):
        return {**result, 'reason': '员工公司与角色管理域不一致，须重新核对。'}
    release = document(RELEASE, role.published_release)
    if release.role != role.name:
        frappe.throw('发布版本来源不一致，已拒绝授权。', frappe.PermissionError)
    try:
        scopes = normalize_scopes([scope_dict(row) for row in selected.responsibilities], role.boundary_kind, management_companies(role))
        features = normalize_features([feature_dict(row) for row in release.features], role.role_key, publishing=True)
        from hbos_portal.iam.role_models import release_hash
        mapping = json.loads(release.native_mapping_json or '[]')
        if mapping != [] or release.content_hash != release_hash(role.name, release.revision, features, mapping):
            return {**result, 'reason': '发布版本内容来源待复核。'}
    except (frappe.PermissionError, frappe.ValidationError):
        return {**result, 'reason': '角色功能或负责范围待复核。'}
    return {**result, 'release': release.name, 'published_revision': release.revision, 'content_hash': release.content_hash,
            'features': features, 'responsibilities': scopes, 'reason': ''}


def legacy_veto(employee, operation_id, scope_type, scope_ref):
    now = policy._now()
    company = frappe.db.get_value('Department', scope_ref, 'company', for_update=True) if scope_type == 'DEPARTMENT' else None
    for kind, name in [('User', policy.value(employee, 'user_id')), ('Department', policy.value(employee, 'department'))]:
        if not name:
            continue
        rules, doc = policy._rules(kind, name)
        if doc and not doc.enabled:
            return '已有权限安排尚未启用。'
        for row in rules:
            if row['app_id'] != 'attendance' or row['operation_id'] not in {'app.enter', operation_id} or not policy._matches(row, scope_type, scope_ref, company):
                continue
            if row['effect'] == 'deny' and policy.active(row, now):
                return '已有禁止或临时禁用仍然生效。'
            if row['effect'] == 'allow' and not policy.active(row, now):
                return '已有许可尚未生效、已过期或资格待确认。'
    return ''


def decide(employee, operation_id, scope_type, scope_ref, *, resolved=None, override_features=None):
    resolved = resolve(employee) if resolved is None else resolved
    if resolved is None:
        return None
    rejected = lambda reason: dict(allowed=False, reason=reason, source='角色安排', role=resolved.get('role'), release=resolved.get('release'))
    if resolved.get('reason'):
        return rejected(resolved['reason'])
    veto = legacy_veto(employee, operation_id, scope_type, scope_ref)
    if veto:
        return rejected(veto)
    features = resolved['features'] if override_features is None else override_features
    feature = next((row for row in features if row['operation_id'] == operation_id), None)
    if not feature:
        return rejected('当前已发布角色未包含此功能。')
    binding = feature['scope_binding']
    if binding == 'SELF':
        allowed = scope_type == 'SELF' and scope_ref == ''
    else:
        allowed = any(row['scope_type'] == scope_type and row['scope_ref'] == scope_ref for row in resolved['responsibilities'])
        if binding == 'RESPONSIBLE_COMPANIES' and scope_type == 'DEPARTMENT':
            company = frappe.db.get_value('Department', scope_ref, 'company', for_update=True)
            allowed = any(row['scope_type'] == 'COMPANY' and row['scope_ref'] == company for row in resolved['responsibilities'])
    return dict(allowed=allowed, reason='' if allowed else '此对象不在该角色的具名负责范围内。', source='部门默认角色' if resolved['source_mode'] == 'department' else '单独指定角色', role=resolved['role'], release=resolved['release'])


def revision_dependencies(user):
    if not enabled():
        return None
    rows = frappe.db.sql('select name,user_id,department,company,status from `tabEmployee` where user_id=%s order by name limit 2 for update', (user,), as_dict=True)
    if len(rows) != 1:
        return {'association': 'unavailable'}
    resolved = resolve(rows[0])
    return {key: resolved.get(key) for key in ('assignment', 'assignment_version', 'default_version', 'source_mode', 'source_ref', 'role', 'release', 'content_hash', 'features', 'responsibilities', 'reason')} if resolved is not None else None
