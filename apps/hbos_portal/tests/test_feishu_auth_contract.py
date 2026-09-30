from __future__ import annotations

import fnmatch
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit


def _fake_whitelist(**kwargs):
    return lambda function: function


sys.modules.setdefault(
    "frappe",
    types.SimpleNamespace(whitelist=_fake_whitelist),
)

from hbos_portal.auth.feishu import (
    FeishuLoginError,
    FeishuSettings,
    _load_protected_text,
    _resolve_or_provision_user,
    _store_protected_text,
    _validate_redirect_uri,
    build_authorize_url,
    exchange_identity,
    identity_key,
    provisioned_user_id,
)
from hbos_portal.auth.state import OAuthStateError, RedisOAuthStateStore, validate_redirect_target


class FakeRedis:
    def __init__(self):
        self.values = {}

    def make_key(self, key):
        return f"test-site|{key}".encode()

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def eval(self, script, count, key, digest):
        value = self.values.get(key)
        if not value or not str(value).startswith(digest):
            return None
        del self.values[key]
        return value


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def settings(**overrides):
    values = {
        "app_id": "cli_test",
        "app_secret": "server-only-secret",
        "tenant_key": "tenant-approved",
        "redirect_uri": "https://hbos.example.test/api/method/hbos_portal.auth.feishu.callback",
        "scopes": ("contact:user.base:readonly",),
        "authorize_id_parameter": "client_id",
        "published": True,
        "redirect_registered": True,
        "pkce_enabled": True,
        "auto_provision_internal": True,
        "account_domain": "feishu.hbos.internal",
    }
    values.update(overrides)
    return FeishuSettings(**values)


class OAuthStateContractTest(unittest.TestCase):
    def test_operation_intent_survives_single_use_and_never_defaults_to_login(self):
        store = RedisOAuthStateStore(FakeRedis())
        for intent in ('rebind', 'handover'):
            state, browser = store.create(redirect_to='/hbos/account-change', intent=intent,
                operation_id='synthetic-operation', participant_digest='synthetic-participant-digest')
            record = store.consume(state=state, browser_nonce=browser)
            self.assertEqual(intent, record.intent)
            self.assertEqual('synthetic-operation', record.operation_id)
            self.assertEqual('synthetic-participant-digest', record.participant_digest)
        for intent in ('admin-claim', 'rebind', 'handover'):
            with self.assertRaises(OAuthStateError):
                store.create(redirect_to='/hbos', intent=intent)

    def test_state_is_browser_bound_and_single_use(self):
        store = RedisOAuthStateStore(FakeRedis())
        state, browser_nonce = store.create(
            redirect_to="/hbos/twin",
            code_verifier="pkce-verifier",
        )
        with self.assertRaises(OAuthStateError):
            store.consume(state=state, browser_nonce="other-browser")

        record = store.consume(state=state, browser_nonce=browser_nonce)
        self.assertEqual("/hbos/twin", record.redirect_to)
        self.assertEqual("pkce-verifier", record.code_verifier)
        with self.assertRaises(OAuthStateError):
            store.consume(state=state, browser_nonce=browser_nonce)

    def test_redirect_rejects_external_backslash_traversal_and_double_encoding(self):
        self.assertEqual("/hbos/knowledge?from=twin", validate_redirect_target("/hbos/knowledge?from=twin"))
        for target in (
            "https://evil.example/hbos",
            "//evil.example/hbos",
            "/hbos\\evil",
            "/hbos/%252e%252e/admin",
            "/hbos-impersonator",
            "/app",
        ):
            with self.subTest(target=target):
                with self.assertRaises(OAuthStateError):
                    validate_redirect_target(target)


class FeishuFlowContractTest(unittest.TestCase):
    def test_site_private_secret_requires_regular_owner_only_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "secret"
            _store_protected_text(path, "rotated-server-secret")
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            self.assertEqual("rotated-server-secret", _load_protected_text(path))

            path.chmod(0o640)
            self.assertEqual("", _load_protected_text(path))

            path.unlink()
            target = Path(temporary_directory) / "target"
            target.write_text("must-not-follow\n", encoding="utf-8")
            target.chmod(0o600)
            os.symlink(target, path)
            self.assertEqual("", _load_protected_text(path))

    def test_redirect_uri_accepts_dedicated_localhost_origin_only(self):
        callback = "http://p1-knowledge-twin.localhost:5188/api/method/hbos_portal.auth.feishu.callback"
        self.assertEqual(callback, _validate_redirect_uri(callback))
        self.assertEqual("", _validate_redirect_uri("http://p1-knowledge-twin.example.test/callback"))
        self.assertEqual("", _validate_redirect_uri("http://localhost.evil.example/callback"))

    def test_authorize_url_has_state_scope_and_explicit_pkce(self):
        url = build_authorize_url(settings(), state="state-value", code_challenge="challenge")
        parsed = parse_qs(urlsplit(url).query)
        self.assertEqual(["cli_test"], parsed["client_id"])
        self.assertEqual(["state-value"], parsed["state"])
        self.assertEqual(["S256"], parsed["code_challenge_method"])
        self.assertNotIn("server-only-secret", url)

    def test_unpublished_or_missing_tenant_is_not_configured(self):
        self.assertFalse(settings(published=False).configured)
        self.assertFalse(settings(redirect_registered=False).configured)
        self.assertFalse(settings(tenant_key="").configured)
        self.assertFalse(settings(auto_provision_internal=False).configured)

    def test_exchange_enforces_tenant_and_does_not_return_token(self):
        calls = []

        def post(url, **kwargs):
            calls.append(("post", url, kwargs))
            if url.endswith("tenant_access_token/internal"):
                return FakeResponse({"code": 0, "tenant_access_token": "application-token"})
            return FakeResponse({"code": 0, "access_token": "short-lived-user-token"})

        def get(url, **kwargs):
            calls.append(("get", url, kwargs))
            if "/tenant/v2/tenant/query" in url:
                return FakeResponse({"code": 0, "data": {"tenant": {"tenant_key": "tenant-approved"}}})
            if "/contact/v3/users/" in url:
                return FakeResponse({"code": 0, "data": {"user": {"open_id": "ou_test_member_123", "department_ids": ["department-synthetic"], "status": {"is_activated": True, "is_frozen": False, "is_resigned": False, "is_unjoin": False, "is_exited": False}}}})
            return FakeResponse(
                {"code": 0, "data": {"open_id": "ou_test_member_123", "tenant_key": "tenant-approved", "email": "ignored@example.test", "name": "内部成员"}}
            )

        identity = exchange_identity(
            settings(),
            code="one-time-code",
            code_verifier="pkce-verifier",
            post=post,
            get=get,
        )
        self.assertEqual(
            {
                "open_id": "ou_test_member_123",
                "tenant_key": "tenant-approved",
                "display_name": "内部成员",
            },
            identity,
        )
        self.assertNotIn("token", str(identity).lower())
        self.assertEqual("pkce-verifier", calls[0][2]["json"]["code_verifier"])

    def test_wrong_tenant_is_rejected(self):
        def post(url, **kwargs):
            return FakeResponse({"code": 0, "access_token": "token"})

        def get(url, **kwargs):
            return FakeResponse({"code": 0, "data": {"open_id": "ou_test_member_123", "tenant_key": "other"}})

        with self.assertRaisesRegex(FeishuLoginError, "租户"):
            exchange_identity(
                settings(),
                code="code",
                code_verifier="verifier",
                post=post,
                get=get,
            )

    def test_identity_key_keeps_id_type_app_and_tenant_boundaries(self):
        base = identity_key(
            provider="feishu",
            tenant_key="tenant-a",
            app_id="app-a",
            id_type="open_id",
            external_id="same-value",
        )
        variants = {
            identity_key(
                provider="feishu",
                tenant_key="tenant-b",
                app_id="app-a",
                id_type="open_id",
                external_id="same-value",
            ),
            identity_key(
                provider="feishu",
                tenant_key="tenant-a",
                app_id="app-b",
                id_type="open_id",
                external_id="same-value",
            ),
            identity_key(
                provider="feishu",
                tenant_key="tenant-a",
                app_id="app-a",
                id_type="user_id",
                external_id="same-value",
            ),
        }
        self.assertNotIn(base, variants)
        self.assertFalse(any(fnmatch.fnmatch(base, item) for item in variants))

    def test_auto_provision_id_never_uses_profile_email_or_name(self):
        first = provisioned_user_id(
            settings(),
            {
                "open_id": "ou_test_member_123",
                "tenant_key": "tenant-approved",
                "display_name": "同名员工",
                "email": "existing@example.test",
            },
        )
        second = provisioned_user_id(
            settings(),
            {
                "open_id": "ou_test_member_123",
                "tenant_key": "tenant-approved",
                "display_name": "另一个姓名",
                "email": "other@example.test",
            },
        )
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("feishu."))
        self.assertTrue(first.endswith("@feishu.hbos.internal"))
        self.assertNotIn("existing", first)

    def test_exact_identity_mapping_is_reused_before_provisioning(self):
        with patch("hbos_portal.auth.onboarding.resolve_verified_login", return_value=("member@example.test", False)) as shared:
            user = _resolve_or_provision_user(
                settings(),
                {
                    "open_id": "ou_test_member_123",
                    "tenant_key": "tenant-approved",
                    "display_name": "内部成员",
                },
            )
        self.assertEqual("member@example.test", user)
        shared.assert_called_once()

    def test_unmapped_verified_member_uses_the_same_automatic_service(self):
        identity = {
            "open_id": "ou_test_member_123",
            "tenant_key": "tenant-approved",
            "display_name": "内部成员",
            "email": "must-not-be-used@example.test",
        }
        with patch("hbos_portal.auth.onboarding.resolve_verified_login", return_value=("permanent@example.test", True)) as shared:
            self.assertEqual("permanent@example.test", _resolve_or_provision_user(settings(), identity))
        shared.assert_called_once_with(unittest.mock.ANY, identity)

    def test_internal_membership_denies_unverifiable_frozen_and_departed_users(self):
        from hbos_portal.auth.feishu import verify_internal_member
        for bad_status in ({}, {"is_activated": True}, {"is_activated": True, "is_frozen": True, "is_resigned": False}, {"is_activated": True, "is_frozen": False, "is_resigned": True}, {"is_activated": True, "is_frozen": False, "is_resigned": False, "is_exited": True}):
            with self.subTest(status=bad_status), self.assertRaises(FeishuLoginError):
                verify_internal_member(settings(), "ou_test_member_123", post=lambda *a, **kw: FakeResponse({"code": 0, "tenant_access_token": "synthetic-token"}), get=lambda url, **kw: FakeResponse({"code": 0, "data": {"tenant": {"tenant_key": "tenant-approved"}}}) if '/tenant/v2/' in url else FakeResponse({"code": 0, "data": {"user": {"open_id": "ou_test_member_123", "status": bad_status}}}))

    def test_active_internal_contact_does_not_need_department_field_permission(self):
        from hbos_portal.auth.feishu import verify_internal_member
        trace = {'calls': [], 'facts': {}}
        verify_internal_member(settings(), "ou_test_member_123", trace=trace,
            post=lambda *a, **kw: FakeResponse({'code': 0, 'tenant_access_token': 'synthetic-token'}),
            get=lambda url, **kw: FakeResponse({'code': 0, 'data': {'tenant': {'tenant_key': 'tenant-approved'}}}) if '/tenant/v2/' in url else FakeResponse({'code': 0, 'data': {'user': {'open_id': 'ou_test_member_123', 'status': {'is_activated': True, 'is_frozen': False, 'is_resigned': False}}}}))
        self.assertFalse(trace['facts']['department_present'])
        self.assertEqual('unknown', trace['facts']['status_fields']['is_exited']['judgement'])


if __name__ == "__main__":
    unittest.main()
