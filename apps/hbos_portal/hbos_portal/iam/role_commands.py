"""Transactional role commands. No command commits its own transaction."""
from __future__ import annotations

import json

import frappe

from hbos_portal.auth import accounts
from hbos_portal.auth.onboarding import serialize
from hbos_portal.iam import audit, guards, policy, role_access as roles
from hbos_portal.iam.role_models import release_hash


def conflict(message='角色、使用者或范围已变化，请重新预览。'):
    frappe.local.response['http_status_code'] = 409
    frappe.throw(message, frappe.ValidationError)


def _version(value):
    try:
        if isinstance(value, bool):
            raise ValueError
        value = int(value)
        if not 0 <= value < 2 ** 31:
            raise ValueError
        return value
    except (ValueError, TypeError, OverflowError):
        frappe.throw('请提交有效的版本。', frappe.ValidationError)


def _role(app_id, role_key):
    roles.require_available()
    if app_id != 'attendance' or role_key not in roles.BLUEPRINTS:
        frappe.throw('应用或角色未注册。', frappe.PermissionError)
    rows = frappe.db.sql('select name from `tabHBOS IAM App Role` where app_id=%s and role_key=%s for update', (app_id, role_key), as_dict=True)
    if len(rows) != 1:
        frappe.throw('角色尚未初始化或存在冲突。', frappe.PermissionError)
    return roles.document(roles.ROLE, rows[0].name)


def _role_authority(role, operation):
    for company in roles.management_companies(role):
        guards.require_capability(operation, company=company, app_id=role.app_id)


def _role_dto(role):
    release = roles.document(roles.RELEASE, role.published_release) if role.published_release else None
    return dict(id=role.name, app_id=role.app_id, role_key=role.role_key, title=role.title,
                boundary_kind=role.boundary_kind, enabled=bool(role.enabled), draft_version=role.draft_version,
                draft_features=[roles.feature_dict(row) for row in role.draft_features],
                published_release=role.published_release or '', published_revision=policy.value(release, 'revision', 0),
                published_features=[roles.feature_dict(row) for row in release.features] if release else [],
                releases=frappe.db.sql('select name,revision,published_at from `tabHBOS IAM Role Release` where role=%s order by revision desc for update', (role.name,), as_dict=True),
                registry=roles.registry(role.role_key))


def list_roles(app_id):
    roles.require_available()
    guards.require_capability('iam.roles.read', app_id=app_id)
    result = []
    for key in roles.BLUEPRINTS:
        role = _role(app_id, key)
        try:
            _role_authority(role, 'iam.roles.read')
        except frappe.PermissionError:
            continue
        result.append(_role_dto(role))
    return {'items': result}


def get_role(app_id, role_key):
    role = _role(app_id, role_key)
    _role_authority(role, 'iam.roles.read')
    return _role_dto(role)


def _proof(*, consume=False):
    proof = accounts.require_proof(policy.get_current_user(), consume=consume)
    if proof['method'] != 'password':
        frappe.throw('请验证管理员本人密码及已有二次认证。', frappe.AuthenticationError)


def _event(request_id, operation, kind, name, payload, before, after, version):
    audit.append_event(request_id, operation, kind, name, payload, before=before, after=after, version=version)


def save_role_draft(app_id, role_key, features, expected_draft_version, request_id):
    guards.require_post()
    with serialize('iam-work', 'site'):
        role = _role(app_id, role_key)
        _role_authority(role, 'iam.roles.edit')
        features = roles.normalize_features(features, role_key)
        payload = dict(app_id=app_id, role_key=role_key, features=features, expected_draft_version=_version(expected_draft_version))
        replayed = audit.replay(request_id, 'role.draft', roles.ROLE, role.name, payload)
        if replayed is not None:
            return {**replayed, 'replayed': True}
        if role.draft_version != payload['expected_draft_version']:
            conflict()
        _proof()
        if features == [roles.feature_dict(row) for row in role.draft_features]:
            return {**_role_dto(role), 'changed': False}
        before = dict(draft_version=role.draft_version, published_revision=role.published_release or '')
        with guards.controlled_write():
            role.set('draft_features', features)
            role.draft_version += 1
            role.save(ignore_permissions=True)
            after = dict(role=role.name, role_key=role_key, draft_version=role.draft_version, published_revision=role.published_release or '', changed=True)
            _event(request_id, 'role.draft', roles.ROLE, role.name, payload, before, after, role.draft_version)
        return after


EMPLOYEE_FIELDS = 'name,user_id,employee_name,employee_number,department,company,status,modified'


def _employee(employee_id, operation, *, write=False):
    if not isinstance(employee_id, str) or not employee_id:
        frappe.throw('请选择已有员工。', frappe.ValidationError)
    rows = frappe.db.sql('select ' + EMPLOYEE_FIELDS + ' from `tabEmployee` where name=%s for update', (employee_id,), as_dict=True)
    if len(rows) != 1:
        frappe.throw('没有该员工的管理权限。', frappe.PermissionError)
    employee = rows[0]
    guards.require_capability(operation, department=employee.department, company=employee.company, app_id='attendance', target_user=employee.user_id if write else None)
    return employee


def _scope_authority(scopes, operation):
    for row in scopes:
        if row['scope_type'] == 'COMPANY':
            guards.require_capability(operation, company=row['scope_ref'], app_id='attendance')
        else:
            guards.require_capability(operation, department=row['scope_ref'], app_id='attendance')


def _member_context(employee):
    user = frappe.db.get_value('User', employee.user_id,
        ['name', 'enabled', 'modified', 'hbos_initial_password_pending', 'hbos_temporary_password', 'hbos_temporary_password_expires_at', 'hbos_password_generation'],
        as_dict=True, for_update=True) if employee.user_id else None
    policies = []
    now = policy._now()
    for kind, name in [('User', employee.user_id), ('Department', employee.department)]:
        if not name:
            continue
        rows, doc = policy._rules(kind, name)
        policies.append(dict(subject_type=kind, subject_name=name, version=policy.value(doc, 'version', 0), enabled=policy.value(doc, 'enabled', 1),
                             rules=[{**row, 'active': policy.active(row, now)} for row in rows if row['app_id'] == 'attendance']))
    native_roles=frappe.db.sql("select role from `tabHas Role` where parenttype='User' and parent=%s order by role for update", (employee.user_id,), as_dict=True) if employee.user_id else []
    return dict(employee=dict(employee), user=user, policies=policies, native_roles=native_roles, legacy_personal=roles.preserves_legacy_personal(employee),
                direct=[row.as_dict() for row in roles.assignments('Employee', employee.name)],
                default=[row.as_dict() for row in roles.assignments('Department', employee.department)] if employee.department else [])


def _effective(employee, resolved, *, features=None):
    if not employee.user_id:
        return {'allowed': False, 'reason': '账号未开通。', 'operations': []}
    from hbos_portal.iam.temporary_passwords import status
    users = frappe.db.sql('select name,enabled from `tabUser` where name=%s for update', (employee.user_id,), as_dict=True)
    associated = frappe.db.sql('select name from `tabEmployee` where user_id=%s order by name limit 2 for update', (employee.user_id,), as_dict=True)
    if len(users) != 1 or not users[0].enabled or employee.status != 'Active' or len(associated) != 1 or associated[0].name != employee.name:
        return {'allowed': False, 'reason': '账号被停用或员工关联待确认。', 'operations': []}
    if status(employee.user_id)['pending']:
        return {'allowed': False, 'reason': '须先完成首次改密。', 'operations': []}
    if resolved is None:
        decision = policy._evaluate(employee.user_id, 'attendance', 'attendance.read', 'SELF', '')
        native_hr = frappe.get_attr("hb_attendance_app.hbos_attendance.portal.permissions.legacy_hr")(employee.user_id)
        return {'allowed': decision['allowed'] or native_hr, 'reason': '沿用已有权限安排。', 'legacy_native_hr': native_hr,
                'operations': [dict(operation_id='attendance.read', scope_type='SELF', scope_ref='', allowed=decision['allowed'])]}
    entries = []
    candidates = resolved.get('features', []) if features is None else features
    for feature in candidates:
        scopes = [{'scope_type': 'SELF', 'scope_ref': ''}] if feature['scope_binding'] == 'SELF' else resolved.get('responsibilities', [])
        for scope in scopes:
            decision = roles.decide(employee, feature['operation_id'], scope['scope_type'], scope['scope_ref'], resolved=resolved, override_features=features)
            entries.append(dict(operation_id=feature['operation_id'], label=roles.OPERATIONS[feature['operation_id']][0], **scope, allowed=bool(decision and decision['allowed']), reason=(decision or {}).get('reason', '')))
    allowed = any(row['allowed'] for row in entries)
    return dict(allowed=allowed, reason='' if allowed else resolved.get('reason') or next((row['reason'] for row in entries if row['reason']), '已发布角色暂无可使用功能。'), operations=entries)


def _signature(access):
    rows = [(row['operation_id'], row['scope_type'], row['scope_ref']) for row in access['operations'] if row['allowed']]
    if access.get('legacy_native_hr'):
        rows.append(('legacy_native_hr', '', ''))
    return sorted(rows)


def _references(role):
    links = frappe.db.sql('select name,subject_type,subject_name from `tabHBOS IAM Role Assignment` where role=%s and app_id=%s and mode=%s order by subject_type,subject_name for update', (role.name, role.app_id, 'DIRECT'), as_dict=True)
    direct = {row.subject_name for row in links if row.subject_type == 'Employee'}
    departments = sorted({row.subject_name for row in links if row.subject_type == 'Department'})
    department_state = []
    for department in departments:
        department_state.append(frappe.db.get_value('Department', department, ['name', 'company', 'disabled', 'modified'], as_dict=True, for_update=True))
    clauses, params = [], {}
    if direct:
        clauses.append('name in %(direct)s'); params['direct'] = tuple(sorted(direct))
    if departments:
        clauses.append('department in %(departments)s'); params['departments'] = tuple(departments)
    candidates = frappe.db.sql('select ' + EMPLOYEE_FIELDS + ' from `tabEmployee` where ' + ' or '.join(clauses) + ' order by name for update', params, as_dict=True) if clauses else []
    members, contexts = [], []
    for employee in candidates:
        context = _member_context(employee)
        contexts.append(context)  # Includes excluded DIRECT/NONE rows to detect membership changes.
        own = context['direct'][0] if context['direct'] else None
        if employee.name in direct or employee.department in departments and (own and own['mode'] == 'FOLLOW_DEPARTMENT' or not own and not roles.preserves_legacy_personal(employee)):
            members.append(employee)
    if direct - {employee.name for employee in candidates}:
        frappe.throw('角色包含失效员工引用，须先核对。', frappe.PermissionError)
    return members, dict(links=links, departments=department_state, members=contexts)


def _authorize_members(role, members):
    for employee in members:
        guards.require_capability('iam.people.read', department=employee.department, company=employee.company, app_id='iam')
        guards.require_capability('iam.access.manage', department=employee.department, company=employee.company, app_id=role.app_id, target_user=employee.user_id or None)
        resolved = roles.resolve(employee)
        if resolved:
            _scope_authority(resolved.get('responsibilities', []), 'iam.roles.assign')


def preview_role_publish(app_id, role_key, expected_draft_version, expected_release):
    role = _role(app_id, role_key)
    _role_authority(role, 'iam.roles.publish')
    if _version(expected_draft_version) != role.draft_version or str(expected_release or '') != str(role.published_release or ''):
        conflict()
    features = roles.normalize_features([roles.feature_dict(row) for row in role.draft_features], role_key, publishing=True)
    members, context = _references(role)
    _authorize_members(role, members)
    people = []
    for employee in members:
        resolved = roles.resolve(employee)
        before = _effective(employee, resolved)
        management_department = bool(resolved and resolved.get('source_mode') == 'department'
                                     and resolved.get('role_key') in roles.MANAGEMENT_ROLE_KEYS)
        # A new release changes the accepted role content, so management-role
        # followers must re-confirm their admission before the published change
        # can take effect. Preview the eventual result but flag the recheck.
        after_resolved = roles.resolve(employee, admission_override=True) if management_department else resolved
        after = _effective(employee, after_resolved, features=features)
        people.append(dict(employee=employee.name, name=employee.employee_name, employee_number=employee.employee_number,
                           source_mode=(resolved or {}).get('source_mode', ''), before_allowed=before['allowed'], after_allowed=after['allowed'],
                           changed=_signature(before) != _signature(after), reason=after['reason'],
                           admission_recheck=management_department))
    revision = roles.digest(dict(role=role.as_dict(), references=context, actor_revision=policy.current_revision(), registry=roles.registry(role_key)))
    return dict(role=role.name, role_key=role_key, draft_version=role.draft_version, published_release=role.published_release or '',
                context_revision=revision, reference_count=len(people), effective_changed_count=sum(row['changed'] for row in people), members=people,
                features=features, changed=features != ([roles.feature_dict(row) for row in roles.document(roles.RELEASE, role.published_release).features] if role.published_release else None))


def publish_role(app_id, role_key, expected_draft_version, expected_release, context_revision, request_id):
    guards.require_post()
    payload = dict(app_id=app_id, role_key=role_key, expected_draft_version=_version(expected_draft_version), expected_release=str(expected_release or ''), context_revision=context_revision)
    with serialize('iam-work', 'site'):
        role = _role(app_id, role_key)
        _role_authority(role, 'iam.roles.publish')
        members, _ = _references(role)
        _authorize_members(role, members)
        replayed = audit.replay(request_id, 'role.publish', roles.ROLE, role.name, payload)
        if replayed is not None:
            return {**replayed, 'replayed': True}
        preview = preview_role_publish(app_id, role_key, expected_draft_version, expected_release)
        if not context_revision or context_revision != preview['context_revision']:
            conflict()
        _proof(consume=True)
        if not preview['changed']:
            return {'role': role.name, 'release': role.published_release, 'changed': False}
        current = roles.document(roles.RELEASE, role.published_release) if role.published_release else None
        revision = int(policy.value(current, 'revision', 0)) + 1
        from frappe.utils import now_datetime
        with guards.controlled_write():
            release = frappe.get_doc(dict(doctype=roles.RELEASE, role=role.name, revision=revision, features=preview['features'], native_mapping_json='[]',
                content_hash=release_hash(role.name, revision, preview['features'], []), source_draft_version=role.draft_version,
                published_by=policy.get_current_user(), published_at=now_datetime(), request_id=request_id)).insert(ignore_permissions=True)
            before = {'release': role.published_release or ''}
            role.published_release = release.name
            role.save(ignore_permissions=True)
            after = dict(role=role.name, role_key=role_key, release=release.name, published_revision=revision, draft_version=role.draft_version,
                         reference_count=preview['reference_count'], effective_changed_count=preview['effective_changed_count'], changed=True)
            _event(request_id, 'role.publish', roles.ROLE, role.name, payload, before, after, revision)
        return after


def _assignment_plan(employee_id, app_id, mode, role_key, responsibilities, expected_version):
    roles.require_available()
    if app_id != 'attendance' or mode not in {'FOLLOW_DEPARTMENT', 'DIRECT', 'NONE'}:
        frappe.throw('应用或角色来源无效。', frappe.ValidationError)
    employee = _employee(employee_id, 'iam.access.manage', write=True)
    guards.require_capability('iam.roles.assign', department=employee.department, company=employee.company, app_id=app_id, target_user=employee.user_id or None)
    own = roles.assignments('Employee', employee_id)
    old = own[0] if own else None
    if _version(expected_version) != int(policy.value(old, 'version', 0)):
        conflict()
    role = _role(app_id, role_key) if mode == 'DIRECT' else None
    if role:
        if not role.enabled or not role.published_release:
            frappe.throw('该角色尚未发布或已停用。', frappe.PermissionError)
        if employee.company not in roles.management_companies(role):
            frappe.throw('目标员工不属于该角色已确认的管理域。', frappe.PermissionError)
        scopes = roles.normalize_scopes(responsibilities, role.boundary_kind, roles.management_companies(role))
        _scope_authority(scopes, 'iam.roles.assign')
        _scope_authority(scopes, 'iam.access.manage')
    else:
        if role_key or responsibilities not in (None, [], '[]'):
            frappe.throw('跟随部门或不选角色时不得携带独立职责。', frappe.ValidationError)
        scopes = []
    proposed = frappe._dict(dict(name=policy.value(old, 'name'), app_id=app_id, mode=mode, role=policy.value(role, 'name'), responsibilities=scopes, enabled=1, version=int(policy.value(old, 'version', 0)) + 1, review_required=0))
    before_context = roles.resolve(employee)
    after_context = roles.resolve(employee, own_override=proposed)
    before, after = _effective(employee, before_context), _effective(employee, after_context)
    context = roles.digest(dict(employee=_member_context(employee), proposed=dict(proposed), role=role.as_dict() if role else None, resolved=after_context, actor_revision=policy.current_revision()))
    return dict(employee=employee, existing=old, proposed=proposed, before=before, after=after, context_revision=context,
                changed=not old or old.mode != mode or old.role != proposed.role or [roles.scope_dict(row) for row in old.responsibilities] != scopes)


def _assignment_preview(plan):
    return dict(employee=plan['employee'].name, version=int(policy.value(plan['existing'], 'version', 0)), context_revision=plan['context_revision'],
                selected_role=plan['proposed'].role, source_mode=plan['proposed'].mode, responsibilities=plan['proposed'].responsibilities,
                before=plan['before'], after=plan['after'], changed=plan['changed'])


def preview_assignment(employee_id, app_id, mode, role_key, responsibilities, expected_version):
    return _assignment_preview(_assignment_plan(employee_id, app_id, mode, role_key, responsibilities, expected_version))


def save_assignment(employee_id, app_id, mode, role_key, responsibilities, expected_version, context_revision, request_id):
    guards.require_post()
    with serialize('iam-work', 'site'):
        # Current rights are checked before replay, even after a successful command.
        employee = _employee(employee_id, 'iam.access.manage', write=True)
        guards.require_capability('iam.roles.assign', department=employee.department, company=employee.company, app_id=app_id, target_user=employee.user_id or None)
        if mode == 'DIRECT':
            selected = _role(app_id, role_key)
            if employee.company not in roles.management_companies(selected):
                frappe.throw('目标员工不属于该角色已确认的管理域。', frappe.PermissionError)
            scopes = roles.normalize_scopes(responsibilities, selected.boundary_kind, roles.management_companies(selected))
            _scope_authority(scopes, 'iam.roles.assign')
            _scope_authority(scopes, 'iam.access.manage')
        payload = dict(app_id=app_id, mode=mode, role_key=role_key, responsibilities=responsibilities, expected_version=_version(expected_version), context_revision=context_revision)
        replayed = audit.replay(request_id, 'role.assignment', 'Employee', employee_id, payload)
        if replayed is not None:
            return {**replayed, 'replayed': True}
        plan = _assignment_plan(employee_id, app_id, mode, role_key, responsibilities, expected_version)
        if not context_revision or context_revision != plan['context_revision']:
            conflict()
        _proof(consume=True)
        if not plan['changed']:
            return {**_assignment_preview(plan), 'changed': False}
        with guards.controlled_write():
            doc = plan['existing'] or frappe.get_doc(dict(doctype=roles.ASSIGNMENT, app_id=app_id, subject_type='Employee', subject_name=employee_id))
            doc.update({key: plan['proposed'][key] for key in ('mode', 'role', 'enabled', 'version', 'review_required')})
            doc.set('responsibilities', plan['proposed'].responsibilities)
            doc.save(ignore_permissions=True)
            after = dict(employee=employee_id, assignment=doc.name, version=doc.version, role=doc.role, source_mode=doc.mode, changed=True)
            _event(request_id, 'role.assignment', 'Employee', employee_id, payload, {'version': _version(expected_version)}, after, doc.version)
        return after


def get_assignment(employee_id, app_id):
    roles.require_available()
    if app_id != 'attendance':
        frappe.throw('本轮仅接入考勤角色。', frappe.PermissionError)
    employee = _employee(employee_id, 'iam.access.read')
    own = roles.assignments('Employee', employee_id, app_id)
    resolved = roles.resolve(employee, app_id)
    return dict(employee=employee_id, department=employee.department, company=employee.company, version=int(policy.value(own[0], 'version', 0)) if own else 0,
                mode=own[0].mode if own else 'LEGACY' if roles.preserves_legacy_personal(employee) else 'FOLLOW_DEPARTMENT', role_key=policy.value(resolved, 'role_key', ''),
                selected_role=resolved, effective_access=_effective(employee, resolved),
                responsibilities=[roles.scope_dict(row) for row in own[0].responsibilities] if own else [],
                # Read-only projection of the same published catalogue the department
                # page uses, so one picker component can show grantability honestly.
                roles=_department_role_catalog(employee.department, employee.company))


def _department_target(department):
    target = frappe.db.get_value('Department', department, ['name', 'company', 'disabled'], as_dict=True, for_update=True)
    if not target or target.disabled:
        frappe.throw('部门不存在或已失效。', frappe.PermissionError)
    return target


def _department_role(role_key):
    return _role('attendance', role_key) if role_key else None


def _department_scope(role, responsibilities):
    if not role:
        if responsibilities not in (None, [], '[]'):
            frappe.throw('不通过部门分配时不能携带角色范围。', frappe.ValidationError)
        return []
    return roles.normalize_scopes(responsibilities, role.boundary_kind, roles.management_companies(role))


def _admission_values(department, app_id, employee, role, release, scopes):
    return dict(department=department, app_id=app_id, employee=employee.name, role=role.name, role_key=role.role_key,
                responsibilities_json=json.dumps(roles._normalized_scope_rows(scopes), ensure_ascii=False, sort_keys=True),
                config_hash=roles.admission_hash(department, app_id, employee, role, release, scopes),
                admission_key=roles.admission_key(department, app_id, employee.name))


def _department_plan(department, app_id, role_key, responsibilities, expected_version):
    roles.require_available()
    if app_id != 'attendance' or role_key not in {'', 'staff', 'clerk', 'admin', None}:
        frappe.throw('部门默认只能选择已发布的考勤角色或不通过部门分配。', frappe.PermissionError)
    target = _department_target(department)
    guards.require_capability('iam.departments.manage', department=department, company=target.company, app_id=app_id)
    guards.require_capability('iam.roles.assign', department=department, company=target.company, app_id=app_id)
    existing = roles.assignments('Department', department, app_id)
    existing = existing[0] if existing else None
    if _version(expected_version) != int(policy.value(existing, 'version', 0)):
        conflict()
    role_key = role_key or ''
    role = _department_role(role_key)
    if role:
        if not role.enabled or not role.published_release:
            frappe.throw('该角色尚未发布或已停用。', frappe.PermissionError)
        if target.company not in roles.management_companies(role):
            frappe.throw('该角色不在本部门已确认的管理域内。', frappe.PermissionError)
        scopes = _department_scope(role, responsibilities)
        _scope_authority(scopes, 'iam.departments.manage')
        _scope_authority(scopes, 'iam.roles.assign')
        release = roles.document(roles.RELEASE, role.published_release)
        if release.role != role.name:
            frappe.throw('发布版本来源不一致，已拒绝授权。', frappe.PermissionError)
    else:
        scopes = _department_scope(None, responsibilities)
        release = None
    proposed = frappe._dict(dict(name=policy.value(existing, 'name'), app_id=app_id, mode='DIRECT' if role else 'NONE',
        role=policy.value(role, 'name'), enabled=1, version=int(policy.value(existing, 'version', 0)) + 1,
        review_required=0, responsibilities=scopes))
    employees = frappe.db.sql('select ' + EMPLOYEE_FIELDS + ' from `tabEmployee` where department=%s order by name for update', (department,), as_dict=True)
    people, contexts, personal, personal_preserved, pending, confirmed = [], [], [], 0, 0, 0
    for employee in employees:
        guards.require_capability('iam.people.read', department=employee.department, company=employee.company, app_id='iam')
        guards.require_capability('iam.access.manage', department=employee.department, company=employee.company, app_id=app_id, target_user=employee.user_id or None)
        context = _member_context(employee)
        contexts.append(context)
        own = context['direct'][0] if context['direct'] else None
        if own and own['mode'] != 'FOLLOW_DEPARTMENT' or not own and roles.preserves_legacy_personal(employee):
            personal_preserved += 1
            personal.append(dict(employee=employee.name, name=employee.employee_name, employee_number=employee.employee_number,
                                 mode=(own or {}).get('mode') or ('LEGACY' if not own else 'NONE'),
                                 reason='个人单独设置或既有安排保持不变'))
            continue
        before = _effective(employee, roles.resolve(employee))
        admission_state, admission_hash = 'AUTO', ''
        if role and role.role_key in roles.MANAGEMENT_ROLE_KEYS:
            admission_hash = roles.admission_hash(department, app_id, employee, role, release, scopes)
            row = roles.admission_row(department, app_id, employee.name)
            admission_state = 'CONFIRMED' if row and row.get('status') == 'CONFIRMED' and row.get('config_hash') == admission_hash else 'PENDING'
            if admission_state == 'CONFIRMED':
                confirmed += 1
            else:
                pending += 1
            after_context = roles.resolve(employee, default_override=proposed, admission_override=True)
        else:
            after_context = roles.resolve(employee, default_override=proposed)
        after = _effective(employee, after_context)
        people.append(dict(employee=employee.name, name=employee.employee_name, employee_number=employee.employee_number,
                           company=employee.company, department=employee.department,
                           admission_state=admission_state, admission_hash=admission_hash,
                           before_allowed=before['allowed'], after_allowed=after['allowed'],
                           before_operations=_signature(before), after_operations=_signature(after),
                           changed=_signature(before) != _signature(after),
                           reason=after['reason'] if not after['allowed'] else ''))
    context_revision = roles.digest(dict(
        target=target, existing=existing.as_dict() if existing else None, members=contexts,
        proposed=dict(proposed), role=role.as_dict() if role else None,
        release=release.as_dict() if release else None, personal=personal,
        actor_revision=policy.current_revision()))
    return dict(target=target, existing=existing, proposed=proposed, role=role, release=release, scopes=scopes,
                context_revision=context_revision, reference_count=len(people),
                effective_changed_count=sum(row['changed'] for row in people),
                personal_preserved=personal_preserved, pending_count=pending, confirmed_count=confirmed,
                members=people, personal=personal,
                changed=not existing or existing.mode != proposed.mode or existing.role != proposed.role
                or [roles.scope_dict(row) for row in existing.responsibilities] != scopes)


def _department_preview(plan):
    return {key: plan[key] for key in ('context_revision', 'reference_count', 'effective_changed_count', 'personal_preserved',
                                        'pending_count', 'confirmed_count', 'members', 'personal', 'changed')} | {
        'department': plan['target'].name, 'version': int(policy.value(plan['existing'], 'version', 0)),
        'role_key': policy.value(plan['role'], 'role_key', '') if plan['role'] else '',
        'selected_role': policy.value(plan['role'], 'name', ''),
        'responsibilities': [roles.scope_dict(row) for row in plan['scopes']]}


def preview_department_role(department, app_id, expected_version, role_key='', responsibilities=None):
    return _department_preview(_department_plan(department, app_id, role_key, responsibilities, expected_version))


def _apply_department_admissions(plan):
    """Persist pending/revoked admission rows inside the department-save transaction."""
    department, app_id = plan['target'].name, 'attendance'
    role = plan['role']
    managed = bool(role and role.role_key in roles.MANAGEMENT_ROLE_KEYS)
    rows = frappe.db.sql('select name,employee,status,version from `tab' + roles.ADMISSION + '` where department=%s and app_id=%s order by name for update',
                         (department, app_id), as_dict=True)
    by_employee = {row.employee: row for row in rows}
    followers = {member['employee']: member for member in plan['members']} if managed else {}
    changes = []
    from frappe.utils import now_datetime
    user = policy.get_current_user()
    for employee_name, member in followers.items():
        if member['admission_state'] == 'CONFIRMED':
            continue
        row = by_employee.get(employee_name)
        values = _admission_values(department, app_id, _employee_context_placeholder(employee_name),
                                   role, plan['release'], plan['scopes'])
        if row:
            doc = frappe.get_doc(roles.ADMISSION, row.name, for_update=True)
            doc.update({key: values[key] for key in ('role', 'role_key', 'responsibilities_json', 'config_hash')})
            doc.status = 'PENDING'
            doc.version = int(row.version) + 1
            doc.confirmed_by = None
            doc.confirmed_at = None
            doc.revoked_by = None
            doc.revoked_at = None
            doc.reason = '部门管理角色配置变化，待重新确认'
            doc.save(ignore_permissions=True)
            changes.append({'employee': employee_name, 'action': 'pending_updated', 'version': doc.version})
        else:
            doc = frappe.get_doc(dict(doctype=roles.ADMISSION, status='PENDING', version=1,
                                      reason='部门管理角色待确认', **values)).insert(ignore_permissions=True)
            changes.append({'employee': employee_name, 'action': 'pending_created', 'version': doc.version})
    for employee_name, row in by_employee.items():
        if employee_name in followers and row.status != 'REVOKED':
            continue
        if row.status == 'REVOKED':
            continue
        doc = frappe.get_doc(roles.ADMISSION, row.name, for_update=True)
        doc.status = 'REVOKED'
        doc.version = int(row.version) + 1
        doc.revoked_by = user
        doc.revoked_at = now_datetime()
        doc.reason = '部门默认已调整或成员不再跟随'
        doc.save(ignore_permissions=True)
        changes.append({'employee': employee_name, 'action': 'revoked', 'version': doc.version})
    return changes


def _employee_context_placeholder(employee_name):
    # Validators/values only need stable employee identity; read it directly here.
    employee = frappe.db.get_value('Employee', employee_name,
        ['name', 'user_id', 'department', 'company', 'status', 'modified', 'employee_name', 'employee_number'],
        as_dict=True, for_update=True)
    if not employee:
        frappe.throw('部门成员已变化，请重新预览。', frappe.PermissionError)
    return employee


def save_department_role(department, app_id, expected_version, context_revision, request_id, role_key='', responsibilities=None):
    guards.require_post()
    with serialize('iam-work', 'site'):
        guards.require_capability('iam.departments.manage', department=department, app_id=app_id)
        guards.require_capability('iam.roles.assign', department=department, app_id=app_id)
        target = _department_target(department)
        role = _department_role(role_key or '')
        if role:
            if not role.enabled or not role.published_release:
                frappe.throw('该角色尚未发布或已停用。', frappe.PermissionError)
            if target.company not in roles.management_companies(role):
                frappe.throw('该角色不在本部门已确认的管理域内。', frappe.PermissionError)
            scopes = _department_scope(role, responsibilities)
        else:
            scopes = []
        payload = dict(app_id=app_id, role_key=role_key or '', responsibilities=scopes,
                       expected_version=_version(expected_version))
        replayed = audit.replay(request_id, 'role.department_default', 'Department', department, payload)
        if replayed is not None:
            current = roles.assignments('Department', department, app_id)
            _department_plan(department, app_id, role_key, responsibilities, current[0].version if current else 0)
            return {**replayed, 'replayed': True}
        plan = _department_plan(department, app_id, role_key, responsibilities, expected_version)
        if not context_revision or context_revision != plan['context_revision']:
            conflict()
        _proof(consume=True)
        if not plan['changed']:
            return {**_department_preview(plan), 'changed': False}
        with guards.controlled_write():
            doc = plan['existing'] or frappe.get_doc(dict(doctype=roles.ASSIGNMENT, app_id=app_id, subject_type='Department', subject_name=department))
            doc.update({key: plan['proposed'][key] for key in ('mode', 'role', 'enabled', 'version', 'review_required')})
            doc.set('responsibilities', plan['proposed'].responsibilities)
            doc.save(ignore_permissions=True)
            admission_changes = _apply_department_admissions(plan)
            after = dict(department=department, assignment=doc.name, role=doc.role, source_mode=doc.mode, version=doc.version,
                         changed=True, role_key=policy.value(plan['role'], 'role_key', ''),
                         responsibilities=scopes, reference_count=plan['reference_count'],
                         effective_changed_count=plan['effective_changed_count'], pending_count=plan['pending_count'],
                         confirmed_count=plan['confirmed_count'], admission_changes=admission_changes)
            _event(request_id, 'role.department_default', 'Department', department, payload, {'version': _version(expected_version)}, after, doc.version)
        return after


def _department_role_catalog(department, company):
    catalog = []
    for key, (title, boundary) in roles.BLUEPRINTS.items():
        item = {'role_key': key, 'title': title, 'boundary_kind': boundary, 'grantable': False, 'reason': '',
                'published_revision': 0}
        try:
            role = _role('attendance', key)
            release = roles.document(roles.RELEASE, role.published_release) if role.published_release else None
            item['published_revision'] = int(policy.value(release, 'revision', 0))
        except frappe.PermissionError:
            item['reason'] = '该角色尚未初始化或当前不可读取。'
            catalog.append(item)
            continue
        if not role.enabled:
            item['reason'] = '角色已停用，暂不能授予。'
        elif not role.published_release:
            item['reason'] = '角色尚未发布，暂不能授予。'
        elif company not in roles.management_companies(role):
            item['reason'] = '该角色不在本部门公司管理域内。'
        else:
            try:
                _role_authority(role, 'iam.roles.assign')
                guards.require_capability('iam.roles.assign', department=department, company=company, app_id='attendance')
                item['grantable'] = True
            except frappe.PermissionError:
                item['reason'] = '当前账号没有授予这个角色所需的管理范围。'
        catalog.append(item)
    return catalog


def get_department_role(department, app_id):
    roles.require_available()
    if app_id != 'attendance':
        frappe.throw('本轮仅接入考勤角色。', frappe.PermissionError)
    guards.require_capability('iam.access.read', department=department, app_id=app_id)
    target = frappe.db.get_value('Department', department, ['name', 'company', 'disabled'], as_dict=True)
    current = roles.assignments('Department', department, app_id)
    current = current[0] if current else None
    role = roles.document(roles.ROLE, current.role) if current and current.role else None
    admissions = {'pending': 0, 'confirmed': 0, 'revoked': 0}
    if frappe.db.exists('DocType', roles.ADMISSION):
        for row in frappe.db.sql('select status,count(*) as total from `tab' + roles.ADMISSION + '` where department=%s and app_id=%s group by status',
                                 (department, app_id), as_dict=True):
            if row.status.lower() in admissions:
                admissions[row.status.lower()] = int(row.total)
    return dict(department=department, version=int(policy.value(current, 'version', 0)),
                role_key=policy.value(role, 'role_key', '') if current and current.mode == 'DIRECT' else '',
                responsibilities=[roles.scope_dict(row) for row in current.responsibilities] if current else [],
                has_role_default=current is not None,
                selected_role=policy.value(role, 'name', '') if role else '',
                roles=_department_role_catalog(department, policy.value(target, 'company')) if target else [],
                admissions=admissions)


def _admission_plan(department, app_id, employee_id, expected_version, action):
    roles.require_available()
    if app_id != 'attendance' or action not in {'confirm', 'revoke'}:
        frappe.throw('准入操作无效。', frappe.ValidationError)
    department_row = _department_target(department)
    current = roles.assignments('Department', department, app_id)
    current = current[0] if current else None
    if not current or current.mode != 'DIRECT' or not current.role:
        frappe.throw('该部门当前没有可逐人确认的管理型角色。', frappe.PermissionError)
    role = roles.document(roles.ROLE, current.role)
    if role.role_key not in roles.MANAGEMENT_ROLE_KEYS:
        frappe.throw('当前部门默认不是管理型角色，无需逐人准入确认。', frappe.PermissionError)
    if not role.enabled or not role.published_release:
        frappe.throw('该角色尚未发布或已停用。', frappe.PermissionError)
    release = roles.document(roles.RELEASE, role.published_release)
    scopes = roles.normalize_scopes([roles.scope_dict(row) for row in current.responsibilities],
                                    role.boundary_kind, roles.management_companies(role))
    employee = _employee(employee_id, 'iam.access.manage', write=True)
    if employee.department != department:
        frappe.throw('该员工已不在本部门，不能确认此部门角色。', frappe.PermissionError)
    guards.require_capability('iam.departments.manage', department=department, company=department_row.company, app_id=app_id)
    guards.require_capability('iam.roles.assign', department=department, company=department_row.company, app_id=app_id)
    _scope_authority(scopes, 'iam.roles.assign')
    _scope_authority(scopes, 'iam.departments.manage')
    own = roles.assignments('Employee', employee.name, app_id)
    own = own[0] if own else None
    if own and own.mode != 'FOLLOW_DEPARTMENT':
        frappe.throw('该员工使用个人单独设置或不安排角色，不继承部门管理角色。', frappe.PermissionError)
    if not own and roles.preserves_legacy_personal(employee):
        frappe.throw('该员工仍有既有独立安排，须先核对个人例外。', frappe.PermissionError)
    if _version(expected_version) != int(policy.value(current, 'version', 0)):
        conflict()
    row = roles.admission_row(department, app_id, employee.name, for_update=True)
    expected_hash = roles.admission_hash(department, app_id, employee, role, release, scopes)
    confirmed = bool(row and row.get('status') == 'CONFIRMED' and row.get('config_hash') == expected_hash)
    status = str(policy.value(row, 'status', 'NONE') or 'NONE').upper()
    before = _effective(employee, roles.resolve(employee))
    after = _effective(employee, roles.resolve(employee, default_override=current, admission_override=action == 'confirm'))
    context_revision = roles.digest(dict(
        department=department, app_id=app_id, assignment=current.as_dict(), role=role.as_dict(), release=release.as_dict(),
        responsibilities=scopes, employee=_member_context(employee), admission=row, expected_hash=expected_hash,
        action=action, actor_revision=policy.current_revision()))
    return dict(department=department, app_id=app_id, employee=employee.name, employee_record=employee,
                employee_name=employee.employee_name,
                employee_number=employee.employee_number, role=role.name, role_key=role.role_key,
                responsibilities=scopes, assignment_version=int(policy.value(current, 'version', 0)),
                admission_status=status, admission_hash=expected_hash, confirmed=confirmed,
                expected_hash=expected_hash, action=action,
                can_confirm=action == 'confirm' and not confirmed,
                can_revoke=action == 'revoke' and bool(row and row.get('status') != 'REVOKED'),
                duplicate_confirm=action == 'confirm' and confirmed,
                row=row, before=before, after=after,
                changed=(action == 'confirm' and not confirmed) or (action == 'revoke' and bool(row and row.get('status') != 'REVOKED')),
                context_revision=context_revision)


def preview_department_admission(department, app_id, employee_id, expected_version, action='confirm'):
    return _admission_plan(department, app_id, employee_id, expected_version, action)


def save_department_admission(department, app_id, employee_id, action, expected_version, context_revision, request_id):
    guards.require_post()
    with serialize('iam-work', 'site'):
        # Re-check the current target/scope authorization before replay.
        _employee(employee_id, 'iam.access.manage', write=True)
        plan = _admission_plan(department, app_id, employee_id, expected_version, action)
        payload = dict(action=action, expected_hash=plan['expected_hash'], expected_version=_version(expected_version))
        replayed = audit.replay(request_id, 'role.department_admission', 'Department', department, payload)
        if replayed is not None:
            return {**replayed, 'replayed': True}
        if not context_revision or context_revision != plan['context_revision']:
            conflict()
        _proof(consume=True)
        if not plan['changed']:
            return {'department': department, 'app_id': app_id, 'employee': employee_id, 'action': action,
                    'status': plan['admission_status'], 'changed': False, 'replayed': False}
        from frappe.utils import now_datetime
        user = policy.get_current_user()
        now = now_datetime()
        with guards.controlled_write():
            row = plan['row']
            if action == 'confirm':
                role_doc = roles.document(roles.ROLE, plan['role'])
                release_doc = roles.document(roles.RELEASE, role_doc.published_release)
                values = _admission_values(department, app_id, plan['employee_record'], role_doc, release_doc,
                                           [dict(scope_type=item['scope_type'], scope_ref=item['scope_ref'], include_descendants=0)
                                            for item in plan['responsibilities']])
                if row:
                    doc = frappe.get_doc(roles.ADMISSION, row.name, for_update=True)
                    doc.update({key: values[key] for key in ('role', 'role_key', 'responsibilities_json', 'config_hash')})
                    doc.status = 'CONFIRMED'
                    doc.version = int(row.get('version') or 0) + 1
                    doc.confirmed_by = user
                    doc.confirmed_at = now
                    doc.revoked_by = None
                    doc.revoked_at = None
                    doc.reason = ''
                    doc.save(ignore_permissions=True)
                else:
                    doc = frappe.get_doc(dict(doctype=roles.ADMISSION, status='CONFIRMED', version=1,
                                              confirmed_by=user, confirmed_at=now, **values)).insert(ignore_permissions=True)
                after = dict(department=department, app_id=app_id, employee=employee_id, role=doc.role,
                             role_key=doc.role_key, status='CONFIRMED', version=doc.version, requested_version=_version(expected_version))
            else:
                if not row:
                    return {'department': department, 'app_id': app_id, 'employee': employee_id, 'action': action,
                            'status': 'REVOKED', 'changed': False, 'replayed': False}
                doc = frappe.get_doc(roles.ADMISSION, row.name, for_update=True)
                doc.status = 'REVOKED'
                doc.version = int(row.get('version') or 0) + 1
                doc.revoked_by = user
                doc.revoked_at = now
                doc.reason = '管理员撤销部门管理角色准入'
                doc.save(ignore_permissions=True)
                after = dict(department=department, app_id=app_id, employee=employee_id, role=doc.role,
                             role_key=doc.role_key, status='REVOKED', version=doc.version, requested_version=_version(expected_version))
            _event(request_id, 'role.department_admission', 'Department', department, payload, {'version': _version(expected_version)}, after, doc.version)
        return {**after, 'changed': True, 'replayed': False}


def restore_role_release(app_id, role_key, source_release, expected_draft_version, request_id):
    role = _role(app_id, role_key)
    _role_authority(role, 'iam.roles.edit')
    release = roles.document(roles.RELEASE, source_release)
    if release.role != role.name:
        frappe.throw('不能借用其他角色或应用的发布内容。', frappe.PermissionError)
    # Restoration is explicit draft preparation. Existing publish preview and
    # authorization are still required before any employee's rights change.
    return save_role_draft(app_id, role_key, [roles.feature_dict(row) for row in release.features], expected_draft_version, request_id)


def seed_isolated_roles(companies):
    """Explicit console setup only; migrate never calls this or grants a person."""
    from hbos_portal.iam.demo_provider import require_isolated_site
    require_isolated_site()
    if not guards.isolated_root() or not companies or any(not frappe.db.exists('Company', company) for company in companies):
        frappe.throw('合成角色初始化范围未确认。', frappe.PermissionError)
    with serialize('iam-work', 'site'), guards.controlled_write():
        result = []
        for key, (title, boundary) in roles.BLUEPRINTS.items():
            existing = frappe.db.get_value(roles.ROLE, {'app_id': 'attendance', 'role_key': key}, 'name', for_update=True)
            if existing:
                result.append(existing)
                continue
            features = roles.normalize_features([dict(operation_id=row['operation_id'], scope_binding=row['scope_binding']) for row in roles.registry(key) if row['allowed']], key)
            role = frappe.get_doc(dict(doctype=roles.ROLE, app_id='attendance', role_key=key, title=title, boundary_kind=boundary, enabled=1,
                draft_version=1, draft_features=features, management_scopes=[dict(scope_type='COMPANY', scope_ref=company, include_descendants=0) for company in sorted(set(companies))])).insert(ignore_permissions=True)
            result.append(role.name)
        return result
