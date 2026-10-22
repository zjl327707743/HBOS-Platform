"""Platform-root authority and capability aggregation boundaries.

The session bootstrap asks "which IAM management capabilities exist?" on every
resume. Two invariants are pinned here because both were real UAT defects:

* the built-in Administrator must be able to manage IAM configuration on any
  IAM-enabled site, not only on a site marked as a test site;
* the aggregation must prune targets that no allow rule can reach and stop at
  the first authorized target, because it used to scan and lock every
  department for every management operation (8-9 seconds per resume).
"""
from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime
from unittest.mock import patch

# Same lightweight module stub the other database-free suites install, so this
# file can also run on its own.
sys.modules.setdefault("frappe", types.SimpleNamespace(whitelist=lambda **kw: lambda fn: fn))

from hbos_portal.iam import guards, policy


class FakePermissionError(Exception):
    pass


class FakeFrappe:
    PermissionError = FakePermissionError

    def __init__(self):
        self.throw = self._throw

    def _throw(self, message, exc=None):
        raise (exc or RuntimeError)(message)


def _rule(operation, effect="allow", scope_type="COMPANY", scope_ref="C1", app_id="iam"):
    return {
        "app_id": app_id,
        "operation_id": operation,
        "effect": effect,
        "scope_type": scope_type,
        "scope_ref": scope_ref,
        "include_descendants": 0,
        "valid_from": None,
        "valid_until": None,
        "qualification_ref": None,
    }


DEPARTMENTS = [
    {"name": "D1", "company": "C1", "disabled": 0},
    {"name": "D2", "company": "C2", "disabled": 0},
]


class PlatformRootTest(unittest.TestCase):
    def _root(self, user, flags):
        with patch.object(policy, "get_current_user", return_value=user), \
             patch.object(policy, "enabled_flag", side_effect=lambda name: flags.get(name, False)):
            return guards.platform_root()

    def test_administrator_is_root_whenever_iam_is_enabled(self):
        self.assertTrue(self._root("Administrator", {"hbos_iam_enabled": True}))

    def test_administrator_root_does_not_depend_on_the_test_site_flag(self):
        self.assertTrue(self._root("Administrator", {"hbos_iam_enabled": True, "hbos_iam_test_site": False}))
        self.assertTrue(self._root("Administrator", {"hbos_iam_enabled": False, "hbos_iam_test_site": True}))

    def test_other_accounts_are_never_platform_root(self):
        self.assertFalse(self._root("uat-iam-admin@example.invalid", {"hbos_iam_enabled": True}))
        self.assertFalse(self._root("Administrator", {}))

    def test_isolated_root_still_requires_the_test_site_flag(self):
        with patch.object(policy, "get_current_user", return_value="Administrator"), \
             patch.object(policy, "enabled_flag", side_effect=lambda name: name == "hbos_iam_enabled"):
            self.assertFalse(guards.isolated_root())


class CapabilityAggregationTest(unittest.TestCase):
    def _can_manage(self, user, operation, rules, permitted, departments=None):
        with patch.object(guards, "frappe", FakeFrappe()), \
             patch.object(policy, "get_current_user", return_value=user), \
             patch.object(policy, "enabled_flag", return_value=True), \
             patch.object(policy, "_rules", return_value=(rules, None)), \
             patch.object(policy, "_now", return_value=datetime(2026, 1, 1)), \
             patch.object(guards, "_permitted", side_effect=permitted):
            return guards.can_manage_any(operation, app_id="iam", departments=departments or DEPARTMENTS)

    def test_no_allow_rule_short_circuits_without_scanning_targets(self):
        calls = []

        def permitted(*args):
            calls.append(args)
            return True

        self.assertFalse(self._can_manage("employee", "iam.people.read", [], permitted))
        self.assertEqual(calls, [])

    def test_candidates_are_pruned_by_company_scope(self):
        visited = []

        def permitted(user, operation, kind, ref, app_id, company=None):
            visited.append(ref)
            return True

        rules = [_rule("iam.people.read", scope_type="COMPANY", scope_ref="C2")]
        self.assertTrue(self._can_manage("employee", "iam.people.read", rules, permitted))
        self.assertEqual(visited, ["D2"])

    def test_first_authorized_target_stops_the_scan(self):
        visited = []

        def permitted(user, operation, kind, ref, app_id, company=None):
            visited.append(ref)
            return True

        rules = [_rule("iam.people.read", scope_type="COMPANY", scope_ref="C1")]
        self.assertTrue(self._can_manage("employee", "iam.people.read", rules, permitted))
        self.assertEqual(visited, ["D1"])

    def test_platform_root_covers_every_department_without_evaluation(self):
        calls = []

        def permitted(*args):
            calls.append(args)
            return False

        with patch.object(guards, "frappe", FakeFrappe()), \
             patch.object(policy, "get_current_user", return_value="Administrator"), \
             patch.object(policy, "enabled_flag", return_value=True), \
             patch.object(policy, "_rules", return_value=([], None)), \
             patch.object(policy, "_now", return_value=datetime(2026, 1, 1)), \
             patch.object(guards, "_permitted", side_effect=permitted):
            self.assertTrue(guards.can_manage_any("iam.people.read", app_id="iam", departments=DEPARTMENTS))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
