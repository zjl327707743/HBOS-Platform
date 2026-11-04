"""Native SQL/credential tests on freshly created, explicitly isolated Sites.

Provider identities are synthetic injected assertions. These checks are never
evidence of human OAuth, inbox delivery, or a real Administrator handover.
"""
from __future__ import annotations

import json
import secrets
import time
from uuid import uuid4
from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import frappe
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request
from hbos_portal.auth import accounts, feishu, onboarding, operations, security


def synthetic_settings():
    return feishu.FeishuSettings(app_id='cli_synthetic_changes', tenant_key='synthetic-tenant',
        redirect_uri='https://hbos.example.test/api/method/hbos_portal.auth.feishu.callback',
        scopes=('contact:user.base:readonly',), authorize_id_parameter='client_id', published=True,
        redirect_registered=True, pkce_enabled=True, app_secret='synthetic-not-a-credential', auto_provision_internal=True)


def run() -> dict:
    if not frappe.conf.get('hbos_account_test_site') or not frappe.conf.get('hbos_custody_test_site') or not str(frappe.local.site).startswith(('account-regression.', 'account-ui-regression.', 'platform-smoke.')):
        raise RuntimeError('Destructive custody checks require a freshly created designated isolated Site')
    suffix = secrets.token_hex(6)
    users, mappings, operation_ids, checks = [], [], [], []
    settings = synthetic_settings()
    original = {k:getattr(frappe.local,k,None) for k in ('request','login_manager','cookie_manager','session','response_headers')}
    flags = {k:frappe.conf.get(k) for k in ('hbos_portal_origin','hbos_feishu_allow_administrator_link','hbos_administrator_custody_handover_enabled')}
    frappe.conf.update({'hbos_portal_origin':'https://hbos.example.test','hbos_feishu_allow_administrator_link':1,'hbos_administrator_custody_handover_enabled':1})
    in_test = frappe.in_test; frappe.in_test = True
    from frappe.auth import CookieManager
    from frappe.utils.password import update_password, check_password, encrypt
    import pyotp

    # This Administrator belongs to this newly-created synthetic test Site.
    # Its credential material stays in memory and is restored for repeat runs.
    admin_auth = frappe.db.sql('SELECT doctype,name,fieldname,password,encrypted FROM `__Auth` WHERE doctype=%s AND name=%s', ('User','Administrator'))
    from frappe.twofactor import PARENT_FOR_DEFAULTS, get_default, set_default
    admin_defaults = frappe.db.sql('SELECT defkey,defvalue FROM `tabDefaultValue` WHERE parent=%s AND defkey LIKE %s', (PARENT_FOR_DEFAULTS,'Administrator\\_%'))
    admin_fields = frappe.db.get_value('User','Administrator',['api_key','api_secret','reset_password_key'],as_dict=True)

    def session(user='Guest', *, sid=None, cookies=None):
        frappe.set_user(user)
        frappe.local.session.sid = sid or 'synthetic-change-' + suffix + '-' + user
        version = security.record(user) if user != 'Guest' else None
        frappe.local.session.data = frappe._dict(csrf_token='synthetic-csrf', hbos_security_version=version.security_version if version else 0)
        headers = {'Origin':'https://hbos.example.test','X-Requested-With':'XMLHttpRequest','X-Frappe-CSRF-Token':'synthetic-csrf'}
        if cookies: headers['Cookie'] = '; '.join(k+'='+v for k,v in cookies.items())
        frappe.local.request = Request(EnvironBuilder(method='POST',base_url='https://hbos.example.test',json={},headers=headers).get_environ())
        frappe.local.request_ip = '127.0.0.1'
        frappe.local.cookie_manager = CookieManager()
        frappe.local.response_headers = {}
        frappe.local.login_manager = SimpleNamespace(login_as=lambda u: None, logout=lambda *a,**kw:None)
        frappe.flags.hbos_custody_mfa_verified = None

    def error(fn, label):
        try: fn()
        except (frappe.AuthenticationError,frappe.PermissionError,frappe.ValidationError,frappe.CSRFTokenError,feishu.FeishuLoginError):
            frappe.db.rollback(); checks.append(label)
        else: raise AssertionError(label+' must reject')

    def identity(label, name='张三'):
        return {'open_id':'ou_synthetic_' + suffix + '_' + label,'tenant_key':settings.tenant_key,'display_name':name}

    def ordinary(label, password=True, roles=()):
        user = 'change-' + suffix + '-' + label + '@example.test'
        users.append(user)
        frappe.set_user('Administrator')
        frappe.get_doc({'doctype':'User','email':user,'username':'u'+suffix+label,'first_name':'合成账号',
            'send_welcome_email':0,'user_type':'Website User','enabled':1}).insert(ignore_permissions=True)
        if roles:
            frappe.get_doc('User',user).add_roles(*roles)
        credential = secrets.token_urlsafe(40) if password else ''
        if password: update_password(user,credential)
        frappe.db.commit()
        return user,credential

    def bind(value,user):
        accounts.bind_identity(settings,value,user)
        name = accounts.identity_row(settings,value).name
        mappings.append(name); frappe.db.commit(); return name

    def prove(user,password, *, sid=None):
        session(user,sid=sid)
        result = unwrap(accounts.reauthenticate)(password=password)
        assert result.get('verified') and not result.get('mfa_required')

    def begin(user,password,kind='rebind',**kw):
        prove(user,password)
        sid = frappe.session.sid
        request_id = str(uuid4())
        result = operations.begin(kind=kind,reason='隔离测试中双方明确核验本人归属及影响',request_id=request_id,**kw)
        operation_ids.append(result['operation']); frappe.db.commit()
        replay = operations.begin(kind=kind,reason='隔离测试中双方明确核验本人归属及影响',request_id=request_id,**kw)
        assert replay['operation'] == result['operation'] and replay['replayed'] and not replay['invitation_url']
        assert operations.get_operation(request_id=request_id)['operation'] == result['operation']
        if 'begin_response_loss_same_request_query_and_retry_without_second_operation' not in checks:
            checks.append('begin_response_loss_same_request_query_and_retry_without_second_operation')
        invitation = parse_qs(urlsplit(result['invitation_url']).fragment)['invitation'][0]
        return result['operation'],invitation,sid

    def authorize(operation,invitation,value, *, kind='rebind'):
        session()
        unwrap(operations.redeem_invitation)(operation=operation,invitation=invitation)
        nonce = frappe.local.cookie_manager.cookies[operations.PARTICIPANT_COOKIE]['value']
        frappe.db.commit(); session(cookies={operations.PARTICIPANT_COOKIE:nonce})
        doc = frappe.get_doc('HBOS Account Operation',operation)
        state = SimpleNamespace(intent='rebind' if kind=='rebind' else 'handover',operation_id=operation,participant_digest=doc.participant_nonce_hash)
        operations.authorized_callback(state,value); frappe.db.commit()
        return nonce,state

    def participant(nonce,user='Guest'):
        session(user,cookies={operations.PARTICIPANT_COOKIE:nonce})

    def confirm(operation,user,password,sid):
        prove(user,password,sid=sid)
        def queue(method,*args,**kw):
            if method == 'hbos_portal.auth.operations.deliver_notifications':
                raise RuntimeError('synthetic notice queue unavailable')
            return None
        with patch('frappe.enqueue',side_effect=queue):
            return operations.commit_change(operation=operation,confirm=1)

    try:
        with patch.object(feishu,'load_settings',return_value=settings):
            # One service supplies both automatic OAuth and legacy pending flows.
            first = identity('automatic'); users.append(feishu.provisioned_user_id(settings,first))
            count = frappe.db.count('User'); session()
            user,created = onboarding.resolve_verified_login(settings,first)
            assert created and frappe.db.count('User')==count+1
            assert frappe.db.get_value('User',user,'first_name')=='张三'
            alias = frappe.db.get_value('User',user,'username')
            assert alias.startswith('zhangsan') and not accounts.has_password(user)
            assert not set(frappe.get_roles(user)) & {'System Manager','HBOS Account Handover Manager','HR Manager','Stock Manager'}
            assert frappe.db.get_value('User',user,'user_type')=='Website User'
            mappings.append(accounts.identity_row(settings,first).name)
            repeated,new = onboarding.resolve_verified_login(settings,first)
            assert repeated==user and not new and frappe.db.count('User')==count+1
            error(lambda: accounts.verify_credentials(alias,''),'new_user_empty_password_rejected')
            error(lambda: accounts.verify_credentials(alias,'HBOS123456'),'new_user_shared_default_password_rejected')
            checks.append('automatic_first_login_and_repeat_same_permanent_user_without_password')
            second = identity('same-name'); users.append(feishu.provisioned_user_id(settings,second))
            user2,new = onboarding.resolve_verified_login(settings,second)
            assert new and frappe.db.get_value('User',user2,'username') != alias
            mappings.append(accounts.identity_row(settings,second).name)
            checks.append('same_verified_name_gets_distinct_native_unique_pinyin_alias')
            from hbos_portal.auth.concurrency_integration import race
            parallel=identity('parallel','并发开户');users.append(feishu.provisioned_user_id(settings,parallel))
            resolved=race([parallel,parallel])
            assert resolved[0]['user']==resolved[1]['user'] and sum(int(r['created']) for r in resolved)==1
            checks.append('concurrent_same_identity_creates_exactly_one_native_user_and_binding')
            same_names=[identity('parallel-name-'+str(i),'并发同名') for i in range(2)]
            for value in same_names:users.append(feishu.provisioned_user_id(settings,value))
            names=race(same_names)
            aliases=[frappe.db.get_value('User',r['user'],'username') for r in names]
            assert len(set(aliases))==2
            checks.append('concurrent_different_identities_same_pinyin_get_unique_aliases')
            failed = identity('rollback'); failed_user=feishu.provisioned_user_id(settings,failed)
            with patch.object(accounts,'bind_identity',side_effect=RuntimeError('synthetic atomic insert failure')):
                try: onboarding.resolve_verified_login(settings,failed)
                except RuntimeError: pass
                else: raise AssertionError('injected binding failure did not fail')
            assert not frappe.db.exists('User',failed_user) and not accounts.identity_row(settings,failed)
            checks.append('binding_failure_rolls_back_user_no_orphan')
            credential=secrets.token_urlsafe(40); session(user)
            accounts.save_proof(user,'feishu_inbox')  # Synthetic provider assertion; not real inbox acceptance.
            accounts.set_password(new_password=credential); frappe.db.commit()
            assert accounts.verify_credentials(alias,credential)[0]==user
            assert onboarding.resolve_verified_login(settings,first)[0]==user
            checks.append('verified_optional_password_and_feishu_resolve_same_native_user_alias')
            target,pwd=ordinary('target'); old=identity('old'); old_name=bind(old,target)
            operation,invite,sid=begin(target,pwd)
            nonce,state=authorize(operation,invite,identity('new'))
            assert frappe.session.user=='Guest' and not accounts.identity_row(settings,identity('new'))
            checks.append('change_callback_neither_auto_provisions_nor_logs_in')
            # Changing the operation OAuth intent cannot fall into ordinary login.
            error(lambda: operations.authorized_callback(SimpleNamespace(intent='login',operation_id=operation,participant_digest=state.participant_digest),identity('wrong-intent')),'handover_oauth_intent_cannot_be_replayed_as_ordinary_login')
            participant(nonce)
            operations.accept_participation(confirm=1); frappe.db.commit()
            # Security state cannot be forged via browser-supplied Document.flags.
            forged=frappe.get_doc('HBOS Account Security',target); forged.blocked=1; forged.flags.hbos_security_authority=target
            error(lambda: forged.save(ignore_permissions=True),'rest_flags_cannot_modify_security_state')
            participant(nonce)
            error(lambda: unwrap(operations.redeem_invitation)(operation=operation,invitation=invite),'redeemed_invitation_single_use')
            result=confirm(operation,target,pwd,sid)
            assert result['completed'] and result['notification_status']=='queue_failed'
            assert accounts.identity_row(settings,identity('new')).user==target
            mappings.append(accounts.identity_row(settings,identity('new')).name)
            assert not frappe.db.get_value('HBOS External Identity',old_name,'enabled')
            check_password(target,pwd)
            checks.append('rebind_atomic_preserves_user_password_roles_and_notification_failure_does_not_rollback')
            error(lambda: onboarding.resolve_verified_login(settings,old),'replaced_identity_cannot_auto_onboard_or_regain_old_account')
            session(target)
            error(lambda: accounts.require_proof(target),'old_stepup_proof_invalid_after_rebind')
            prove(target,pwd,sid=sid)
            error(lambda: operations.commit_change(operation=operation,confirm=1),'completed_confirmation_cannot_replay')
            # Old session and target-bound security proofs are invalidated.
            session(target); frappe.local.session.data.hbos_security_version=0
            error(security.check_request,'old_cookie_session_version_rejected')
            session(target);frappe.local.session.data.hbos_security_version=0
            frappe.local.request=Request(EnvironBuilder(method='GET',base_url='https://hbos.example.test',headers={'Authorization':'Bearer synthetic-invalid'}).get_environ())
            error(security.check_request,'invalid_auth_header_cannot_bypass_old_cookie_version')
            for ending in ('same','cancel','expire'):
                operation,invite,sid=begin(target,pwd)
                current=identity('new')
                if ending=='same':
                    session(); unwrap(operations.redeem_invitation)(operation=operation,invitation=invite)
                    nonce=frappe.local.cookie_manager.cookies[operations.PARTICIPANT_COOKIE]['value'];frappe.db.commit();participant(nonce)
                    doc=frappe.get_doc('HBOS Account Operation',operation)
                    state=SimpleNamespace(intent='rebind',operation_id=operation,participant_digest=doc.participant_nonce_hash)
                    error(lambda: operations.authorized_callback(state,current),'same_identity_rejected_without_binding_change')
                elif ending=='cancel':
                    session(target,sid=sid); operations.cancel(operation=operation);frappe.db.commit()
                    assert frappe.db.get_value('HBOS Account Operation',operation,'state')=='Cancelled'
                    checks.append('cancel_keeps_original_binding')
                else:
                    frappe.db.set_value('HBOS Account Operation',operation,'expires_at',frappe.utils.add_to_date(frappe.utils.now_datetime(),seconds=-1));frappe.db.commit()
                    error(lambda: unwrap(operations.redeem_invitation)(operation=operation,invitation=invite),'expired_invitation_rejected')
                    operations.expire_operations();frappe.db.commit();checks.append('expiry_keeps_original_binding')
                assert accounts.identity_row(settings,current).enabled
            # One short-lived invitation cannot be claimed by two DB connections.
            operation, invite, sid = begin(target, pwd)
            invitation_results = race([{'operation': operation, 'invitation': invite}] * 2, redeeming=True)
            assert sum(int(result['accepted']) for result in invitation_results) == 1
            checks.append('concurrent_invitation_redemption_is_single_use')
            # A bound source is never stolen; migration needs both concrete proofs.
            source,source_pwd=ordinary('source'); occupied=identity('occupied');bind(occupied,source)
            operation,invite,sid=begin(target,pwd);nonce,_=authorize(operation,invite,occupied)
            assert operations.get_participant()['conflict']
            error(lambda: operations.accept_participation(confirm=1),'occupied_identity_default_no_takeover')
            participant(nonce);assert unwrap(operations.verify_source)(password=source_pwd)['verified'];frappe.db.commit()
            prove(target,pwd,sid=sid);operations.authorize_source_migration(operation=operation,confirm=1);frappe.db.commit()
            participant(nonce);operations.accept_participation(confirm=1);frappe.db.commit()
            confirm(operation,target,pwd,sid)
            assert accounts.identity_row(settings,occupied).user==target and frappe.db.get_value('User',source,'enabled')
            check_password(source,source_pwd);checks.append('two_account_migration_atomic_retains_source_last_password_data_roles')
            pwdless,_=ordinary('passwordless',password=False);last=identity('last');bind(last,pwdless)
            operation,invite,sid=begin(target,pwd);nonce,_=authorize(operation,invite,last)
            participant(nonce,pwdless);accounts.save_proof(pwdless,'feishu_inbox')
            error(lambda: unwrap(operations.verify_source)(),'source_cannot_lose_last_login_method')
            # Two independent verified ceremonies race for one absent identity.
            contenders=[];contender_old=[];shared=identity('race-rebind')
            for index in range(2):
                account,secret=ordinary('race'+str(index));old_value=identity('race-old'+str(index));old_mapping=bind(old_value,account)
                op,inv,owner_sid=begin(account,secret);participant_nonce,_=authorize(op,inv,shared)
                operations.accept_participation(confirm=1);frappe.db.commit()
                contenders.append({'user':account,'password':secret,'operation':op,'sid':owner_sid});contender_old.append(old_mapping)
            committed=race(contenders,committing=True)
            assert sum(int(r['completed']) for r in committed)==1
            for index,result in enumerate(committed):
                assert bool(frappe.db.get_value('HBOS External Identity',contender_old[index],'enabled')) != result['completed']
            checks.append('concurrent_controlled_rebind_one_winner_loser_original_binding_retained')
            # Personal management handover transfers only selected roles.
            manager,manager_pwd=ordinary('manager',roles=('HBOS Account Handover Manager','System Manager'))
            recipient,recipient_pwd=ordinary('recipient');recipient_identity=identity('recipient');bind(recipient_identity,recipient)
            manager_identity=identity('manager');
            # Explicit link policy for this synthetic pre-existing manager only.
            with patch('hbos_portal.auth.accounts.require_user',side_effect=lambda u=None,**kw:u or frappe.session.user): bind(manager_identity,manager)
            operation,invite,sid=begin(manager,manager_pwd,'roles',roles=['System Manager'])
            nonce,_=authorize(operation,invite,recipient_identity,kind='roles');participant(nonce)
            unwrap(operations.verify_source)(password=recipient_pwd);frappe.db.commit();operations.accept_participation(confirm=1);frappe.db.commit()
            confirm(operation,manager,manager_pwd,sid)
            assert 'System Manager' not in frappe.get_roles(manager) and 'HBOS Account Handover Manager' in frappe.get_roles(manager)
            assert 'System Manager' in frappe.get_roles(recipient)
            assert accounts.identity_row(settings,recipient_identity).user==recipient
            from hbos_portal.services.internal_users import load_internal_user_decision
            assert load_internal_user_decision(recipient).allowed
            checks.append('personal_role_handover_selective_no_account_merge_or_identity_swap')
            # High risk built-in test Administrator: all credentials are synthetic.
            admin_pwd=secrets.token_urlsafe(40);session('Administrator');update_password('Administrator',admin_pwd)
            admin_old=identity('admin-old');admin_mapping=bind(admin_old,'Administrator')
            frappe.db.set_value('User','Administrator',{'api_key':'synthetic-api-key-'+suffix,'api_secret':'synthetic-api-secret-'+suffix,'reset_password_key':accounts.digest('synthetic-reset-'+suffix)})
            for index in range(105):
                frappe.db.sql('INSERT INTO `tabSessions` (user,sid,sessiondata,ipaddress,lastupdate,status) VALUES (%s,%s,%s,%s,NOW(),%s)',('Administrator','owned-change-'+suffix+'-'+str(index),'{}','127.0.0.1','Active'))
            frappe.db.commit()
            operation,invite,sid=begin('Administrator',admin_pwd,'custody')
            session('Administrator',sid=sid)
            error(lambda: unwrap(operations.redeem_invitation)(operation=operation,invitation=invite),'custody_recipient_requires_separate_browser')
            new_admin_identity=identity('admin-successor');nonce,_=authorize(operation,invite,new_admin_identity,kind='custody')
            successor_pwd=secrets.token_urlsafe(40)
            prepared=operations.prepare_custody_credentials(new_password=successor_pwd,confirmation=successor_pwd)
            assert prepared['mfa_qr'].startswith('data:image/png;base64,')
            frappe.db.commit();participant(nonce)
            error(lambda: operations.accept_participation(confirm=1),'custody_no_cutover_before_new_password_and_mfa_verified')
            doc=frappe.get_doc('HBOS Account Operation',operation); new_secret=operations._open(doc.mfa_sealed)
            participant(nonce);unwrap(operations.verify_custody_credentials)(password=successor_pwd,otp=pyotp.TOTP(new_secret).now());frappe.db.commit()
            operations.accept_participation(confirm=1);frappe.db.commit()
            session('Administrator',sid=sid)
            assert not operations.get_operation(operation).get('mfa_qr')
            assert 'credential_sealed' not in operations.get_operation(operation)
            confirm(operation,'Administrator',admin_pwd,sid)
            assert not frappe.db.get_value('HBOS External Identity',admin_mapping,'enabled')
            mappings.append(accounts.identity_row(settings,new_admin_identity).name)
            assert accounts.identity_row(settings,new_admin_identity).user=='Administrator'
            error(lambda: check_password('Administrator',admin_pwd),'custody_old_password_invalid')
            check_password('Administrator',successor_pwd)
            assert frappe.db.count('Sessions',{'user':'Administrator'})==0
            assert not frappe.db.get_value('User','Administrator','api_key')
            assert not frappe.db.get_value('User','Administrator','api_secret')
            assert not frappe.db.get_value('User','Administrator','reset_password_key')
            error(lambda: accounts._recovery_record('synthetic-reset-'+suffix),'custody_old_recovery_key_cannot_reset_builtin_admin')
            assert security.requires_mfa('Administrator')
            session('Administrator')
            error(lambda: security.require_custody_mfa_for_login('Administrator'),'custody_builtin_admin_native_mfa_exemption_cannot_bypass')
            session('Guest');challenge=accounts.verify_mfa('Administrator')
            cookie=frappe.local.cookie_manager.cookies[security.MFA_COOKIE]['value'];frappe.db.commit()
            session('Guest',cookies={security.MFA_COOKIE:cookie})
            assert accounts.verify_mfa('Administrator',tmp_id=challenge['tmp_id'],otp=pyotp.TOTP(new_secret).now()) is None
            security.require_custody_mfa_for_login('Administrator')
            frappe.db.commit()
            checks.append('custody_successor_only_sees_sets_and_verifies_new_credentials_mandatory_mfa')
            session('Guest',cookies={security.MFA_COOKIE:cookie})
            error(lambda: accounts.verify_mfa('Administrator',tmp_id=challenge['tmp_id'],otp=pyotp.TOTP(new_secret).now()),'custody_mfa_challenge_and_code_single_use')
            error(lambda: onboarding.resolve_verified_login(settings,admin_old),'old_admin_identity_never_auto_restores_administrator')
            checks.append('custody_revokes_old_sessions_api_reset_and_native_credentials_target_only')
        return {'status':'PASS','checks':checks,'scope':'synthetic_isolated_native_sql_only','live_owner_oauth':'NOT_TESTED','real_handover':'NOT_EXECUTED'}
    finally:
        frappe.db.rollback();frappe.set_user('Administrator');frappe.flags.hbos_owned_test_cleanup=True
        for op in operation_ids:
            frappe.db.delete('HBOS Account Change Event',{'operation':op})
            frappe.db.delete('HBOS Account Operation',{'name':op})
        owned_users=users+['Administrator']
        for user in owned_users:
            frappe.db.delete('HBOS Account Security',{'user':user})
            frappe.db.sql('DELETE FROM `__Auth` WHERE doctype=%s AND name=%s',('HBOS Account Security',user))
        for name in frappe.get_all('HBOS External Identity',filters={'app_id':settings.app_id,'external_id':['like','%'+suffix+'%']},pluck='name'):
            frappe.delete_doc('HBOS External Identity',name,force=True,ignore_permissions=True)
        for user in users:
            if frappe.db.exists('User',user):frappe.delete_doc('User',user,force=True,ignore_permissions=True)
        frappe.db.sql('DELETE FROM `__Auth` WHERE doctype=%s AND name=%s',('User','Administrator'))
        for row in admin_auth:
            frappe.db.sql('INSERT INTO `__Auth` (doctype,name,fieldname,password,encrypted) VALUES (%s,%s,%s,%s,%s)',row)
        frappe.db.sql('DELETE FROM `tabDefaultValue` WHERE parent=%s AND defkey LIKE %s',(PARENT_FOR_DEFAULTS,'Administrator\\_%'))
        for key,value in admin_defaults: set_default(key,value)
        from frappe.defaults import clear_defaults_cache
        clear_defaults_cache(PARENT_FOR_DEFAULTS)
        frappe.db.set_value('User','Administrator',dict(admin_fields),update_modified=False)
        frappe.db.commit();frappe.flags.hbos_owned_test_cleanup=False
        for key,value in original.items():setattr(frappe.local,key,value)
        for key,value in flags.items():frappe.conf[key]=value
        frappe.in_test=in_test
