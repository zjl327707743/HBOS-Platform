from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote, unquote, urlencode, urlsplit

import frappe

from hbos_portal.auth.state import OAuthStateError, RedisOAuthStateStore, validate_redirect_target


AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
USER_INFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"
TENANT_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
TENANT_INFO_URL = "https://open.feishu.cn/open-apis/tenant/v2/tenant/query"
CONTACT_USER_URL = "https://open.feishu.cn/open-apis/contact/v3/users/"
BROWSER_COOKIE = "hbos_feishu_oauth_browser"
IDENTITY_PROVIDER = "feishu"
IDENTITY_TYPE = "open_id"
SCOPE_PATTERN = re.compile(r"^[a-zA-Z0-9:_\-. ]{1,512}$")
OPEN_ID_PATTERN = re.compile(r"^ou_[A-Za-z0-9_-]{8,200}$")
SECRET_FILENAME = "hbos_feishu_app_secret"
TENANT_FILENAME = "hbos_feishu_tenant_key"
TENANT_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{4,200}$")
ACCOUNT_DOMAIN_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{1,118}[a-z0-9])?$")


class FeishuLoginError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message


@dataclass(frozen=True)
class FeishuSettings:
    app_id: str
    tenant_key: str
    redirect_uri: str
    scopes: tuple[str, ...]
    authorize_id_parameter: str
    published: bool
    redirect_registered: bool
    pkce_enabled: bool
    app_secret: str = field(repr=False)
    auto_provision_internal: bool = False
    account_domain: str = "feishu.hbos.internal"

    @property
    def configured(self) -> bool:
        return bool(
            self.app_id
            and self.app_secret
            and self.tenant_key
            and self.redirect_uri
            and self.scopes
            and self.authorize_id_parameter in {"client_id", "app_id"}
            and self.published
            and self.redirect_registered
            and self.auto_provision_internal
            and bool(ACCOUNT_DOMAIN_PATTERN.fullmatch(self.account_domain))
        )

    def public_status(self) -> dict[str, object]:
        missing = []
        if not self.app_id:
            missing.append("app_id")
        if not self.app_secret:
            missing.append("server_secret")
        if not self.tenant_key:
            missing.append("tenant_key")
        if not self.redirect_uri:
            missing.append("redirect_uri")
        elif not self.redirect_registered:
            missing.append("redirect_registration")
        if not self.scopes:
            missing.append("approved_scopes")
        if self.authorize_id_parameter not in {"client_id", "app_id"}:
            missing.append("authorize_id_parameter")
        if not self.published:
            missing.append("internal_member_publication")
        if not self.auto_provision_internal:
            missing.append("internal_member_auto_provision")
        return {
            "configured": self.configured,
            "provider": IDENTITY_PROVIDER,
            "pkce_enabled": self.pkce_enabled,
            "audience": "enterprise_internal_members",
            "auto_provision_internal": self.auto_provision_internal,
            "missing": missing,
        }


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _validate_redirect_uri(value: str) -> str:
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.fragment or parsed.username or parsed.password:
        return ""
    if parsed.scheme == "https" and parsed.netloc:
        return value
    is_loopback_name = parsed.hostname == "localhost" or str(parsed.hostname or "").endswith(".localhost")
    if parsed.scheme == "http" and (parsed.hostname == "127.0.0.1" or is_loopback_name) and parsed.netloc:
        return value
    return ""


def _site_private_path(filename: str) -> Path:
    return Path(str(frappe.get_site_path("private", filename)))


def _load_protected_text(path: Path, *, maximum: int = 512) -> str:
    """Read a site-private value only when ownership and permissions are safe."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return ""
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
        return ""
    if hasattr(os, "geteuid") and metadata.st_uid != os.geteuid():
        return ""
    if metadata.st_size <= 0 or metadata.st_size > maximum + 1:
        return ""
    value = path.read_text(encoding="utf-8").strip()
    if not value or len(value) > maximum or any(character.isspace() for character in value):
        return ""
    return value


def _load_app_secret() -> str:
    value = _load_protected_text(_site_private_path(SECRET_FILENAME))
    if value:
        return value
    # Environment fallback is opt-in so an old shared-process secret cannot
    # silently become active in this isolated pilot Site.
    if _truthy(frappe.conf.get("hbos_feishu_allow_env_secret")):
        return str(os.getenv("FEISHU_APP_SECRET") or "").strip()
    return ""


def _load_tenant_key() -> str:
    value = _load_protected_text(_site_private_path(TENANT_FILENAME), maximum=200)
    if value and TENANT_KEY_PATTERN.fullmatch(value):
        return value
    return str(frappe.conf.get("hbos_feishu_tenant_key") or "").strip()


def _store_protected_text(path: Path, value: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _require_p1_local_configuration() -> None:
    if os.environ.get("HBOS_P1_LOCAL_CONFIGURATION") != "1":
        raise RuntimeError("P1 local configuration authority is required")
    if not str(frappe.local.site or "").startswith("p1-knowledge-twin"):
        raise RuntimeError("This helper is restricted to the isolated P1 Site")


def store_app_secret_from_stdin() -> dict[str, object]:
    """Store a rotated app secret without placing it in argv, logs, or Site config."""

    _require_p1_local_configuration()
    value = sys.stdin.readline().rstrip("\r\n")
    if len(value) < 16 or len(value) > 512 or any(character.isspace() for character in value):
        raise RuntimeError("The app secret input is invalid")
    _store_protected_text(_site_private_path(SECRET_FILENAME), value)
    return {"stored": True, "location": "site-private", "restart_required": True}


def store_tenant_key_from_stdin() -> dict[str, object]:
    """Store the approved tenant identifier without exposing it in process argv."""

    _require_p1_local_configuration()
    value = sys.stdin.readline().strip()
    if not TENANT_KEY_PATTERN.fullmatch(value):
        raise RuntimeError("The tenant_key input is invalid")
    _store_protected_text(_site_private_path(TENANT_FILENAME), value)
    return {"stored": True, "location": "site-private", "restart_required": True}


def bind_open_id_from_stdin(user: str) -> dict[str, object]:
    raise RuntimeError("Manual identity binding is retired; verify both identities in Account Security")


def load_settings() -> FeishuSettings:
    raw_scope = str(frappe.conf.get("hbos_feishu_oauth_scopes") or "").strip()
    if raw_scope and not SCOPE_PATTERN.fullmatch(raw_scope):
        raw_scope = ""
    scopes = tuple(dict.fromkeys(part for part in raw_scope.split() if part))
    account_domain = str(
        frappe.conf.get("hbos_feishu_account_domain") or "feishu.hbos.internal"
    ).strip().lower()
    if not ACCOUNT_DOMAIN_PATTERN.fullmatch(account_domain) or ".." in account_domain:
        account_domain = ""
    return FeishuSettings(
        app_id=str(frappe.conf.get("hbos_feishu_app_id") or os.getenv("FEISHU_APP_ID") or "").strip(),
        app_secret=_load_app_secret(),
        tenant_key=_load_tenant_key(),
        redirect_uri=_validate_redirect_uri(str(frappe.conf.get("hbos_feishu_redirect_uri") or "").strip()),
        scopes=scopes,
        authorize_id_parameter=str(
            frappe.conf.get("hbos_feishu_authorize_id_parameter") or ""
        ).strip(),
        published=_truthy(frappe.conf.get("hbos_feishu_app_published")),
        redirect_registered=_truthy(frappe.conf.get("hbos_feishu_redirect_registered")),
        pkce_enabled=_truthy(frappe.conf.get("hbos_feishu_pkce_enabled")),
        auto_provision_internal=_truthy(
            frappe.conf.get("hbos_feishu_auto_provision_internal")
        ),
        account_domain=account_domain,
    )


def _redirect(location: str) -> None:
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = location


def _error_redirect(code: str) -> None:
    allowed = {
        "cancelled",
        "config_required",
        "invalid_state",
        "identity_unmapped",
        "identity_conflict",
        "account_disabled",
        "tenant_rejected",
        "exchange_failed",
    }
    status = code if code in allowed else "exchange_failed"
    _redirect(f"/hbos/login?status={quote(status)}")


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def build_authorize_url(
    settings: FeishuSettings,
    *,
    state: str,
    code_challenge: str | None,
) -> str:
    if not settings.configured:
        raise FeishuLoginError("config_required", "飞书登录尚未完成安全配置。")
    params = {
        settings.authorize_id_parameter: settings.app_id,
        "redirect_uri": settings.redirect_uri,
        "response_type": "code",
        "scope": " ".join(settings.scopes),
        "state": state,
    }
    if settings.pkce_enabled:
        if not code_challenge:
            raise FeishuLoginError("config_required", "PKCE 配置不完整。")
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _unwrap_feishu_payload(response: Any) -> Mapping[str, Any]:
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, Mapping):
        raise FeishuLoginError("exchange_failed", "飞书身份服务返回无效响应。")
    code = value.get("code")
    if code not in (None, 0, "0"):
        safe_code = str(code) if str(code).isdigit() and len(str(code)) <= 12 else "unknown"
        raise FeishuLoginError("exchange_failed", f"飞书调用未成功（错误码 {safe_code}），请核对应用能力、权限和可用范围。")
    data = value.get("data")
    return data if isinstance(data, Mapping) else value


def exchange_identity(
    settings: FeishuSettings,
    *,
    code: str,
    code_verifier: str | None,
    post: Any = None,
    get: Any = None,
) -> dict[str, str]:
    if not settings.configured:
        raise FeishuLoginError("config_required", "飞书登录尚未完成安全配置。")
    if not code or len(code) > 2048:
        raise FeishuLoginError("exchange_failed", "飞书授权码无效。")
    if settings.pkce_enabled and not code_verifier:
        raise FeishuLoginError("invalid_state", "PKCE 登录状态无效。")

    if post is None or get is None:
        import requests

        post = post or requests.post
        get = get or requests.get

    token_body = {
        "client_id": settings.app_id,
        "client_secret": settings.app_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.redirect_uri,
    }
    if settings.pkce_enabled:
        token_body["code_verifier"] = code_verifier

    try:
        token_data = _unwrap_feishu_payload(post(TOKEN_URL, json=token_body, timeout=10))
        access_token = str(token_data.get("access_token") or "").strip()
        if not access_token:
            raise FeishuLoginError("exchange_failed", "飞书用户凭证不可用。")
        user_data = _unwrap_feishu_payload(
            get(
                USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
        )
    except FeishuLoginError:
        raise
    except Exception as exc:
        raise FeishuLoginError("exchange_failed", "飞书身份服务暂时不可用。") from exc

    # The token is deliberately not returned or persisted. Only the immutable
    # identity fields required for mapping leave this function.
    open_id = str(user_data.get("open_id") or "").strip()
    tenant_key = str(user_data.get("tenant_key") or token_data.get("tenant_key") or "").strip()
    if not OPEN_ID_PATTERN.fullmatch(open_id):
        raise FeishuLoginError("exchange_failed", "飞书身份缺少 open_id。")
    if not tenant_key or not secrets.compare_digest(tenant_key, settings.tenant_key):
        raise FeishuLoginError("tenant_rejected", "当前企业租户未获准访问 HBOS。")
    display_name = " ".join(str(user_data.get("name") or "").split())[:120]
    verify_internal_member(settings, open_id, post=post, get=get)
    return {
        "open_id": open_id,
        "tenant_key": tenant_key,
        "display_name": display_name or "飞书企业成员",
    }


def identity_key(
    *,
    provider: str,
    tenant_key: str,
    app_id: str,
    id_type: str,
    external_id: str,
) -> str:
    value = "\x1f".join((provider, tenant_key, app_id, id_type, external_id))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def provisioned_user_id(settings: FeishuSettings, identity: Mapping[str, str]) -> str:
    """Build a non-routable account id without trusting profile email or name."""

    key = identity_key(
        provider=IDENTITY_PROVIDER,
        tenant_key=identity["tenant_key"],
        app_id=settings.app_id,
        id_type=IDENTITY_TYPE,
        external_id=identity["open_id"],
    )
    return f"feishu.{key[:24]}@{settings.account_domain}"


def _validate_login_account(user: str) -> str:
    from hbos_portal.auth.accounts import require_user

    try:
        return require_user(user, external=True)
    except (frappe.AuthenticationError, frappe.PermissionError) as exc:
        raise FeishuLoginError("account_disabled", "HBOS 账号已停用或不可用于内部门户。") from exc


def _resolve_or_provision_user(settings: FeishuSettings, identity: Mapping[str, str]) -> str:
    # Kept for callers of the previous API; provisioning now requires an
    # explicit owner choice through the cookie-bound account connection flow.
    rows = frappe.get_all("HBOS External Identity", filters={"identity_key": identity_key(provider="feishu", tenant_key=identity["tenant_key"], app_id=settings.app_id, id_type="open_id", external_id=identity["open_id"]), "enabled": 1}, fields=["user"], limit=2)
    if len(rows) != 1:
        raise FeishuLoginError("identity_unmapped", "请选择绑定已有账号或新开户。")
    return _validate_login_account(rows[0]["user"])


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_status() -> dict[str, object]:
    frappe.local.response_headers["Cache-Control"] = "private, no-store, max-age=0"
    settings = load_settings()
    return {**settings.public_status(), "callback": settings.redirect_uri,
        "administrator_link": {"enabled": _truthy(frappe.conf.get("hbos_feishu_allow_administrator_link")), "requires_password_and_existing_mfa": True},
        "inbox_stepup": {"enabled": _truthy(frappe.conf.get("hbos_feishu_inbox_recovery_enabled")), "recipient_policy": "verified_bound_self_on_request", "actual_delivery": "requires_self_request"},
        "live_oauth": "requires_owner_browser_acceptance"}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def start(redirect_to: str = "/hbos") -> None:
    settings = load_settings()
    if not settings.configured:
        _error_redirect("config_required")
        return None
    try:
        safe_redirect = validate_redirect_target(redirect_to)
        verifier = challenge = None
        if settings.pkce_enabled:
            verifier, challenge = _pkce_pair()
        state, browser_nonce = RedisOAuthStateStore(frappe.cache).create(
            redirect_to=safe_redirect,
            code_verifier=verifier,
        )
        frappe.local.cookie_manager.set_cookie(
            BROWSER_COOKIE,
            browser_nonce,
            httponly=True,
            samesite="Lax",
            max_age=8 * 60,
        )
        _redirect(build_authorize_url(settings, state=state, code_challenge=challenge))
    except (OAuthStateError, FeishuLoginError):
        _error_redirect("config_required")
    return None


@frappe.whitelist(methods=["POST"])
def start_link() -> dict:
    from hbos_portal.auth.accounts import require_user, require_proof, require_post, session_digest, epoch

    require_post()
    user = require_user(external=True)
    proof = require_proof(user, consume=True)
    if user == "Administrator" and proof["method"] != "password":
        frappe.throw("Administrator 绑定须验证管理员密码及原有二次认证。", frappe.AuthenticationError)
    settings = load_settings()
    if not settings.configured:
        frappe.throw("飞书配置尚未完成。", frappe.AuthenticationError)
    verifier = challenge = None
    if settings.pkce_enabled:
        verifier, challenge = _pkce_pair()
    state, nonce = RedisOAuthStateStore(frappe.cache).create(
        redirect_to="/hbos/profile", code_verifier=verifier, intent="link",
        user=user, session_digest=session_digest(), security_epoch=epoch(user), verified_at=proof["verified_at"],
    )
    frappe.local.cookie_manager.set_cookie(BROWSER_COOKIE, nonce, httponly=True, samesite="Lax", max_age=8 * 60)
    return {"authorize_url": build_authorize_url(settings, state=state, code_challenge=challenge)}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> None:
    settings = load_settings()
    if error:
        frappe.local.cookie_manager.delete_cookie(BROWSER_COOKIE)
        _error_redirect("cancelled")
        return None
    if not settings.configured:
        _error_redirect("config_required")
        return None

    browser_nonce = unquote(str(frappe.local.request.cookies.get(BROWSER_COOKIE) or ""))
    try:
        state_record = RedisOAuthStateStore(frappe.cache).consume(
            state=str(state or ""),
            browser_nonce=browser_nonce,
        )
        frappe.local.cookie_manager.delete_cookie(BROWSER_COOKIE)
        identity = exchange_identity(
            settings,
            code=str(code or ""),
            code_verifier=state_record.code_verifier,
        )
        from hbos_portal.auth.accounts import create_pending, identity_row, require_user, session_digest, epoch, PROOF_TTL
        import time
        if state_record.intent == "link":
            if state_record.user != frappe.session.user or state_record.session_digest != session_digest() or state_record.security_epoch != epoch(state_record.user) or state_record.verified_at + PROOF_TTL < time.time():
                raise OAuthStateError("link session or ownership proof changed")
            require_user(state_record.user, external=True)
            row = identity_row(settings, identity)
            if row and row.user != state_record.user:
                raise FeishuLoginError("identity_conflict", "此飞书身份已绑定其他账号。")
            create_pending(identity, intent="link", user=state_record.user, redirect_to=state_record.redirect_to, verified_at=state_record.verified_at)
            _redirect("/hbos/account-connect")
            return None
        if state_record.intent != "login":
            raise OAuthStateError("unknown OAuth intent")
        row = identity_row(settings, identity)
        if row and not frappe.db.get_value("User", row.user, "enabled"):
            raise FeishuLoginError("account_disabled", "对应账号已停用。")
        if not row or not row.enabled:
            create_pending(identity, intent="choose", redirect_to=state_record.redirect_to)
            _redirect("/hbos/account-connect")
            return None
        user = _validate_login_account(row.user)
        from frappe.twofactor import should_run_2fa
        if should_run_2fa(user):
            create_pending(identity, intent="login_mfa", user=user, redirect_to=state_record.redirect_to)
            _redirect("/hbos/account-connect")
            return None
        frappe.db.set_value("HBOS External Identity", row.name, "last_verified_at", frappe.utils.now_datetime(), update_modified=False)
        frappe.db.commit()

        # Frappe's own OAuth implementation uses LoginManager.login_as after
        # provider verification. The pre-checks above cover enabled account,
        # explicit binding, tenant, and privileged-account policy; post_login
        # then enforces IP/hour restrictions and creates a fresh Frappe Session.
        # Do this last so a nonessential audit-update failure cannot leave the
        # browser authenticated while rendering an OAuth failure response.
        frappe.local.login_manager.login_as(user)
        _redirect(state_record.redirect_to)
    except OAuthStateError:
        frappe.db.rollback()
        _error_redirect("invalid_state")
    except FeishuLoginError as exc:
        frappe.db.rollback()
        _error_redirect(exc.code)
    except Exception:
        frappe.db.rollback()
        request_id = secrets.token_hex(8)
        frappe.log_error(
            title=f"HBOS Feishu login error [{request_id}]",
            # Frappe traceback is retained server-side. This module never logs
            # the authorization code, token response, or user profile payload.
            message="Feishu callback failed; credentials and provider payload deliberately omitted.",
        )
        _error_redirect("exchange_failed")
    finally:
        frappe.local.cookie_manager.delete_cookie(BROWSER_COOKIE)
        frappe.local.form_dict.pop("code", None)
    return None


def _tenant_token(settings: FeishuSettings, *, post=None) -> str:
    if post is None:
        import requests
        post = requests.post
    data = _unwrap_feishu_payload(post(TENANT_TOKEN_URL, json={"app_id": settings.app_id, "app_secret": settings.app_secret}, timeout=10))
    token = str(data.get("tenant_access_token") or "")
    if not token:
        raise FeishuLoginError("exchange_failed", "飞书应用身份不可用。")
    return token


def discover_enterprise(settings: FeishuSettings) -> dict:
    """Discover from the trusted server application, never the first login."""
    import requests
    token = _tenant_token(settings)
    data = _unwrap_feishu_payload(requests.get(TENANT_INFO_URL, headers={"Authorization": f"Bearer {token}"}, timeout=10))
    tenant = data.get("tenant") or {}
    key = str(tenant.get("tenant_key") or "")
    if not TENANT_KEY_PATTERN.fullmatch(key) or not tenant.get("name"):
        raise FeishuLoginError("config_required", "应用企业信息不可验证。")
    return {"name": str(tenant["name"]), "tenant_key": key}


def verify_internal_member(settings: FeishuSettings, open_id: str, *, post=None, get=None) -> None:
    if get is None:
        import requests
        get = requests.get
    token = _tenant_token(settings, post=post)
    data = _unwrap_feishu_payload(get(CONTACT_USER_URL + quote(open_id, safe=""), params={"user_id_type": "open_id"}, headers={"Authorization": f"Bearer {token}"}, timeout=10))
    member = data.get("user") or {}
    status = member.get("status") or {}
    if member.get("open_id") != open_id or status.get("is_activated") is not True or any(status.get(k) is not False for k in ["is_frozen", "is_resigned", "is_unjoin", "is_exited"]) or not member.get("department_ids"):
        raise FeishuLoginError("tenant_rejected", "无法验证当前应用范围内的在职内部成员。")


def probe_inbox_bot(settings: FeishuSettings, *, post=None, get=None) -> bool:
    if get is None:
        import requests
        get = requests.get
    token = _tenant_token(settings, post=post)
    data = _unwrap_feishu_payload(get("https://open.feishu.cn/open-apis/bot/v3/info", headers={"Authorization": f"Bearer {token}"}, timeout=10))
    bot = data.get("bot") or {}
    if not bot.get("open_id") or not bot.get("app_name"):
        raise FeishuLoginError("config_required", "当前应用的机器人能力不可验证。")
    return True


def send_inbox_code(settings: FeishuSettings, open_id: str, code: str) -> None:
    import requests
    import json
    token = _tenant_token(settings)
    # The receive_id is read from the persistent verified binding, never supplied
    # by a caller. A website request sends only to that account's own inbox.
    data = _unwrap_feishu_payload(requests.post("https://open.feishu.cn/open-apis/im/v1/messages", params={"receive_id_type": "open_id"}, headers={"Authorization": f"Bearer {token}"}, json={"receive_id": open_id, "msg_type": "text", "content": json.dumps({"text": f"HBOS 账号安全验证码：{code}，5 分钟内有效。仅在本人操作时输入，请勿转发。"}, ensure_ascii=False), "uuid": secrets.token_hex(16)}, timeout=10))
    if not data.get("message_id"):
        raise FeishuLoginError("exchange_failed", "飞书没有确认消息发送；没有签发验证码。")
