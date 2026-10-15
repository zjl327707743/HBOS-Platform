"""Controlled native Employee/User lifecycle. Never query attendance business data."""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager

import frappe
from hbos_portal.auth import accounts
from hbos_portal.auth.onboarding import serialize, login_alias_base, alias_candidate
from hbos_portal.iam import guards, policy, audit, temporary_passwords

EMPLOYEE_FIELDS = ['name', 'employee_name', 'employee_number', 'department', 'company', 'designation', 'user_id', 'status', 'modified', 'attendance_device_id']
CREATE_FIELDS = frozenset({'first_name', 'middle_name', 'last_name', 'employee_number', 'company', 'department', 'designation', 'gender', 'date_of_birth', 'date_of_joining', 'status', 'naming_series'})


def reject(message, status=400):
    frappe.local.response['http_status_code'] = status
    frappe.throw(message, frappe.ValidationError)


def parse_object(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            reject('请求内容不是有效对象。')
    if not isinstance(value, dict):
        reject('请提交明确的对象内容。')
    return value


def pagination(page, page_size):
    try:
        page, page_size = int(page), int(page_size)
    except (TypeError, ValueError):
        reject('页码与每页数量必须为整数。')
    if not 1 <= page <= 100000 or not 1 <= page_size <= 50:
        reject('页码或每页数量超出允许范围。')
    return page, page_size


def _user(user_id):
    if not user_id:
        return None
    fields = ['name', 'username', 'enabled', 'modified', 'user_type']
    if temporary_passwords.available():
        fields += list(temporary_passwords.FIELDS)
    return frappe.db.get_value('User', user_id, fields, as_dict=True, for_update=True)


def person_version(employee, user=None):
    user = user if user is not None else _user(employee.get('user_id'))
    value = [employee.get('name'), str(employee.get('modified')), str(user.get('modified')) if user else '', user.get('enabled') if user else '', user.get('hbos_password_generation', 0) if user else 0]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()


def employee_dto(employee):
    user = _user(employee.get('user_id'))
    return dict(id=employee.name, name=employee.employee_name, employee_number=str(employee.employee_number or ''), department=employee.department, department_name=employee.department, company=employee.company, position=employee.designation or '', user_id=employee.user_id or '', account_status='unopened' if not user else 'active' if user.enabled else 'disabled', attendance_status='confirmed' if employee.get('attendance_device_id') else 'pending', version=person_version(employee, user))


def list_people(page=1, page_size=20, search='', department='', account_status='', category='employees'):
    page, page_size = pagination(page, page_size)
    guards.require_capability('iam.people.read')
    if category not in {'employees', 'pending', 'other'}:
        reject('账号分类无效。')
    if category != 'employees':
        # Unlinked accounts have no trustworthy department/company ownership.
        # Scoped employee readers cannot enumerate them through a null scope.
        if not (frappe.session.user == 'Administrator' and frappe.conf.get('hbos_iam_test_site')):
            return dict(items=[], total=0, page=page, page_size=page_size, unavailable=True)
        linked = frappe.db.sql("select user_id from `tabEmployee` where coalesce(user_id,'')<>'' for update", pluck=True)
        users = frappe.db.sql('select name,full_name,username,enabled,user_type,modified from `tabUser` where name not in %(linked)s order by name for update', {'linked': tuple(set(linked + ['Guest']))}, as_dict=True)
        rows = []
        for user in users:
            ordinary = user.user_type != 'System User' and user.name != 'Administrator'
            if ordinary != (category == 'pending'):
                continue
            if search and str(search).lower() not in ' '.join(str(user.get(k) or '') for k in ['name', 'full_name', 'username']).lower():
                continue
            rows.append(dict(id=user.name, name=user.full_name or user.name, employee_number='', department='', department_name='', company='', position='员工待关联' if ordinary else '服务 / 应急管理', user_id=user.name, username=user.username, account_status='active' if user.enabled else 'disabled', attendance_status='pending', version=str(user.modified)))
        return dict(items=rows[(page-1)*page_size:page*page_size], total=len(rows), page=page, page_size=page_size)
    departments = guards.managed_departments('iam.people.read')
    if department:
        if department not in departments:
            frappe.throw('不在可管理的部门范围内。', frappe.PermissionError)
        departments = [department]
    if not departments:
        return dict(items=[], total=0, page=page, page_size=page_size)
    # User state is filtered in SQL through a fixed EXISTS predicate, before
    # pagination/count. No business table or display-name identity matching.
    conditions = ['e.department in %(departments)s']
    values = {'departments': tuple(departments), 'start': (page-1)*page_size, 'limit': page_size}
    if search:
        values['search'] = '%' + str(search)[:120].replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        conditions.append('(e.employee_name like %(search)s or e.employee_number like %(search)s)')
    if account_status == 'unopened':
        conditions.append("coalesce(e.user_id,'')=''")
    elif account_status in {'active', 'disabled'}:
        conditions.append('exists(select 1 from `tabUser` u where u.name=e.user_id and u.enabled=%(enabled)s)')
        values['enabled'] = int(account_status == 'active')
    elif account_status:
        reject('账号状态无效。')
    where = ' and '.join(conditions)
    # A locking read must load the values as well as the row identity. A later
    # ordinary get_doc can otherwise reuse an older repeatable-read snapshot.
    total = frappe.db.sql('select count(*) from `tabEmployee` e where ' + where + ' for update', values)[0][0]
    result = frappe.db.sql('select ' + ','.join('e.`'+key+'`' for key in EMPLOYEE_FIELDS) + ' from `tabEmployee` e where ' + where + ' order by e.employee_name,e.name limit %(limit)s offset %(start)s for update', values, as_dict=True)
    for row in result:
        guards.require_capability('iam.people.read', department=row.department, company=row.company, target_user=row.user_id or None)
    return dict(items=[employee_dto(row) for row in result], total=total, page=page, page_size=page_size)


def _employee(employee_id, operation, lock=False):
    if not isinstance(employee_id, str) or not employee_id:
        reject('请选择明确的员工档案。')
    employee = frappe.get_doc('Employee', employee_id, for_update=True)
    guards.require_capability(operation, department=employee.department, company=employee.company, target_user=employee.user_id or None)
    return employee


def get_person(employee_id):
    if not frappe.db.get_value('Employee', employee_id, 'name', for_update=True):
        guards.require_capability('iam.people.read')
        if not guards.isolated_root():
            frappe.throw('未确认员工归属的账号不在当前部门管理范围内。', frappe.PermissionError)
        user = _user(employee_id)
        if not user or user.name == 'Guest':
            reject('没有找到员工或可管理账号。')
        row = dict(id=user.name, name=frappe.db.get_value('User', user.name, 'full_name', for_update=True) or user.name,
                   employee_number='', department='', department_name='', company='', position='员工待关联' if user.user_type != 'System User' else '服务 / 应急管理',
                   user_id=user.name, account_status='active' if user.enabled else 'disabled', attendance_status='pending', version=str(user.modified), subject_type='account')
        return dict(employee=row, account=dict(user_id=user.name, username=user.username, enabled=bool(user.enabled),
                    feishu_bound=bool(frappe.db.exists('HBOS External Identity', {'user': user.name, 'enabled': 1})), initial_password_pending=temporary_passwords.status(user.name)['pending']),
                    association=dict(employee_id=None, user_id=user.name, attendance_identifier='', attendance_status='pending'), history=[])
    employee = _employee(employee_id, 'iam.people.read')
    user = _user(employee.user_id)
    bound = bool(user and frappe.db.exists('HBOS External Identity', {'user': user.name, 'enabled': 1}))
    state = temporary_passwords.status(employee.user_id) if user else {}
    proposed = 'iam.' + hashlib.sha256(employee.name.encode()).hexdigest()[:24] + '@users.invalid'
    return dict(employee=employee_dto(employee), account=dict(user_id=employee.user_id or '', proposed_user_id=proposed if not employee.user_id else '', username=user.username if user else '', enabled=bool(user and user.enabled), feishu_bound=bound, initial_password_pending=bool(state.get('pending'))), association=dict(employee_id=employee.name, user_id=employee.user_id or '', attendance_identifier=employee.get('attendance_device_id') or '', attendance_status='confirmed' if employee.get('attendance_device_id') else 'pending'), history=[])


def get_employee_metadata():
    guards.require_capability('iam.people.read')
    departments = guards.managed_departments('iam.people.read')
    options = frappe.db.sql('select name,department_name,company from `tabDepartment` where name in %(departments)s order by name for update', {'departments': tuple(departments)}, as_dict=True) if departments else []
    companies = sorted({row.company for row in options if row.company})
    meta = frappe.get_meta('Employee')
    required = [dict(fieldname=df.fieldname, label=df.label, fieldtype=df.fieldtype, options=df.options) for df in meta.fields if df.reqd and not df.read_only and df.fieldname in CREATE_FIELDS]
    return dict(required_fields=required, companies=[dict(value=name, label=name) for name in companies], departments=[dict(value=row.name, label=row.department_name or row.name, company=row.company) for row in options], genders=[dict(value=row.name, label=row.name) for row in frappe.get_all('Gender', fields=['name'], order_by='name', limit_page_length=0)], version=policy.current_revision())


def get_my_employee_status():
    user = policy.get_current_user()
    try:
        employee = policy.resolve_employee(user, required=False)
    except frappe.PermissionError:
        return dict(status='conflict', employee_id=None, employee_number=None, department=None, initial_password_pending=temporary_passwords.status(user)['pending'])
    return dict(status='linked' if employee else 'unlinked', employee_id=employee.name if employee else None, employee_number=employee.employee_number if employee else None, department=employee.department if employee else None, initial_password_pending=temporary_passwords.status(user)['pending'])


def check_evidence(employee, user_id, evidence):
    evidence = parse_object(evidence)
    if set(evidence) != {'employee_number', 'company', 'account_user_id', 'reference'}:
        reject('请提供明确的工号、公司、账号主键和归属核验来源。')
    if not isinstance(evidence['employee_number'], str) or evidence['employee_number'] != str(employee.employee_number or '') or not evidence['employee_number']:
        reject('工号不匹配，不能按姓名认定归属。', 409)
    if evidence['company'] != employee.company or evidence['account_user_id'] != user_id:
        reject('公司或账号主键与核验对象不一致。', 409)
    if not isinstance(evidence['reference'], str) or not 12 <= len(evidence['reference'].strip()) <= 500:
        reject('请记录12至500字的可靠归属核验依据。')
    return evidence


def _proof():
    actor = accounts.require_user()
    proof = accounts.require_proof(actor, consume=True)
    if proof['method'] != 'password':
        frappe.throw('请重新验证管理员本人密码及已有二次认证。', frappe.AuthenticationError)


def _version(employee, expected_version):
    if not expected_version or person_version(employee) != str(expected_version):
        reject('员工或账号状态已变化，请刷新后重新核对。', 409)


def _department(name, company):
    department = frappe.get_doc('Department', name, for_update=True)
    if department.company != company or department.get('disabled') or department.get('is_group'):
        reject('该部门不适合分配员工，请选择已确认的同公司部门。')
    return department


def side_effect_snapshot(user):
    doc = frappe.get_doc('User', user, for_update=True)
    permissions = frappe.db.get_values('User Permission', {'user': user}, ['allow', 'for_value'], as_dict=True, for_update=True)
    return dict(user_type=doc.user_type, enabled=int(doc.enabled), roles=sorted(row.role for row in doc.roles), user_permissions=sorted((row.allow, row.for_value) for row in permissions))


def _check_side_effects(user, before):
    after = side_effect_snapshot(user)
    if set(after['roles']) - set(before['roles']) - {'Employee', 'Employee Self Service'}:
        reject('原生关联产生非预期角色变化，事务未保存。', 409)
    if set(before['roles']) - set(after['roles']) - {'Employee'}:
        reject('原生关联会撤销原账号既有角色，事务未保存，请单独核验。', 409)
    if before['user_type'] != 'System User' and after['user_type'] == 'System User':
        reject('普通员工关联产生非预期后台权限，事务未保存。', 409)
    return after


@contextmanager
def website_compatibility(user):
    old = frappe.flags.get('hbos_iam_website_compatibility')
    frappe.flags.hbos_iam_website_compatibility = user
    try:
        yield
    finally:
        frappe.flags.hbos_iam_website_compatibility = old


def on_native_user_update(doc, method=None):
    """Constrain native automatic promotion only for an existing IAM web user.

    Employee.save and its native role/UserPermission hooks run in full. The
    compatibility adjustment changes no Role definition or upstream source.
    Explicit HTTP type/role writes are separately rejected before validation.
    """
    if not frappe.conf.get('hbos_iam_enabled'):
        return
    before = doc.get_doc_before_save()
    if not before or before.user_type != 'Website User':
        return
    controlled = frappe.flags.get('hbos_iam_website_compatibility') == doc.name
    if not controlled and not guards._managed_user(doc.name):
        return
    if frappe.flags.get('hbos_iam_user_type_upgrade_authority') == doc.name:
        return
    old_roles = {row.role for row in before.get('roles', [])}
    new_roles = {row.role for row in doc.get('roles', [])}
    if new_roles - old_roles - {'Employee'}:
        reject('原生保存产生非预期角色变化，未授予后台权限。', 409)
    updates = {}
    if doc.user_type != 'Website User':
        doc.user_type = 'Website User'
        updates['user_type'] = 'Website User'
    # There is no approved ordinary-account enable command in this release.
    # Native Employee.status synchronization must not revive a disabled User.
    if not before.enabled and doc.enabled:
        doc.enabled = 0
        updates['enabled'] = 0
    if updates:
        frappe.db.set_value('User', doc.name, updates, update_modified=False)
        frappe.clear_cache(user=doc.name)


def link_native_employee(employee, user):
    frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE', (user,))
    target = frappe.get_doc('User', user, for_update=True)
    if not target.enabled or user in {'Guest', 'Administrator'} or employee.status != 'Active':
        reject('账号或员工状态不可关联，不能自动复活停用账号。', 409)
    existing = frappe.db.sql('SELECT name FROM `tabEmployee` WHERE user_id=%s AND name<>%s FOR UPDATE', (user, employee.name))
    if existing or employee.user_id and employee.user_id != user:
        reject('员工或账号已有其他明确关联，不能抢占。', 409)
    before = side_effect_snapshot(user)
    if target.user_type == 'Website User':
        employee.create_user_permission = 1
    employee.user_id = user
    with guards.controlled_write(), website_compatibility(user):
        employee.save(ignore_permissions=True)
    after = _check_side_effects(user, before)
    if after['enabled'] != before['enabled']:
        reject('关联产生非预期账号状态变化，事务未保存。', 409)
    return dict(before=before, after=after)


def preview_link(employee_id, user_id, ownership_evidence):
    employee = _employee(employee_id, 'iam.people.link')
    guards.require_capability('iam.people.link', department=employee.department, company=employee.company, target_user=user_id)
    accounts.require_proof(accounts.require_user())
    check_evidence(employee, user_id, ownership_evidence)
    target = _user(user_id)
    if not target or not target.enabled or user_id in {'Guest', 'Administrator'}:
        reject('目标账号不存在或不可关联。', 409)
    if employee.user_id or frappe.db.get_value('Employee', {'user_id': user_id}, 'name', for_update=True):
        reject('员工或账号已经关联，不能重复关联。', 409)
    return dict(employee=employee_dto(employee), user_id=user_id, username=target.username, version=person_version(employee, target), effects=['复用已有账号，不新建员工档案', '按原生员工自助规则校验角色与范围', '保留员工历史记录归属'])


def _begin(employee_id, operation, expected_version, request_id, payload, version_user=None):
    employee = _employee(employee_id, operation, lock=True)
    previous = audit.replay(request_id, operation, 'Employee', employee_id, payload)
    if previous is not None:
        return employee, dict(employee=employee_dto(employee), version=person_version(employee), replayed=True)
    if version_user:
        frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE', (version_user,))
        if person_version(employee, _user(version_user)) != str(expected_version):
            reject('员工或所选账号已变化，请重新预览归属关联。', 409)
    else:
        _version(employee, expected_version)
    _proof()
    return employee, None


def _finish(employee, operation, request_id, payload, before=None, secret=None):
    employee.reload()
    data = dict(employee=employee_dto(employee), version=person_version(employee), replayed=False)
    audit.append_event(request_id, operation, 'Employee', employee.name, payload, before=before or {}, after={'employee_id': employee.name, 'user_id': employee.user_id or '', 'department': employee.department, 'version': data['version']}, version=0)
    return dict(data, **(secret or {}))


def link_user(employee_id, user_id, ownership_evidence, expected_version, request_id):
    operation = 'iam.people.link'
    payload = dict(employee_id=employee_id, user_id=user_id, ownership_evidence=parse_object(ownership_evidence), expected_version=expected_version)
    with serialize('iam-request', str(request_id)):
        employee, replayed = _begin(employee_id, operation, expected_version, request_id, payload, version_user=user_id)
        if replayed:
            return replayed
        guards.require_capability(operation, department=employee.department, company=employee.company, target_user=user_id)
        check_evidence(employee, user_id, ownership_evidence)
        before = {'employee_id': employee.name, 'user_id': employee.user_id or ''}
        link_native_employee(employee, user_id)
        return _finish(employee, operation, request_id, payload, before)


def _insert_user(employee):
    user_id = 'iam.' + hashlib.sha256(employee.name.encode()).hexdigest()[:24] + '@users.invalid'
    if frappe.db.get_value('User', user_id, 'name', for_update=True):
        reject('已有账号记录，请核验后关联，不重复创建。', 409)
    base = login_alias_base(employee.employee_name)
    with serialize('alias', base):
        for number in range(1, 100001):
            alias = alias_candidate(base, number)
            if frappe.db.get_value('User', {'username': alias}, 'name', for_update=True) or frappe.db.get_value('User', alias, 'name', for_update=True):
                continue
            user = frappe.get_doc(dict(doctype='User', email=user_id, username=alias, first_name=employee.employee_name, user_type='Website User', enabled=1, send_welcome_email=0, roles=[]))
            frappe.db.savepoint('hbos_iam_alias_insert')
            try:
                with guards.controlled_write():
                    user.insert(ignore_permissions=True)
                return user.name
            except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
                frappe.db.rollback(save_point='hbos_iam_alias_insert')
                if frappe.db.get_value('User', user_id, 'name', for_update=True):
                    reject('账号主键发生并发冲突，请核验已有账号。', 409)
    reject('无法分配唯一登录名，请稍后重试。', 409)


def create_user(employee_id, ownership_evidence, expected_version, request_id):
    operation = 'iam.people.provision'
    payload = dict(employee_id=employee_id, ownership_evidence=parse_object(ownership_evidence), expected_version=expected_version)
    with serialize('iam-request', str(request_id)):
        employee, replayed = _begin(employee_id, operation, expected_version, request_id, payload)
        if replayed:
            return replayed
        if employee.user_id:
            reject('员工已有关联账号，请复用原账号。', 409)
        expected_user = 'iam.' + hashlib.sha256(employee.name.encode()).hexdigest()[:24] + '@users.invalid'
        check_evidence(employee, expected_user, ownership_evidence)
        before = {'employee_id': employee.name, 'user_id': ''}
        user = _insert_user(employee)
        link_native_employee(employee, user)
        secret = temporary_passwords.issue(user)
        return _finish(employee, operation, request_id, payload, before, secret)


def transfer_employee(employee_id, department, expected_version, request_id):
    operation = 'iam.people.transfer'; payload = dict(employee_id=employee_id, department=department, expected_version=expected_version)
    with serialize('iam-request', str(request_id)):
        employee, replayed = _begin(employee_id, operation, expected_version, request_id, payload)
        if replayed:
            return replayed
        _department(department, employee.company)
        guards.require_capability(operation, department=department, company=employee.company, target_user=employee.user_id or None)
        before = {'department': employee.department}
        original = side_effect_snapshot(employee.user_id) if employee.user_id else None
        if employee.user_id:
            frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE', (employee.user_id,))
        employee.department = department
        with guards.controlled_write(), website_compatibility(employee.user_id):
            employee.save(ignore_permissions=True)
        if original:
            if int(frappe.db.get_value('User', employee.user_id, 'enabled', for_update=True)) != original['enabled']:
                doc = frappe.get_doc('User', employee.user_id, for_update=True)
                doc.enabled = original['enabled']
                with guards.controlled_write(), website_compatibility(employee.user_id):
                    doc.save(ignore_permissions=True)
            _check_side_effects(employee.user_id, original)
            from hbos_portal.auth.security import advance_version
            advance_version(employee.user_id)
        return _finish(employee, operation, request_id, payload, before)


def disable_user(employee_id, expected_version, request_id):
    return _account_command(employee_id, expected_version, request_id, 'iam.people.disable')


def reset_temporary_password(employee_id, expected_version, request_id):
    return _account_command(employee_id, expected_version, request_id, 'iam.people.reset')


def _account_command(employee_id, expected_version, request_id, operation):
    payload = dict(employee_id=employee_id, expected_version=expected_version)
    with serialize('iam-request', str(request_id)):
        employee, replayed = _begin(employee_id, operation, expected_version, request_id, payload)
        if replayed:
            return replayed
        if not employee.user_id:
            reject('员工尚无关联账号。')
        frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE', (employee.user_id,))
        doc = frappe.get_doc('User', employee.user_id, for_update=True)
        if doc.name in {'Administrator', 'Guest'}:
            frappe.throw('不能通过员工管理改变系统应急账号。', frappe.PermissionError)
        secret = None
        if operation == 'iam.people.disable':
            doc.enabled = 0
            with guards.controlled_write(), website_compatibility(doc.name):
                doc.save(ignore_permissions=True)
        else:
            if not doc.enabled:
                reject('停用账号不能重置临时密码。', 409)
            secret = temporary_passwords.issue(doc.name)
        from hbos_portal.auth.security import advance_version
        advance_version(doc.name)
        return _finish(employee, operation, request_id, payload, secret=secret)


def create_employee(fields, expected_version, request_id):
    fields = parse_object(fields)
    if set(fields) - CREATE_FIELDS:
        reject('员工字段超出允许范围，不能直接修改账号或内部设置。')
    company, department = fields.get('company'), fields.get('department')
    guards.require_capability('iam.people.create', department=department, company=company)
    payload = dict(fields=fields, expected_version=expected_version)
    with serialize('iam-request', str(request_id)):
        previous = audit.replay(request_id, 'iam.people.create', 'Department', department or '', payload)
        if previous is not None:
            employee_id = previous.get('employee_id')
            if not employee_id:
                reject('原请求已执行，请刷新员工列表查看结果。', 409)
            employee = _employee(employee_id, 'iam.people.create')
            return dict(employee=employee_dto(employee), version=person_version(employee), replayed=True)
        if str(expected_version) != policy.current_revision():
            reject('管理上下文已变化，请刷新员工必填信息。', 409)
        _proof()
        if not company or not frappe.db.get_value('Company', company, 'name', for_update=True):
            reject('请选择可管理的已有公司。')
        _department(department, company)
        for field in ['first_name', 'employee_number', 'company', 'department', 'gender', 'date_of_birth', 'date_of_joining']:
            if not isinstance(fields.get(field), str) or not fields[field].strip():
                reject('请完整填写姓名、工号、公司、部门、性别、生日及入职日期，不自动补齐日期。')
        if fields.get('status', 'Active') != 'Active':
            reject('新增员工状态必须明确为在职。')
        with serialize('employee-number', company + '\x1f' + fields['employee_number']):
            if frappe.db.get_value('Employee', {'company': company, 'employee_number': fields['employee_number']}, 'name', for_update=True):
                reject('该公司工号已有员工档案，请核对，不能重复新增。', 409)
            doc = frappe.get_doc(dict(fields, doctype='Employee', status='Active', create_user_automatically=0))
            with guards.controlled_write():
                doc.insert(ignore_permissions=True)
            data = dict(employee=employee_dto(doc), version=person_version(doc), replayed=False)
            audit.append_event(request_id, 'iam.people.create', 'Department', department, payload, after={'employee_id': doc.name, 'department': department, 'version': data['version']})
            return data
