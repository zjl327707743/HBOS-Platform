"""Knowledge-only compatibility with the deployed V4 native Frappe session.

This view marker is never an authorization credential. Business API permission,
native session validity, CSRF and document policy remain independently checked.
No IAM provisioning, role, temporary-password or login implementation is added.
"""
import hashlib
import hmac

import frappe

from .shared_reference import configuration


def _enabled():
    if configuration().get('knowledge_native_session_compat') is not True:
        frappe.throw('此会话兼容入口未启用。', frappe.PermissionError)
    frappe.local.response_headers['Cache-Control'] = 'private, no-store, max-age=0'


def _context(user):
    # Existing knowledge server secret; the legacy site need not have Frappe's
    # optional encryption_key. No new key or credential is exposed to the UI.
    key = configuration().get('proof_key')
    sid = frappe.session.sid
    if not key or not sid or sid == 'Guest':
        frappe.throw('当前会话无法确认，请重新登录。', frappe.AuthenticationError)
    message = '\0'.join(('hbos-knowledge-native-session-v1', str(frappe.local.site), user, sid))
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_request_security():
    _enabled()
    user = frappe.session.user
    authenticated = bool(user and user != 'Guest' and frappe.db.get_value('User', user, 'enabled'))
    return {'authenticated': authenticated,
            'session_context': _context(user) if authenticated else None,
            'csrf_token': frappe.sessions.get_csrf_token() if authenticated else None}


@frappe.whitelist(methods=['GET'])
def get_security():
    _enabled()
    fact = get_request_security()
    if not fact['authenticated']:
        frappe.throw('请重新登录。', frappe.AuthenticationError)
    # Reuse the installed Portal's account/security checks rather than copying
    # password, MFA, identity-linking or account recovery behavior.
    from hbos_portal.auth.accounts import get_security as native_security
    status = dict(native_security())
    if status.get('user') != frappe.session.user:
        frappe.throw('当前会话已改变，请重新登录。', frappe.AuthenticationError)
    status['session_context'] = fact['session_context']
    status['knowledge_session_contract'] = 'native-v4-v1'
    return status
