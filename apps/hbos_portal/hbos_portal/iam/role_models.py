"""Server-only validation of the bounded role persistence models, including department admissions."""
from __future__ import annotations

import json

import frappe

from hbos_portal.iam import guards, role_access as roles


def deny(message):
    frappe.throw(message, frappe.PermissionError)


def validate_role(doc):
    guards.require_controlled_write()
    if doc.app_id != 'attendance' or doc.role_key not in roles.BLUEPRINTS or doc.boundary_kind != roles.BLUEPRINTS[doc.role_key][1]:
        deny('应用角色标识和范围上限由服务器固定。')
    companies = roles.management_companies(doc)
    if any(not frappe.db.exists('Company', company) for company in companies):
        deny('角色管理公司不存在。')
    previous = doc.get_doc_before_save()
    if previous and any(doc.get(key) != previous.get(key) for key in ('app_id', 'role_key', 'boundary_kind')):
        deny('角色稳定标识与上限不可通过编辑改变。')
    if previous and [roles.scope_dict(row) for row in doc.management_scopes] != [roles.scope_dict(row) for row in previous.management_scopes]:
        deny('功能编辑不能扩大角色本身的管理范围。')
    if not doc.title or int(doc.draft_version or 0) < 1:
        deny('角色名称或草稿版本无效。')
    roles.normalize_features([roles.feature_dict(row) for row in doc.draft_features], doc.role_key)
    if doc.published_release:
        if frappe.db.get_value(roles.RELEASE, doc.published_release, 'role', for_update=True) != doc.name:
            deny('角色发布指针必须引用本角色版本。')


def release_hash(role, revision, features, native_mapping):
    return roles.digest(dict(role=role, revision=int(revision), features=features, native_mapping=native_mapping))


def validate_release(doc):
    guards.require_controlled_write()
    if not doc.is_new():
        deny('已发布版本不可改写；恢复功能须发布新版本。')
    role = roles.document(roles.ROLE, doc.role)
    features = roles.normalize_features([roles.feature_dict(row) for row in doc.features], role.role_key, publishing=True)
    try:
        mapping = json.loads(doc.native_mapping_json or '[]')
    except (ValueError, TypeError):
        deny('原生权限映射不是服务器清单。')
    # SELF uses the existing bounded executor; no broad native HR Role is needed.
    if mapping != [] or doc.published_by != frappe.session.user or int(doc.revision or 0) < 1:
        deny('原生映射、发布者或版本无效。')
    if doc.content_hash != release_hash(role.name, doc.revision, features, mapping):
        deny('发布内容指纹不一致。')


def validate_assignment(doc):
    guards.require_controlled_write()
    if doc.app_id != 'attendance' or doc.subject_type not in {'Employee', 'Department'} or not frappe.db.exists(doc.subject_type, doc.subject_name):
        deny('角色只能关联明确的原生员工或部门。')
    if doc.mode not in {'FOLLOW_DEPARTMENT', 'DIRECT', 'NONE'} or int(doc.version or 0) < 1:
        deny('角色来源或关联版本无效。')
    if doc.subject_type == 'Department' and doc.mode == 'FOLLOW_DEPARTMENT':
        deny('部门默认不能再次继承部门。')
    if doc.mode != 'DIRECT':
        if doc.role or doc.responsibilities:
            deny('跟随默认或未选角色时不能携带独立职责。')
    else:
        role = roles.document(roles.ROLE, doc.role)
        if role.app_id != doc.app_id or not role.enabled or not role.published_release:
            deny('只能关联已启用、已发布的同应用角色。')
        if doc.subject_type == 'Department' and role.role_key not in roles.BLUEPRINTS:
            deny('部门默认只能选择已登记的考勤角色。')
        # Same published role catalogue and same boundary/scope pairing for both
        # a department default and one employee's direct assignment.
        roles.normalize_scopes([roles.scope_dict(row) for row in doc.responsibilities], role.boundary_kind, roles.management_companies(role))
    previous = doc.get_doc_before_save()
    if previous:
        if any(doc.get(key) != previous.get(key) for key in ('app_id', 'subject_type', 'subject_name')):
            deny('角色关联对象不可改名或替换。')
        if int(doc.version) != int(previous.version) + 1:
            deny('关联变更必须在受控事务中递增版本。')
    duplicates = frappe.db.sql('select name from `tabHBOS IAM Role Assignment` where app_id=%s and subject_type=%s and subject_name=%s and name!=%s for update', (doc.app_id, doc.subject_type, doc.subject_name, doc.name or ''), as_dict=True)
    if duplicates:
        deny('考勤初版每位员工或部门只能选择一种角色来源。')


def validate_department_admission(doc):
    """A management-role admission is bound to one employee and one exact context."""
    guards.require_controlled_write()
    if doc.app_id != 'attendance' or not frappe.db.exists('Department', doc.department) or not frappe.db.exists('Employee', doc.employee):
        deny('部门管理角色准入对象无效。')
    employee = frappe.db.get_value('Employee', doc.employee,
        ['name', 'user_id', 'department', 'company', 'status', 'modified'], as_dict=True, for_update=True)
    if not employee or employee.department != doc.department:
        deny('准入成员与当前主部门不一致，须重新核对。')
    role = roles.document(roles.ROLE, doc.role)
    if role.app_id != doc.app_id or role.role_key != doc.role_key or role.role_key not in roles.MANAGEMENT_ROLE_KEYS:
        deny('准入角色不是当前可用的管理型部门角色。')
    if not role.enabled or not role.published_release:
        deny('只有已启用、已发布的角色才能确认准入。')
    release = roles.document(roles.RELEASE, role.published_release)
    try:
        scopes = json.loads(doc.responsibilities_json or '[]')
    except (ValueError, TypeError):
        deny('准入范围不是服务器清单。')
    scopes = roles.normalize_scopes(scopes, role.boundary_kind, roles.management_companies(role))
    expected = roles.admission_hash(doc.department, doc.app_id, employee, role, release, scopes)
    if doc.config_hash != expected:
        deny('准入上下文已变化，请重新读取后再确认。')
    if doc.status not in {'PENDING', 'CONFIRMED', 'REVOKED'}:
        deny('准入状态无效。')
    if doc.status == 'CONFIRMED' and (not doc.confirmed_by or not doc.confirmed_at):
        deny('确认准入必须记录确认人和时间。')
    if doc.status == 'REVOKED' and (not doc.revoked_by or not doc.revoked_at):
        deny('撤销准入必须记录撤销人和时间。')
    previous = doc.get_doc_before_save()
    if previous:
        if any(doc.get(key) != previous.get(key) for key in ('department', 'app_id', 'employee')):
            deny('准入对象不可改名或替换。')
        role_changed = any(doc.get(key) != previous.get(key) for key in ('role', 'role_key'))
        if role_changed:
            # A department default can be re-baselined to another management role.
            # That is only a PENDING re-confirmation; the new role must equal the
            # current department default (never an arbitrary substitution).
            if doc.status != 'PENDING':
                deny('角色变化只能由部门默认重置为待确认。')
            current = roles.assignments('Department', doc.department, doc.app_id)
            current = current[0] if current else None
            if not current or current.mode != 'DIRECT' or current.role != doc.role:
                deny('准入角色与当前部门默认不一致。')
            current_scopes = roles.normalize_scopes([roles.scope_dict(row) for row in current.responsibilities],
                                                     role.boundary_kind, roles.management_companies(role))
            if current_scopes != scopes:
                deny('准入范围与当前部门默认不一致。')
        if int(doc.version) != int(previous.version) + 1:
            deny('准入变更必须在受控事务中递增版本。')
        allowed = {('PENDING', 'CONFIRMED'), ('PENDING', 'REVOKED'), ('CONFIRMED', 'REVOKED'),
                   ('CONFIRMED', 'PENDING'), ('REVOKED', 'PENDING'), ('REVOKED', 'CONFIRMED'), ('PENDING', 'PENDING')}
        if (previous.status, doc.status) not in allowed:
            deny('准入状态转换无效。')
    elif doc.status not in {'PENDING', 'CONFIRMED'}:
        deny('新建准入只能进入待确认或已确认状态。')
    if doc.admission_key != roles.admission_key(doc.department, doc.app_id, doc.employee):
        deny('准入唯一标识必须由服务器生成。')


def validate_child(doc, kind):
    guards.require_controlled_write()
    allowed = {(roles.ROLE, 'draft_features'), (roles.RELEASE, 'features')} if kind == 'feature' else {(roles.ROLE, 'management_scopes'), (roles.ASSIGNMENT, 'responsibilities')}
    if (doc.parenttype, doc.parentfield) not in allowed:
        deny('角色子表只能由受控父对象保存。')
    if doc.parenttype == roles.RELEASE and frappe.db.exists(roles.RELEASE, doc.parent):
        deny('已发布版本的子项不可改写。')
