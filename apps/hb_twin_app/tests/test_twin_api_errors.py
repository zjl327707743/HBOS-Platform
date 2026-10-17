from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from hb_twin_app.hb_twin.errors import TwinError


class ResponseBoundary(unittest.TestCase):
    def setUp(self):
        self.logged = []
        self.frappe = types.SimpleNamespace(
            whitelist=lambda **kwargs: lambda method: method,
            local=types.SimpleNamespace(response={}, response_headers={}),
            log_error=lambda **kwargs: self.logged.append(kwargs),
        )
        path = Path(__file__).resolve().parents[1] / "hb_twin_app/hb_twin/api.py"
        spec = importlib.util.spec_from_file_location("twin_api_error_fixture", path)
        self.api = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe}):
            spec.loader.exec_module(self.api)

    def test_unexpected_error_hides_private_paths_and_request_details_in_response_and_log(self):
        def failed():
            raise RuntimeError("/private/fixture/source.glb credential=fixture-only-secret")
        response = self.api._run(failed)
        self.assertFalse(response["ok"])
        self.assertEqual("SERVICE_ERROR", response["error"]["code"])
        for value in [response, self.logged]:
            self.assertNotIn("/private/fixture", str(value))
            self.assertNotIn("fixture-only-secret", str(value))
        self.assertIn("no-store", self.frappe.local.response_headers["Cache-Control"])

    def test_json_rpc_preserves_domain_codes_without_losing_local_process_errors(self):
        for code in ["PROCESS_INCOMPATIBLE", "MAPPING_INVALID", "ASSET_REVISION_MISMATCH"]:
            def failed():
                raise TwinError(code, "fixture")
            result = self.api._run_v1(failed)
            self.assertEqual(code, result["error"]["code"])
            self.assertNotIn("http_status_code", self.frappe.local.response)
        for code in ["FORBIDDEN", "MEMBERS_PENDING"]:
            def denied():
                raise TwinError(code, "fixture")
            self.api._run_v1(denied)
            self.assertEqual(403, self.frappe.local.response["http_status_code"])

    def test_binary_errors_keep_auth_and_integrity_status_semantics(self):
        for code, expected in [("FORBIDDEN", 403), ("MEMBERS_PENDING", 403), ("ASSET_REVISION_MISMATCH", 409), ("ASSET_INTEGRITY_FAILED", 409), ("ASSET_UNAVAILABLE", 404)]:
            self.assertEqual(expected, self.api._model_error_status(code))


if __name__ == "__main__":
    unittest.main()
