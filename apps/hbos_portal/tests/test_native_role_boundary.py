"""Unit boundaries for GLOBAL native-role grants, audit snapshots and replay order.

These tests never touch a Site database. They pin the invariants that must hold
before the isolated/UAT integration runs: a restricted administrator cannot grant
a GLOBAL native role, the site-level grantor is an explicit allowlist, audit keeps
structured role changes but drops secrets, and replay is only reachable after the
current authorization checks.
"""
from __future__ import annotations

import contextlib
import unittest
from unittest.mock import patch

import frappe

from hbos_portal.iam import app_roles, audit, policy


class FakeDB:
    def __init__(self, rows=None):
        self.rows = rows or []

    def sql(self, *args, **kwargs):
        return self.rows


class FakeFrappe:
    def __init__(self, grantors=(), permissions=None):
        self.conf = {"hbos_native_role_grantors": list(grantors)}
        self.PermissionError = frappe.PermissionError
        self.ValidationError = frappe.ValidationError
        self.db = FakeDB(permissions)

    def throw(self, message, exc=None):
        raise (exc or frappe.ValidationError)(message)


class NativeRoleBoundaryTest(unittest.TestCase):
    def test_registry_keeps_stock_manager_and_other_high_roles_unavailable(self):
        self.assertIn("Stock User", app_roles.REGISTRY["inventory"]["roles"])
        self.assertNotIn("Stock Manager", app_roles.REGISTRY["inventory"]["roles"])
        for blocked in ("Stock Manager", "System Manager", "HR Manager", "Accounts Manager"):
            self.assertIn(blocked, app_roles.REGISTRY["inventory"]["blocked"])

    def test_stock_user_is_registered_as_global(self):
        meta = app_roles.REGISTRY["inventory"]["roles"]["Stock User"]
        self.assertEqual(meta["native_scope"], "GLOBAL")

    def test_normalize_rejects_unregistered_and_deduplicates(self):
        fake = FakeFrappe()
        with patch.object(app_roles, "frappe", fake):
            self.assertEqual(app_roles._normalize("inventory", ["Stock User", "Stock User"]), ["Stock User"])
            for bad in (["Stock Manager"], ["System Manager"], ["Unknown"], "not-json"):
                with self.subTest(bad=bad), self.assertRaises(frappe.ValidationError):
                    app_roles._normalize("inventory", bad)

    def test_restricted_admin_cannot_grant_global_role(self):
        fake = FakeFrappe()
        app = app_roles.REGISTRY["inventory"]
        with patch.object(app_roles, "frappe", fake), patch.object(policy, "get_current_user", return_value="hr-admin"):
            with self.assertRaises(frappe.PermissionError):
                app_roles._assert_grant_authority(app, True)

    def test_no_acknowledgement_is_refused_even_for_grantor(self):
        fake = FakeFrappe(grantors=["site-grantor"])
        app = app_roles.REGISTRY["inventory"]
        with patch.object(app_roles, "frappe", fake), patch.object(policy, "get_current_user", return_value="site-grantor"):
            with self.assertRaises(frappe.PermissionError):
                app_roles._assert_grant_authority(app, False)

    def test_site_grantor_with_acknowledgement_passes(self):
        fake = FakeFrappe(grantors=["site-grantor"])
        app = app_roles.REGISTRY["inventory"]
        with patch.object(app_roles, "frappe", fake), patch.object(policy, "get_current_user", return_value="site-grantor"):
            app_roles._assert_grant_authority(app, True)

    def test_company_envelope_requires_one_exact_permission(self):
        employee = {"name": "E1", "user_id": "u1", "department": "D1", "company": "C1", "status": "Active"}
        matching = {"name": "UP1", "allow": "Company", "for_value": "C1", "applicable_for": None}
        with patch.object(app_roles, "frappe", FakeFrappe(permissions=[matching])):
            self.assertEqual(app_roles.company_envelope(employee)["company"], "C1")
        for rows in ([], [matching, dict(matching, name="UP2")], [dict(matching, for_value="C2")], [dict(matching, applicable_for="Warehouse")]):
            with self.subTest(rows=rows), patch.object(app_roles, "frappe", FakeFrappe(permissions=rows)):
                self.assertIsNone(app_roles.company_envelope(employee))

    def test_grantor_without_company_envelope_is_refused(self):
        employee = {"name": "E1", "user_id": "u1", "department": "D1", "company": "C1", "status": "Active"}
        fake = FakeFrappe(grantors=["site-grantor"], permissions=[])
        with patch.object(app_roles, "frappe", fake), patch.object(policy, "get_current_user", return_value="site-grantor"):
            with self.assertRaises(frappe.PermissionError):
                app_roles._assert_grant_authority(app_roles.REGISTRY["inventory"], True, employee)

    def test_audit_keeps_role_changes_and_drops_secrets(self):
        fake = FakeFrappe()
        value = {
            "employee": "E1",
            "app_roles": ["Stock User"],
            "other_roles": ["Employee"],
            "roles": ["Stock User"],
            "added": ["Stock User"],
            "removed": [],
            "acknowledged_global_scope": True,
            "password": "secret",
            "proof": "token",
            "sid": "session",
            "employee_name": "Synthetic",
        }
        with patch.object(audit, "frappe", fake):
            snapshot = audit.safe_snapshot(value)
        for key in ("employee", "app_roles", "other_roles", "roles", "added", "removed", "acknowledged_global_scope"):
            self.assertIn(key, snapshot)
        for key in ("password", "proof", "sid"):
            self.assertNotIn(key, snapshot)

    def test_replay_is_not_reachable_before_current_authorization(self):
        employee = {"name": "E1", "user_id": "u1", "department": "D1", "company": "C1", "status": "Active", "modified": "v1"}
        fake = FakeFrappe()
        with patch.object(app_roles, "frappe", fake), patch.object(app_roles.guards, "require_post"), \
             patch.object(app_roles, "serialize", lambda *a, **k: contextlib.nullcontext()), \
             patch.object(app_roles, "_employee", return_value=employee), \
             patch.object(app_roles, "_authorize", side_effect=frappe.PermissionError("no scope")), \
             patch.object(app_roles.audit, "replay") as replay:
            with self.assertRaises(frappe.PermissionError):
                app_roles.save("E1", "inventory", ["Stock User"], "v1", "ctx", "req-12345678", True)
            replay.assert_not_called()

    def test_replay_is_not_reachable_after_grantor_status_is_lost(self):
        employee = {"name": "E1", "user_id": "u1", "department": "D1", "company": "C1", "status": "Active", "modified": "v1"}
        fake = FakeFrappe(grantors=[])  # grantor revoked, access.manage would still pass
        with patch.object(app_roles, "frappe", fake), patch.object(app_roles.guards, "require_post"), \
             patch.object(app_roles, "serialize", lambda *a, **k: contextlib.nullcontext()), \
             patch.object(app_roles, "_employee", return_value=employee), \
             patch.object(app_roles, "_authorize"), \
             patch.object(app_roles.audit, "replay") as replay, \
             patch.object(policy, "get_current_user", return_value="former-grantor"):
            with self.assertRaises(frappe.PermissionError):
                app_roles.save("E1", "inventory", ["Stock User"], "v1", "ctx", "req-87654321", True)
            replay.assert_not_called()

    def test_replay_runs_after_authorization_when_scope_still_valid(self):
        employee = {"name": "E1", "user_id": "u1", "department": "D1", "company": "C1", "status": "Active", "modified": "v1"}
        fake = FakeFrappe(grantors=["site-grantor"], permissions=[{"name": "UP1", "allow": "Company", "for_value": "C1", "applicable_for": None}])
        with patch.object(app_roles, "frappe", fake), patch.object(app_roles.guards, "require_post"), \
             patch.object(app_roles, "serialize", lambda *a, **k: contextlib.nullcontext()), \
             patch.object(app_roles, "_employee", return_value=employee), \
             patch.object(app_roles, "_authorize"), \
             patch.object(policy, "get_current_user", return_value="site-grantor"), \
             patch.object(app_roles.audit, "replay", return_value={"changed": True, "after": ["Stock User"]}) as replay:
            result = app_roles.save("E1", "inventory", ["Stock User"], "v1", "ctx", "req-abcdefgh", True)
            self.assertTrue(result["replayed"])
            replay.assert_called_once()


if __name__ == "__main__":
    unittest.main()
