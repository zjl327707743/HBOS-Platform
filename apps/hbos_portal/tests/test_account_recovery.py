from __future__ import annotations

import datetime as dt
import sys
import types
import unittest
from unittest.mock import Mock, patch

# These isolated contracts never create a Site, User, Session or provider
# identity. Live Owner/employee acceptance is recorded separately.
sys.modules.setdefault("frappe", types.SimpleNamespace(whitelist=lambda **kw: lambda fn: fn))
sys.modules.setdefault("frappe.rate_limiter", types.SimpleNamespace(rate_limit=lambda **kw: lambda fn: fn))
from hbos_portal.auth import accounts, feishu, security


class Rejected(Exception):
    pass


def reject(message, error=Rejected):
    raise Rejected(message)


class Flags(dict):
    __getattr__ = dict.get

    def __setattr__(self, name, value):
        self[name] = value


class MFAProofTest(unittest.TestCase):
    def setUp(self):
        self.user = "Administrator"
        self.row = types.SimpleNamespace(security_version=7, custody_mode=0)
        self.values = {}
        self.flags = Flags()
        self.fake = types.SimpleNamespace(
            flags=self.flags, session=types.SimpleNamespace(sid="synthetic-proof-session"),
            cache=types.SimpleNamespace(set_value=lambda key, value, **kw: self.values.__setitem__(key, value), get_value=self.values.get),
            throw=reject, AuthenticationError=Rejected,
        )
        for context in [patch.object(accounts, "frappe", self.fake), patch.object(security, "frappe", self.fake),
                patch.object(accounts, "epoch", return_value=3), patch.object(security, "record", return_value=self.row),
                patch.object(security, "administrator_native_mfa", side_effect=lambda user: user == "Administrator")]:
            context.start()
            self.addCleanup(context.stop)

    def test_existing_administrator_mfa_survives_proof_request_boundary(self):
        self.flags.hbos_custody_mfa_verified = (self.user, 7)
        accounts.save_proof(self.user, "password")
        self.flags.clear()  # The subsequent password write is a new request.
        proof = accounts.require_proof(self.user)
        self.assertEqual(7, proof["custody_version"])
        self.assertEqual((self.user, 7), self.flags.get("hbos_custody_mfa_verified"))
        security.require_custody_mfa_for_login(self.user)

    def test_existing_administrator_mfa_requires_server_verified_flag(self):
        accounts.save_proof(self.user, "password")
        with self.assertRaises(Rejected):
            accounts.require_proof(self.user)
        self.assertIsNone(self.flags.get("hbos_custody_mfa_verified"))

    def test_existing_administrator_mfa_rejects_changed_security_version(self):
        self.flags.hbos_custody_mfa_verified = (self.user, 7)
        accounts.save_proof(self.user, "password")
        self.flags.clear()
        self.row.security_version = 8
        with self.assertRaises(Rejected):
            accounts.require_proof(self.user)
        self.assertIsNone(self.flags.get("hbos_custody_mfa_verified"))

    def test_custody_mfa_still_requires_same_verified_version(self):
        self.user = "custodian@example.test"
        self.row.custody_mode = 1
        self.flags.hbos_custody_mfa_verified = (self.user, 7)
        accounts.save_proof(self.user, "password")
        self.flags.clear()
        accounts.require_proof(self.user)
        security.require_custody_mfa_for_login(self.user)
        self.row.security_version = 8
        with self.assertRaises(Rejected):
            accounts.require_proof(self.user)

    def test_ordinary_user_proof_cannot_restore_an_mfa_flag(self):
        self.user = "employee@example.test"
        accounts.save_proof(self.user, "password")
        self.assertIsNone(accounts.require_proof(self.user)["custody_version"])
        self.assertIsNone(self.flags.get("hbos_custody_mfa_verified"))


class RecoverySecurityTest(unittest.TestCase):
    key = "synthetic-recovery-ticket-for-contract"
    user = "employee@example.test"
    now = dt.datetime(2026, 1, 1, 12)

    def record(self, **changes):
        value = dict(name=self.user, enabled=1, last_reset_password_key_generated_on=self.now)
        value.update(changes)
        return types.SimpleNamespace(**value)

    def test_recovery_rejects_admin_disabled_expired_future_and_used_keys(self):
        utility = types.SimpleNamespace(now_datetime=lambda: self.now, get_datetime=lambda value: value)
        invalid = [None, self.record(name="Administrator"), self.record(name="Guest"),
            self.record(enabled=0), self.record(last_reset_password_key_generated_on=None),
            self.record(last_reset_password_key_generated_on=self.now - dt.timedelta(seconds=900)),
            self.record(last_reset_password_key_generated_on=self.now + dt.timedelta(seconds=1))]
        with patch.dict(sys.modules, {"frappe.utils": utility}):
            for record in invalid:
                fake = types.SimpleNamespace(db=types.SimpleNamespace(get_value=lambda *a, **kw: record), throw=reject, AuthenticationError=Rejected, ValidationError=Rejected)
                with self.subTest(record=record), patch.object(accounts, "frappe", fake), patch.object(accounts, "require_user", Mock()) as check:
                    with self.assertRaises(Rejected):
                        accounts._recovery_record(self.key)
                    check.assert_not_called()
            valid = self.record(last_reset_password_key_generated_on=self.now - dt.timedelta(seconds=10))
            fake = types.SimpleNamespace(db=types.SimpleNamespace(get_value=lambda *a, **kw: valid), throw=reject, AuthenticationError=Rejected, ValidationError=Rejected)
            with patch.object(accounts, "frappe", fake), patch.object(accounts, "require_user", lambda user: user):
                record, remaining = accounts._recovery_record(self.key)
                self.assertEqual(self.user, record.name)
                self.assertEqual(890, remaining)

    def test_context_is_bound_to_key_target_browser_session_and_account_epoch(self):
        context = {"user": self.user, "key_hash": accounts.digest(self.key),
            "browser_hash": accounts.digest("synthetic-browser"), "session": "session-A", "epoch": 2}
        fake = types.SimpleNamespace(cache=types.SimpleNamespace(get_value=lambda key: context),
            local=types.SimpleNamespace(request=types.SimpleNamespace(cookies={accounts.RECOVERY_COOKIE: "synthetic-browser"})),
            throw=reject, AuthenticationError=Rejected, ValidationError=Rejected)
        with patch.object(accounts, "frappe", fake), patch.object(accounts, "epoch", return_value=2), patch.object(accounts, "session_digest", return_value="session-A"):
            accounts._require_recovery_context("context-A", self.key, self.user)
            for field, value in [("user", "other@example.test"), ("key_hash", "wrong"),
                ("browser_hash", "wrong"), ("session", "session-B"), ("epoch", 3)]:
                with self.subTest(field=field), patch.dict(context, {field: value}):
                    with self.assertRaises(Rejected):
                        accounts._require_recovery_context("context-A", self.key, self.user)
            with self.assertRaises(Rejected):
                accounts._require_recovery_context("", self.key, self.user)

    def test_native_mfa_and_context_failure_cannot_write_password(self):
        fake = types.SimpleNamespace(throw=reject, AuthenticationError=Rejected, ValidationError=Rejected)
        with patch.object(accounts, "frappe", fake), patch.object(accounts, "require_post"), patch.object(accounts, "_recovery_record", return_value=(self.record(), 900)), patch.object(accounts, "_write_password") as write:
            with patch.object(accounts, "_require_recovery_context", side_effect=Rejected("wrong browser")):
                with self.assertRaises(Rejected):
                    accounts.update_password("synthetic-password", key=self.key, recovery_context="context-A")
            write.assert_not_called()
            with patch.object(accounts, "_require_recovery_context"), patch.object(accounts, "verify_mfa", return_value={"mfa_required": True, "tmp_id": "synthetic-mfa"}):
                result = accounts.update_password("synthetic-password", key=self.key, recovery_context="context-A")
                self.assertTrue(result["mfa_required"])
            write.assert_not_called()

    def test_repeatable_read_snapshot_cannot_revive_current_revoked_disabled_or_expired_key(self):
        utility = types.SimpleNamespace(now_datetime=lambda: self.now, get_datetime=lambda value: value)
        old = self.record()
        current_rows = [None, self.record(enabled=0),
            self.record(last_reset_password_key_generated_on=self.now - dt.timedelta(seconds=900)),
            self.record(name="another-employee@example.test")]
        for current in current_rows:
            reads = []
            def get_value(doctype, filters, fields, **kwargs):
                reads.append(kwargs.get("for_update", False))
                if isinstance(filters, str) and fields == "reset_password_key":
                    return accounts.digest(self.key)  # old RR snapshot
                return current if kwargs.get("for_update") else old
            fake = types.SimpleNamespace(flags=Flags(),
                db=types.SimpleNamespace(get_value=get_value, sql=Mock(return_value=[])),
                throw=reject, AuthenticationError=Rejected, ValidationError=Rejected,
                QueryDeadlockError=type('Deadlock', (Exception,), {}), QueryTimeoutError=type('LockTimeout', (Exception,), {}))
            with self.subTest(current=current), patch.dict(sys.modules, {"frappe.utils": utility}), \
                    patch.object(accounts, "frappe", fake), patch.object(accounts, "require_post"), \
                    patch.object(accounts, "require_user", return_value=self.user), \
                    patch.object(accounts, "_require_recovery_context", return_value={"epoch": 7}), \
                    patch.object(accounts, "verify_mfa", return_value=None), \
                    patch.object(accounts, "_write_password") as write:
                with self.assertRaises(Rejected):
                    accounts.update_password("synthetic-new-password", key=self.key, recovery_context="context-A")
                write.assert_not_called()
                self.assertIn(True, reads)

    def test_recovery_rechecks_context_after_user_lock_and_keeps_original_proof_epoch(self):
        utility = types.SimpleNamespace(now_datetime=lambda: self.now, get_datetime=lambda value: value)
        context = {"user": self.user, "key_hash": accounts.digest(self.key),
            "browser_hash": accounts.digest("synthetic-browser"), "session": "session-A", "epoch": 7}
        fake = types.SimpleNamespace(flags=Flags(),
            db=types.SimpleNamespace(get_value=lambda *a, **kw: self.record()),
            cache=types.SimpleNamespace(get_value=lambda key: context),
            local=types.SimpleNamespace(request=types.SimpleNamespace(cookies={accounts.RECOVERY_COOKIE: "synthetic-browser"})),
            throw=reject, AuthenticationError=Rejected, ValidationError=Rejected)
        with patch.dict(sys.modules, {"frappe.utils": utility}), patch.object(accounts, "frappe", fake), \
                patch.object(accounts, "require_post"), patch.object(accounts, "require_user", return_value=self.user), \
                patch.object(accounts, "session_digest", return_value="session-A"), \
                patch.object(accounts, "epoch", side_effect=[7, 8]), \
                patch.object(accounts, "verify_mfa", return_value=None), patch.object(accounts, "_write_password") as write:
            with self.assertRaises(Rejected):
                accounts.update_password("synthetic-new-password", key=self.key, recovery_context="context-A")
            self.assertEqual((self.user, 7), fake.flags.hbos_iam_password_proof_epoch)
            write.assert_not_called()

    def test_password_writer_rejects_recovery_epoch_revoked_at_user_lock(self):
        native_write = Mock()
        fake = types.SimpleNamespace(flags=Flags(hbos_iam_password_proof_epoch=(self.user, 7)),
            db=types.SimpleNamespace(sql=Mock(return_value=[(1,)]), commit=Mock()),
            throw=reject, AuthenticationError=Rejected)
        modules = {"frappe.utils.password": types.SimpleNamespace(update_password=native_write),
            "frappe.core.doctype.user.user": types.SimpleNamespace(test_password_strength=Mock(), handle_password_test_fail=Mock())}
        with patch.dict(sys.modules, modules), patch.object(accounts, "frappe", fake), \
                patch.object(accounts, "require_user", return_value=self.user), patch.object(accounts, "epoch", return_value=8):
            with self.assertRaises(Rejected):
                accounts._write_password(self.user, "synthetic-new-password")
        native_write.assert_not_called()
        fake.db.commit.assert_not_called()

    def test_recovery_link_uses_fragment_and_preserves_exact_key(self):
        fake = types.SimpleNamespace(conf={"hbos_portal_origin": "https://hbos.example.test"}, throw=reject, AuthenticationError=Rejected, ValidationError=Rejected)
        from urllib.parse import parse_qs, urlsplit
        with patch.object(accounts, "frappe", fake):
            url = accounts.recovery_url("/update-password?key=" + self.key)
        parsed = urlsplit(url)
        self.assertEqual("", parsed.query)
        self.assertEqual("/hbos/reset-password", parsed.path)
        self.assertEqual(self.key, parse_qs(parsed.fragment)["key"][0])

    def test_deliverable_address_alone_is_not_a_verified_mailbox(self):
        fake = types.SimpleNamespace(conf={})
        with patch.object(accounts, "frappe", fake), patch.object(accounts, "mail_ready", return_value=True), patch.object(accounts, "deliverable_email", return_value=True):
            self.assertFalse(accounts.verified_recovery_email(self.user))
            fake.conf["hbos_account_verified_recovery_emails"] = {self.user: self.user}
            self.assertTrue(accounts.verified_recovery_email(self.user))
            self.assertFalse(accounts.verified_recovery_email("Administrator"))
            fake.conf["hbos_account_verified_recovery_emails"] = {self.user: "other@example.test"}
            self.assertFalse(accounts.verified_recovery_email(self.user))

    def test_admin_recovery_issuance_requires_password_proof(self):
        fake = types.SimpleNamespace(throw=reject, AuthenticationError=Rejected, ValidationError=Rejected, get_doc=Mock())
        with patch.object(accounts, "frappe", fake), patch.object(accounts, "require_post"), patch.object(accounts, "require_user", return_value="Administrator"), patch.object(accounts, "require_proof", return_value={"method": "feishu_inbox"}):
            with self.assertRaises(Rejected):
                accounts.admin_issue_recovery(self.user, "synthetic identity verification reason")
            fake.get_doc.assert_not_called()

    def test_admin_link_requires_password_proof(self):
        fake = types.SimpleNamespace(throw=reject, AuthenticationError=Rejected, ValidationError=Rejected)
        with patch.object(feishu, "frappe", fake), patch.object(accounts, "require_post"), patch.object(accounts, "require_user", return_value="Administrator"), patch.object(accounts, "require_proof", return_value={"method": "feishu_inbox"}), patch.object(feishu, "load_settings") as settings:
            with self.assertRaises(Rejected):
                feishu.start_link()
            settings.assert_not_called()

    def test_failed_provider_delivery_never_stores_or_confirms_a_code(self):
        settings = types.SimpleNamespace(configured=True)
        cache = Mock()
        fake = types.SimpleNamespace(conf={"hbos_feishu_inbox_recovery_enabled": 1}, cache=cache)
        row = types.SimpleNamespace(name="synthetic-binding", external_id="ou_synthetic_bound_member")
        with patch.object(accounts, "frappe", fake), patch.object(accounts, "require_post"), patch.object(accounts, "require_user", return_value=self.user), patch.object(accounts, "_bound_identity", return_value=row), patch.object(accounts, "audit"), patch.object(feishu, "load_settings", return_value=settings), patch.object(feishu, "send_inbox_code", side_effect=feishu.FeishuLoginError("exchange_failed", "provider rejected synthetic delivery")) as send:
            result = accounts.request_feishu_code()
            self.assertFalse(result["sent"])
            cache.set_value.assert_not_called()
            self.assertEqual(row.external_id, send.call_args.args[1])

    def test_provider_success_without_message_ack_is_not_delivery(self):
        class Response:
            def raise_for_status(self):
                pass
            def json(self):
                return {"code": 0, "data": {}}
        transport = types.SimpleNamespace(post=lambda *a, **kw: Response())
        with patch.dict(sys.modules, {"requests": transport}), patch.object(feishu, "_tenant_token", return_value="synthetic-token"):
            with self.assertRaises(feishu.FeishuLoginError):
                feishu.send_inbox_code(types.SimpleNamespace(), "ou_synthetic_bound_member", "000000")

    def test_post_security_discards_credentials_even_when_origin_is_rejected(self):
        metadata = {"key": self.key, "new_password": "synthetic-password", "otp": "000000", "user": self.user}
        fake = types.SimpleNamespace(flags=types.SimpleNamespace(), conf={"hbos_portal_origin": "https://hbos.example.test"},
            local=types.SimpleNamespace(form_dict=metadata, request=types.SimpleNamespace(method="POST", scheme="https", host="hbos.example.test", headers={"Origin": "https://other.example.test"})),
            throw=reject, CSRFTokenError=Rejected)
        with patch.object(accounts, "frappe", fake):
            with self.assertRaises(Rejected):
                accounts.require_post()
        self.assertEqual({"user": self.user}, metadata)


class AuthenticatedRequestDispatchTest(unittest.TestCase):
    def setUp(self):
        from hbos_portal.iam import guards, policy, temporary_passwords
        self.guards, self.policy, self.temporary = guards, policy, temporary_passwords
        self.attendance = Mock()
        self.fake = types.SimpleNamespace(conf={"hbos_iam_enabled": 1},
            session=types.SimpleNamespace(user="api-user@example.test", sid="Guest", data={}),
            get_installed_apps=Mock(return_value=["frappe", "hbos_portal", "hb_attendance_app"]),
            get_attr=Mock(return_value=self.attendance),
            get_hooks=Mock(side_effect=AssertionError("no arbitrary auth hook dispatcher")))
        for target in (guards, policy):
            context = patch.object(target, "frappe", self.fake)
            context.start(); self.addCleanup(context.stop)

    def test_feature_off_does_not_inspect_apps_or_dispatch_guards(self):
        self.fake.conf["hbos_iam_enabled"] = 0
        with patch.object(self.guards, "check_identity_request") as identity:
            self.guards.check_authenticated_request()
        identity.assert_not_called()
        self.fake.get_installed_apps.assert_not_called()
        self.fake.get_attr.assert_not_called()
        self.fake.get_hooks.assert_not_called()

    def test_enabled_api_actor_runs_only_the_fixed_installed_attendance_guard(self):
        self.fake.get_installed_apps.return_value += ["unknown_external_auth_app"]
        with patch.object(self.guards, "check_identity_request") as identity:
            self.guards.check_authenticated_request()
        identity.assert_called_once_with()
        self.fake.get_attr.assert_called_once_with("hb_attendance_app.hbos_attendance.portal.permissions.check_request")
        self.attendance.assert_called_once_with()
        self.fake.get_hooks.assert_not_called()

    def test_uninstalled_attendance_is_not_imported_and_broken_installed_guard_fails_closed(self):
        with patch.object(self.guards, "check_identity_request") as identity:
            self.fake.get_installed_apps.return_value = ["frappe", "hbos_portal"]
            self.guards.check_authenticated_request()
            self.fake.get_attr.assert_not_called()
            self.fake.get_installed_apps.return_value.append("hb_attendance_app")
            self.fake.get_attr.side_effect = ImportError("installed guard missing")
            with self.assertRaises(ImportError):
                self.guards.check_authenticated_request()
        self.assertEqual(2, identity.call_count)

    def test_native_token_actor_is_checked_after_the_guest_before_request_stage(self):
        # Native API-key/OAuth authentication starts with Guest sid and sets
        # the actor before invoking auth_hooks. A cookie sid is not required.
        calls = []
        self.fake.session.user = "Guest"
        self.fake.get_attr.return_value = lambda: calls.append(("attendance", self.fake.session.user))
        with patch.object(accounts, "frappe", self.fake), \
                patch.object(accounts, "require_user", side_effect=lambda: calls.append(("user", self.fake.session.user))), \
                patch.object(security, "check_request", side_effect=lambda: calls.append(("security", self.fake.session.user))), \
                patch.object(self.temporary, "check_request", side_effect=lambda: calls.append(("temporary", self.fake.session.user))), \
                patch.object(self.guards, "check_identity_request", side_effect=lambda: calls.append(("identity", self.fake.session.user))):
            accounts.check_request()  # before_request, before native token parsing
            self.assertEqual([], calls)
            self.fake.session.user = "native-token-user@example.test"
            accounts.check_request()  # original auth_hook, after native token parsing
        self.assertEqual([(name, "native-token-user@example.test") for name in ("user", "security", "temporary", "identity", "attendance")], calls)
        self.assertEqual("Guest", self.fake.session.sid)
        self.fake.get_hooks.assert_not_called()

    def test_existing_custody_inventory_still_rejects_an_unknown_auth_hook(self):
        from hbos_portal.auth import operations
        fake = types.SimpleNamespace(conf={"hbos_administrator_custody_handover_enabled": 1},
            get_hooks=Mock(return_value=["hbos_portal.auth.accounts.check_request", "external_auth_app.authenticate"]),
            get_doc=Mock(), throw=reject, PermissionError=Rejected)
        operation = types.SimpleNamespace(target_user="Administrator", initiator="Administrator", credential_verified=True)
        with patch.object(operations, "frappe", fake), self.assertRaises(Rejected):
            operations._custody_cutover(operation)
        fake.get_doc.assert_not_called()

    def test_only_the_original_auth_hook_remains_registered(self):
        import runpy
        from pathlib import Path
        from hbos_portal import hooks
        self.assertEqual(["hbos_portal.auth.accounts.check_request"], hooks.auth_hooks)
        attendance_hooks = runpy.run_path(str(Path(__file__).resolve().parents[2] / "hb_attendance_app" / "hb_attendance_app" / "hooks.py"))
        self.assertNotIn("auth_hooks", attendance_hooks)
        self.assertIn("hbos_portal.iam.guards.check_identity_request", hooks.before_request)
        self.assertEqual(["hb_attendance_app.hbos_attendance.portal.permissions.check_request"], attendance_hooks["before_request"])


if __name__ == "__main__":
    unittest.main()
