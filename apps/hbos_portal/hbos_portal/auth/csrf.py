"""Close the initial CSRF-token gap for authenticated Frappe sessions."""

import hmac
from datetime import datetime, timezone
from urllib.parse import unquote

import frappe


def _previous_session_token(sid):
    from frappe.sessions import get_expired_threshold, get_expiry_in_seconds

    sid = unquote(sid)
    cached = frappe.cache.hget("session", sid)
    if cached:
        data = cached.get("data")
    else:
        sessions = frappe.qb.DocType("Sessions")
        records = (
            frappe.qb.from_(sessions)
            .select(sessions.sessiondata)
            .where(sessions.sid == sid)
            .where(sessions.status == "Active")
            .where(sessions.lastupdate > get_expired_threshold())
            .limit(1)
        ).run()
        if not records:
            return None
        try:
            data = frappe.parse_json(records[0][0])
        except (TypeError, ValueError):
            return None
    try:
        if not isinstance(data, dict):
            return None
        if cached and not data.get("last_updated"):
            return None
        if data.get("last_updated") and frappe.utils.time_diff_in_seconds(
            frappe.utils.now(), data["last_updated"]
        ) > get_expiry_in_seconds(data.get("session_expiry")):
            return None
        if data.get("session_end") and datetime.now(timezone.utc) > datetime.fromisoformat(data["session_end"]):
            return None
        return data.get("csrf_token")
    except (AttributeError, TypeError, ValueError):
        return None


def require_native_login_csrf(login_manager=None):
    request = getattr(frappe.local, "request", None)
    if not request:
        return
    incoming_sid = request.cookies.get("sid")
    if incoming_sid in (None, "", "Guest"):
        return
    supplied = request.headers.get("X-Frappe-CSRF-Token") or frappe.form_dict.get("csrf_token")
    expected = _previous_session_token(incoming_sid) if supplied else None
    if isinstance(supplied, str) and isinstance(expected, str) and hmac.compare_digest(
        supplied.encode("utf-8"), expected.encode("utf-8")
    ):
        return
    frappe.flags.disable_traceback = True
    frappe.throw("安全会话尚未确认，请刷新后重试。", frappe.CSRFTokenError)


def require_initialized_session_token():
    request = getattr(frappe.local, "request", None)
    if not request or request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    session = getattr(frappe.local, "session", None)
    if not session or not session.user or session.user == "Guest":
        return

    # Native login has already checked the incoming session in before_login.
    native_login = request.path == "/api/method/login" or frappe.form_dict.get("cmd") == "login"
    if native_login:
        return

    data = session.get("data") or {}
    if not data.get("csrf_token"):
        frappe.flags.disable_traceback = True
        frappe.throw("安全会话尚未初始化，请刷新后重试。", frappe.CSRFTokenError)
