from contextlib import nullcontext
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
from hbos_portal.auth import onboarding, feishu, accounts
from hbos_portal.auth.feishu import FeishuLoginError, _pilot_users, require_pilot_user
from .test_feishu_auth_contract import settings

IDENTITY = {'open_id':'ou_synthetic_pilot123','tenant_key':'tenant-approved'}
PILOT = 'pilot@example.invalid'

class ControlledPilotTest(unittest.TestCase):
    def test_configured_login_is_separate_from_auto_provision(self):
        s = settings(auto_provision_internal=False, pilot_mode=True, pilot_users=(PILOT,))
        self.assertTrue(s.configured)
        self.assertFalse(s.public_status()['auto_provision_internal'])
        self.assertNotIn('internal_member_auto_provision',s.public_status()['missing'])
        self.assertNotIn(PILOT,str(s.public_status()))
        self.assertFalse(settings(pilot_mode=True,pilot_users=()).configured)

    def test_pilot_allowlist_is_small_and_fails_closed(self):
        for v in [None,'garbage','["Administrator"]',['Guest'],[''],[' '+PILOT],['a','b','c'],{'a':PILOT},[1]]:
            with self.subTest(v=v): self.assertEqual((),_pilot_users(v))
        self.assertEqual((PILOT,),_pilot_users('["pilot@example.invalid"]'))

    def test_account_policy_never_expands_privileges(self):
        s=settings(pilot_mode=True,pilot_users=(PILOT,))
        require_pilot_user(s,PILOT)
        for user in ['Administrator','Guest','other@example.invalid']:
            with self.assertRaises(FeishuLoginError):require_pilot_user(s,user)

    def resolve(self,s,row):
        fake=SimpleNamespace(db=SimpleNamespace(get_value=Mock(return_value=1),rollback=Mock()),flags=SimpleNamespace())
        with patch.object(onboarding,'frappe',fake),patch.object(onboarding,'serialize',return_value=nullcontext()),patch('hbos_portal.auth.accounts.identity_row',return_value=row),patch.object(feishu,'_validate_login_account',side_effect=lambda user:user),patch.object(onboarding,'insert_ordinary_user') as create:
            return onboarding.resolve_verified_login(s,IDENTITY),create,fake

    def test_existing_binding_logs_in_when_auto_provision_off(self):
        result,create,fake=self.resolve(settings(auto_provision_internal=False,pilot_mode=True,pilot_users=(PILOT,)),SimpleNamespace(user=PILOT,enabled=True))
        self.assertEqual((PILOT,False),result);create.assert_not_called()
        self.assertEqual(PILOT,fake.flags.hbos_iam_verified_oauth_login)

    def test_unknown_identity_cannot_create_with_auto_off_or_in_pilot(self):
        for s in [settings(auto_provision_internal=False),settings(pilot_mode=True,pilot_users=(PILOT,)),settings(auto_provision_internal=False,pilot_mode=True,pilot_users=(PILOT,))]:
            with self.subTest(s=s),self.assertRaises(FeishuLoginError) as e:self.resolve(s,None)
            self.assertEqual('identity_unmapped',e.exception.code)

    def test_bound_non_pilot_account_denied(self):
        with self.assertRaises(FeishuLoginError) as e:self.resolve(settings(auto_provision_internal=False,pilot_mode=True,pilot_users=(PILOT,)),SimpleNamespace(user='other@example.invalid',enabled=True))
        self.assertEqual('member_scope_denied',e.exception.code)

    def test_cross_tenant_never_enters_binding_or_creation(self):
        with self.assertRaises(FeishuLoginError) as e:self.resolve(settings(tenant_key='different-tenant'),None)
        self.assertEqual('tenant_rejected',e.exception.code)

    def test_binding_write_rejects_non_pilot_before_any_account_or_db_write(self):
        with patch.object(accounts, 'require_user') as account_check:
            with self.assertRaises(FeishuLoginError):
                accounts.bind_identity(settings(pilot_mode=True,pilot_users=(PILOT,)), IDENTITY, 'other@example.invalid')
            account_check.assert_not_called()

    def test_start_link_rechecks_current_policy_before_issuing_oauth_state(self):
        with patch.object(accounts, 'require_post'), patch.object(accounts, 'require_user', return_value='other@example.invalid'), \
             patch.object(accounts, 'require_proof', return_value={'method':'password','verified_at':1}), \
             patch.object(feishu, 'load_settings', return_value=settings(pilot_mode=True,pilot_users=(PILOT,))), \
             patch.object(feishu.RedisOAuthStateStore, 'create') as issue:
            with patch.object(feishu.frappe, 'PermissionError', PermissionError, create=True), patch.object(feishu.frappe, 'throw', side_effect=PermissionError, create=True):
                with self.assertRaises(PermissionError): feishu.start_link()
            issue.assert_not_called()

    def test_callback_rechecks_live_policy_for_previously_issued_link(self):
        local=SimpleNamespace(form_dict={}, request=SimpleNamespace(cookies={}), cookie_manager=Mock())
        fake=SimpleNamespace(local=local,flags=SimpleNamespace(),cache=Mock(),db=Mock())
        state=SimpleNamespace(intent='link', user='other@example.invalid', code_verifier='synthetic')
        with patch.object(feishu,'frappe',fake),patch.object(feishu,'load_settings',return_value=settings(pilot_mode=True,pilot_users=(PILOT,))), \
             patch.object(feishu.RedisOAuthStateStore,'consume',return_value=state),patch.object(feishu,'exchange_identity',return_value=IDENTITY), \
             patch('hbos_portal.auth.diagnostics.persist'),patch('hbos_portal.auth.diagnostics.new_trace',return_value={'id':'synthetic','facts':{},'result':'pending'}),patch.object(feishu,'_error_redirect') as error,patch.object(accounts,'create_pending') as pending:
            feishu.callback(code='synthetic',state='synthetic')
            self.assertEqual('member_scope_denied',error.call_args.args[0]); pending.assert_not_called();fake.db.rollback.assert_called_once()

    def test_pending_confirm_link_rechecks_policy_without_consuming_or_login(self):
        record={'intent':'link','user':'other@example.invalid','identity':IDENTITY}
        fake=SimpleNamespace(db=Mock(),UniqueValidationError=type('Unique', (Exception,), {}),DuplicateEntryError=type('Duplicate', (Exception,), {}))
        with patch.object(accounts,'frappe',fake),patch.object(accounts,'pending',return_value=('synthetic',record)), \
             patch.object(feishu,'load_settings',return_value=settings(pilot_mode=True,pilot_users=(PILOT,))), \
             patch.object(accounts,'require_user',return_value=record['user']),patch.object(accounts,'consume_pending') as consume:
            result=accounts.complete_pending('confirm_link')
            self.assertFalse(result['completed']);self.assertEqual('member_scope_denied',result['error']['code']);consume.assert_not_called();fake.db.rollback.assert_called_once()

    def test_pending_mfa_live_removal_is_structured_before_challenge_or_login(self):
        record={'intent':'login_mfa','user':'other@example.invalid','identity':IDENTITY}
        fake=SimpleNamespace(db=Mock(),UniqueValidationError=type('Unique', (Exception,), {}),DuplicateEntryError=type('Duplicate', (Exception,), {}))
        with patch.object(accounts,'frappe',fake),patch.object(accounts,'pending',return_value=('synthetic',record)), \
             patch.object(feishu,'load_settings',return_value=settings(pilot_mode=True,pilot_users=(PILOT,))), \
             patch.object(accounts,'require_user',return_value=record['user']),patch.object(accounts,'verify_mfa') as mfa,patch.object(accounts,'consume_pending') as consume:
            result=accounts.complete_pending('login_mfa')
            self.assertEqual('member_scope_denied',result['error']['code']);mfa.assert_not_called();consume.assert_not_called()

    def test_legacy_pending_create_cannot_bypass_disabled_enrollment(self):
        record={'intent':'choose','identity':IDENTITY}
        fake=SimpleNamespace(db=Mock(),UniqueValidationError=type('Unique', (Exception,), {}),DuplicateEntryError=type('Duplicate', (Exception,), {}))
        with patch.object(accounts,'frappe',fake),patch.object(accounts,'pending',return_value=('synthetic',record)), \
             patch.object(feishu,'load_settings',return_value=settings(auto_provision_internal=False,pilot_mode=True,pilot_users=(PILOT,))), \
             patch.object(onboarding,'resolve_verified_login',side_effect=FeishuLoginError('identity_unmapped','synthetic denial')),patch.object(accounts,'consume_pending') as consume:
            result=accounts.complete_pending('create_new')
            self.assertEqual('identity_unmapped',result['error']['code']);consume.assert_not_called();fake.db.rollback.assert_called_once()

    def test_owner_administrator_exception_requires_flag_and_explicit_pilot_entry(self):
        self.assertEqual((), _pilot_users(['Administrator']))
        self.assertEqual(('Administrator',), _pilot_users(['Administrator'], allow_administrator=True))
        for value in [['Guest'], ['administrator'], ['Administrator', 'a', 'b']]:
            self.assertEqual((), _pilot_users(value, allow_administrator=True))
        self.assertFalse(settings(pilot_mode=True, pilot_users=('Administrator',)).configured)
        permitted = settings(auto_provision_internal=False, pilot_mode=True, pilot_users=('Administrator',), allow_administrator_link=True)
        self.assertTrue(permitted.configured)
        require_pilot_user(permitted, 'Administrator')
        for policy in [settings(pilot_mode=True, pilot_users=(PILOT,), allow_administrator_link=True), settings(pilot_users=('Administrator',))]:
            with self.assertRaises(FeishuLoginError): require_pilot_user(policy, 'Administrator')
        with self.assertRaises(FeishuLoginError): require_pilot_user(permitted, PILOT)

    def test_approved_existing_administrator_binding_reuses_user_without_provisioning(self):
        result,create,fake=self.resolve(settings(auto_provision_internal=False,pilot_mode=True,pilot_users=('Administrator',),allow_administrator_link=True),SimpleNamespace(user='Administrator',enabled=True))
        self.assertEqual(('Administrator',False),result);create.assert_not_called()

    def test_administrator_exception_still_requires_password_proof_before_oauth(self):
        policy=settings(pilot_mode=True,pilot_users=('Administrator',),allow_administrator_link=True)
        with patch.object(accounts,'require_post'),patch.object(accounts,'require_user',return_value='Administrator'), \
             patch.object(accounts,'require_proof',return_value={'method':'feishu_inbox','verified_at':1}), \
             patch.object(feishu,'load_settings',return_value=policy),patch.object(feishu.RedisOAuthStateStore,'create') as issue, \
             patch.object(feishu.frappe,'AuthenticationError',PermissionError,create=True),patch.object(feishu.frappe,'throw',side_effect=PermissionError,create=True):
            with self.assertRaises(PermissionError):feishu.start_link()
            issue.assert_not_called()
