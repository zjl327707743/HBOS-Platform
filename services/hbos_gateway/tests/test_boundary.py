from __future__ import annotations

import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from services.hbos_gateway.app import Search, search_local


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.grant = {"enabled": True, "capabilities": ["knowledge.search"], "policy_revision": "synthetic-v1", "dataset_ids": ["synthetic-set"], "document_ids": ["synthetic-doc"], "equipment_document_ids": {"synthetic-equipment": ["synthetic-doc"]}}
        self.policy = {"default_internal": self.grant}
        self.payload = {"query": "synthetic question", "client_id": "synthetic-client", "subject": "synthetic@example.test", "policy_revision": "synthetic-v1", "dataset_ids": ["synthetic-set"], "document_ids": ["synthetic-doc"], "request_id": "synthetic-request"}
        self.index = SimpleNamespace(search=lambda **kw: [{"document_id": "synthetic-doc", "dataset_id": "synthetic-set", "excerpt": "x" * 900}])

    def test_limits_excerpt_without_exposing_private_rows(self):
        result = search_local(Search(**self.payload), self.policy, self.index)
        self.assertEqual(500, len(result["results"][0]["excerpt"]))

    def test_denies_visitor_admin_and_server_denied_subjects(self):
        for subject in ["Guest", "Administrator", "denied@example.test"]:
            self.policy["denied_subjects"] = ["denied@example.test"]
            with self.assertRaises(HTTPException):
                search_local(Search(**{**self.payload, "subject": subject}), self.policy, self.index)

    def test_client_scope_cannot_expand(self):
        for change in [{"document_ids": ["unapproved"]}, {"dataset_ids": ["unapproved"]}, {"context": {"equipment_id": "unapproved"}}, {"policy_revision": "stale"}]:
            with self.assertRaises(HTTPException):
                search_local(Search(**{**self.payload, **change}), self.policy, self.index)

    def test_index_scope_violation_fails_closed(self):
        self.index.search = lambda **kw: [{"document_id": "unapproved", "dataset_id": "synthetic-set"}]
        with self.assertRaises(HTTPException) as caught:
            search_local(Search(**self.payload), self.policy, self.index)
        self.assertEqual(502, caught.exception.status_code)
