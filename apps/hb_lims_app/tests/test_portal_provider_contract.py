from __future__ import annotations

import sys
import types
import unittest

from hb_lims_app import hooks
from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.portal.access import (
    READ_CAPABILITY,
    build_access_context,
)
from hb_lims_app.hbos_lims.portal.manifest import get_manifest
from hb_lims_app.hbos_lims.portal.provider import get_provider
from hb_lims_app.hbos_lims.portal.routes import resolve_stable_route
from hb_lims_app.hbos_lims.todo_contract import TODO_RULES


class PortalManifestContractTest(unittest.TestCase):
    def test_hook_registers_provider_factory(self):
        self.assertEqual(
            [
                "hb_lims_app.hbos_lims.portal.provider.get_provider",
            ],
            hooks.hbos_portal_provider,
        )

    def test_manifest_is_stable_minimal_registration(self):
        manifest = get_manifest()
        self.assertEqual(1, manifest["contract_version"])
        self.assertEqual("lims", manifest["id"])
        self.assertEqual("/hbos/lims", manifest["route"])
        self.assertEqual("native", manifest["migration_mode"])
        self.assertEqual("ExperimentOutlined", manifest["icon"])
        self.assertEqual("lims", manifest["accent"])
        self.assertEqual([], manifest["capabilities"])


class PortalRouteContractTest(unittest.TestCase):
    def test_root_maps_to_current_lims_dashboard(self):
        self.assertEqual(
            "/hbos-lims/dashboard",
            resolve_stable_route("/hbos/lims"),
        )

    def test_all_current_todo_routes_have_stable_mapping(self):
        routes = sorted({rule.route for rule in TODO_RULES})
        self.assertTrue(routes)
        for route in routes:
            with self.subTest(route=route):
                self.assertEqual(
                    f"/hbos-lims{route}",
                    resolve_stable_route(f"/hbos/lims{route}"),
                )

    def test_query_string_is_preserved(self):
        self.assertEqual(
            "/hbos-lims/tasks?scope=mine&status=open",
            resolve_stable_route(
                "/hbos/lims/tasks?scope=mine&status=open"
            ),
        )

    def test_rejects_paths_outside_lims_namespace(self):
        for path in (
            "/hbos/inventory/tasks",
            "/hbos/limsx/tasks",
            "https://evil.example/hbos/lims",
            "/hbos/lims/%2e%2e/admin",
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    resolve_stable_route(path)


class PortalAccessContractTest(unittest.TestCase):
    def test_guest_cannot_enter(self):
        access = build_access_context("Guest", ["LIMS Analyst"])
        self.assertFalse(access["can_enter"])
        self.assertEqual([], access["capabilities"])

    def test_lims_business_role_can_enter(self):
        access = build_access_context("analyst@example.com", [wf.ROLE_ANALYST])
        self.assertTrue(access["can_enter"])
        self.assertEqual([READ_CAPABILITY], access["capabilities"])

    def test_system_manager_has_read_entry_only(self):
        access = build_access_context("ops@example.com", [wf.ROLE_SYSTEM])
        self.assertTrue(access["can_enter"])
        self.assertEqual([READ_CAPABILITY], access["capabilities"])

    def test_unrelated_role_cannot_enter(self):
        access = build_access_context("user@example.com", ["Employee"])
        self.assertFalse(access["can_enter"])

    def test_administrator_is_break_glass_entry(self):
        access = build_access_context("Administrator", [])
        self.assertTrue(access["can_enter"])

    def test_access_contract_does_not_expose_role_names(self):
        access = build_access_context("analyst@example.com", [wf.ROLE_ANALYST])
        self.assertEqual(
            {"app_id", "can_enter", "capabilities", "scopes"},
            set(access),
        )
        self.assertNotIn(wf.ROLE_ANALYST, str(access))


class PortalProviderRuntimeBoundaryTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("frappe", None)

    def test_provider_derives_identity_from_frappe_session(self):
        fake_frappe = types.SimpleNamespace(
            session=types.SimpleNamespace(user="reviewer@example.com"),
            get_roles=lambda user: [wf.ROLE_REVIEWER] if user == "reviewer@example.com" else [],
        )
        sys.modules["frappe"] = fake_frappe

        access = get_provider().access_context()

        self.assertTrue(access["can_enter"])
        self.assertEqual([READ_CAPABILITY], access["capabilities"])


if __name__ == "__main__":
    unittest.main()
