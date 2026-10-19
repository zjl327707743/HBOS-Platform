"""Bounded role API. Authentication remains the existing Frappe Session."""
from __future__ import annotations

import frappe

from hbos_portal.api.iam_access import _only
from hbos_portal.iam import policy, role_access, role_commands as commands


def _call(function, *, read_only=False):
    try:
        role_access.require_available()
        return {'ok': True, 'data': policy.current_read(function) if read_only else function()}
    except Exception as exc:
        status = frappe.local.response.get('http_status_code')
        if isinstance(exc, frappe.AuthenticationError):
            status, code, message = 403, 'PROOF_REQUIRED', '请重新验证管理员本人密码及已有二次认证。'
        elif isinstance(exc, frappe.PermissionError):
            status, code, message = 403, 'FORBIDDEN', str(exc)
        elif isinstance(exc, (frappe.QueryDeadlockError, frappe.QueryTimeoutError, frappe.TimestampMismatchError)) or status == 409:
            status, code, message = 409, 'CONFLICT', '角色、成员或权限已变化，本次未保存，请重新预览。'
        elif isinstance(exc, (frappe.ValidationError, ValueError, TypeError)):
            status, code, message = 400, 'INVALID_REQUEST', str(exc)
        else:
            status, code, message = 500, 'SERVICE_ERROR', '角色操作暂时无法完成，权限未作部分更新。'
            frappe.logger('hbos_iam').error('Role service failure (%s)', type(exc).__name__)
        frappe.db.rollback()
        frappe.local.response['http_status_code'] = status
        return {'ok': False, 'error': {'code': code, 'message': message, 'retryable': status in {409, 500}}}


@frappe.whitelist(methods=['GET'])
def list_roles(app_id='attendance', **kwargs):
    def run():
        _only(kwargs, ('app_id',))
        return commands.list_roles(app_id)
    return _call(run, read_only=True)


@frappe.whitelist(methods=['GET'])
def get_role(app_id, role_key, **kwargs):
    def run():
        _only(kwargs, ('app_id', 'role_key'))
        return commands.get_role(app_id, role_key)
    return _call(run, read_only=True)


@frappe.whitelist(methods=['POST'])
def save_role_draft(app_id, role_key, features, expected_draft_version, request_id, **kwargs):
    def run():
        _only(kwargs, ('app_id', 'role_key', 'features', 'expected_draft_version', 'request_id'))
        return commands.save_role_draft(app_id, role_key, features, expected_draft_version, request_id)
    return _call(run)


@frappe.whitelist(methods=['POST'])
def preview_role_publish(app_id, role_key, expected_draft_version, expected_release='', **kwargs):
    def run():
        _only(kwargs, ('app_id', 'role_key', 'expected_draft_version', 'expected_release'))
        return commands.preview_role_publish(app_id, role_key, expected_draft_version, expected_release)
    return _call(run, read_only=True)


@frappe.whitelist(methods=['POST'])
def publish_role(app_id, role_key, expected_draft_version, expected_release, context_revision, request_id, **kwargs):
    def run():
        _only(kwargs, ('app_id', 'role_key', 'expected_draft_version', 'expected_release', 'context_revision', 'request_id'))
        return commands.publish_role(app_id, role_key, expected_draft_version, expected_release, context_revision, request_id)
    return _call(run)


@frappe.whitelist(methods=['GET'])
def get_assignment(employee_id, app_id='attendance', **kwargs):
    def run():
        _only(kwargs, ('employee_id', 'app_id'))
        return commands.get_assignment(employee_id, app_id)
    return _call(run, read_only=True)


@frappe.whitelist(methods=['POST'])
def preview_assignment(employee_id, app_id, mode, role_key='', responsibilities=None, expected_version=0, **kwargs):
    def run():
        _only(kwargs, ('employee_id', 'app_id', 'mode', 'role_key', 'responsibilities', 'expected_version'))
        return commands.preview_assignment(employee_id, app_id, mode, role_key, responsibilities, expected_version)
    return _call(run, read_only=True)


@frappe.whitelist(methods=['POST'])
def save_assignment(employee_id, app_id, mode, expected_version, context_revision, request_id, role_key='', responsibilities=None, **kwargs):
    def run():
        _only(kwargs, ('employee_id', 'app_id', 'mode', 'role_key', 'responsibilities', 'expected_version', 'context_revision', 'request_id'))
        return commands.save_assignment(employee_id, app_id, mode, role_key, responsibilities, expected_version, context_revision, request_id)
    return _call(run)


@frappe.whitelist(methods=['GET'])
def get_department_role(department, app_id='attendance', **kwargs):
    def run():
        _only(kwargs, ('department', 'app_id'))
        return commands.get_department_role(department, app_id)
    return _call(run, read_only=True)


@frappe.whitelist(methods=['POST'])
def preview_department_role(department, app_id, expected_version, role_key='', **kwargs):
    def run():
        _only(kwargs, ('department', 'app_id', 'expected_version', 'role_key'))
        return commands.preview_department_role(department, app_id, role_key, expected_version)
    return _call(run, read_only=True)


@frappe.whitelist(methods=['POST'])
def save_department_role(department, app_id, expected_version, context_revision, request_id, role_key='', **kwargs):
    def run():
        _only(kwargs, ('department', 'app_id', 'expected_version', 'context_revision', 'request_id', 'role_key'))
        return commands.save_department_role(department, app_id, role_key, expected_version, context_revision, request_id)
    return _call(run)


@frappe.whitelist(methods=['POST'])
def restore_role_release(app_id, role_key, source_release, expected_draft_version, request_id, **kwargs):
    def run():
        _only(kwargs, ('app_id', 'role_key', 'source_release', 'expected_draft_version', 'request_id'))
        return commands.restore_role_release(app_id, role_key, source_release, expected_draft_version, request_id)
    return _call(run)
