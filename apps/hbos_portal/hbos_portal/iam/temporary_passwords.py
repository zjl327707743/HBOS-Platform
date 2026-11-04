"""Native password hashes and four protected lifecycle fields; no secret store."""
from __future__ import annotations

import secrets
from contextlib import contextmanager

import frappe

FIELDS = ('hbos_initial_password_pending', 'hbos_temporary_password',
          'hbos_temporary_password_expires_at', 'hbos_password_generation')
# Exact Frappe command names, never a prefix or client-supplied target.
PENDING_METHODS = frozenset({
    'login',
    'hbos_portal.auth.accounts.get_request_security',
    'hbos_portal.api.csrf.get_token',
    'hbos_portal.auth.accounts.get_security',
    'hbos_portal.auth.accounts.claim_initial_password',
    'hbos_portal.auth.accounts.reauthenticate',
    'hbos_portal.auth.accounts.request_feishu_code',
    'hbos_portal.auth.accounts.verify_feishu_code',
    'hbos_portal.auth.accounts.set_password',
    'hbos_portal.auth.accounts.update_password',
    'frappe.core.doctype.user.user.update_password',
    'hbos_portal.auth.accounts.password_login',
    'hbos_portal.auth.accounts.get_recovery_channels',
    'hbos_portal.api.iam_people.get_my_employee_status',
    'logout', 'frappe.handler.logout',
})


def available():
    try:
        return frappe.get_meta('User').has_field(FIELDS[0])
    except (AttributeError, ImportError):
        return False


def status(user):
    empty = dict(pending=False, temporary=False, expires_at=None, generation=0, can_claim=False)
    if not available():
        return empty
    value = frappe.db.get_value('User', user, list(FIELDS), as_dict=True, for_update=True)
    if not value:
        return empty
    pending = bool(value.get(FIELDS[0]))
    temporary = bool(value.get(FIELDS[1]))
    session = getattr(frappe, 'session', None)
    delivery_session = bool(session and session.user == user and (session.data or {}).get('hbos_iam_initial_delivery'))
    return dict(pending=pending, temporary=temporary, expires_at=value.get(FIELDS[2]),
                generation=int(value.get(FIELDS[3]) or 0),
                can_claim=pending and not temporary and not int(value.get(FIELDS[3]) or 0) and delivery_session)


@contextmanager
def authority(user):
    old = frappe.flags.get('hbos_iam_temporary_authority')
    frappe.flags.hbos_iam_temporary_authority = user
    try:
        yield
    finally:
        frappe.flags.hbos_iam_temporary_authority = old


def guard_user_fields(doc, method=None):
    if not available():
        return
    old = doc.get_doc_before_save()
    changed = any(doc.get(key) != (old.get(key) if old else None)
                  and (old or doc.get(key) not in (None, '', 0, False)) for key in FIELDS)
    if changed and frappe.flags.get('hbos_iam_temporary_authority') != doc.name:
        frappe.throw('临时密码状态仅能通过受控账号服务修改。', frappe.PermissionError)


def mark_initial(user):
    """Called only for a newly created verified enterprise User, before commit."""
    if not available():
        frappe.throw('初始密码状态尚未迁移，开户未完成。')
    frappe.db.set_value('User', user, dict(zip(FIELDS, (1, 0, None, 0))))


def issue(user):
    """Caller locks/authorizes User and owns transaction; only return is secret."""
    from frappe.utils.password import update_password
    from frappe.core.doctype.user.user import test_password_strength, handle_password_test_fail
    from hbos_portal.auth.accounts import invalidate_user_tickets, revoke_sessions
    if not available():
        frappe.throw('临时密码状态尚未迁移。')
    current = status(user)
    password = secrets.token_urlsafe(32) + 'aA7!'
    expires = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=24)
    tested = test_password_strength(password, user_data=frappe.db.get_value('User', user, ['first_name', 'middle_name', 'last_name', 'email', 'birth_date'], for_update=True))
    feedback = tested.get('feedback')
    if feedback and not feedback.get('password_policy_validation_passed', False):
        handle_password_test_fail(feedback)
    # Native service has no internal commit in the frozen Frappe source.
    update_password(user, password)
    frappe.db.set_value('User', user, dict(zip(FIELDS, (1, 1, expires, current['generation'] + 1))))
    frappe.db.set_value('User', user, 'reset_password_key', '', update_modified=False)
    invalidate_user_tickets(user)
    revoke_sessions(user)
    return dict(temporary_password=password, expires_at=expires, generation=current['generation'] + 1)


def claim_initial_password():
    from hbos_portal.auth.accounts import require_post, require_user, no_store
    require_post()
    user = require_user()
    no_store()
    frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE', (user,))
    current = status(user)
    if not current['can_claim']:
        return dict(claimed=False, generation=current['generation'], expires_at=current['expires_at'])
    # Entitlement is a server-created enterprise OAuth Session, not a user ID
    # in an HTTP argument. Native password sessions cannot claim new secrets.
    if not frappe.session.data.get('hbos_iam_initial_delivery'):
        frappe.throw('请通过已验证的本企业飞书会话领取初始密码。', frappe.PermissionError)
    result = issue(user)
    # Rotate the same verified caller using the standard Session machinery.
    # Preserve any already verified custody MFA; no password/MFA bypass flag.
    frappe.db.commit()
    frappe.local.login_manager.login_as(user)
    return dict(claimed=True, **result)


def on_password_changed(user):
    if not available():
        return
    generation = status(user)['generation']
    frappe.db.set_value('User', user, {FIELDS[0]: 0, FIELDS[1]: 0, FIELDS[2]: None, FIELDS[3]: generation + 1})


def check_login(login_manager=None):
    if not available():
        return
    user = login_manager.user if login_manager else frappe.session.user
    current = status(user)
    if current['temporary']:
        if not current['expires_at'] or frappe.utils.get_datetime(current['expires_at']) <= frappe.utils.now_datetime():
            # OAuth can still authenticate for account recovery, but the
            # business gate remains pending. Password authentication expires.
            from hbos_portal.auth.accounts import has_password
            if frappe.flags.get('hbos_iam_verified_oauth_login') != user and has_password(user):
                frappe.throw('临时密码已过期，请通过账号恢复或管理员重置。', frappe.AuthenticationError)


def check_credentials(user):
    if not available():
        return
    current = status(user)
    if current['temporary'] and (not current['expires_at'] or frappe.utils.get_datetime(current['expires_at']) <= frappe.utils.now_datetime()):
        frappe.throw('临时密码已过期，请使用受控恢复或重置流程。', frappe.AuthenticationError)


def on_session_creation(login_manager=None):
    if not available():
        return
    user = login_manager.user if login_manager else frappe.session.user
    current = status(user)
    if (current['pending'] and not current['temporary'] and not current['generation']
            and frappe.flags.get('hbos_iam_verified_oauth_login') == user
            and frappe.session.user == user):
        frappe.session.data['hbos_iam_initial_delivery'] = 1
        frappe.local.session_obj._update_in_cache = True


def check_request():
    user = frappe.session.user
    if user == 'Guest' or not available() or not status(user)['pending']:
        return
    cmd = str(frappe.local.form_dict.get('cmd') or '')
    path = str(getattr(frappe.local.request, 'path', '') or '')
    route_cmd = path[len('/api/method/'):] if path.startswith('/api/method/') else cmd if path == '/api/method' else ''
    if route_cmd in PENDING_METHODS and (not cmd or cmd == route_cmd):
        return
    # Serve the existing SPA so its FirstPasswordGate can render, never Desk,
    # native REST, bootstrap business projections or arbitrary auth methods.
    if not cmd and (path in {'/hbos', '/hbos/', '/hbos/profile', '/hbos/login', '/hbos/reset-password'} or path.startswith('/assets/')):
        return
    frappe.throw('请先完成初始密码领取与首次改密，暂不能访问业务数据。', frappe.PermissionError)
