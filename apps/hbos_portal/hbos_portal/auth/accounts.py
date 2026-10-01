"""Account ownership proofs around standard Frappe Users, passwords and sessions.

No OAuth cookie or fresh authorization code is treated as strong reauthentication.
Passwordless step-up uses a one-time code delivered to the bound Feishu inbox.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from contextlib import contextmanager
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

import frappe
from frappe.rate_limiter import rate_limit

PROOF_TTL = 300
PENDING_COOKIE = "hbos_account_pending"
PENDING_TTL = 480
RECOVERY_TTL = 900
RECOVERY_COOKIE = "hbos_account_recovery"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def epoch(user: str) -> int:
    # INCR uses raw Redis integers, not Frappe's pickled get_value/set_value.
    return int(frappe.cache.get(frappe.cache.make_key(f"hbos:account:epoch:{user}")) or 0)


def session_digest() -> str:
    return digest(str(frappe.session.sid))


def require_user(user: str | None = None, *, external: bool = False) -> str:
    user = user or frappe.session.user
    if not user or user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
        frappe.throw("账号不可用，请重新登录。", frappe.AuthenticationError)
    from hbos_portal.auth.security import assert_available
    assert_available(user)
    if external:
        from hbos_portal.services.internal_users import load_internal_user_decision

        if user == "Administrator":
            if not frappe.conf.get("hbos_feishu_allow_administrator_link"):
                frappe.throw("管理员飞书绑定尚未由 Owner 专门启用。", frappe.PermissionError)
        elif not load_internal_user_decision(user).allowed:
            # Existing privileged business users retain their authorization;
            # service/external users still fail the internal-account policy.
            roles = set(frappe.get_roles(user))
            if "System Manager" not in roles or not frappe.conf.get("hbos_feishu_allow_privileged_link"):
                frappe.throw("此账号未获准使用飞书入口。", frappe.PermissionError)
    return user


def require_post() -> None:
    frappe.flags.disable_traceback = True
    # Python arguments have already been bound by Frappe's dispatcher. Remove
    # credential values from the request metadata before any diagnostic error.
    for field in ("password", "pwd", "new_password", "old_password", "confirmation", "invitation", "key", "code", "otp", "tmp_id", "recovery_context"):
        frappe.local.form_dict.pop(field, None)
    request = frappe.local.request
    if request.method != "POST":
        frappe.throw("请使用安全的 POST 请求。", frappe.PermissionError)
    # Guest requests have no persistent Frappe session CSRF token. They use
    # same-origin JSON + an independent server-issued, cookie-bound CSRF token.
    origin = request.headers.get("Origin")
    configured_origin = str(frappe.conf.get("hbos_portal_origin") or "").rstrip("/")
    allowed = {configured_origin} if configured_origin else {f"{request.scheme}://{request.host}"}
    if frappe.conf.get("hbos_account_test_site"):
        for value in frappe.conf.get("hbos_portal_development_origins") or []:
            parsed = urlsplit(value)
            if parsed.hostname == "localhost" or str(parsed.hostname).endswith(".localhost"):
                allowed.add(str(value).rstrip("/"))
    if not origin or origin.rstrip("/") not in allowed or urlsplit(origin).hostname != urlsplit(f"//{request.host}").hostname:
        frappe.throw("请求来源无效。", frappe.CSRFTokenError)
    if frappe.session.user == "Guest" and (not request.is_json or request.headers.get("X-Requested-With") != "XMLHttpRequest"):
        frappe.throw("请使用同源 JSON 请求。", frappe.CSRFTokenError)
    if frappe.session.user != "Guest":
        token = request.headers.get("X-Frappe-CSRF-Token") or ""
        expected = str(frappe.session.data.get("csrf_token") or "")
        if not expected or not secrets.compare_digest(token, expected):
            frappe.throw("安全会话已更新，请刷新后重试。", frappe.CSRFTokenError)


def no_store() -> None:
    frappe.local.response_headers["Cache-Control"] = "private, no-store, max-age=0"


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_request_security() -> dict:
    no_store()
    return {"csrf_token": frappe.sessions.get_csrf_token() if frappe.session.user != "Guest" else None}


def has_password(user: str) -> bool:
    # Query only existence; a hash must never leave Frappe's password service.
    return bool(frappe.db.sql(
        "SELECT 1 FROM `__Auth` WHERE doctype='User' AND name=%s "
        "AND fieldname='password' AND encrypted=0 LIMIT 1", (user,)
    ))


def audit(action: str, user: str | None = None, *, status: str = "Success") -> None:
    from frappe.core.doctype.activity_log.activity_log import add_authentication_log

    add_authentication_log(f"HBOS account: {action}", user or frappe.session.user, status=status)


def _proof_key(user: str) -> str:
    return f"hbos:account:proof:{digest(user)}:{session_digest()}"


def save_proof(user: str, method: str) -> None:
    from hbos_portal.auth.security import administrator_native_mfa, record
    row = record(user)
    current_version = row.security_version if row else 0
    requires_verified_mfa = bool(row and row.custody_mode) or administrator_native_mfa(user)
    version = current_version if requires_verified_mfa and frappe.flags.get('hbos_custody_mfa_verified') == (user, current_version) else None
    frappe.cache.set_value(_proof_key(user), {
        "user": user, "method": method, "epoch": epoch(user), "verified_at": int(time.time()), "nonce": secrets.token_hex(16), 'custody_version': version,
    }, expires_in_sec=PROOF_TTL)


def require_proof(user: str, *, consume: bool = False) -> dict:
    proof = frappe.cache.get_value(_proof_key(user))
    if not proof or proof.get("user") != user or proof.get("epoch") != epoch(user) or int(proof.get("verified_at", 0)) + PROOF_TTL < time.time():
        frappe.throw("请先重新验证本人身份。", frappe.AuthenticationError)
    from hbos_portal.auth.security import administrator_native_mfa, record
    row = record(user)
    if bool(row and row.custody_mode) or administrator_native_mfa(user):
        version = row.security_version if row else 0
        if proof.get('custody_version') != version:
            frappe.throw('请重新完成保管人二次认证。', frappe.AuthenticationError)
        frappe.flags.hbos_custody_mfa_verified = (user, version)
    if consume:
        # Use the same atomic browser-bound store primitive for consumption.
        claim = f"hbos:account:proof-claim:{digest(_proof_key(user))}:{proof['nonce']}"
        if not frappe.cache.set(frappe.cache.make_key(claim), "1", ex=PROOF_TTL, nx=True):
            frappe.throw("身份验证已使用，请重新验证。", frappe.AuthenticationError)
        frappe.cache.delete_value(_proof_key(user))
    return proof


def proof_status(user: str) -> dict:
    """Read the same browser/epoch/TTL authority used by sensitive writes.

    No nonce, credential or cache key is exposed. Reading never consumes or
    extends a proof; another tab's consumption is therefore visible here.
    """
    try:
        proof = require_proof(user)
    except frappe.AuthenticationError:
        # require_proof deliberately throws for writes. This read has a normal
        # expired state and must not leave framework error messages behind.
        frappe.clear_messages()
        return {"valid": False, "expires_in": 0, "method": None}
    remaining = max(0, int(proof["verified_at"] + PROOF_TTL - time.time()))
    return {"valid": remaining > 0, "expires_in": remaining,
        "method": proof["method"] if remaining > 0 else None}


@contextmanager
def _form(values: dict):
    original = dict(frappe.local.form_dict)
    frappe.local.form_dict.clear()
    frappe.local.form_dict.update(values)
    try:
        yield
    finally:
        frappe.local.form_dict.clear()
        frappe.local.form_dict.update({k: v for k, v in original.items() if k not in {"password", "pwd", "new_password", "old_password", "otp", "code"}})


def _manager():
    from frappe.auth import LoginManager

    manager = object.__new__(LoginManager)
    for name in LoginManager.__slots__:
        setattr(manager, name, None)
    return manager


def verify_mfa(user: str, *, otp: str = "", tmp_id: str = "", password: str = "") -> dict | None:
    from frappe.twofactor import authenticate_for_2factor, confirm_otp_token, should_run_2fa

    from hbos_portal.auth.security import record, verify_custody_mfa, administrator_native_mfa
    row = record(user)
    if row and row.custody_mode or administrator_native_mfa(user):
        return verify_custody_mfa(user, otp=otp, tmp_id=tmp_id)
    if not should_run_2fa(user):
        return None
    manager = _manager()
    manager.user = user
    if otp:
        cached_user = frappe.safe_decode(frappe.cache.get(tmp_id + "_usr")) if tmp_id else ""
        if cached_user != user or not confirm_otp_token(manager, otp=otp, tmp_id=tmp_id):
            frappe.throw("二次认证无效或已过期。", frappe.AuthenticationError)
        for suffix in ("_usr", "_pwd", "_otp_secret", "_token"):
            frappe.cache.delete(tmp_id + suffix)
        return None
    with _form({"pwd": password or secrets.token_urlsafe(32)}):
        authenticate_for_2factor(user)
    return {"mfa_required": True, "tmp_id": frappe.local.response.get("tmp_id"), "verification": frappe.local.response.get("verification")}


def verify_credentials(username: str, password: str, *, otp: str = "", tmp_id: str = "") -> tuple[str, dict | None]:
    manager = _manager()
    manager.authenticate(user=username, pwd=password)
    user = require_user(manager.user)
    return user, verify_mfa(user, otp=otp, tmp_id=tmp_id, password=password)


def _pending_key(nonce: str) -> str:
    return f"hbos:account:pending:{digest(nonce)}"


def create_pending(identity: dict, *, intent: str, redirect_to: str, user: str | None = None, verified_at: int = 0) -> None:
    nonce = secrets.token_urlsafe(32)
    record = {
        "identity": identity, "intent": intent, "redirect_to": redirect_to,
        "user": user, "epoch": epoch(user) if user else None,
        "session_digest": session_digest() if user else None,
        "verified_at": verified_at, "created_at": int(time.time()),
        "csrf": secrets.token_urlsafe(32),
    }
    frappe.cache.set_value(_pending_key(nonce), record, expires_in_sec=PENDING_TTL)
    frappe.local.cookie_manager.set_cookie(PENDING_COOKIE, nonce, httponly=True, samesite="Lax", max_age=PENDING_TTL)


def pending(*, write: bool = False) -> tuple[str, dict]:
    nonce = unquote(str(frappe.local.request.cookies.get(PENDING_COOKIE) or ""))
    record = frappe.cache.get_value(_pending_key(nonce)) if nonce and len(nonce) < 128 else None
    # Invalid operation tickets do not invalidate an authenticated account.
    # Frappe clears login cookies for AuthenticationError.
    if not record or record["created_at"] + PENDING_TTL < time.time():
        frappe.throw("待绑定身份已过期，请重新发起飞书授权。", frappe.ValidationError)
    if record.get("user"):
        require_user(record["user"])
        if record["epoch"] != epoch(record["user"]) or record["session_digest"] != session_digest() or (record["intent"] == "link" and record["user"] != frappe.session.user):
            frappe.throw("绑定会话已变化，请重新验证。", frappe.ValidationError)
        if record["intent"] == "link" and record["verified_at"] + PROOF_TTL < time.time():
            frappe.throw("本人身份验证已过期。", frappe.ValidationError)
    if write:
        require_post()
        token = frappe.local.request.headers.get("X-HBOS-Pending-CSRF") or ""
        if not secrets.compare_digest(token, record["csrf"]):
            frappe.throw("待绑定请求安全校验失败。", frappe.CSRFTokenError)
    return nonce, record


def consume_pending(nonce: str) -> None:
    claim = f"hbos:account:pending-claim:{digest(nonce)}"
    if not frappe.cache.set(frappe.cache.make_key(claim), "1", ex=PENDING_TTL, nx=True):
        frappe.throw("请求已使用，请重新授权。", frappe.ValidationError)
    frappe.cache.delete_value(_pending_key(nonce))
    frappe.local.cookie_manager.delete_cookie(PENDING_COOKIE)


def identity_row(settings, identity: dict, *, lock: bool = False):
    from hbos_portal.auth.feishu import identity_key

    key = identity_key(provider="feishu", tenant_key=identity["tenant_key"], app_id=settings.app_id, id_type="open_id", external_id=identity["open_id"])
    return frappe.db.get_value("HBOS External Identity", {"identity_key": key}, ["name", "user", "enabled"], as_dict=True, **({'for_update': True} if lock else {}))


def bind_identity(settings, identity: dict, user: str) -> str:
    from hbos_portal.auth.feishu import FeishuLoginError

    require_user(user, external=True)
    # Serialize competing bindings to one User, then let DB unique constraints
    # arbitrate the same external identity requested by two different Users.
    locked = frappe.db.sql("SELECT enabled FROM `tabUser` WHERE name=%s FOR UPDATE", (user,))
    if not locked or not locked[0][0]:
        frappe.throw("账号已停用。", frappe.AuthenticationError)
    row = identity_row(settings, identity)
    if row and row.user != user:
        raise FeishuLoginError("identity_conflict", "飞书身份已绑定其他账号，不能转移。")
    if row and not row.enabled and frappe.db.get_value('HBOS External Identity', row.name, 'retired_reason') in {'replaced', 'custody'}:
        raise FeishuLoginError('identity_revoked', '已替换身份须通过新的受控换绑或普通账号归属流程，不能直接恢复旧关系。')
    existing = frappe.get_all("HBOS External Identity", filters={"provider": "feishu", "tenant_key": settings.tenant_key, "app_id": settings.app_id, "user": user, "enabled": 1}, fields=["name"], limit=2)
    if any(item.name != (row.name if row else None) for item in existing):
        raise FeishuLoginError("identity_conflict", "当前账号已经绑定另一飞书身份。")
    doc = frappe.get_doc("HBOS External Identity", row.name) if row else frappe.get_doc({
        "doctype": "HBOS External Identity", "provider": "feishu", "tenant_key": settings.tenant_key,
        "app_id": settings.app_id, "id_type": "open_id", "external_id": identity["open_id"], "user": user,
    })
    doc.enabled = 1
    doc.last_verified_at = frappe.utils.now_datetime()
    # Document.flags can arrive in REST JSON; the authority must live in the
    # trusted server request context, with the exact verified identity tuple.
    original_authority = frappe.flags.get("hbos_identity_authority")
    frappe.flags.hbos_identity_authority = tuple(doc.get(k) for k in ("provider", "tenant_key", "app_id", "id_type", "external_id", "user"))
    try:
        doc.save(ignore_permissions=True) if row else doc.insert(ignore_permissions=True)
    finally:
        frappe.flags.hbos_identity_authority = original_authority
    audit("link", user)
    return user


def _bound_identity(user: str, *, lock: bool = False):
    from hbos_portal.auth.feishu import load_settings

    settings = load_settings()
    return frappe.db.get_value("HBOS External Identity", {
        "provider": "feishu", "tenant_key": settings.tenant_key, "app_id": settings.app_id,
        "user": user, "enabled": 1,
    }, ["name", "external_id"], as_dict=True, **({'for_update': True} if lock else {}))


def _write_receipt(user: str, request_id: str, action: str, *, save=False):
    if not request_id:
        return None
    # An identifier is an idempotency key, never an authorization credential.
    # Receipts are only readable after ordinary authorization for the same User.
    from uuid import UUID
    try:
        UUID(request_id)
    except (ValueError, TypeError, AttributeError):
        frappe.throw("提交编号无效，请重新打开安全操作。")
    key = "hbos:account:write-result:" + digest(user + ":" + request_id)
    if save:
        try:
            frappe.cache.set_value(key, {"completed": True, "action": action}, expires_in_sec=RECOVERY_TTL)
        except Exception:
            # The SQL mutation is committed; a receipt failure cannot undo it
            # or turn the successful response into an instruction to repeat it.
            pass
        return None
    result = frappe.cache.get_value(key)
    if result and action and result.get("action") != action:
        frappe.throw("此提交编号已用于另一项安全操作。")
    return result


@frappe.whitelist(methods=["GET"])
def get_security(request_id: str = "") -> dict:
    no_store()
    user = require_user()
    from hbos_portal.auth.feishu import load_settings

    settings = load_settings()
    account = frappe.get_doc("User", user)
    bound = _bound_identity(user)
    return {"user": user, "login_name": account.username or user, "has_password": has_password(user),
        "password_login_available": has_password(user) and not bool(frappe.get_system_settings("disable_user_pass_login")),
        "proof": proof_status(user),
        "write_result": _write_receipt(user, request_id, ""),
        "feishu_bound": bool(bound), "feishu_configured": settings.configured,
        "feishu_stepup_available": bool(bound and settings.configured and frappe.conf.get("hbos_feishu_inbox_recovery_enabled")),
        "desk_access": account.user_type == "System User", "administrator": user == "Administrator",
        "administrator_link_enabled": bool(frappe.conf.get("hbos_feishu_allow_administrator_link")),
        "mail_recovery_available": verified_recovery_email(user),
        "feishu_disable_sync": "enabled_5_minutes" if frappe.conf.get("hbos_feishu_disable_sync_enabled") else "not_configured", "can_admin_recover": user == "Administrator" or "System Manager" in frappe.get_roles(user)}


@frappe.whitelist(methods=["POST"])
def admin_issue_recovery(user: str, reason: str, request_id: str = '') -> dict:
    require_post()
    administrator = require_user()
    if administrator != "Administrator" and "System Manager" not in frappe.get_roles(administrator):
        frappe.throw("仅管理员可执行受控恢复。", frappe.PermissionError)
    if _write_receipt(administrator, request_id, 'recovery_issue'):
        return {'already_issued': True, 'recovery_url': '', 'target': None, 'expires_in': 0}
    proof = require_proof(administrator, consume=True)
    if proof["method"] != "password":
        frappe.throw("签发恢复链接须重新验证管理员密码及原有二次认证。", frappe.AuthenticationError)
    # The form accepts the employee's login alias as well as canonical User ID.
    # A bad target is a workflow validation error, not the issuer's login error.
    user = str(user or '').strip()
    user = user if frappe.db.exists('User', user) else frappe.db.get_value('User', {'username': user}, 'name')
    if not user:
        frappe.throw('未找到该员工账号，请核对登录名或账号。', frappe.ValidationError)
    try:
        require_user(user)
    except (frappe.AuthenticationError, frappe.PermissionError):
        frappe.throw('该员工账号当前不可恢复，请核对启用状态和归属。', frappe.ValidationError)
    if user == "Administrator" or len(str(reason).strip()) < 12:
        frappe.throw("Administrator 保留原生应急恢复；其他账号恢复须填写身份核验依据。")
    doc = frappe.get_doc("User", user)
    link = doc._reset_password(send_email=False)
    audit("administrator_recovery_issued", user)
    frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "User", "reference_name": user, "content": "管理员受控恢复：" + frappe.utils.escape_html(reason[:1000])}).insert(ignore_permissions=True)
    frappe.db.commit()
    _write_receipt(administrator, request_id, 'recovery_issue', save=True)
    no_store()
    return {"recovery_url": recovery_url(link), "target": recovery_target(doc), "expires_in": RECOVERY_TTL, "delivery": "仅私下交付给已核验的账号本人；管理员不设置员工密码"}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=8, seconds=300)
def reauthenticate(password: str, otp: str = "", tmp_id: str = "") -> dict:
    require_post()
    user = require_user()
    verified, challenge = verify_credentials(user, password, otp=otp, tmp_id=tmp_id)
    if challenge:
        return challenge
    if verified != user:
        frappe.throw("账号验证失败。", frappe.AuthenticationError)
    save_proof(user, "password")
    audit("reauthenticate", user)
    return {"verified": True, "expires_in": PROOF_TTL}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_pending() -> dict:
    no_store()
    _, record = pending()
    return {"intent": record["intent"], "user": record.get("user"), "display_name": record["identity"].get("display_name"), "csrf": record["csrf"], "expires_in": max(0, record["created_at"] + PENDING_TTL - int(time.time()))}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=8, seconds=300)
def complete_pending(action: str, username: str = "", password: str = "", otp: str = "", tmp_id: str = "") -> dict:
    from hbos_portal.auth.feishu import FeishuLoginError, load_settings

    nonce, record = pending(write=True)
    if action == "cancel":
        consume_pending(nonce)
        no_store()
        return {"cancelled": True}
    settings = load_settings()
    if not settings.configured:
        frappe.throw("飞书配置尚未完成。", frappe.AuthenticationError)
    if record["intent"] == "link":
        if action != "confirm_link":
            frappe.throw("请确认绑定当前账号。", frappe.PermissionError)
        user = require_user(record["user"], external=True)
    elif record["intent"] == "login_mfa":
        if action != "login_mfa":
            frappe.throw("请完成二次认证。", frappe.PermissionError)
        user = require_user(record["user"], external=True)
        row = identity_row(settings, record["identity"])
        if not row or not row.enabled or row.user != user:
            frappe.throw("飞书绑定已撤销。", frappe.AuthenticationError)
        challenge = verify_mfa(user, otp=otp, tmp_id=tmp_id)
        if challenge:
            return challenge
    elif action == "bind_existing":
        user, challenge = verify_credentials(username, password, otp=otp, tmp_id=tmp_id)
        if challenge:
            return challenge
        require_user(user, external=True)
    elif action == "create_new":
        # Compatibility for an already issued pre-upgrade pending cookie.
        # The same service handles current automatic onboarding, tombstones,
        # concurrency and permanent ordinary Users; there is no second path.
        from hbos_portal.auth.onboarding import resolve_verified_login
        user, created = resolve_verified_login(settings, record["identity"])
    else:
        frappe.throw("请明确选择绑定已有账号或新开户。", frappe.PermissionError)
    try:
        if record["intent"] != "login_mfa" and action != "create_new":
            bind_identity(settings, record["identity"], user)
        from hbos_portal.auth.profile import sync_verified_avatar
        sync_verified_avatar(user, record["identity"])
        consume_pending(nonce)
        frappe.db.commit()
        if record["intent"] != "link":
            frappe.local.login_manager.login_as(user)
        return {"completed": True, "user": user, "login_name": frappe.db.get_value("User", user, "username") or user,
            "password_optional": not has_password(user), "created": created if action == "create_new" else False, "redirect_to": record["redirect_to"]}
    except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
        frappe.db.rollback()
        frappe.throw("绑定发生并发冲突，请重新登录后核对。", frappe.AuthenticationError)
    except FeishuLoginError as exc:
        frappe.db.rollback()
        return {"completed": False, "error": {"code": exc.code, "message": exc.public_message}}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=3, seconds=300)
def request_feishu_code() -> dict:
    require_post()
    user = require_user()
    from hbos_portal.auth.feishu import load_settings, send_inbox_code

    settings = load_settings()
    row = _bound_identity(user)
    if not row or not settings.configured or not frappe.conf.get("hbos_feishu_inbox_recovery_enabled"):
        frappe.throw("飞书安全验证码尚未启用，请使用已验证邮箱或管理员恢复。", frappe.PermissionError)
    code = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_urlsafe(32)
    try:
        send_inbox_code(settings, row.external_id, code)
    except Exception as exc:
        audit("inbox_delivery_failed", user, status="Failed")
        # No code is stored or a successful-delivery response returned when the
        # provider cannot acknowledge delivery. Provider payload stays private.
        from hbos_portal.auth.feishu import FeishuLoginError
        return {"sent": False, "error": exc.public_message if isinstance(exc, FeishuLoginError) else "飞书未确认投递；请核对机器人、发送权限及本人是否在应用可用范围内。"}
    frappe.cache.set_value(f"hbos:account:inbox:{digest(user)}:{session_digest()}", {
        "salt": salt, "hash": digest(salt + code), "epoch": epoch(user), "binding": row.name,
    }, expires_in_sec=PROOF_TTL)
    audit("inbox_code_requested", user)
    return {"sent": True, "expires_in": PROOF_TTL}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=8, seconds=300)
def verify_feishu_code(code: str, otp: str = "", tmp_id: str = "") -> dict:
    require_post()
    user = require_user()
    key = f"hbos:account:inbox:{digest(user)}:{session_digest()}"
    record = frappe.cache.get_value(key)
    row = _bound_identity(user)
    if not record or not row or record["binding"] != row.name or record["epoch"] != epoch(user) or not hmac.compare_digest(digest(record["salt"] + str(code)), record["hash"]):
        frappe.throw("验证码无效或已过期。", frappe.AuthenticationError)
    challenge = verify_mfa(user, otp=otp, tmp_id=tmp_id)
    if challenge:
        return challenge
    claim = f"hbos:account:inbox-claim:{digest(key + record['hash'])}"
    if not frappe.cache.set(frappe.cache.make_key(claim), "1", ex=PROOF_TTL, nx=True):
        frappe.throw("验证码已使用。", frappe.AuthenticationError)
    frappe.cache.delete_value(key)
    save_proof(user, "feishu_inbox")
    audit("inbox_verified", user)
    return {"verified": True, "expires_in": PROOF_TTL}


def _write_password(user: str, new_password: str) -> None:
    from frappe.core.doctype.user.user import test_password_strength, handle_password_test_fail
    from frappe.utils.password import update_password as write_standard_password

    require_user(user)
    locked = frappe.db.sql("SELECT enabled FROM `tabUser` WHERE name=%s FOR UPDATE", (user,))
    if not locked or not locked[0][0]:
        frappe.throw("账号已停用。", frappe.AuthenticationError)
    if not new_password or len(new_password) > 512:
        frappe.throw("请输入符合站点策略且不超过 512 字符的密码。")
    result = test_password_strength(new_password, user_data=frappe.db.get_value("User", user, ["first_name", "middle_name", "last_name", "email", "birth_date"]))
    feedback = result.get("feedback")
    if feedback and not feedback.get("password_policy_validation_passed", False):
        handle_password_test_fail(feedback)
    write_standard_password(user, new_password)
    frappe.db.set_value("User", user, {"last_password_reset_date": frappe.utils.today(), "reset_password_key": ""})
    # Explicitly invalidate all existing sessions, then issue a new standard
    # session to the already verified caller. No business data or roles change.
    revoke_sessions(user)
    invalidate_user_tickets(user)
    audit("password_changed", user)
    frappe.db.commit()
    frappe.local.login_manager.login_as(user)


@frappe.whitelist(methods=["POST"])
def set_password(new_password: str, request_id: str = "") -> dict:
    require_post()
    user = require_user()
    if _write_receipt(user, request_id, "password"):
        return {"changed": True, "login_name": frappe.db.get_value("User", user, "username") or user, "replayed": True}
    require_proof(user, consume=True)
    _write_password(user, new_password)
    _write_receipt(user, request_id, "password", save=True)
    return {"changed": True, "login_name": frappe.db.get_value("User", user, "username") or user, "session_rotated": True}


@frappe.whitelist(methods=["POST"])
def unlink_feishu(request_id: str = "") -> dict:
    require_post()
    user = require_user()
    if _write_receipt(user, request_id, "unlink"):
        return {"unlinked": True, "replayed": True}
    proof = require_proof(user, consume=True)
    if proof["method"] != "password":
        frappe.throw("解绑须验证已可用的本地密码及原有二次认证。", frappe.AuthenticationError)
    if not has_password(user) or frappe.get_system_settings("disable_user_pass_login"):
        frappe.throw("飞书是当前唯一可用登录方式，请先设置并启用本地密码。")
    frappe.db.sql("SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE", (user,))
    row = _bound_identity(user)
    if row:
        frappe.db.set_value("HBOS External Identity", row.name, {"enabled": 0, "active_user_key": None})
    invalidate_user_tickets(user)
    audit("unlink", user)
    frappe.db.commit()
    _write_receipt(user, request_id, "unlink", save=True)
    return {"unlinked": True}


def mail_ready() -> bool:
    return bool(frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}))


def deliverable_email(user: str) -> bool:
    from hbos_portal.auth.feishu import load_settings

    # Internal account identifiers and test addresses are not delivery channels.
    domain = user.rpartition("@")[2].lower()
    return bool(domain and domain != load_settings().account_domain and not domain.endswith((".internal", ".test", ".invalid", ".localhost")) and domain != "localhost")


def verified_recovery_email(user: str) -> bool:
    # Frappe User has no built-in email-ownership verification field. Only
    # addresses explicitly verified by the site's operator are eligible. Never
    # trust an OAuth profile email or the generated internal account identifier.
    verified = frappe.conf.get("hbos_account_verified_recovery_emails") or {}
    return bool(isinstance(verified, dict) and user not in {"Administrator", "Guest"}
        and mail_ready() and deliverable_email(user)
        and str(verified.get(user) or "").strip().lower() == user.lower())


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_recovery_channels() -> dict:
    no_store()
    from hbos_portal.auth.feishu import load_settings

    settings = load_settings()
    verified = frappe.conf.get("hbos_account_verified_recovery_emails") or {}
    return {"site": frappe.local.site, "feishu_login": settings.configured,
        "feishu_password_recovery": bool(settings.configured and frappe.conf.get("hbos_feishu_inbox_recovery_enabled")),
        "verified_email": bool(mail_ready() and isinstance(verified, dict) and any(verified_recovery_email(user) for user in verified)),
        "administrator_assistance": True}


def recovery_url(native_link: str) -> str:
    key = parse_qs(urlsplit(native_link).query).get("key", [""])[0]
    if not key or len(key) > 512:
        frappe.throw("无法签发恢复链接。", frappe.AuthenticationError)
    # A fragment never enters HTTP request URLs or proxy access logs.
    origin = str(frappe.conf.get("hbos_portal_origin") or "").rstrip("/")
    return origin + "/hbos/reset-password#" + urlencode({"key": key})


def recovery_target(doc) -> dict:
    return {"user": doc.name, "login_name": doc.username or doc.name, "display_name": doc.full_name or doc.first_name or doc.name}


def _recovery_record(key: str):
    from frappe.utils import get_datetime, now_datetime

    record = None
    if isinstance(key, str) and 16 <= len(key) <= 512 and not any(c.isspace() for c in key):
        record = frappe.db.get_value("User", {"reset_password_key": digest(key)},
            ["name", "last_reset_password_key_generated_on", "enabled"], as_dict=True)
    age = None
    if record and record.last_reset_password_key_generated_on:
        age = (now_datetime() - get_datetime(record.last_reset_password_key_generated_on)).total_seconds()
    if not record or not record.enabled or record.name in {"Guest", "Administrator"} or age is None or not 0 <= age < RECOVERY_TTL:
        frappe.throw("恢复链接无效、已使用或已过期。", frappe.ValidationError)
    require_user(record.name)
    return record, max(1, int(RECOVERY_TTL - age))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=8, seconds=300)
def validate_recovery(key: str) -> dict:
    require_post()
    no_store()
    try:
        record, remaining = _recovery_record(key)
        context = secrets.token_urlsafe(32)
        browser = secrets.token_urlsafe(32)
        frappe.cache.set_value("hbos:account:recovery:" + digest(context), {
            "user": record.name, "key_hash": digest(key), "browser_hash": digest(browser),
            "session": session_digest(), "epoch": epoch(record.name),
        }, expires_in_sec=remaining)
        frappe.local.cookie_manager.set_cookie(RECOVERY_COOKIE, browser, httponly=True, samesite="Lax", max_age=remaining)
        return {"target": recovery_target(frappe.get_doc("User", record.name)), "recovery_context": context, "expires_in": remaining}
    finally:
        frappe.local.form_dict.pop("key", None)


def _require_recovery_context(context: str, key: str, user: str) -> None:
    record = frappe.cache.get_value("hbos:account:recovery:" + digest(str(context))) if context else None
    browser = unquote(str(frappe.local.request.cookies.get(RECOVERY_COOKIE) or ""))
    if not record or record.get("user") != user or record.get("epoch") != epoch(user) or record.get("session") != session_digest() or not secrets.compare_digest(record.get("key_hash", ""), digest(key)) or not browser or not secrets.compare_digest(record.get("browser_hash", ""), digest(browser)):
        frappe.throw("恢复验证已失效，请重新打开恢复链接。", frappe.ValidationError)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=3, seconds=3600)
def request_reset(user: str) -> dict:
    require_post()
    from frappe.core.doctype.user.user import User

    try:
        found = User.find_by_credentials(user, "", validate_password=False)
        if found and found.enabled and verified_recovery_email(found.name):
            doc = frappe.get_doc("User", found.name)
            doc.validate_reset_password()
            doc.password_reset_mail(recovery_url(doc._reset_password(send_email=False)))
            audit("email_recovery_requested", found.name)
    except Exception:
        # Missing accounts, provider failures and throttled accounts share the
        # same response. No account-existence or mailbox error is disclosed.
        frappe.db.rollback()
    return {"message": "如账号存在且有可用恢复邮箱，系统已发送恢复说明。也可使用已绑定飞书登录后进行安全验证。"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=8, seconds=300)
def update_password(new_password: str, logout_all_sessions: int = 1, key: str | None = None, old_password: str | None = None, otp: str = "", tmp_id: str = "", recovery_context: str = "", request_id: str = ""):
    """Secure the framework's historical public password-update path as well."""
    require_post()
    if key:
        record, _ = _recovery_record(key)
        _require_recovery_context(recovery_context, key, record.name)
        challenge = verify_mfa(record.name, otp=otp, tmp_id=tmp_id)
        if challenge:
            return challenge
        frappe.db.sql("SELECT name FROM `tabUser` WHERE name=%s AND reset_password_key=%s FOR UPDATE", (record.name, digest(key)))
        if frappe.db.get_value("User", record.name, "reset_password_key", cache=False) != digest(key):
            frappe.throw("恢复链接已使用。", frappe.AuthenticationError)
        # Re-check expiry, enabled account and the target under the User lock.
        locked, _ = _recovery_record(key)
        if locked.name != record.name:
            frappe.throw("恢复验证已失效。", frappe.AuthenticationError)
        _write_password(record.name, new_password)
        _write_receipt(record.name, request_id, "recovery", save=True)
        frappe.cache.delete_value("hbos:account:recovery:" + digest(recovery_context))
        frappe.local.cookie_manager.delete_cookie(RECOVERY_COOKIE)
    else:
        user = require_user()
        if old_password:
            _, challenge = verify_credentials(user, old_password, otp=otp, tmp_id=tmp_id)
            if challenge:
                return challenge
        else:
            require_proof(user, consume=True)
        _write_password(user, new_password)
    return "/hbos/profile"


def invalidate_user_tickets(user: str) -> None:
    key = frappe.cache.make_key(f"hbos:account:epoch:{user}")
    frappe.cache.incr(key)


def revoke_sessions(user: str) -> None:
    from frappe.sessions import clear_sessions

    # Frappe clears at most 100 rows per call. Drain every existing session.
    while frappe.db.sql("SELECT COUNT(*) FROM `tabSessions` WHERE user=%s", (user,))[0][0]:
        clear_sessions(user, force=True)


def guard_document_password(doc, method=None) -> None:
    # REST/Desk User.new_password is another native password-writing path.
    # A session alone must not authorize setting a password after SSO.
    if doc.get("new_password") and getattr(frappe.local, "request", None):
        require_post()
        actor = require_user()
        if actor != doc.name and actor != "Administrator" and "System Manager" not in frappe.get_roles(actor):
            frappe.throw("请在账号与安全页面修改本人密码。", frappe.PermissionError)
        require_proof(actor, consume=True)
        doc.flags.hbos_password_written = True


def user_updated(doc, method=None) -> None:
    if doc.flags.get("hbos_password_written"):
        revoke_sessions(doc.name)
        invalidate_user_tickets(doc.name)
        frappe.db.set_value("User", doc.name, "reset_password_key", "", update_modified=False)
        audit("document_password_changed", doc.name)
    if not doc.enabled:
        revoke_sessions(doc.name)
        invalidate_user_tickets(doc.name)
        frappe.db.set_value("User", doc.name, "reset_password_key", "", update_modified=False)
        if frappe.db.exists("DocType", "HBOS External Identity"):
            for name in frappe.get_all("HBOS External Identity", filters={"user": doc.name, "enabled": 1}, pluck="name"):
                frappe.db.set_value("HBOS External Identity", name, {"enabled": 0, "active_user_key": None})


def check_login(login_manager=None) -> None:
    if login_manager and login_manager.user != "Guest":
        require_user(login_manager.user)
        from hbos_portal.auth.security import require_custody_mfa_for_login
        require_custody_mfa_for_login(login_manager.user)


def check_request() -> None:
    if frappe.session.user != "Guest":
        require_user()
        from hbos_portal.auth.security import check_request as check_version
        check_version()


@frappe.whitelist(allow_guest=True, methods=['POST'])
@rate_limit(limit=8, seconds=300)
def password_login(username: str, password: str, otp: str = '', tmp_id: str = '') -> dict:
    require_post()
    if frappe.get_system_settings('disable_user_pass_login'):
        frappe.throw('站点已禁用密码登录。', frappe.AuthenticationError)
    user, challenge = verify_credentials(username, password, otp=otp, tmp_id=tmp_id)
    if challenge:
        return challenge
    frappe.local.login_manager.login_as(user)
    return {'logged_in': True, 'message': 'Logged In'}


def on_logout(login_manager=None) -> None:
    if frappe.session.user != "Guest":
        frappe.cache.delete_value(_proof_key(frappe.session.user))
    nonce = unquote(str(frappe.local.request.cookies.get(PENDING_COOKIE) or ""))
    if nonce:
        frappe.cache.delete_value(_pending_key(nonce))
    frappe.local.cookie_manager.delete_cookie(PENDING_COOKIE)


def validate_auth_paths() -> None:
    enabled = frappe.get_all("Social Login Key", filters={"enable_social_login": 1}, fields=["name", "provider_name", "authorize_url"])
    if any("feishu" in str(row).lower() or "larksuite" in str(row).lower() for row in enabled):
        frappe.throw("请先停用历史飞书 Social Login Key；原生邮箱自动匹配不得绕过 HBOS 双方验证。")
