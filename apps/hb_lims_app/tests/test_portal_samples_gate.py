from __future__ import annotations

import unittest

from hb_lims_app.hbos_lims.portal.manifest import get_manifest
from hb_lims_app.hbos_lims.portal.provider import get_provider


class PortalSamplesGateTest(unittest.TestCase):
    """Sample pages stay pending until read and registration contracts are explicit."""

    def test_manifest_does_not_publish_uncontracted_samples_capability(self):
        self.assertNotIn("samples", get_manifest()["capabilities"])

    def test_provider_has_no_uncontracted_samples_adapter(self):
        provider = get_provider()
        self.assertFalse(hasattr(provider, "samples"))
        self.assertFalse(hasattr(provider, "register_sample"))


if __name__ == "__main__":
    unittest.main()
