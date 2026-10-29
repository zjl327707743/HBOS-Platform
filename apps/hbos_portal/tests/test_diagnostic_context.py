import sys
import types
import unittest
from unittest.mock import patch

from hbos_portal.services.diagnostic_context import diagnostic_user_context


class Attributes(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class DiagnosticContextTests(unittest.TestCase):
    def check_preservation(self, fail=False):
        data = Attributes(user="Administrator", csrf_token="synthetic-csrf")
        session = Attributes(user="Administrator", sid="synthetic-session", data=data)
        form = {"user": "ordinary@example.test"}
        local = types.SimpleNamespace(session=session, form_dict=form,
            cache={"original": True}, role_permissions={"original": True})
        session_obj = types.SimpleNamespace(data=session)

        def set_user(user):
            # The relevant destructive behavior of native Frappe set_user.
            session.user = user
            session.sid = user
            session.data = Attributes()
            local.form_dict = {}
            local.cache = {}
            local.role_permissions = {}

        fake = types.SimpleNamespace(local=local, set_user=set_user)
        with patch.dict(sys.modules, {"frappe": fake}):
            try:
                with diagnostic_user_context("ordinary@example.test"):
                    self.assertEqual("ordinary@example.test", session.user)
                    self.assertEqual({}, local.role_permissions)
                    if fail:
                        raise RuntimeError("provider failed")
            except RuntimeError:
                self.assertTrue(fail)
        self.assertIs(session_obj.data, local.session)
        self.assertEqual("synthetic-session", session_obj.data.sid)
        self.assertEqual("Administrator", session_obj.data.user)
        self.assertIs(data, session_obj.data.data)
        self.assertEqual("synthetic-csrf", session_obj.data.data.csrf_token)
        self.assertIs(form, local.form_dict)
        self.assertEqual({"original": True}, local.role_permissions)

    def test_diagnostic_restores_request_session_and_permission_context(self):
        self.check_preservation()

    def test_provider_failure_still_restores_session(self):
        self.check_preservation(fail=True)
