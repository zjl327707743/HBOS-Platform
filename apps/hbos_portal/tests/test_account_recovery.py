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


if __name__ == "__main__":
    unittest.main()
