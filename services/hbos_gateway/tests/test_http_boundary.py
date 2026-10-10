"""Exercise the ASGI boundary after FastAPI / Starlette security upgrades."""
from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.hbos_gateway.app import app


class HttpBoundaryTests(unittest.TestCase):
    def setUp(self):
        grant = {
            "enabled": True, "capabilities": ["knowledge.search"],
            "policy_revision": "synthetic-v1", "dataset_ids": ["synthetic-set"],
            "document_ids": ["synthetic-doc"],
        }
        self.payload = {
            "query": "synthetic question", "client_id": "synthetic-client",
            "subject": "synthetic@example.test", "policy_revision": "synthetic-v1",
            "dataset_ids": ["synthetic-set"], "document_ids": ["synthetic-doc"],
            "request_id": "synthetic-request",
        }
        self.headers = {"Authorization": "Bearer synthetic-token"}
        index = SimpleNamespace(search=lambda **kwargs: [{
            "document_id": "synthetic-doc", "dataset_id": "synthetic-set",
            "excerpt": "x" * 900,
        }])
        self.enterContext(patch.dict(os.environ, {"HBOS_GATEWAY_CLIENT_ID": "synthetic-client"}, clear=True))
        self.enterContext(patch("services.hbos_gateway.app.protected_file", side_effect=lambda name, maximum:
            "synthetic-token" if name == "HBOS_GATEWAY_TOKEN_FILE" else json.dumps({"default_internal": grant})))
        self.enterContext(patch("services.hbos_gateway.app.LocalIndex.from_file", return_value=index))
        self.client = self.enterContext(TestClient(app))

    def test_search_preserves_json_contract_and_excerpt_bound(self):
        response = self.client.post("/v1/knowledge/search", json=self.payload, headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual("SUCCESS", response.json()["status"])
        self.assertEqual(500, len(response.json()["results"][0]["excerpt"]))

    def test_missing_or_incorrect_credentials_cannot_reach_search(self):
        for headers in [{}, {"Authorization": "Bearer invalid"}]:
            with self.subTest(headers=headers):
                response = self.client.post("/v1/knowledge/search", json=self.payload, headers=headers)
                self.assertEqual(401, response.status_code)

    def test_scope_and_subject_restrictions_survive_http_dispatch(self):
        for change in [{"subject": "Guest"}, {"document_ids": ["unapproved"]}, {"client_id": "wrong-client"}]:
            with self.subTest(change=change):
                response = self.client.post("/v1/knowledge/search", json={**self.payload, **change}, headers=self.headers)
                self.assertEqual(401 if "client_id" in change else 403, response.status_code)

    def test_stale_policy_and_invalid_payload_keep_explicit_errors(self):
        for change, status in [({"policy_revision": "stale"}, 409), ({"query": "x" * 501}, 422)]:
            response = self.client.post("/v1/knowledge/search", json={**self.payload, **change}, headers=self.headers)
            self.assertEqual(status, response.status_code)

    def test_health_remains_ready_without_exposing_private_configuration(self):
        response = self.client.get("/health")
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["configured"])
        self.assertNotIn("synthetic-token", response.text)


if __name__ == "__main__":
    unittest.main()
