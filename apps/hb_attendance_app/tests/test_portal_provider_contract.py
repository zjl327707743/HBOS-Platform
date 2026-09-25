from __future__ import annotations

import sys
import types
import unittest

from hb_attendance_app import hooks
from hb_attendance_app.hbos_attendance.portal.access import (
    ATTENDANCE_PORTAL_ROLES,
    READ_CAPABILITY,
    build_access_context,
)
from hb_attendance_app.hbos_attendance.portal.manifest import get_manifest
from hb_attendance_app.hbos_attendance.portal.provider import get_provider
from hb_attendance_app.hbos_attendance.portal.routes import resolve_stable_route
from hb_attendance_app.hbos_attendance.portal.summary import project_dashboard_summary


class AttendancePortalManifestTest(unittest.TestCase):
    def test_hook_registers_provider(self):
        self.assertEqual(
            ["hb_attendance_app.hbos_attendance.portal.provider.get_provider"],
            hooks.hbos_portal_provider,
        )

    def test_manifest_registers_legacy_stable_entry_only(self):
        manifest = get_manifest()
        self.assertEqual(1, manifest["contract_version"])
        self.assertEqual("attendance", manifest["id"])
        self.assertEqual("/hbos/attendance", manifest["route"])
        self.assertEqual("legacy", manifest["migration_mode"])
        self.assertEqual(["summary"], manifest["capabilities"])


class AttendancePortalAccessTest(unittest.TestCase):
    def test_guest_and_ordinary_employee_are_not_exposed_yet(self):
        self.assertFalse(build_access_context("Guest", ["HR User"])["can_enter"])
        self.assertFalse(build_access_context("emp@example.com", ["Employee"])["can_enter"])

    def test_current_hr_roles_can_enter(self):
        for role in sorted(ATTENDANCE_PORTAL_ROLES):
            with self.subTest(role=role):
                access = build_access_context("hr@example.com", [role])
                self.assertTrue(access["can_enter"])
                self.assertEqual([READ_CAPABILITY], access["capabilities"])

    def test_administrator_break_glass_entry(self):
        self.assertTrue(build_access_context("Administrator", [])["can_enter"])

    def test_access_does_not_expose_raw_roles(self):
        access = build_access_context("hr@example.com", ["HR User"])
        self.assertEqual(
            {"app_id", "can_enter", "capabilities", "scopes"},
            set(access),
        )
        self.assertNotIn("HR User", str(access))


class AttendancePortalRouteTest(unittest.TestCase):
    def test_root_and_dashboard_map_to_current_desk_page(self):
        self.assertEqual(
            "/app/hbos-attendance-dashboard",
            resolve_stable_route("/hbos/attendance"),
        )
        self.assertEqual(
            "/app/hbos-attendance-dashboard",
            resolve_stable_route("/hbos/attendance/dashboard"),
        )

    def test_query_is_preserved(self):
        self.assertEqual(
            "/app/hbos-attendance-dashboard?range=week",
            resolve_stable_route("/hbos/attendance?range=week"),
        )

    def test_unregistered_or_unsafe_paths_are_rejected(self):
        for path in (
            "/hbos/attendance/employees",
            "/hbos/inventory",
            "https://evil.example/hbos/attendance",
            "/hbos/attendance/%2e%2e/admin",
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    resolve_stable_route(path)


class AttendancePortalSummaryTest(unittest.TestCase):
    def test_projects_existing_dashboard_facts(self):
        projected = project_dashboard_summary(
            {
                "anomaly_people": 5,
                "total_late": 8,
                "total_early": 2,
                "total_absent": 1,
            }
        )
        self.assertEqual("attendance", projected["app_id"])
        self.assertEqual("attention", projected["status"])
        values = {metric["id"]: metric["value"] for metric in projected["metrics"]}
        self.assertEqual(5, values["attendance_anomaly_people"])
        self.assertEqual(8, values["attendance_late"])
        self.assertEqual(2, values["attendance_early"])
        self.assertEqual(1, values["attendance_absent"])
        self.assertTrue(
            all(
                metric["deep_link"] == "/hbos/attendance/dashboard"
                for metric in projected["metrics"]
            )
        )

    def test_zero_dashboard_is_non_alarm(self):
        projected = project_dashboard_summary({})
        self.assertEqual("normal", projected["status"])
        self.assertEqual(4, len(projected["metrics"]))


class AttendancePortalProviderRuntimeBoundaryTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("frappe", None)

    def test_provider_uses_frappe_session_identity(self):
        fake_frappe = types.SimpleNamespace(
            session=types.SimpleNamespace(user="hr@example.com"),
            get_roles=lambda user: ["HR User"] if user == "hr@example.com" else [],
        )
        sys.modules["frappe"] = fake_frappe

        provider = get_provider()
        access = provider.access_context()
        self.assertTrue(access["can_enter"])
        self.assertTrue(callable(provider.summary))
        self.assertEqual([READ_CAPABILITY], access["capabilities"])


if __name__ == "__main__":
    unittest.main()
