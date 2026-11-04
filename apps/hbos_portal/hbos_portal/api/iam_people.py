"""Employee administration endpoints; actor always remains frappe.session.user."""
from __future__ import annotations

import frappe
from hbos_portal.iam import people, guards


def _call(method, values, write=False):
    from hbos_portal.auth.accounts import no_store
    no_store()
    if not frappe.conf.get('hbos_iam_enabled'):
        frappe.local.response['http_status_code'] = 403
        return {'ok': False, 'error': {'code': 'FORBIDDEN', 'message': '此站点尚未启用员工与应用管理功能。', 'retryable': False}}
    # Frappe normally drops unknown Python kwargs. Explicitly reject them so
    # subject replacement cannot appear accepted by an otherwise self API.
    allowed = set(values) | {'cmd'}
    if set(frappe.local.form_dict or {}) - allowed:
        frappe.local.response['http_status_code'] = 400
        return {'ok': False, 'error': {'code': 'INVALID_REQUEST', 'message': '请求包含未允许的参数。', 'retryable': False}}
    try:
        if write:
            guards.require_post()
        from hbos_portal.iam import policy
        read = lambda: getattr(people, method)(**values)
        retry_read = not write and method in {'list_people', 'get_person', 'get_employee_metadata', 'get_my_employee_status'}
        return {'ok': True, 'data': policy.current_read(read) if retry_read else read()}
    except frappe.AuthenticationError:
        frappe.db.rollback()
        frappe.local.response['http_status_code'] = 403
        return {'ok': False, 'error': {'code': 'PROOF_REQUIRED', 'message': '本人身份验证已过期，请重新验证后再保存。', 'retryable': False}}
    except frappe.PermissionError:
        frappe.db.rollback()
        frappe.local.response['http_status_code'] = 403
        return {'ok': False, 'error': {'code': 'FORBIDDEN', 'message': '没有此操作权限，或本人安全验证已过期；请重新验证后核对管理范围。', 'retryable': False}}
    except (frappe.ValidationError, frappe.DoesNotExistError, frappe.DuplicateEntryError, frappe.MandatoryError) as exc:
        frappe.db.rollback()
        status = frappe.local.response.get('http_status_code') or 400
        frappe.local.response['http_status_code'] = status
        return {'ok': False, 'error': {'code': 'CONFLICT' if status == 409 else 'INVALID_REQUEST', 'message': str(exc)[:400], 'retryable': status == 409}}
    except (frappe.QueryDeadlockError, frappe.QueryTimeoutError):
        frappe.db.rollback()
        frappe.local.response['http_status_code'] = 409
        return {'ok': False, 'error': {'code': 'CONFLICT' if write else 'READ_CONFLICT', 'message': '并发操作使当前事务失效，改动未保存，请刷新后重新验证。' if write else '读取遇到暂时冲突，请重试查询。', 'retryable': True}}
    except Exception:
        frappe.db.rollback()
        frappe.local.response['http_status_code'] = 500
        # No form payload, proof, credential or target business data is logged.
        return {'ok': False, 'error': {'code': 'SERVICE_ERROR', 'message': '人员服务暂时不可用，改动未保存。', 'retryable': True}}


@frappe.whitelist(methods=['GET'])
def list_people(page=1, page_size=20, search='', department='', account_status='', category='employees', view_group='daily'):
    return _call('list_people', dict(page=page, page_size=page_size, search=search, department=department, account_status=account_status, category=category, view_group=view_group))


@frappe.whitelist(methods=['GET'])
def get_person(employee_id):
    return _call('get_person', dict(employee_id=employee_id))


@frappe.whitelist(methods=['GET'])
def get_employee_metadata(view_group='daily'):
    return _call('get_employee_metadata', dict(view_group=view_group))


@frappe.whitelist(methods=['GET'])
def get_my_employee_status():
    return _call('get_my_employee_status', {})


@frappe.whitelist(methods=['POST'])
def preview_link(employee_id, user_id, ownership_evidence):
    return _call('preview_link', dict(employee_id=employee_id, user_id=user_id, ownership_evidence=ownership_evidence), True)


@frappe.whitelist(methods=['POST'])
def link_user(employee_id, user_id, ownership_evidence, expected_version, request_id):
    return _call('link_user', dict(employee_id=employee_id, user_id=user_id, ownership_evidence=ownership_evidence, expected_version=expected_version, request_id=request_id), True)


@frappe.whitelist(methods=['POST'])
def create_user(employee_id, ownership_evidence, expected_version, request_id):
    return _call('create_user', dict(employee_id=employee_id, ownership_evidence=ownership_evidence, expected_version=expected_version, request_id=request_id), True)


@frappe.whitelist(methods=['POST'])
def create_employee(fields, expected_version, request_id):
    return _call('create_employee', dict(fields=fields, expected_version=expected_version, request_id=request_id), True)


@frappe.whitelist(methods=['POST'])
def transfer_employee(employee_id, department, expected_version, request_id, context_revision=''):
    return _call('transfer_employee', dict(employee_id=employee_id, department=department, expected_version=expected_version, request_id=request_id, context_revision=context_revision), True)


@frappe.whitelist(methods=['GET'])
def preview_transfer_employee(employee_id, department, expected_version):
    return _call('preview_transfer_employee', dict(employee_id=employee_id, department=department, expected_version=expected_version))


@frappe.whitelist(methods=['POST'])
def disable_user(employee_id, expected_version, request_id):
    return _call('disable_user', dict(employee_id=employee_id, expected_version=expected_version, request_id=request_id), True)


@frappe.whitelist(methods=['POST'])
def reset_temporary_password(employee_id, expected_version, request_id):
    return _call('reset_temporary_password', dict(employee_id=employee_id, expected_version=expected_version, request_id=request_id), True)
