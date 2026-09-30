"""One atomic ordinary-account service shared by verified OAuth entry points."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from contextlib import contextmanager

import frappe

RESERVED = {'administrator', 'admin', 'guest', 'root', 'system', 'systemmanager',
    'support', 'hbos', 'api', 'service', 'owner', 'test', 'null', 'none'}
# Surname readings take precedence only at the beginning of a Chinese name.
# This affects a login alias, never the identity or ownership of an account.
SURNAMES = {'单': 'shan', '解': 'xie', '曾': 'zeng', '区': 'ou', '仇': 'qiu',
    '查': 'zha', '乐': 'yue', '翟': 'zhai', '尉迟': 'yuchi', '长孙': 'zhangsun',
    '万俟': 'moqi', '朴': 'piao'}


def login_alias_base(display_name: str) -> str:
    from pypinyin import Style, lazy_pinyin

    name = unicodedata.normalize('NFKC', str(display_name or ''))[:120].strip()
    prefix = ''
    for surname in sorted(SURNAMES, key=len, reverse=True):
        if name.startswith(surname):
            prefix, name = SURNAMES[surname], name[len(surname):]
            break
    text = prefix + ''.join(lazy_pinyin(name, style=Style.NORMAL, errors=lambda x: [x]))
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    alias = re.sub('[^a-z0-9]', '', text)
    if not alias or not alias[0].isalpha():
        alias = 'member' + alias
    if alias in RESERVED:
        alias = 'member' + alias
    return alias[:56]


def alias_candidate(base: str, number: int) -> str:
    suffix = str(number) if number > 1 else ''
    return base[:64 - len(suffix)] + suffix


@contextmanager
def serialize(namespace: str, value: str):
    # Connection-scoped MariaDB locks cover an absent identity/alias row. The
    # ordinary User and identity unique indexes remain the final arbiter.
    site_key = str(frappe.local.site) + '\x1f' + namespace + '\x1f' + value
    key = 'hbos:account:' + hashlib.sha256(site_key.encode()).hexdigest()[:40]
    if not frappe.db.sql('SELECT GET_LOCK(%s, 10)', (key,))[0][0]:
        from hbos_portal.auth.feishu import FeishuLoginError
        raise FeishuLoginError('account_busy', '账号正在完成另一项操作，请重新授权。')
    try:
        yield
    finally:
        frappe.db.sql('SELECT RELEASE_LOCK(%s)', (key,))


def insert_ordinary_user(settings, identity: dict) -> str:
    """Called only inside an authorized transaction; never adopts an old User."""
    from hbos_portal.auth.accounts import has_password
    from hbos_portal.auth.feishu import FeishuLoginError, provisioned_user_id

    user = provisioned_user_id(settings, identity)
    if frappe.db.exists('User', user):
        raise FeishuLoginError('identity_conflict', '该身份已有账号记录，请验证原账号或联系管理员核对。')
    try:
        base = login_alias_base(identity.get('display_name') or '')
    except ImportError as exc:
        raise FeishuLoginError('onboarding_dependency_missing', '登录名组件未部署，请管理员更新 Portal 依赖。') from exc
    with serialize('alias', base):
        for number in range(1, 100001):
            alias = alias_candidate(base, number)
            if frappe.db.exists('User', {'username': alias}) or frappe.db.exists('User', alias):
                continue
            frappe.db.savepoint('hbos_alias_insert')
            try:
                frappe.get_doc({'doctype': 'User', 'email': user, 'username': alias,
                    'first_name': identity.get('display_name') or '企业成员',
                    'user_type': 'Website User', 'enabled': 1, 'send_welcome_email': 0,
                    'roles': []}).insert(ignore_permissions=True)
                break
            except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
                frappe.db.rollback(save_point='hbos_alias_insert')
                # Retry an alias collision; an existing primary account is
                # never silently adopted or merged by its profile name/email.
                if frappe.db.exists('User', user):
                    raise FeishuLoginError('identity_conflict', '账号主标识存在并发冲突，请重新授权。')
        else:
            raise FeishuLoginError('account_busy', '登录别名暂时无法分配，请联系管理员。')
        if has_password(user):
            raise FeishuLoginError('identity_conflict', '新飞书账号的密码状态异常，开户未完成。')
        return user


def resolve_verified_login(settings, identity: dict) -> tuple[str, bool]:
    """Verified login creates User+binding together, or returns the original User.

    All callers must have completed exchange_identity. Disabled/revoked rows
    are tombstones and require a separate explicitly authorized recovery.
    """
    from hbos_portal.auth import accounts
    from hbos_portal.auth.feishu import FeishuLoginError, identity_key, _validate_login_account

    key = identity_key(provider='feishu', tenant_key=identity['tenant_key'], app_id=settings.app_id,
        id_type='open_id', external_id=identity['open_id'])
    if identity['tenant_key'] != settings.tenant_key or not settings.auto_provision_internal:
        raise FeishuLoginError('tenant_rejected', '当前企业身份不符合本 Site 的准入条件。')
    with serialize('identity', key):
        try:
            row = accounts.identity_row(settings, identity)
            if row:
                if not frappe.db.get_value('User', row.user, 'enabled'):
                    raise FeishuLoginError('account_disabled', '对应 HBOS 账号已停用。')
                if not row.enabled:
                    raise FeishuLoginError('identity_revoked', '此身份的旧绑定已撤销或更换；请验证原账号或通过受控归属流程恢复。')
                return _validate_login_account(row.user), False
            user = insert_ordinary_user(settings, identity)
            accounts.bind_identity(settings, identity, user)
            accounts.audit('verified_feishu_automatic_onboarding', user)
            frappe.db.commit()
            return user, True
        except Exception:
            frappe.db.rollback()
            raise
