from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
# This module retains the original P1 transport assertions unchanged.
# The new candidate requires tickets and is covered by test_gateway_boundary and K1C2 replay.
from .legacy_p1.gateway import GatewayClient, filter_authorized_results
from hb_knowledge_app.hb_knowledge.import_manifest import ManifestError, build_manifest, main
from hb_knowledge_app.hb_knowledge.policy import policy_for_subject
from hb_knowledge_app.hb_knowledge.portal.manifest import get_manifest


VALID_CONFIG = {
    "subjects": {
        "pilot@example.test": {
            "enabled": True,
            "capabilities": ["knowledge.search"],
            "dataset_ids": ["ds-a"],
            "document_ids": ["doc-a"],
            "policy_revision": "policy-test-1",
        }
    }
}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class KnowledgePolicyTest(unittest.TestCase):
    def test_unknown_and_guest_subjects_are_default_deny(self):
        self.assertFalse(policy_for_subject(VALID_CONFIG, "unknown@example.test").can_enter)
        self.assertFalse(policy_for_subject(VALID_CONFIG, "Guest").can_enter)

    def test_empty_document_scope_cannot_search(self):
        config = {
            "subjects": {
                "pilot@example.test": {
                    "enabled": True,
                    "capabilities": ["knowledge.search"],
                    "dataset_ids": ["ds-a"],
                    "document_ids": [],
                }
            }
        }
        policy = policy_for_subject(config, "pilot@example.test")
        self.assertFalse(policy.can_search)
        with self.assertRaisesRegex(KnowledgeError, "当前没有"):
            policy.require_search()

    def test_default_internal_policy_allows_non_pilot_but_not_ineligible_account(self):
        config = {
            "default_internal": {
                "enabled": True,
                "capabilities": ["knowledge.search"],
                "dataset_ids": ["ds-a"],
                "document_ids": ["doc-a"],
                "policy_revision": "internal-v1",
            },
            "subjects": {},
        }
        self.assertTrue(
            policy_for_subject(
                config,
                "employee@example.test",
                internal_user=True,
            ).can_search
        )
        self.assertFalse(
            policy_for_subject(
                config,
                "external@example.test",
                internal_user=False,
            ).can_enter
        )

    def test_explicit_administrator_scope_does_not_depend_on_internal_default(self):
        config = {
            "default_internal": {"enabled": False},
            "subjects": {
                "Administrator": {
                    "enabled": True,
                    "capabilities": ["knowledge.search"],
                    "dataset_ids": ["ds-a"],
                    "document_ids": ["doc-a"],
                }
            },
        }
        self.assertTrue(
            policy_for_subject(
                config,
                "Administrator",
                internal_user=False,
            ).can_search
        )

    def test_manifest_does_not_publish_portal_search_capability(self):
        manifest = get_manifest()
        self.assertEqual("/hbos/knowledge", manifest["route"])
        self.assertEqual([], manifest["capabilities"])


class KnowledgeGatewayTest(unittest.TestCase):
    def test_filters_are_sent_before_upstream_call(self):
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse(
                {
                    "results": [
                        {
                            "document_id": "doc-a",
                            "dataset_id": "ds-a",
                            "version": "1",
                            "title": "Approved source",
                            "status_note": "现行状态待核",
                            "section": "2.1",
                            "page_number": 3,
                            "excerpt": "approved evidence",
                            "score": 0.99,
                            "path": "/private/source.pdf",
                        }
                    ]
                }
            )

        policy = policy_for_subject(VALID_CONFIG, "pilot@example.test")
        client = GatewayClient(
            endpoint="http://gateway.test",
            token="server-token",
            client_id="hbos-pilot",
            post=post,
        )
        records = client.search(query="question", policy=policy, limit=5, request_id="req-1")

        body = calls[0][1]["json"]
        self.assertEqual(["ds-a"], body["dataset_ids"])
        self.assertEqual(["doc-a"], body["document_ids"])
        self.assertEqual("pilot@example.test", body["subject"])
        self.assertEqual("approved evidence", records[0].excerpt)
        self.assertEqual("Approved source", records[0].title)
        self.assertEqual("现行状态待核", records[0].status_note)
        self.assertEqual(3, records[0].page_number)
        self.assertFalse(hasattr(records[0], "path"))

    def test_equipment_context_is_forwarded_as_structured_data(self):
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse({"results": []})

        policy = policy_for_subject(VALID_CONFIG, "pilot@example.test")
        client = GatewayClient(
            endpoint="http://gateway.test",
            token="server-token",
            client_id="hbos-pilot",
            post=post,
        )
        client.search(
            query="维护要求",
            policy=policy,
            limit=5,
            request_id="req-equipment",
            context={"equipment_id": "M607B"},
        )

        body = calls[0][1]["json"]
        self.assertEqual({"equipment_id": "M607B"}, body["context"])
        self.assertEqual("维护要求", body["query"])

    def test_empty_scope_never_calls_upstream(self):
        called = False

        def post(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("upstream must not be called")

        policy = policy_for_subject(
            {
                "subjects": {
                    "pilot@example.test": {
                        "enabled": True,
                        "capabilities": ["knowledge.search"],
                        "dataset_ids": ["ds-a"],
                        "document_ids": [],
                    }
                }
            },
            "pilot@example.test",
        )
        client = GatewayClient(
            endpoint="http://gateway.test",
            token="server-token",
            client_id="hbos-pilot",
            post=post,
        )
        with self.assertRaises(KnowledgeError):
            client.search(query="question", policy=policy, limit=5, request_id="req-1")
        self.assertFalse(called)

    def test_unauthorized_upstream_hit_fails_closed(self):
        policy = policy_for_subject(VALID_CONFIG, "pilot@example.test")
        with self.assertRaisesRegex(KnowledgeError, "权限校验失败"):
            filter_authorized_results(
                {"results": [{"document_id": "doc-b", "dataset_id": "ds-a", "excerpt": "leak"}]},
                policy,
                limit=5,
            )

    def test_upstream_hit_without_dataset_id_fails_closed(self):
        policy = policy_for_subject(VALID_CONFIG, "pilot@example.test")
        with self.assertRaisesRegex(KnowledgeError, "权限校验失败"):
            filter_authorized_results(
                {"results": [{"document_id": "doc-a", "excerpt": "missing dataset"}]},
                policy,
                limit=5,
            )

    def test_excerpt_is_capped_to_500_codepoints(self):
        policy = policy_for_subject(VALID_CONFIG, "pilot@example.test")
        records = filter_authorized_results(
            {"results": [{"document_id": "doc-a", "dataset_id": "ds-a", "excerpt": "知" * 700}]},
            policy,
            limit=5,
        )
        self.assertEqual(500, len(records[0].excerpt))


class ImportManifestTest(unittest.TestCase):
    def test_requires_explicit_selection_and_hashes_only_selected_file(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            selected = root_path / "approved.pdf"
            selected.write_bytes(b"approved")
            (root_path / "not-selected.pdf").write_bytes(b"not selected")

            with self.assertRaises(ManifestError):
                build_manifest(root, [])

            manifest = build_manifest(root, ["approved.pdf"])
            self.assertEqual(1, manifest["item_count"])
            self.assertEqual("approved.pdf", manifest["items"][0]["relative_path"])
            self.assertNotIn(str(root_path), str(manifest))

    def test_rejects_traversal_symlink_and_secret_files(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            root_path = Path(root)
            outside_file = Path(outside) / "outside.pdf"
            outside_file.write_bytes(b"outside")
            (root_path / "link.pdf").symlink_to(outside_file)
            (root_path / ".env").write_text("SECRET=value", encoding="utf-8")

            for selection in ("../outside.pdf", "link.pdf", ".env"):
                with self.subTest(selection=selection):
                    with self.assertRaises(ManifestError):
                        build_manifest(root, [selection])

    def test_private_manifest_output_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as output_root:
            root_path = Path(root)
            (root_path / "approved.pdf").write_bytes(b"approved")
            target = Path(output_root) / "target.json"
            target.write_text("preserve", encoding="utf-8")
            output = Path(output_root) / "manifest.json"
            output.symlink_to(target)

            with self.assertRaises(ManifestError):
                main([
                    "--root", root,
                    "--select", "approved.pdf",
                    "--output", str(output),
                ])
            self.assertEqual("preserve", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
