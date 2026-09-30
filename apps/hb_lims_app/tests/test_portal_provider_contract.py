from __future__ import annotations

import sys
import types
import unittest

from hb_lims_app import hooks
from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.portal.access import (
    AUDIT_READ_CAPABILITY,
    LEDGER_READ_CAPABILITY,
    READ_CAPABILITY,
    RESULTS_APPROVE_CAPABILITY,
    RESULTS_READ_CAPABILITY,
    RESULTS_REVIEW_CAPABILITY,
    RESULTS_SUBMIT_CAPABILITY,
    RETENTION_READ_CAPABILITY,
    build_access_context,
)
from hb_lims_app.hbos_lims.portal.manifest import get_manifest
from hb_lims_app.hbos_lims.portal.provider import get_provider
from hb_lims_app.hbos_lims.portal.search import project_result_row
from hb_lims_app.hbos_lims.portal.summary import project_todo_summary
from hb_lims_app.hbos_lims.portal.routes import build_stable_deep_link, resolve_stable_route
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
        self.assertEqual(
            [
                "summary", "tasks", "search", "results", "ledger", "audit",
                "coa", "specifications", "retains", "stability",
            ],
            manifest["capabilities"],
        )


class PortalRouteContractTest(unittest.TestCase):
    def test_todo_internal_routes_build_stable_links(self):
        routes = sorted({rule.route for rule in TODO_RULES})
        self.assertTrue(routes)
        for route in routes:
            with self.subTest(route=route):
                stable = build_stable_deep_link(route, {"scope": "mine"})
                self.assertTrue(stable.startswith("/hbos/lims"))
                self.assertEqual(
                    f"/hbos-lims{route}?scope=mine",
                    resolve_stable_route(stable),
                )

    def test_stable_builder_encodes_route_params(self):
        self.assertEqual(
            "/hbos/lims/tasks?scope=mine&task=TASK+001%2F2",
            build_stable_deep_link(
                "/tasks",
                {"scope": "mine", "task": "TASK 001/2"},
            ),
        )

    def test_stable_builder_rejects_unsafe_internal_routes(self):
        for route in (
            "tasks",
            "//evil.example/tasks",
            "https://evil.example/tasks",
            "/%2e%2e/admin",
        ):
            with self.subTest(route=route):
                with self.assertRaises(ValueError):
                    build_stable_deep_link(route)

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

    def test_frontend_alias_routes_map_to_current_native_paths(self):
        self.assertEqual(
            "/hbos-lims/results/ledger",
            resolve_stable_route("/hbos/lims/ledger"),
        )
        self.assertEqual(
            "/hbos-lims/samples",
            resolve_stable_route("/hbos/lims/samples/new"),
        )

    def test_native_alias_routes_project_back_to_stable_paths(self):
        self.assertEqual(
            "/hbos/lims/ledger",
            build_stable_deep_link("/results/ledger"),
        )
        self.assertEqual(
            "/hbos/lims/samples",
            build_stable_deep_link("/samples"),
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
        self.assertEqual(
            [READ_CAPABILITY, RESULTS_READ_CAPABILITY, LEDGER_READ_CAPABILITY,
             RETENTION_READ_CAPABILITY, RESULTS_SUBMIT_CAPABILITY],
            access["capabilities"],
        )

    def test_system_manager_has_audit_read_entry(self):
        access = build_access_context("ops@example.com", [wf.ROLE_SYSTEM])
        self.assertTrue(access["can_enter"])
        self.assertEqual(
            [READ_CAPABILITY, RESULTS_READ_CAPABILITY, LEDGER_READ_CAPABILITY,
             RETENTION_READ_CAPABILITY, AUDIT_READ_CAPABILITY],
            access["capabilities"],
        )

    def test_quality_roles_do_not_receive_result_or_ledger_read(self):
        qa_access = build_access_context("qa@example.com", [wf.ROLE_LIMS_QA])
        qa_manager_access = build_access_context("qa-manager@example.com", [wf.ROLE_LIMS_QA_MANAGER])

        self.assertIn(RETENTION_READ_CAPABILITY, qa_access["capabilities"])
        for access in (qa_access, qa_manager_access):
            self.assertNotIn(RESULTS_READ_CAPABILITY, access["capabilities"])
            self.assertNotIn(LEDGER_READ_CAPABILITY, access["capabilities"])

    def test_unrelated_role_cannot_enter(self):
        access = build_access_context("user@example.com", ["Employee"])
        self.assertFalse(access["can_enter"])

    def test_administrator_is_break_glass_entry(self):
        access = build_access_context("Administrator", [])
        self.assertTrue(access["can_enter"])

    def test_administrator_receives_portal_read_capabilities(self):
        access = build_access_context("Administrator", [])
        self.assertTrue(
            {
                RESULTS_READ_CAPABILITY,
                LEDGER_READ_CAPABILITY,
                RETENTION_READ_CAPABILITY,
            }.issubset(access["capabilities"])
        )

    def test_access_contract_does_not_expose_role_names(self):
        access = build_access_context("analyst@example.com", [wf.ROLE_ANALYST])
        self.assertEqual(
            {"app_id", "can_enter", "capabilities", "scopes"},
            set(access),
        )
        self.assertNotIn(wf.ROLE_ANALYST, str(access))


class PortalSearchProjectionContractTest(unittest.TestCase):
    def test_projects_result_to_stable_search_contract(self):
        projected = project_result_row(
            {
                "name": "RESULT 001/2",
                "sample": "SAMPLE-001",
                "item_name": "含量",
                "verdict": "合格",
                "result_status": "已批准",
            }
        )

        self.assertEqual("lims", projected["app_id"])
        self.assertEqual("test_result", projected["entity_type"])
        self.assertEqual("RESULT 001/2", projected["entity_id"])
        self.assertEqual("含量 · RESULT 001/2", projected["title"])
        self.assertEqual("SAMPLE-001 · 合格", projected["subtitle"])
        self.assertEqual("已批准", projected["status"])
        self.assertEqual(
            "/hbos/lims/results/RESULT%20001%2F2",
            projected["deep_link"],
        )

    def test_search_projection_rejects_missing_identity(self):
        with self.assertRaises(ValueError):
            project_result_row({"item_name": "含量"})


class PortalSummaryProjectionContractTest(unittest.TestCase):
    def test_projects_permission_aware_todo_summary(self):
        projected = project_todo_summary(
            {
                "summary": {
                    "total": 7,
                    "overdue": 2,
                    "assigned_to_me": 3,
                    "role_pending": 4,
                    "by_module": {
                        "testing": 4,
                        "stability": 2,
                        "retention": 1,
                    },
                },
                "scope_label": "检验范围",
                "semantic": {
                    "pending_testing": 2,
                    "in_testing": 1,
                    "pending_review": 3,
                    "pending_coa_publish": 1,
                },
                "generated_at": "2026-09-25T02:00:00+08:00",
            }
        )

        self.assertEqual("lims", projected["app_id"])
        self.assertEqual("attention", projected["status"])
        self.assertEqual("检验范围", projected["scope_label"])
        self.assertEqual(4, len(projected["metrics"]))
        values = {item["id"]: item["value"] for item in projected["metrics"]}
        self.assertEqual(2, values["my_testing"])
        self.assertEqual(1, values["in_testing"])
        self.assertEqual(3, values["my_review"])
        self.assertEqual(1, values["coa_publish"])
        links = {item["id"]: item["deep_link"] for item in projected["metrics"]}
        self.assertEqual("/hbos/lims/tasks?view=my-testing", links["my_testing"])
        self.assertIn("status=%E6%A3%80%E9%AA%8C%E4%B8%AD", links["in_testing"])
        self.assertEqual("/hbos/lims/tasks?view=my-review", links["my_review"])
        self.assertEqual("/hbos/lims/tasks?view=my-approval", links["coa_publish"])

    def test_zero_summary_uses_non_alarm_tones(self):
        projected = project_todo_summary(
            {
                "summary": {"total": 0, "overdue": 0, "by_module": {}},
                "semantic": {},
                "generated_at": "",
            }
        )
        by_id = {item["id"]: item for item in projected["metrics"]}
        self.assertEqual("normal", projected["status"])
        self.assertEqual("success", by_id["coa_publish"]["tone"])
        self.assertEqual("neutral", by_id["my_testing"]["tone"])


class PortalProviderRuntimeBoundaryTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("frappe", None)

    def test_provider_exposes_declared_capability_methods(self):
        provider = get_provider()
        self.assertTrue(callable(provider.summary))
        self.assertTrue(callable(provider.my_tasks))
        self.assertTrue(callable(provider.search))
        self.assertTrue(callable(provider.results))
        self.assertTrue(callable(provider.ledger))
        self.assertTrue(callable(provider.audit))
        self.assertTrue(callable(provider.coa))
        self.assertTrue(callable(provider.specifications))
        self.assertTrue(callable(provider.retains))
        self.assertTrue(callable(provider.stability))

    def test_provider_derives_identity_from_frappe_session(self):
        fake_frappe = types.SimpleNamespace(
            session=types.SimpleNamespace(user="reviewer@example.com"),
            get_roles=lambda user: [wf.ROLE_REVIEWER] if user == "reviewer@example.com" else [],
        )
        sys.modules["frappe"] = fake_frappe

        access = get_provider().access_context()

        self.assertTrue(access["can_enter"])
        self.assertEqual(
            [READ_CAPABILITY, RESULTS_READ_CAPABILITY, LEDGER_READ_CAPABILITY,
             RETENTION_READ_CAPABILITY, RESULTS_REVIEW_CAPABILITY,
             RESULTS_APPROVE_CAPABILITY, AUDIT_READ_CAPABILITY],
            access["capabilities"],
        )


if __name__ == "__main__":
    unittest.main()
