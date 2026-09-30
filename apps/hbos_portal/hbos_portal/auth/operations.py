"""Explicit, two-party identity changes; a verified invitation never logs in.

Ordinary binding remains conflict-rejecting. Only this service may move a
binding after scoped ownership proofs and both confirmations are complete.
"""
from __future__ import annotations

import json
import secrets
import time
from contextlib import contextmanager, nullcontext
from urllib.parse import unquote, urlencode

import frappe
from frappe.rate_limiter import rate_limit

from hbos_portal.auth import accounts, security

OPERATION_TTL = 1200
PARTICIPANT_COOKIE = 'hbos_account_change_participant'
KINDS = {'rebind', 'roles', 'custody', 'identity_restore'}
FINAL = {'Completed', 'Cancelled', 'Expired'}


def _settings():
    from hbos_portal.auth.feishu import load_settings
    settings = load_settings()
    if not settings.configured:
        frappe.throw('当前飞书授权配置不可用。', frappe.PermissionError)
    return settings


def _seal(value) -> str:
    from frappe.utils.password import encrypt
    return encrypt(json.dumps(value, ensure_ascii=False, separators=(',', ':')))


def _open(value):
    from frappe.utils.password import decrypt
    return json.loads(decrypt(value)) if value else None


@contextmanager
def _authority(operation: str):
    old = frappe.flags.get('hbos_operation_authority')
    frappe.flags.hbos_operation_authority = operation
    try:
        yield
    finally:
        frappe.flags.hbos_operation_authority = old


def _save(doc, *, insert=False):
    with _authority(doc.name):
        doc.insert(ignore_permissions=True) if insert else doc.save(ignore_permissions=True)


def _event(doc, event: str, **details):
    old_key = frappe.db.get_value('HBOS External Identity', doc.old_identity, 'identity_key') if doc.old_identity else None
    with _authority(doc.name):
        frappe.get_doc({'doctype': 'HBOS Account Change Event', 'operation': doc.name,
            'event': event, 'actor': frappe.session.user, 'target_user': doc.target_user,
            'source_user': doc.source_user, 'old_identity_key': old_key,
            'new_identity_key': doc.new_identity_key, 'details_json': json.dumps(details, ensure_ascii=False),
            'occurred_at': frappe.utils.now_datetime()}).insert(ignore_permissions=True)


def _load(operation: str, *, lock=False):
    if not isinstance(operation, str) or not 8 <= len(operation) <= 64 or not frappe.db.exists('HBOS Account Operation', operation):
        frappe.throw('账号变更不可用或已过期。', frappe.ValidationError)
    if lock:
        frappe.db.sql('SELECT name FROM `tabHBOS Account Operation` WHERE name=%s FOR UPDATE', (operation,))
    doc = frappe.get_doc('HBOS Account Operation', operation, for_update=lock)
    if doc.state in FINAL or frappe.utils.get_datetime(doc.expires_at) <= frappe.utils.now_datetime():
        frappe.throw('账号变更已完成、取消或过期，请重新发起。', frappe.ValidationError)
    settings = _settings()
    if settings.app_id != doc.app_id or settings.tenant_key != doc.tenant_key:
        frappe.throw('应用或已批准企业配置已变化，当前申请失效。', frappe.ValidationError)
    return doc


def _operator(user: str) -> bool:
    return user == 'Administrator' or 'HBOS Account Handover Manager' in frappe.get_roles(user)


def _owner(operation: str, *, lock=False):
    user = accounts.require_user()
    doc = _load(operation, lock=lock)
    if doc.initiator != user or doc.initiator_epoch != accounts.epoch(user) or doc.initiator_session != accounts.session_digest():
        frappe.throw('此申请不属于当前验证会话。', frappe.PermissionError)
    return doc


def _participant(*, lock=False):
    nonce = unquote(str(frappe.local.request.cookies.get(PARTICIPANT_COOKIE) or ''))
    ref = frappe.cache.get_value('hbos:change:participant:' + accounts.digest(nonce)) if nonce and len(nonce) < 128 else None
    if not ref:
        frappe.throw('邀请验证会话已过期，请由发起人重新邀请。', frappe.ValidationError)
    doc = _load(ref['operation'], lock=lock)
    if not secrets.compare_digest(str(doc.participant_nonce_hash or ''), accounts.digest(nonce)):
        frappe.throw('邀请验证浏览器不匹配。', frappe.ValidationError)
    return doc


def _scope(doc):
    return {'provider': 'feishu', 'app_id': doc.app_id, 'enterprise_verified': True}


def _label(user: str | None):
    if not user:
        return None
    doc = frappe.get_doc('User', user)
    return {'user': user, 'login_name': doc.username or user, 'display_name': doc.full_name or doc.first_name or user}


def _fingerprint(identity_key: str | None):
    return str(identity_key or '')[:10] or None


def _view(doc, *, participant=False):
    identity = _open(doc.new_identity_sealed) or {}
    old = frappe.db.get_value('HBOS External Identity', doc.old_identity, ['identity_key', 'enabled'], as_dict=True) if doc.old_identity else None
    source_proven = _source_ready(doc)
    conflict = bool(doc.source_user and doc.source_user != doc.target_user and doc.kind in {'rebind', 'custody'} and not doc.allow_source_migration)
    return {'operation': doc.name, 'kind': doc.kind, 'state': doc.state,
        'participant': participant, 'expires_in': max(0, int((frappe.utils.get_datetime(doc.expires_at) - frappe.utils.now_datetime()).total_seconds())),
        'can_return_to_initiator': bool(participant and frappe.session.user == doc.initiator and accounts.session_digest() == doc.initiator_session and accounts.epoch(doc.initiator) == doc.initiator_epoch),
        'target': _label(doc.target_user), 'source': _label(doc.source_user),
        'old_identity': {'fingerprint': _fingerprint(old.identity_key), **_scope(doc)} if old else None,
        'new_identity': {'fingerprint': _fingerprint(doc.new_identity_key), 'display_name': identity.get('display_name'), **_scope(doc)} if identity else None,
        'source_proven': source_proven, 'conflict': conflict, 'allow_source_migration': bool(doc.allow_source_migration),
        'recipient_accepted': bool(doc.recipient_accepted), 'credentials_verified': bool(doc.credential_verified),
        'roles': json.loads(doc.roles_json or '[]'), 'restore_personal_account': bool(doc.restore_personal_account),
        'effects': _effects(doc), 'ready': bool(identity and source_proven and doc.recipient_accepted and not conflict and (doc.kind != 'custody' or doc.credential_verified)),
        'reason': doc.reason}


def _effects(doc):
    if doc.kind == 'roles':
        return ['仅将确认选择的管理角色从交出人撤销、授予接任者；双方账号和历史作者保留。', '双方旧会话和待恢复凭据失效，须重新登录。']
    if doc.kind == 'custody':
        return ['旧飞书、密码、MFA、恢复方式、恢复码、Session、待绑定/恢复/设密票据、API 和 OAuth 凭据全部失效。',
            '仅接任者本人设置并验证的新密码、新 MFA 和新飞书身份可登录 Administrator。',
            '旧身份不会自动恢复 Administrator；后续普通账号归属需独立受控处理。',
            '主机、数据库和其他运维权限须单独交接；共享飞书 App Secret 不轮换。']
    if doc.kind == 'identity_restore':
        return ['仅将已撤销身份明确归属到本人普通账号，不继承原账号或 Administrator 的权限、密码或业务资料。']
    effects = ['旧飞书绑定失效，原 HBOS 账号、密码、角色、业务资料保留。', '旧会话和待恢复凭据失效，须重新登录。']
    if doc.source_user and doc.source_user != doc.target_user:
        effects.append('新身份从来源账号迁出；来源账号保留数据和角色，已验证的可用密码入口保留。不会交换两个账号。')
    return effects


def _source_ready(doc) -> bool:
    if not doc.source_user:
        return True
    if not doc.source_verified_at or doc.source_epoch != accounts.epoch(doc.source_user):
        return False
    return frappe.utils.get_datetime(doc.source_verified_at).timestamp() + accounts.PROOF_TTL >= time.time()


@frappe.whitelist(methods=['GET'])
def actions() -> dict:
    accounts.no_store()
    user = accounts.require_user()
    doc = frappe.get_doc('User', user)
    migrated = bool(frappe.db.exists('DocType', 'HBOS Account Operation'))
    return {'rebind': bool(migrated and user != 'Administrator' and accounts._bound_identity(user)),
        'roles': bool(migrated and user != 'Administrator' and _operator(user)),
        'role_choices': [r.role for r in doc.roles if r.role not in {'All', 'Guest'}] if _operator(user) and user != 'Administrator' else [],
        'custody': bool(migrated and user == 'Administrator' and frappe.conf.get('hbos_administrator_custody_handover_enabled')),
        'custody_needs_special_authorization': not bool(frappe.conf.get('hbos_administrator_custody_handover_enabled')),
        'identity_restore': bool(migrated and _operator(user)), 'builtin_administrator': user == 'Administrator', 'migrated': migrated}


@frappe.whitelist(methods=['POST'])
def begin(kind: str, reason: str, allow_source_migration: int = 0, roles=None, target_user: str = '', new_personal_account: int = 0, request_id: str = '') -> dict:
    accounts.require_post()
    actor = accounts.require_user()
    operation_name = secrets.token_hex(16)
    if request_id:
        from uuid import UUID
        try:
            UUID(request_id)
        except (ValueError, TypeError, AttributeError):
            frappe.throw('提交编号无效，请重新发起。')
        operation_name = accounts.digest(actor + ':' + accounts.session_digest() + ':' + request_id)[:32]
        if frappe.db.exists('HBOS Account Operation', operation_name):
            existing = _owner(operation_name)
            if existing.kind != kind:
                frappe.throw('此提交编号已用于另一项账号变更。', frappe.PermissionError)
            return {'operation': existing.name, 'invitation_url': '', 'replayed': True}
    if kind not in KINDS or not 12 <= len(str(reason).strip()) <= 500:
        frappe.throw('请选择操作，并说明本人或组织核验依据（12–500 字）。')
    if frappe.utils.cint(allow_source_migration):
        frappe.throw('请在新身份验证后核对具体来源账号，再单独批准迁出。', frappe.PermissionError)
    if kind != 'rebind' and not _operator(actor):
        frappe.throw('需要专项账号交接权限。', frappe.PermissionError)
    if kind == 'custody' and (actor != 'Administrator' or not frappe.conf.get('hbos_administrator_custody_handover_enabled')):
        frappe.throw('Administrator 保管人交接需独立启用专项许可，不能通过普通换绑执行。', frappe.PermissionError)
    if actor == 'Administrator' and kind in {'rebind', 'roles'}:
        frappe.throw('Administrator 使用保管人交接；管理职责由双方永久个人账号承接。', frappe.PermissionError)
    proof = accounts.require_proof(actor, consume=True)
    if kind != 'rebind' and proof['method'] != 'password':
        frappe.throw('组织授权和管理员交接须验证当前负责人的密码及既有 MFA。', frappe.AuthenticationError)
    settings = _settings()
    if not frappe.db.exists('DocType', 'HBOS Account Operation'):
        frappe.throw('账号变更结构尚未部署，请管理员先备份并迁移。')
    target = actor
    create_personal = bool(frappe.utils.cint(new_personal_account))
    if kind == 'identity_restore':
        resolved = target_user if frappe.db.exists('User', target_user) else frappe.db.get_value('User', {'username': target_user}, 'name')
        target = '' if create_personal else accounts.require_user(resolved or 'Guest')
        if target in {'Guest', 'Administrator'}:
            frappe.throw('身份归属只允许本人永久普通账号。', frappe.PermissionError)
    old_identity = accounts._bound_identity(target) if target else None
    if kind == 'rebind' and not old_identity:
        frappe.throw('当前没有飞书绑定，请使用已有账号绑定入口。')
    selected = json.loads(roles) if isinstance(roles, str) else list(roles or [])
    if kind == 'roles':
        owned_roles = {r.role for r in frappe.get_doc('User', actor).roles} - {'All', 'Guest'}
        if not selected or len(selected) != len(set(selected)) or not set(selected) <= owned_roles:
            frappe.throw('只能交接当前账号明确持有且逐项选择的管理角色。', frappe.PermissionError)
    elif selected:
        frappe.throw('此操作不转移角色。', frappe.PermissionError)
    version = security.ensure(target).security_version if target else 0
    security.ensure(actor)
    doc = frappe.get_doc({'doctype': 'HBOS Account Operation', 'name': operation_name,
        'kind': kind, 'state': 'Invited', 'initiator': actor, 'initiator_session': accounts.session_digest(),
        'initiator_epoch': accounts.epoch(actor), 'target_user': target or None, 'target_version': version,
        'tenant_key': settings.tenant_key, 'app_id': settings.app_id, 'old_identity': old_identity.name if old_identity else None,
        'expires_at': frappe.utils.add_to_date(frappe.utils.now_datetime(), seconds=OPERATION_TTL),
        'reason': str(reason).strip(), 'allow_source_migration': 0,
        'roles_json': json.dumps(selected), 'restore_personal_account': int(kind == 'identity_restore' and create_personal)})
    token = secrets.token_urlsafe(32)
    doc.invite_hash = accounts.digest(token)
    _save(doc, insert=True)
    _event(doc, 'initiated', proof_method=proof['method'], reason=doc.reason)
    accounts.no_store()
    origin = str(frappe.conf.get('hbos_portal_origin') or '').rstrip('/')
    return {'operation': doc.name, 'invitation_url': origin + '/hbos/account-change#' + urlencode({'operation': doc.name, 'invitation': token}), 'expires_in': OPERATION_TTL}


@frappe.whitelist(allow_guest=True, methods=['POST'])
@rate_limit(limit=10, seconds=300)
def redeem_invitation(operation: str, invitation: str) -> dict:
    accounts.require_post()
    doc = _load(operation, lock=True)
    if doc.kind in {'roles', 'custody'} and accounts.session_digest() == doc.initiator_session:
        frappe.throw('请由接任者在自己的独立浏览器打开邀请，不共享交出人的 Session。', frappe.PermissionError)
    if doc.invite_redeemed or len(str(invitation)) > 128 or not secrets.compare_digest(str(doc.invite_hash), accounts.digest(str(invitation))):
        frappe.throw('邀请已使用、无效或过期。', frappe.ValidationError)
    nonce = secrets.token_urlsafe(32)
    doc.invite_redeemed, doc.invite_hash, doc.participant_nonce_hash = 1, None, accounts.digest(nonce)
    _save(doc)
    frappe.cache.set_value('hbos:change:participant:' + accounts.digest(nonce), {'operation': doc.name}, expires_in_sec=OPERATION_TTL)
    frappe.local.cookie_manager.set_cookie(PARTICIPANT_COOKIE, nonce, httponly=True, samesite='Lax', max_age=OPERATION_TTL)
    _event(doc, 'invitation_redeemed')
    accounts.no_store()
    # A redeemed invitation authorizes only its verification ceremony. It does
    # not reveal a target account or authenticate its bearer as that account.
    return {'operation': doc.name, 'kind': doc.kind, 'requires_feishu_verification': True}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def start_authorization() -> dict:
    from hbos_portal.auth.feishu import _pkce_pair, build_authorize_url, BROWSER_COOKIE
    from hbos_portal.auth.state import RedisOAuthStateStore
    accounts.require_post()
    doc = _participant()
    settings = _settings()
    verifier, challenge = _pkce_pair() if settings.pkce_enabled else (None, None)
    state, browser = RedisOAuthStateStore(frappe.cache).create(redirect_to='/hbos/account-change',
        intent='rebind' if doc.kind == 'rebind' else 'handover', code_verifier=verifier,
        operation_id=doc.name, participant_digest=doc.participant_nonce_hash)
    frappe.local.cookie_manager.set_cookie(BROWSER_COOKIE, browser, httponly=True, samesite='Lax', max_age=480)
    return {'authorize_url': build_authorize_url(settings, state=state, code_challenge=challenge)}


def authorized_callback(state, identity: dict) -> None:
    from hbos_portal.auth.feishu import identity_key, FeishuLoginError
    doc = _participant(lock=True)
    expected_intent = 'rebind' if doc.kind == 'rebind' else 'handover'
    if state.intent != expected_intent or state.operation_id != doc.name or state.participant_digest != doc.participant_nonce_hash:
        raise FeishuLoginError('operation_invalid', '账号变更意图或验证浏览器不匹配。')
    settings = _settings()
    key = identity_key(provider='feishu', tenant_key=identity['tenant_key'], app_id=settings.app_id, id_type='open_id', external_id=identity['open_id'])
    row = accounts.identity_row(settings, identity)
    if doc.old_identity and frappe.db.get_value('HBOS External Identity', doc.old_identity, 'identity_key') == key:
        raise FeishuLoginError('same_identity', '新旧飞书身份相同，没有更改绑定。')
    if row and not frappe.db.get_value('User', row.user, 'enabled'):
        raise FeishuLoginError('account_disabled', '该身份对应的原账号已停用，不得通过变更绕过。')
    if doc.kind == 'roles' and (not row or not row.enabled or row.user in {doc.target_user, 'Guest', 'Administrator'}):
        raise FeishuLoginError('personal_account_required', '接任者须先使用自己的永久个人账号；此回调不会开户或签发管理员会话。')
    if doc.kind == 'identity_restore':
        if not row or row.enabled:
            raise FeishuLoginError('identity_conflict', '只有已撤销的身份可通过明确的普通账号归属流程恢复。')
        source = doc.target_user
    else:
        source = row.user if row else None
        if row and not row.enabled and source != doc.target_user:
            raise FeishuLoginError('identity_revoked', '旧身份需组织授权的普通账号归属处理，不能直接迁移。')
    verified_identity = {field: identity.get(field) for field in ('tenant_key', 'open_id', 'display_name')}
    doc.new_identity_key, doc.new_identity_sealed, doc.source_user = key, _seal(verified_identity), source
    doc.source_verified_at, doc.recipient_accepted, doc.credential_verified = None, 0, 0
    doc.credential_sealed, doc.mfa_sealed = None, None
    doc.state = 'Identity Verified'
    _save(doc)
    _event(doc, 'new_identity_verified', has_source_account=bool(source))


@frappe.whitelist(methods=['GET'])
def get_operation(operation: str = '', request_id: str = '') -> dict:
    accounts.no_store()
    user = accounts.require_user()
    if request_id:
        from uuid import UUID
        try:
            UUID(request_id)
        except (ValueError, TypeError, AttributeError):
            frappe.throw('提交编号无效，请重新发起。')
        operation = accounts.digest(user + ':' + accounts.session_digest() + ':' + request_id)[:32]
    if isinstance(operation, str) and 8 <= len(operation) <= 64 and frappe.db.exists('HBOS Account Operation', operation):
        doc = frappe.get_doc('HBOS Account Operation', operation)
        # A new normal login may query the final outcome of its own operation.
        # No actor can resume a write or see another user's target from here.
        if doc.initiator == user and (doc.state in FINAL or frappe.utils.get_datetime(doc.expires_at) <= frappe.utils.now_datetime()):
            return {'operation': doc.name, 'kind': doc.kind, 'state': doc.state if doc.state in FINAL else 'Expired', 'ready': False, 'expires_in': 0}
    return _view(_owner(operation))


@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_participant() -> dict:
    accounts.no_store()
    doc = _participant()
    if not doc.new_identity_sealed:
        return {'operation': doc.name, 'kind': doc.kind, 'requires_feishu_verification': True}
    return _view(doc, participant=True)


@frappe.whitelist(allow_guest=True, methods=['POST'])
@rate_limit(limit=8, seconds=300)
def verify_source(password: str = '', otp: str = '', tmp_id: str = '') -> dict:
    accounts.require_post()
    doc = _participant(lock=True)
    if not doc.new_identity_sealed:
        frappe.throw('请先完成新飞书身份授权。', frappe.AuthenticationError)
    if not doc.source_user:
        return {'verified': True, 'source_account_required': False}
    if password:
        user, challenge = accounts.verify_credentials(doc.source_user, password, otp=otp, tmp_id=tmp_id)
        if challenge:
            return challenge
        if user != doc.source_user:
            frappe.throw('来源账号所有权验证不一致。', frappe.AuthenticationError)
        from frappe.auth import validate_ip_address
        validate_ip_address(user)
        manager = accounts._manager(); manager.user = user; manager.validate_hour()
        method = 'password'
    else:
        if frappe.session.user != doc.source_user:
            frappe.throw('请在接任者自己的浏览器验证本人账号密码，或登录本人账号后使用收件验证码验证。', frappe.AuthenticationError)
        proof = accounts.require_proof(doc.source_user, consume=True)
        method = proof['method']
    migrating = doc.kind in {'rebind', 'custody'} and doc.source_user != doc.target_user
    if migrating and (method != 'password' or not accounts.has_password(doc.source_user) or frappe.get_system_settings('disable_user_pass_login')):
        frappe.throw('迁出前须验证来源账号仍可用的密码及既有 MFA，不能丢失最后一种登录方式。', frappe.PermissionError)
    doc.source_epoch = accounts.epoch(doc.source_user)
    doc.source_verified_at = frappe.utils.now_datetime()
    _save(doc)
    _event(doc, 'source_account_verified', proof_method=method, alternate_login_preserved=bool(migrating))
    return {'verified': True, 'expires_in': accounts.PROOF_TTL}


@frappe.whitelist(methods=['POST'])
def authorize_source_migration(operation: str, confirm: int = 0) -> dict:
    accounts.require_post()
    doc = _owner(operation, lock=True)
    if not frappe.utils.cint(confirm) or doc.kind not in {'rebind', 'custody'} or not doc.new_identity_sealed or not doc.source_user or doc.source_user == doc.target_user:
        frappe.throw('没有已验证的新身份来源迁出方案。', frappe.PermissionError)
    proof = accounts.require_proof(doc.initiator, consume=True)
    if doc.kind == 'custody' and proof['method'] != 'password':
        frappe.throw('Administrator 迁出方案须原密码与 MFA 重新认证。', frappe.AuthenticationError)
    doc.allow_source_migration = 1
    _save(doc); _event(doc, 'source_migration_authorized', source_user=doc.source_user,
        new_identity_key=doc.new_identity_key, requires_alternate_password=True)
    return {'authorized': True, 'requires_source_proof_and_final_confirmation': True}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def prepare_custody_credentials(new_password: str, confirmation: str) -> dict:
    accounts.require_post()
    doc = _participant(lock=True)
    if doc.kind != 'custody' or not doc.new_identity_sealed or not _source_ready(doc):
        frappe.throw('请先完成接任者身份与来源账号验证。', frappe.AuthenticationError)
    if new_password != confirmation:
        frappe.throw('两次密码不一致，没有保存。')
    from frappe.core.doctype.user.user import test_password_strength, handle_password_test_fail
    from frappe.utils.password import passlibctx
    import pyotp
    if not 16 <= len(new_password) <= 512:
        frappe.throw('接任密码须为 16–512 字符，且符合站点策略。')
    feedback = test_password_strength(new_password, user_data=['Administrator']).get('feedback')
    if feedback and not feedback.get('password_policy_validation_passed', False):
        handle_password_test_fail(feedback)
    secret = pyotp.random_base32()
    doc.credential_sealed = _seal(passlibctx.hash(new_password))
    doc.mfa_sealed, doc.credential_verified = _seal(secret), 0
    _save(doc)
    accounts.no_store()
    # Authenticator enrollment is shown only to this verified participant,
    # never to the initiator or a public QR-image service.
    uri = pyotp.TOTP(secret).provisioning_uri(name='Administrator @ ' + str(frappe.local.site), issuer_name='HBOS')
    import base64, io, pyqrcode
    image = io.BytesIO(); pyqrcode.create(uri).png(image, scale=5)
    return {'mfa_qr': 'data:image/png;base64,' + base64.b64encode(image.getvalue()).decode(), 'expires_in': OPERATION_TTL}


@frappe.whitelist(allow_guest=True, methods=['POST'])
@rate_limit(limit=8, seconds=300)
def verify_custody_credentials(password: str, otp: str) -> dict:
    accounts.require_post()
    doc = _participant(lock=True)
    if doc.kind != 'custody' or not doc.credential_sealed or not doc.mfa_sealed or not _source_ready(doc):
        frappe.throw('接任凭据尚未准备或本人验证已过期。', frappe.AuthenticationError)
    from frappe.utils.password import passlibctx
    import pyotp
    if not passlibctx.verify(password, _open(doc.credential_sealed)) or not pyotp.TOTP(_open(doc.mfa_sealed)).verify(str(otp), valid_window=0):
        frappe.throw('新密码或新 MFA 验证未通过。', frappe.AuthenticationError)
    doc.credential_verified = 1
    _save(doc)
    _event(doc, 'successor_credentials_verified', new_password=True, new_mfa=True)
    return {'verified': True}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def accept_participation(confirm: int = 0) -> dict:
    accounts.require_post()
    doc = _participant(lock=True)
    view = _view(doc, participant=True)
    if not frappe.utils.cint(confirm) or not doc.new_identity_sealed or not view['source_proven'] or view['conflict'] or (doc.kind == 'custody' and not doc.credential_verified):
        frappe.throw('请完成本人验证、冲突处理及新凭据准备，并明确确认影响。', frappe.AuthenticationError)
    doc.recipient_accepted, doc.recipient_accepted_at, doc.state = 1, frappe.utils.now_datetime(), 'Ready'
    _save(doc)
    _event(doc, 'recipient_confirmed', participant_identity=doc.new_identity_key)
    return {'accepted': True, 'awaiting_initiator_confirmation': True}


def _lock_subjects(doc):
    for user in sorted({u for u in [doc.target_user, doc.source_user] if u}):
        rows = frappe.db.sql('SELECT enabled FROM `tabUser` WHERE name=%s FOR UPDATE', (user,))
        if not rows or not rows[0][0]:
            frappe.throw('涉及账号已停用，没有改变绑定。', frappe.AuthenticationError)
        row = security.ensure(user)
        frappe.db.sql('SELECT name FROM `tabHBOS Account Security` WHERE name=%s FOR UPDATE', (row.name,))
    if doc.target_user and security.record(doc.target_user, lock=True).security_version != doc.target_version:
        frappe.throw('目标账号已发生其他安全变更，请重新发起。', frappe.AuthenticationError)


def _write_identity(doc, identity: dict):
    from hbos_portal.auth.feishu import FeishuLoginError
    settings = _settings()
    current = accounts._bound_identity(doc.target_user, lock=True)
    if (current.name if current else None) != (doc.old_identity or None):
        raise FeishuLoginError('identity_conflict', '旧绑定已变化，没有执行变更。')
    new = accounts.identity_row(settings, identity, lock=True)
    if new and doc.kind != 'identity_restore' and new.user != (doc.source_user or doc.target_user):
        raise FeishuLoginError('identity_conflict', '新身份归属已变化，没有执行变更。')
    if new and new.enabled and new.user != doc.target_user:
        if not doc.allow_source_migration or not _source_ready(doc) or not accounts.has_password(new.user) or frappe.get_system_settings('disable_user_pass_login'):
            raise FeishuLoginError('identity_conflict', '新身份仍属于另一账号，迁出证明或最后登录方式不满足。')
    if doc.old_identity:
        frappe.db.set_value('HBOS External Identity', doc.old_identity, {'enabled': 0, 'active_user_key': None,
            'retired_reason': 'custody' if doc.kind == 'custody' else 'replaced', 'retired_operation': doc.name})
    mapping = frappe.get_doc('HBOS External Identity', new.name, for_update=True) if new else frappe.get_doc({
        'doctype': 'HBOS External Identity', 'provider': 'feishu', 'tenant_key': settings.tenant_key,
        'app_id': settings.app_id, 'id_type': 'open_id', 'external_id': identity['open_id']})
    mapping.user, mapping.enabled = doc.target_user, 1
    mapping.retired_reason, mapping.retired_operation = None, None
    mapping.last_verified_at = frappe.utils.now_datetime()
    authority = frappe.flags.get('hbos_identity_authority')
    frappe.flags.hbos_identity_authority = tuple(mapping.get(k) for k in ('provider', 'tenant_key', 'app_id', 'id_type', 'external_id', 'user'))
    try:
        mapping.save(ignore_permissions=True) if new else mapping.insert(ignore_permissions=True)
    except (frappe.UniqueValidationError, frappe.DuplicateEntryError) as exc:
        raise FeishuLoginError('identity_conflict', '另一申请已取得此身份，当前事务未提交；请重新核对双方归属。') from exc
    finally:
        frappe.flags.hbos_identity_authority = authority


def _role_transfer(doc):
    if not _operator(doc.initiator) or doc.target_user == 'Administrator' or doc.source_user in {doc.target_user, 'Administrator', 'Guest', None}:
        frappe.throw('须使用双方各自的永久个人账号。', frappe.PermissionError)
    roles = set(json.loads(doc.roles_json))
    outgoing, successor = frappe.get_doc('User', doc.target_user), frappe.get_doc('User', doc.source_user)
    if not roles <= {r.role for r in outgoing.roles}:
        frappe.throw('待交接角色已变化，请重新核对。', frappe.PermissionError)
    outgoing.roles = [r for r in outgoing.roles if r.role not in roles]
    successor.add_roles(*sorted(roles))
    outgoing.save(ignore_permissions=True)
    if 'System Manager' in roles:
        # A specific, mutually verified role handover may approve this one
        # manager's internal Portal/Feishu access. No tenant-wide privileged
        # allowance or automatic role grant is created by ordinary onboarding.
        frappe.db.set_value('HBOS Account Security', doc.source_user, 'management_operation', doc.name)
        frappe.db.set_value('HBOS Account Security', doc.target_user, 'management_operation', None)
    security.advance_version(doc.source_user)
    security.advance_version(doc.target_user)
    frappe.clear_cache(user=doc.target_user); frappe.clear_cache(user=doc.source_user)


def _custody_cutover(doc):
    if doc.target_user != 'Administrator' or doc.initiator != 'Administrator' or not frappe.conf.get('hbos_administrator_custody_handover_enabled') or not doc.credential_verified:
        frappe.throw('Administrator 专项交接证明不满足。', frappe.PermissionError)
    hooks = frappe.get_hooks('auth_hooks')
    if set(hooks) - {'hbos_portal.auth.accounts.check_request'}:
        frappe.throw('存在尚未纳入交接清单的认证 Hook；先核对其目标账号撤销方式，当前交接未提交。', frappe.PermissionError)
    # All known native auth paths are target-scoped. The global app's Secret,
    # integrations and unrelated users are never rotated or removed here.
    for name in ('OAuth Bearer Token', 'OAuth Authorization Code', 'Passkey'):
        if frappe.db.exists('DocType', name):
            fields = [f.fieldname for f in frappe.get_meta(name).fields if f.fieldtype == 'Link' and f.options == 'User']
            if not fields:
                frappe.throw('认证提供方结构无法安全核对：' + name + '，交接没有提交。')
            for field in fields:
                frappe.db.delete(name, {field: doc.target_user})
    user = frappe.get_doc('User', doc.target_user)
    if user.meta.has_field('social_logins'):
        user.social_logins = []
    for field in ('api_key', 'api_secret', 'reset_password_key'):
        if user.meta.has_field(field):
            user.set(field, None)
    user.save(ignore_permissions=True)
    frappe.db.sql('DELETE FROM `__Auth` WHERE doctype=%s AND name=%s', ('User', doc.target_user))
    from frappe.twofactor import PARENT_FOR_DEFAULTS
    # These are the native User-specific OTP enrollment and recovery defaults.
    frappe.db.sql('DELETE FROM `tabDefaultValue` WHERE parent=%s AND defkey LIKE %s',
        (PARENT_FOR_DEFAULTS, doc.target_user + '\\_%'))
    frappe.db.sql('INSERT INTO `__Auth` (doctype,name,fieldname,password,encrypted) VALUES (%s,%s,%s,%s,0)',
        ('User', doc.target_user, 'password', _open(doc.credential_sealed)))
    row = security.ensure(doc.target_user)
    state = frappe.get_doc('HBOS Account Security', row.name)
    state.custody_mode, state.blocked, state.mfa_counter = 1, 0, 0
    state.mfa_secret = _open(doc.mfa_sealed)
    old = frappe.flags.get('hbos_security_authority'); frappe.flags.hbos_security_authority = doc.target_user
    try:
        state.save(ignore_permissions=True)
    finally:
        frappe.flags.hbos_security_authority = old
    # Re-enroll the native record too; the custody login guard additionally
    # enforces MFA even for the framework-exempt built-in Administrator.
    from frappe.twofactor import set_default
    from frappe.utils.password import encrypt
    set_default(doc.target_user + '_otpsecret', encrypt(_open(doc.mfa_sealed)))
    set_default(doc.target_user + '_otplogin', 1)
    security.advance_version(doc.target_user)


@frappe.whitelist(methods=['POST'])
def commit_change(operation: str, confirm: int = 0) -> dict:
    accounts.require_post()
    doc = _owner(operation, lock=True)
    proof = accounts.require_proof(doc.initiator, consume=True)
    if doc.kind != 'rebind' and proof['method'] != 'password':
        frappe.throw('最终交接须重新验证当前负责人的密码及 MFA。', frappe.AuthenticationError)
    if not frappe.utils.cint(confirm) or not _view(doc)['ready']:
        frappe.throw('双方验证、冲突检查或明确确认尚未完成。', frappe.AuthenticationError)
    from hbos_portal.auth.onboarding import serialize
    # The same absent-identity lock is used by ordinary automatic onboarding.
    # Hold it through the commit, then re-read ownership with locking reads.
    from hbos_portal.auth.feishu import FeishuLoginError
    try:
        with serialize('identity', doc.new_identity_key) if doc.kind != 'roles' else nullcontext():
            return _commit_verified(doc)
    except FeishuLoginError as exc:
        frappe.db.rollback()
        frappe.throw(str(exc), frappe.PermissionError)
    except (frappe.QueryDeadlockError, frappe.QueryTimeoutError):
        frappe.db.rollback()
        frappe.throw('并发账号变更使本次事务失效，原绑定未改变。请刷新状态、核对归属并重新验证。', frappe.PermissionError)


def _commit_verified(doc) -> dict:
    _lock_subjects(doc)
    identity = _open(doc.new_identity_sealed)
    if doc.source_user and not _source_ready(doc):
        frappe.throw('来源账号本人验证已过期。', frappe.AuthenticationError)
    if doc.kind == 'roles':
        _role_transfer(doc)
    else:
        if doc.kind == 'identity_restore':
            if not _operator(doc.initiator):
                frappe.throw('组织授权已失效。', frappe.PermissionError)
            if doc.restore_personal_account:
                from hbos_portal.auth.onboarding import insert_ordinary_user
                doc.target_user = insert_ordinary_user(_settings(), identity)
            elif doc.target_user == 'Administrator' or doc.target_user != doc.source_user:
                frappe.throw('普通账号归属证明不一致。', frappe.PermissionError)
        _write_identity(doc, identity)
        if doc.kind == 'custody':
            _custody_cutover(doc)
        else:
            security.advance_version(doc.target_user)
        if doc.source_user and doc.source_user != doc.target_user and doc.kind != 'identity_restore':
            security.advance_version(doc.source_user)
    doc.state, doc.completed_at = 'Completed', frappe.utils.now_datetime()
    # Erase staged credential material after atomic cutover; history contains
    # relationship/approval facts, never passwords, OTPs or invitation tokens.
    doc.credential_sealed, doc.mfa_sealed, doc.invite_hash, doc.participant_nonce_hash = None, None, None, None
    _save(doc)
    _event(doc, 'completed', initiator_confirmed=True, recipient_confirmed=True,
        roles=json.loads(doc.roles_json or '[]'), source_login_preserved=bool(doc.source_user and doc.kind in {'rebind', 'custody'}), reason=doc.reason)
    frappe.db.commit()
    _notify_after_commit(doc, identity)
    return {'completed': True, 'operation': doc.name, 'requires_login': True,
        'notification_status': doc.notification_status, 'redirect_to': '/hbos/login?status=account_changed'}


def _notify_after_commit(doc, identity: dict):
    try:
        frappe.enqueue('hbos_portal.auth.operations.deliver_notifications', operation=doc.name,
            job_id='hbos-account-change-' + doc.name, enqueue_after_commit=True)
        doc.notification_status = 'queued'
    except Exception:
        doc.notification_status = 'queue_failed'
    try:
        _save(doc)
        _event(doc, 'notification_queued', status=doc.notification_status)
        frappe.db.commit()
    except Exception:
        # The security transaction is already committed. Notice failures must
        # never report a failed cutover or restore the old access paths.
        frappe.db.rollback()
        doc.notification_status = 'status_unconfirmed'


def deliver_notifications(operation: str):
    doc = frappe.get_doc('HBOS Account Operation', operation)
    if doc.state != 'Completed' or doc.notification_status.startswith('['):
        return
    identity = _open(doc.new_identity_sealed)
    from hbos_portal.auth.feishu import send_inbox_notice
    recipients = {identity['open_id']}
    if doc.old_identity:
        recipients.add(frappe.db.get_value('HBOS External Identity', doc.old_identity, 'external_id'))
    outcomes = []
    for recipient in sorted(x for x in recipients if x):
        try:
            send_inbox_notice(_settings(), recipient, 'HBOS 账号安全变更已完成。操作编号 ' + doc.name + '。请重新登录；如非本人确认，请立即联系组织管理员。', message_uuid=accounts.digest(doc.name + recipient)[:32])
            outcomes.append('provider_acknowledged')
        except Exception:
            outcomes.append('delivery_failed')
    doc.notification_status = json.dumps(outcomes)
    _save(doc); _event(doc, 'notification_result', statuses=outcomes)
    frappe.db.commit()  # Notification failure never restores old credentials.


@frappe.whitelist(methods=['POST'])
def cancel(operation: str) -> dict:
    accounts.require_post()
    doc = _owner(operation, lock=True)
    doc.state, doc.invite_hash, doc.participant_nonce_hash = 'Cancelled', None, None
    doc.credential_sealed, doc.mfa_sealed, doc.new_identity_sealed = None, None, None
    _save(doc); _event(doc, 'cancelled')
    return {'cancelled': True, 'old_binding_preserved': True}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def cancel_participation() -> dict:
    accounts.require_post()
    doc = _participant(lock=True)
    if not doc.new_identity_sealed:
        frappe.throw('请先验证本次参与的飞书身份。', frappe.AuthenticationError)
    doc.state, doc.invite_hash, doc.participant_nonce_hash = 'Cancelled', None, None
    doc.credential_sealed, doc.mfa_sealed, doc.new_identity_sealed = None, None, None
    _save(doc); _event(doc, 'recipient_cancelled', old_binding_preserved=True)
    return {'cancelled': True, 'old_binding_preserved': True}


def expire_operations():
    if not frappe.db.exists('DocType', 'HBOS Account Operation'):
        return
    for name in frappe.get_all('HBOS Account Operation', filters={'state': ['not in', list(FINAL)], 'expires_at': ['<', frappe.utils.now_datetime()]}, pluck='name'):
        frappe.db.sql('SELECT name FROM `tabHBOS Account Operation` WHERE name=%s FOR UPDATE', (name,))
        doc = frappe.get_doc('HBOS Account Operation', name, for_update=True)
        if doc.state not in FINAL:
            doc.state = 'Expired'
            doc.credential_sealed, doc.mfa_sealed, doc.invite_hash, doc.participant_nonce_hash, doc.new_identity_sealed = None, None, None, None, None
            _save(doc); _event(doc, 'expired', old_binding_preserved=True)


@frappe.whitelist(methods=['GET'])
def recent_changes() -> dict:
    accounts.no_store()
    user = accounts.require_user()
    if not frappe.db.exists('DocType', 'HBOS Account Operation'):
        return {'changes': []}
    rows = frappe.get_all('HBOS Account Operation', or_filters=[['initiator', '=', user], ['target_user', '=', user], ['source_user', '=', user]],
        filters={'state': ['in', list(FINAL)]}, fields=['name', 'kind', 'state', 'completed_at', 'notification_status'], order_by='modified desc', limit=10)
    return {'changes': rows}
