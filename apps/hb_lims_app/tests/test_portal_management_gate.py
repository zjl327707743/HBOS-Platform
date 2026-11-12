from __future__ import annotations

import unittest

from hb_lims_app.hbos_lims.portal.access import build_access_context
from hb_lims_app.hbos_lims.portal.manifest import get_manifest
from hb_lims_app.hbos_lims.portal.provider import get_provider


class PortalManagementGateTest(unittest.TestCase):
    """Management V0 stays closed until a safe Provider target is explicit."""

    def test_manifest_does_not_publish_management_capability(self):
        self.assertNotIn("management", get_manifest()["capabilities"])

    def test_provider_has_no_uncontracted_management_adapter(self):
        self.assertFalse(hasattr(get_provider(), "management"))

    def test_access_context_does_not_grant_management(self):
        for user, roles in (
            ("analyst@example.com", ["LIMS Analyst"]),
            ("ops@example.com", ["System Manager"]),
            ("Administrator", []),
        ):
            with self.subTest(user=user):
                access = build_access_context(user, roles)
                self.assertNotIn("management", access["capabilities"])


if __name__ == "__main__":
    unittest.main()
