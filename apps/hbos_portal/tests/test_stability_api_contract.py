from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from hbos_portal.api._utils import normalize_limit
from hbos_portal.contracts.errors import PortalException


def _load_stability_api():
    fake_frappe = types.ModuleType("frappe")
    def whitelist(*args, **kwargs):
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]
        return lambda func: func

    fake_frappe.whitelist = whitelist
    sys.modules.setdefault("frappe", fake_frappe)
    from hbos_portal.api import stability

    return stability


class StabilityApiContractTest(unittest.TestCase):
    def test_normalize_limit_accepts_api_ceiling(self):
        self.assertEqual(50, normalize_limit(50))

    def test_normalize_limit_rejects_values_above_api_ceiling(self):
        with self.assertRaises(PortalException) as raised:
            normalize_limit(51)
        self.assertEqual("INVALID_REQUEST", raised.exception.error.code)

    def test_stability_api_default_matches_ceiling(self):
        stability = _load_stability_api()
        captured: dict[str, object] = {}

        def provider(*args, **kwargs):
            captured.update(kwargs)
            return {"section": "workbench"}

        with patch.object(stability, "dispatch_provider", side_effect=provider):
            response = stability.get_stability("lims")

        self.assertTrue(response["ok"])
        self.assertEqual(50, captured["limit"])

    def test_stability_api_propagates_invalid_limit_as_error_envelope(self):
        stability = _load_stability_api()
        with patch.object(stability, "dispatch_provider") as provider:
            response = stability.get_stability("lims", limit=100)

        self.assertFalse(response["ok"])
        self.assertEqual("INVALID_REQUEST", response["error"]["code"])
        provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
