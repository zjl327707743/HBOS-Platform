from __future__ import annotations

import datetime as dt
import sys
import types
import unittest
from unittest.mock import Mock, patch

from .test_feishu_auth_contract import _fake_whitelist  # initialize pure contract stubs
from .test_account_recovery import Flags as _ExistingProofFlags
from hbos_portal.iam import temporary_passwords as temporary


class Rejected(Exception):
    pass


class Flags(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


def reject(message, *args):
    raise Rejected(message)


class TemporaryPasswordContractTest(unittest.TestCase):
    def fake(self, path='/api/method/hbos_portal.auth.accounts.get_security', cmd=''):
        return types.SimpleNamespace(flags=Flags(), session=types.SimpleNamespace(user='user@example.test', data={}),
            local=types.SimpleNamespace(form_dict={'cmd': cmd} if cmd else {}, request=types.SimpleNamespace(path=path), response={}),
            db=types.SimpleNamespace(set_value=Mock(), sql=Mock(), commit=Mock(), get_value=Mock()), throw=reject,
            PermissionError=Rejected, AuthenticationError=Rejected,
            QueryDeadlockError=type('Deadlock', (Exception,), {}), QueryTimeoutError=type('LockTimeout', (Exception,), {}),
            utils=types.SimpleNamespace(now_datetime=lambda: dt.datetime(2026, 10, 15), get_datetime=lambda value: value, add_to_date=lambda value, **kw: value + dt.timedelta(hours=kw.get('hours', 0))))

    def test_exact_gate_cannot_be_spoofed_by_cmd_on_rest_or_other_auth_routes(self):
        fake = self.fake()
        with patch.object(temporary, 'frappe', fake), patch.object(temporary, 'available', return_value=True), patch.object(temporary, 'status', return_value={'pending': True}):
            temporary.check_request()
            for path, cmd in [('/api/method/login', ''), ('/api/method', 'login')]:
                fake.local.request.path = path; fake.local.form_dict = {'cmd': cmd} if cmd else {}
                temporary.check_request()
            for path, cmd in [('/api/resource/Employee', 'hbos_portal.auth.accounts.get_security'),
                    ('/api/method/hbos_portal.auth.operations.begin', ''),
                    ('/api/method/hbos_portal.api.bootstrap.get_bootstrap', ''),
                    ('/api/method/hbos_portal.auth.accounts.get_security', 'other'),
                    ('/api/method/login.extra', ''),
                    ('/api/resource/Attendance', 'login'),
                    ('/api/v2/document/Attendance', '')]:
                fake.local.request.path = path; fake.local.form_dict = {'cmd': cmd} if cmd else {}
                with self.subTest(path=path), self.assertRaises(Rejected):
                    temporary.check_request()

    def test_document_flags_cannot_forge_lifecycle_authority(self):
        fake = self.fake()
        values = dict(zip(temporary.FIELDS, (1, 1, None, 1)))
        doc = types.SimpleNamespace(name='user@example.test', flags=Flags(hbos_iam_temporary_authority='user@example.test'), get=values.get, get_doc_before_save=lambda: dict.fromkeys(temporary.FIELDS, 0))
        with patch.object(temporary, 'frappe', fake), patch.object(temporary, 'available', return_value=True):
            with self.assertRaises(Rejected): temporary.guard_user_fields(doc)
            with temporary.authority(doc.name): temporary.guard_user_fields(doc)
            self.assertIsNone(fake.flags.get('hbos_iam_temporary_authority'))

    def test_issue_uses_native_hash_and_stores_only_status_not_plaintext(self):
        fake = self.fake()
        native = Mock()
        module = types.SimpleNamespace(update_password=native)
        core = types.SimpleNamespace(test_password_strength=lambda *a, **kw: {}, handle_password_test_fail=Mock())
        with patch.object(temporary, 'frappe', fake), patch.object(temporary, 'available', return_value=True), patch.object(temporary, 'status', return_value={'generation': 3}), patch.dict(sys.modules, {'frappe.utils.password': module, 'frappe.core.doctype.user.user': core}), patch('hbos_portal.auth.accounts.invalidate_user_tickets'), patch('hbos_portal.auth.accounts.revoke_sessions'):
            first = temporary.issue('user@example.test'); second = temporary.issue('user@example.test')
            self.assertNotEqual(first['temporary_password'], second['temporary_password'])
            native.assert_any_call('user@example.test', first['temporary_password'])
            self.assertNotIn(first['temporary_password'], repr(fake.db.set_value.call_args_list))
            fake.db.commit.assert_not_called()  # caller owns hash + status transaction

    def test_claim_is_server_session_bound_once_and_never_returns_old_secret(self):
        fake = self.fake(); fake.local.login_manager = types.SimpleNamespace(login_as=Mock())
        fake.session.data['hbos_iam_initial_delivery'] = 1
        initial = {'can_claim': True, 'generation': 0, 'expires_at': None}
        consumed = {'can_claim': False, 'generation': 1, 'expires_at': 'future'}
        with patch.object(temporary, 'frappe', fake), patch('hbos_portal.auth.accounts.require_post'), patch('hbos_portal.auth.accounts.require_user', return_value=fake.session.user), patch('hbos_portal.auth.accounts.no_store'), patch.object(temporary, 'status', side_effect=[initial, consumed]), patch.object(temporary, 'issue', return_value={'temporary_password': 'test-only', 'generation': 1, 'expires_at': 'future'}) as issue:
            self.assertTrue(temporary.claim_initial_password()['claimed'])
            replay = temporary.claim_initial_password()
            self.assertFalse(replay['claimed']); self.assertNotIn('temporary_password', replay)
            issue.assert_called_once(); fake.db.commit.assert_called_once()
        fake.session.data.clear()
        with patch.object(temporary, 'frappe', fake), patch('hbos_portal.auth.accounts.require_post'), patch('hbos_portal.auth.accounts.require_user', return_value=fake.session.user), patch('hbos_portal.auth.accounts.no_store'), patch.object(temporary, 'status', return_value=initial):
            with self.assertRaises(Rejected): temporary.claim_initial_password()

    def test_expired_or_missing_expiry_cannot_authenticate_by_password(self):
        fake = self.fake()
        with patch.object(temporary, 'frappe', fake), patch.object(temporary, 'available', return_value=True):
            for expiry in [None, dt.datetime(2026, 10, 14)]:
                with patch.object(temporary, 'status', return_value={'temporary': True, 'expires_at': expiry}):
                    with self.assertRaises(Rejected): temporary.check_credentials(fake.session.user)

    def test_password_settlement_clears_both_flags_and_advances_generation_without_commit(self):
        fake = self.fake()
        with patch.object(temporary, 'frappe', fake), patch.object(temporary, 'available', return_value=True), patch.object(temporary, 'status', return_value={'generation': 2}):
            temporary.on_password_changed(fake.session.user)
            fields = fake.db.set_value.call_args.args[2]
            self.assertEqual([0, 0, None, 3], [fields[key] for key in temporary.FIELDS])
            fake.db.commit.assert_not_called()

    def test_state_settlement_failure_precedes_password_commit_or_session_rotation(self):
        from hbos_portal.auth import accounts
        fake = self.fake()
        fake.db.sql.return_value = [(1,)]
        fake.db.get_value = Mock(return_value=('given', '', '', 'user@example.test', None))
        fake.utils.today = lambda: '2026-10-15'
        core = types.SimpleNamespace(test_password_strength=lambda *a, **kw: {}, handle_password_test_fail=Mock())
        native = types.SimpleNamespace(update_password=Mock())
        with patch.object(accounts, 'frappe', fake), patch.object(accounts, 'require_user'), patch.dict(sys.modules, {'frappe.core.doctype.user.user': core, 'frappe.utils.password': native}), patch.object(temporary, 'on_password_changed', side_effect=Rejected('transaction failure')), patch.object(accounts, 'revoke_sessions') as rotate:
            with self.assertRaises(Rejected): accounts._write_password(fake.session.user, 'test-only-strong-password')
            native.update_password.assert_called_once()
            fake.db.commit.assert_not_called(); rotate.assert_not_called()

    def test_forged_document_flag_cannot_settle_initial_state(self):
        from hbos_portal.auth import accounts
        fake = self.fake()
        doc = types.SimpleNamespace(name=fake.session.user, enabled=1, flags={'hbos_password_written': True})
        with patch.object(accounts, 'frappe', fake), patch.object(temporary, 'on_password_changed') as settle:
            accounts.user_updated(doc)
            settle.assert_not_called()

