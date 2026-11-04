"""Target-scoped authorization versions and custody MFA; native roles stay native."""
from __future__ import annotations

import secrets
import time
from urllib.parse import unquote

import frappe

MFA_COOKIE = 'hbos_custody_mfa_browser'
MFA_TTL = 180


def record(user: str, *, lock: bool = False):
    if not frappe.db.exists('DocType', 'HBOS Account Security'):
        return None
    rows = frappe.db.sql('SELECT name,security_version,custody_mode,blocked,mfa_counter FROM `tabHBOS Account Security` WHERE user=%s' + (' LOCK IN SHARE MODE' if lock else ''), (user,), as_dict=True)
    return rows[0] if rows else None


def ensure(user: str):
    if not frappe.db.exists('DocType', 'HBOS Account Security'):
        frappe.throw('账号变更结构尚未迁移，请管理员先备份并部署。', frappe.PermissionError)
    if not record(user):
        old = frappe.flags.get('hbos_security_authority')
        frappe.flags.hbos_security_authority = user
        try:
            frappe.get_doc({'doctype': 'HBOS Account Security', 'user': user,
                'security_version': 0, 'custody_mode': 0, 'blocked': 0}).insert(ignore_permissions=True)
        finally:
            frappe.flags.hbos_security_authority = old
    return record(user)


def assert_available(user: str) -> None:
    row = record(user)
    if row and row.blocked:
        frappe.throw('此账号正在完成受控交接，请稍后重新登录。', frappe.AuthenticationError)


def check_request() -> None:
    user = frappe.session.user
    if user == 'Guest':
        return
    row = record(user, lock=True)
    if not row:
        return
    if row.blocked:
        frappe.throw('账号正在交接，请重新登录。', frappe.AuthenticationError)
    # API credentials are revoked in the same cutover transaction. Cookie
    # sessions also carry the version; pre-cutover in-flight DB transactions
    # hold this shared lock until they finish before the exclusive cutover.
    # A header alone is not proof of API authentication: native Frappe can
    # retain a cookie session after an unrecognized/invalid bearer header.
    # Fresh API auth has Guest sid; every cookie sid must match its version.
    cookie_session = bool(frappe.session.sid and frappe.session.sid != 'Guest')
    if cookie_session and int(frappe.session.data.get('hbos_security_version') or 0) != row.security_version:
        frappe.throw('账号登录方式已更换，旧会话已失效。', frappe.AuthenticationError)


def on_session_creation(login_manager=None) -> None:
    user = login_manager.user if login_manager else frappe.session.user
    row = record(user)
    if row:
        frappe.session.data['hbos_security_version'] = row.security_version
        # Persist through the standard Session object, including its cache.
        frappe.local.session_obj._update_in_cache = True


def require_custody_mfa_for_login(user: str) -> None:
    row = record(user)
    if (row and row.custody_mode or administrator_native_mfa(user)) and frappe.flags.get('hbos_custody_mfa_verified') != (user, row.security_version if row else 0):
        frappe.throw('请从 HBOS 登录页完成保管人二次认证，不能通过其他登录入口绕过。', frappe.AuthenticationError)


def administrator_native_mfa(user: str) -> bool:
    if user != 'Administrator':
        return False
    from frappe.twofactor import get_default
    return bool(get_default(user + '_otplogin') and get_default(user + '_otpsecret'))


def requires_mfa(user: str) -> bool:
    from frappe.twofactor import should_run_2fa
    row = record(user)
    return bool(row and row.custody_mode) or administrator_native_mfa(user) or should_run_2fa(user)


def verify_custody_mfa(user: str, *, otp: str = '', tmp_id: str = '') -> dict | None:
    """Frappe exempts built-in Administrator from native 2FA. Custody does not."""
    import pyotp
    from hbos_portal.auth.accounts import digest, epoch, session_digest

    row = record(user)
    legacy = administrator_native_mfa(user)
    if not (row and row.custody_mode or legacy):
        return None
    if not row:
        row = ensure(user)
    nonce = unquote(str(frappe.local.request.cookies.get(MFA_COOKIE) or ''))
    if not otp:
        nonce = secrets.token_urlsafe(32)
        tmp_id = 'custody_' + secrets.token_urlsafe(24)
        frappe.cache.set_value('hbos:custody:mfa:' + digest(tmp_id), {
            'user': user, 'browser': digest(nonce), 'session': session_digest(),
            'version': row.security_version, 'epoch': epoch(user)}, expires_in_sec=MFA_TTL)
        frappe.local.cookie_manager.set_cookie(MFA_COOKIE, nonce, httponly=True, samesite='Lax', max_age=MFA_TTL)
        return {'mfa_required': True, 'tmp_id': tmp_id, 'verification': {'method': 'OTP App'}}
    key = 'hbos:custody:mfa:' + digest(tmp_id)
    challenge = frappe.cache.get_value(key) if tmp_id.startswith('custody_') else None
    if not challenge or challenge['user'] != user or challenge['browser'] != digest(nonce) or challenge['session'] != session_digest() or challenge['epoch'] != epoch(user) or challenge['version'] != row.security_version:
        frappe.throw('二次认证已过期或浏览器不匹配。', frappe.AuthenticationError)
    doc = frappe.get_doc('HBOS Account Security', row.name)
    secret = doc.get_password('mfa_secret', raise_exception=False) if row.custody_mode else None
    if not secret and legacy:
        from frappe.twofactor import get_otpsecret_for_
        secret = get_otpsecret_for_(user)  # Existing enrollment only; never reset it.
    totp = pyotp.TOTP(secret) if secret else None
    counter = int(time.time() // 30)
    if not totp or not totp.verify(str(otp), valid_window=0):
        frappe.throw('保管人二次认证无效。', frappe.AuthenticationError)
    locked = frappe.db.sql('SELECT mfa_counter,security_version FROM `tabHBOS Account Security` WHERE name=%s FOR UPDATE', (row.name,))
    if not locked or locked[0][1] != row.security_version or int(locked[0][0] or 0) >= counter:
        frappe.throw('二次认证验证码已使用，请使用下一个验证码。', frappe.AuthenticationError)
    if not frappe.cache.set(frappe.cache.make_key(key + ':claim'), '1', nx=True, ex=MFA_TTL):
        frappe.throw('二次认证已使用。', frappe.AuthenticationError)
    frappe.cache.delete_value(key)
    frappe.db.set_value('HBOS Account Security', row.name, 'mfa_counter', counter, update_modified=False)
    frappe.flags.hbos_custody_mfa_verified = (user, row.security_version)
    frappe.local.cookie_manager.delete_cookie(MFA_COOKIE)
    return None


def advance_version(user: str) -> None:
    row = ensure(user)
    frappe.db.sql('UPDATE `tabHBOS Account Security` SET security_version=security_version+1 WHERE name=%s', (row.name,))
    from hbos_portal.auth.accounts import invalidate_user_tickets, revoke_sessions
    invalidate_user_tickets(user)
    revoke_sessions(user)
    frappe.db.set_value('User', user, 'reset_password_key', '', update_modified=False)


def session_for_verified_user(user: str) -> None:
    # Caller has already completed verify_mfa in this request; the flag is
    # server-only and cannot be supplied through Document.flags or REST JSON.
    require_custody_mfa_for_login(user)
    frappe.local.login_manager.login_as(user)
