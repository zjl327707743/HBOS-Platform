"""Synthetic lifecycle checks, restricted to explicitly designated test Sites.

This is never evidence of an Owner/Administrator live login. No provider network
request is made; provider assertions use an injected verified synthetic identity.
"""
from __future__ import annotations

import secrets
import time
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from hbos_portal.auth import accounts, feishu


def run() -> dict:
    if not frappe.conf.get("hbos_account_test_site"):
        raise RuntimeError("Account lifecycle checks require an explicitly designated test Site")
    suffix = secrets.token_hex(6)
    users = [f"account-v3-{suffix}-{i}@example.test" for i in range(2)]
    identity = {"open_id": "ou_synthetic_" + suffix, "tenant_key": "synthetic-tenant", "display_name": "合成身份"}
    settings = feishu.FeishuSettings(app_id="cli_synthetic", tenant_key="synthetic-tenant", redirect_uri="https://hbos.example.test/api/method/hbos_portal.auth.feishu.callback", scopes=("contact:user.base:readonly",), authorize_id_parameter="client_id", published=True, redirect_registered=True, pkce_enabled=True, app_secret="synthetic-not-a-credential", auto_provision_internal=True)
    checks = []
    original = {k: getattr(frappe.local, k, None) for k in ["request", "login_manager", "cookie_manager", "session", "response_headers"]}
    original_origin = frappe.conf.get("hbos_portal_origin")
    frappe.conf["hbos_portal_origin"] = "https://hbos.example.test"
    original_in_test = frappe.in_test
    frappe.in_test = True
    credentials = [secrets.token_urlsafe(40), secrets.token_urlsafe(40)]
    login_calls = []
    from frappe.auth import CookieManager
    from frappe.utils.password import update_password, check_password

    def session(user, sid=None, nonce=None, csrf=None):
        frappe.set_user(user)
        frappe.local.session.sid = sid or "synthetic-" + suffix + user
        frappe.local.session.data = frappe._dict(csrf_token="synthetic-csrf")
        headers = {"Origin": "https://hbos.example.test", "X-Requested-With": "XMLHttpRequest", "X-Frappe-CSRF-Token": "synthetic-csrf"}
        if nonce:
            headers["Cookie"] = accounts.PENDING_COOKIE + "=" + nonce
        if csrf:
            headers["X-HBOS-Pending-CSRF"] = csrf
        frappe.local.request = Request(EnvironBuilder(method="POST", base_url="https://hbos.example.test", json={}, headers=headers).get_environ())
        frappe.local.request_ip = "127.0.0.1"
        frappe.local.cookie_manager = CookieManager()
        frappe.local.response_headers = {}
        frappe.local.login_manager = SimpleNamespace(login_as=login_calls.append, logout=lambda *a, **kw: None)

    def expect_error(fn, label):
        try:
            fn()
        except (frappe.AuthenticationError, frappe.PermissionError, frappe.ValidationError, frappe.CSRFTokenError, feishu.FeishuLoginError):
            checks.append(label)
        else:
            raise AssertionError(label + " did not reject")

    try:
        frappe.set_user("Administrator")
        frappe.db.commit()
        for user in users:
            frappe.get_doc({"doctype": "User", "email": user, "first_name": "合成账号", "send_welcome_email": 0, "user_type": "Website User", "enabled": 1}).insert(ignore_permissions=True)
        update_password(users[0], credentials[0])
        frappe.db.commit()
        roles_before = set(frappe.get_roles(users[0]))
        with patch.object(feishu, "load_settings", return_value=settings):
            session(users[0])
            user, challenge = accounts.verify_credentials(users[0], credentials[0])
            assert user == users[0] and not challenge
            accounts.bind_identity(settings, identity, user)
            assert accounts.identity_row(settings, identity).user == user
            assert set(frappe.get_roles(user)) == roles_before
            checks.append("existing_user_binding_preserves_user_password_roles")
            check_password(user, credentials[0])
            forged = frappe.get_doc({"doctype": "HBOS External Identity", "provider": "feishu", "tenant_key": settings.tenant_key, "app_id": settings.app_id, "id_type": "open_id", "external_id": "ou_synthetic_forged_" + suffix, "user": users[1], "enabled": 1})
            forged.flags.hbos_verified_binding = True
            expect_error(lambda: forged.insert(ignore_permissions=True), "rest_document_flags_cannot_forge_binding_authority")
            expect_error(lambda: accounts.guard_document_password(frappe._dict(name=user, new_password=credentials[1])), "native_user_document_password_requires_stepup")
            expect_error(lambda: accounts.bind_identity(settings, identity, users[1]), "bound_identity_cannot_transfer")
            second = dict(identity, open_id="ou_synthetic_other_" + suffix)
            expect_error(lambda: accounts.bind_identity(settings, second, user), "one_active_identity_per_user")
            accounts.save_proof(user, "password")
            accounts.set_password(new_password=credentials[1])
            check_password(user, credentials[1])
            assert login_calls[-1] == user
            expect_error(lambda: accounts.set_password(new_password=credentials[0]), "consumed_proof_cannot_replay")
            checks.append("password_changes_on_same_user_and_revokes_old_sessions")
            session(user)
            accounts.save_proof(user, "password")
            accounts.unlink_feishu()
            assert not accounts.identity_row(settings, identity).enabled
            checks.append("unlink_retains_user_and_password_tombstone")
            check_password(user, credentials[1])
            accounts.bind_identity(settings, identity, user)
            session(users[1])
            accounts.bind_identity(settings, second, users[1])
            assert not accounts.has_password(users[1])
            accounts.save_proof(users[1], "feishu_inbox")
            expect_error(lambda: accounts.unlink_feishu(), "cannot_unlink_last_login_method")
            accounts.save_proof(users[1], "feishu_inbox")
            accounts.set_password(new_password=credentials[0])
            check_password(users[1], credentials[0])
            checks.append("passwordless_user_sets_password_without_old_password")
            session(users[0])
            accounts.create_pending(identity, intent="link", user=users[0], redirect_to="/hbos/profile", verified_at=int(time.time()))
            nonce = frappe.local.cookie_manager.cookies[accounts.PENDING_COOKIE]["value"]
            record = frappe.cache.get_value(accounts._pending_key(nonce))
            session(users[0], nonce=nonce, csrf=record["csrf"])
            accounts.pending(write=True)
            session(users[1], nonce=nonce, csrf=record["csrf"])
            expect_error(lambda: accounts.pending(write=True), "link_cannot_switch_target_session")
            session(users[0], nonce=nonce, csrf="wrong")
            expect_error(lambda: accounts.pending(write=True), "pending_requires_browser_bound_csrf")
            session(users[0])
            accounts.save_proof(users[0], "password")
            doc = frappe.get_doc("User", users[0]); doc.enabled = 0; doc.save(ignore_permissions=True)
            expect_error(lambda: accounts.require_proof(users[0]), "disable_revokes_pending_security_proofs")
            expect_error(lambda: accounts.require_user(users[0]), "disabled_account_rejected")
            assert not accounts.identity_row(settings, identity).enabled
            checks.append("disable_revokes_external_binding_and_password_reset_key")
            # First OAuth authorization creates no User until an explicit
            # choice. Exercise the actual complete_pending handler, not a
            # separate provisioning helper.
            new_identity = dict(identity, open_id="ou_synthetic_new_" + suffix)
            new_user = feishu.provisioned_user_id(settings, new_identity)
            users.append(new_user)
            count_before = frappe.db.count("User")
            session("Guest")
            accounts.create_pending(new_identity, intent="choose", redirect_to="/hbos")
            assert frappe.db.count("User") == count_before
            nonce = frappe.local.cookie_manager.cookies[accounts.PENDING_COOKIE]["value"]
            record = frappe.cache.get_value(accounts._pending_key(nonce))
            session("Guest", nonce=nonce, csrf=record["csrf"])
            result = accounts.complete_pending.__wrapped__(action="create_new")
            assert result["user"] == new_user and frappe.db.count("User") == count_before + 1
            assert frappe.db.get_value("User", new_user, "username") and not accounts.has_password(new_user)
            assert not set(frappe.get_roles(new_user)) & {"System Manager", "HR Manager", "Stock Manager", "HBOS LIMS Manager"}
            expect_error(lambda: accounts.pending(write=True), "new_account_choice_cannot_replay")
            checks.append("explicit_first_login_creates_permanent_user_with_alias_without_password")
            session("Guest")
            accounts.create_pending(second, intent="choose", redirect_to="/hbos")
            nonce = frappe.local.cookie_manager.cookies[accounts.PENDING_COOKIE]["value"]
            record = frappe.cache.get_value(accounts._pending_key(nonce))
            session("Guest", nonce=nonce, csrf=record["csrf"])
            count_before = frappe.db.count("User")
            result = accounts.complete_pending.__wrapped__(action="bind_existing", username=users[1], password=credentials[0])
            assert result["user"] == users[1] and frappe.db.count("User") == count_before
            checks.append("feishu_first_existing_account_verified_without_duplicate_user")
            indexes = frappe.db.sql("SHOW INDEX FROM `tabHBOS External Identity`", as_dict=True)
            assert {row.Column_name for row in indexes if not row.Non_unique} >= {"identity_key", "active_user_key"}
            checks.append("database_enforces_identity_and_active_user_unique_constraints")
            # Standard framework TOTP, including single-use native tmp_id.
            import pyotp
            from frappe.twofactor import get_otpsecret_for_, set_default
            session(users[1])
            set_default(users[1] + "_otplogin", 1)
            secret = get_otpsecret_for_(users[1])
            with patch("frappe.twofactor.should_run_2fa", return_value=True), patch("frappe.twofactor.get_verification_method", return_value="OTP App"):
                challenge = accounts.verify_mfa(users[1], password=credentials[0])
                assert challenge and challenge["mfa_required"]
                assert accounts.verify_mfa(users[1], otp=pyotp.TOTP(secret).now(), tmp_id=challenge["tmp_id"]) is None
                expect_error(lambda: accounts.verify_mfa(users[1], otp=pyotp.TOTP(secret).now(), tmp_id=challenge["tmp_id"]), "native_mfa_challenge_single_use")
            checks.append("standard_frappe_totp_preserved")
            from hbos_portal.auth.lifecycle import member_suspended, sync_disabled_members
            assert not member_suspended({"open_id": second["open_id"], "status": {}}, second["open_id"])
            assert not member_suspended({"open_id": "other", "status": {"is_resigned": True}}, second["open_id"])
            original_sync = frappe.conf.get("hbos_feishu_disable_sync_enabled")
            try:
                frappe.conf.hbos_feishu_disable_sync_enabled = 1
                with patch("hbos_portal.auth.feishu._tenant_token", return_value="synthetic-not-a-token"), patch("hbos_portal.auth.feishu._unwrap_feishu_payload", return_value={"user": {"open_id": second["open_id"], "status": {"is_resigned": True}}}), patch("requests.get"):
                    summary = sync_disabled_members()
                    assert summary["suspended"] == 1
                    assert not frappe.db.get_value("User", users[1], "enabled")
                    assert not accounts.identity_row(settings, second).enabled
                checks.append("feishu_explicit_offboarding_suspends_user_and_binding")
                checks.append("missing_status_or_wrong_identity_cannot_suspend_user")
            finally:
                frappe.conf.hbos_feishu_disable_sync_enabled = original_sync
        return {"status": "PASS", "checks": checks, "scope": "synthetic_test_site_only", "live_owner_login": "NOT_TESTED"}
    finally:
        frappe.set_user("Administrator")
        for name in frappe.get_all("HBOS External Identity", filters={"app_id": "cli_synthetic", "external_id": ["like", "%" + suffix]}, pluck="name"):
            frappe.delete_doc("HBOS External Identity", name, force=True, ignore_permissions=True)
        for user in users:
            if frappe.db.exists("User", user):
                frappe.delete_doc("User", user, force=True, ignore_permissions=True)
        frappe.db.commit()
        for key, value in original.items():
            setattr(frappe.local, key, value)
        frappe.conf["hbos_portal_origin"] = original_origin
        frappe.in_test = original_in_test
