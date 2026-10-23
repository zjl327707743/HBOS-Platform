"""Trusted enterprise onboarding bridge; names never establish employee ownership."""
from __future__ import annotations

import frappe


def verified_employee(settings, identity):
    """Only an internal validated adapter can supply a stable Employee claim.

    This is deliberately not an HTTP argument or a document flag. Real OAuth
    currently has no verified Employee key; its new User remains unlinked.
    """
    claim = frappe.flags.get('hbos_iam_verified_employee_link')
    expected = (identity.get('tenant_key'), settings.app_id, identity.get('open_id'))
    if not claim or tuple(claim.get('identity') or ()) != expected:
        return None
    employee_id = claim.get('employee_id')
    if not employee_id or not claim.get('evidence_reference'):
        frappe.throw('员工归属证明不完整。', frappe.PermissionError)
    return frappe.get_doc('Employee', employee_id)


def before_create(settings, identity):
    if not frappe.conf.get('hbos_iam_enabled'):
        return
    from hbos_portal.auth.feishu import FeishuLoginError
    employee = verified_employee(settings, identity)
    if employee and employee.user_id:
        raise FeishuLoginError('existing_account_requires_link', '员工已有账号，请先登录原账号并验证本人身份后绑定飞书。')


def prepare_new_user(user, settings, identity):
    if not frappe.conf.get('hbos_iam_enabled'):
        return
    from hbos_portal.iam.temporary_passwords import mark_initial
    mark_initial(user)
    employee = verified_employee(settings, identity)
    if employee:
        from hbos_portal.iam.people import link_native_employee
        # This path is reachable only after exchange_identity and server-side
        # stable ownership proof, never by matching display_name or username.
        frappe.db.sql('SELECT name FROM `tabEmployee` WHERE name=%s FOR UPDATE', (employee.name,))
        link_native_employee(employee, user)
