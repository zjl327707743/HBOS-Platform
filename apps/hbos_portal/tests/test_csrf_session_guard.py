from __future__ import annotations

import json
import sys
import types
import unittest
from unittest.mock import Mock, patch

sys.modules.setdefault("frappe", types.SimpleNamespace())
from hbos_portal.auth import csrf


class AttrDict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class CSRFRejected(Exception):
    pass


class Column:
    def __init__(self, name):
        self.name = name

    def __eq__(self, value):
        return (self.name, "=", value)

    def __gt__(self, value):
        return (self.name, ">", value)


class SessionTokenGuardTest(unittest.TestCase):
    def setUp(self):
        self.request = types.SimpleNamespace(method="POST", path="/api/method/frappe.client.set_value", cookies={"sid": "session"}, headers={})
        self.session = AttrDict(user="test@example.test", data=AttrDict())
        self.fake = types.SimpleNamespace(
            local=types.SimpleNamespace(request=self.request, session=self.session),
            flags=AttrDict(), form_dict=AttrDict(), CSRFTokenError=CSRFRejected,
            throw=lambda message, error: (_ for _ in ()).throw(error(message)),
        )
        self.patch = patch.object(csrf, "frappe", self.fake)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_authenticated_unsafe_requests_without_saved_token_are_rejected(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                self.request.method = method
                with self.assertRaises(CSRFRejected):
                    csrf.require_initialized_session_token()

    def test_initialized_session_proceeds_to_frappe_validation(self):
        self.session.data.csrf_token = "test-token"
        csrf.require_initialized_session_token()

    def test_safe_and_guest_requests_are_not_interrupted(self):
        self.request.method = "GET"
        csrf.require_initialized_session_token()
        self.request.method = "POST"
        self.session.user = "Guest"
        csrf.require_initialized_session_token()

    def test_native_login_without_authenticated_cookie_is_not_interrupted(self):
        self.request.path = "/api/method/login"
        self.request.cookies = {}
        csrf.require_native_login_csrf()
        csrf.require_initialized_session_token()
        self.request.cookies = {"sid": "Guest"}
        csrf.require_native_login_csrf()
        csrf.require_initialized_session_token()

    def test_existing_cookie_cannot_use_native_login_exception(self):
        self.request.path = "/api/method/login"
        with self.assertRaises(CSRFRejected):
            csrf.require_native_login_csrf()

    def test_native_relogin_accepts_only_previous_session_token(self):
        self.request.path = "/api/method/login"
        self.request.headers["X-Frappe-CSRF-Token"] = "valid-token"
        with patch.object(csrf, "_previous_session_token", return_value="valid-token"):
            csrf.require_native_login_csrf()
            csrf.require_initialized_session_token()
        with patch.object(csrf, "_previous_session_token", return_value="different-token"):
            with self.assertRaises(CSRFRejected):
                csrf.require_native_login_csrf()
        with patch.object(csrf, "_previous_session_token", return_value=None):
            with self.assertRaises(CSRFRejected):
                csrf.require_native_login_csrf()
        self.request.headers["X-Frappe-CSRF-Token"] = "令牌"
        with patch.object(csrf, "_previous_session_token", return_value="valid-token"):
            with self.assertRaises(CSRFRejected):
                csrf.require_native_login_csrf()

    def test_authenticated_sid_in_request_without_cookie_is_not_exempt(self):
        self.request.cookies = {}
        with self.assertRaises(CSRFRejected):
            csrf.require_initialized_session_token()

    def test_previous_session_lookup_uses_active_unexpired_session(self):
        table = types.SimpleNamespace(
            sid=Column("sid"), status=Column("status"),
            lastupdate=Column("lastupdate"), sessiondata=Column("sessiondata"),
        )
        query = Mock()
        query.select.return_value = query
        query.where.return_value = query
        query.limit.return_value = query
        query.run.return_value = [('{"csrf_token":"valid-token"}',)]
        self.fake.qb = types.SimpleNamespace(DocType=lambda name: table, from_=lambda value: query)
        self.fake.cache = types.SimpleNamespace(hget=lambda *args: None)
        self.fake.parse_json = json.loads
        self.fake.utils = types.SimpleNamespace(now=lambda: "now", time_diff_in_seconds=lambda now, then: 100)
        sessions = types.SimpleNamespace(get_expired_threshold=lambda: "threshold", get_expiry_in_seconds=lambda value: 60)
        with patch.dict(sys.modules, {"frappe.sessions": sessions}):
            self.assertEqual("valid-token", csrf._previous_session_token("encoded%2Dsid"))
            self.assertEqual(
                [("sid", "=", "encoded-sid"), ("status", "=", "Active"), ("lastupdate", ">", "threshold")],
                [call.args[0] for call in query.where.call_args_list],
            )
            query.run.return_value = []
            self.assertIsNone(csrf._previous_session_token("missing"))
            query.run.return_value = [("invalid json",)]
            self.assertIsNone(csrf._previous_session_token("invalid"))
            query.run.return_value = [('["not", "an", "object"]',)]
            self.assertIsNone(csrf._previous_session_token("invalid"))
            query.run.return_value = [('{"csrf_token":"token","last_updated":"earlier","session_expiry":"00:01:00"}',)]
            self.assertIsNone(csrf._previous_session_token("expired"))
            query.run.return_value = [('{"csrf_token":"token","session_end":"2000-01-01T00:00:00+00:00"}',)]
            self.assertIsNone(csrf._previous_session_token("expired"))
            self.fake.utils.time_diff_in_seconds = lambda now, then: 0
            self.fake.cache.hget = lambda *args: {"data": {"csrf_token": "cached-token", "last_updated": "recent"}}
            self.assertEqual("cached-token", csrf._previous_session_token("cached"))
            self.fake.utils.time_diff_in_seconds = lambda now, then: 100
            self.fake.cache.hget = lambda *args: {"data": {"csrf_token": "token", "last_updated": "earlier"}}
            self.assertIsNone(csrf._previous_session_token("expired-cache"))
            self.fake.cache.hget = lambda *args: {"data": {"csrf_token": "token"}}
            self.assertIsNone(csrf._previous_session_token("invalid-cache"))

    def test_security_hooks_are_registered(self):
        from hbos_portal import hooks

        self.assertIn("hbos_portal.auth.csrf.require_native_login_csrf", hooks.before_login)
        self.assertEqual("hbos_portal.auth.csrf.require_initialized_session_token", hooks.before_request[0])


if __name__ == "__main__":
    unittest.main()
