from __future__ import annotations

import unittest

from hbos_portal.contracts.errors import PortalException
from hbos_portal.services.routes import (
    validate_resolved_path,
    validate_stable_path,
)


class RouteContractTest(unittest.TestCase):
    def test_accepts_exact_app_root(self):
        self.assertEqual(
            "/hbos/lims",
            validate_stable_path("lims", "/hbos/lims"),
        )

    def test_preserves_query_string(self):
        self.assertEqual(
            "/hbos/lims/tasks?scope=mine",
            validate_stable_path("lims", "/hbos/lims/tasks?scope=mine"),
        )

    def test_rejects_prefix_confusion(self):
        with self.assertRaises(PortalException):
            validate_stable_path("lims", "/hbos/limsx/tasks")

    def test_rejects_external_url(self):
        with self.assertRaises(PortalException):
            validate_stable_path("lims", "https://evil.example/hbos/lims")

    def test_rejects_traversal(self):
        with self.assertRaises(PortalException):
            validate_stable_path("lims", "/hbos/lims/%2e%2e/admin")

    def test_resolved_path_must_remain_local(self):
        self.assertEqual(
            "/hbos-lims/tasks?scope=mine",
            validate_resolved_path("/hbos-lims/tasks?scope=mine"),
        )
        with self.assertRaises(PortalException):
            validate_resolved_path("//evil.example/redirect")


if __name__ == "__main__":
    unittest.main()
