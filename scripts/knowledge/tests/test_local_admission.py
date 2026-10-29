from __future__ import annotations

import importlib.util
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "local_admission.py"
SPEC = importlib.util.spec_from_file_location("local_admission", MODULE_PATH)
admission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admission)


def source(alias="hr", name="policy.txt", sha="a" * 64):
    return {"root_alias": alias, "relative_path": name, "source_sha256": sha, "size_bytes": 7, "extension": ".txt"}


def reviewed(sha="a" * 64):
    return {"source_sha256": sha, "decision": "ADMIT_INTERNAL_REFERENCE", "actual_content_checked": True, "extraction_complete": True, "internal_sharing_applicable": True, "external_processing_applicable": True, "review_evidence_sha256": "b" * 64, "sensitive_flags": []}


def plan(files, *, reviews=None, registry=(), datasets=(), relations=None):
    return admission.build_plan({"files": files}, reviews if reviews is not None else {"a" * 64: reviewed()}, registry, {"hr": "human_resources", "safety": "safety"}, datasets, batch_name="synthetic", version_relations=relations)


class DiscoveryTests(unittest.TestCase):
    def test_file_and_directory_symlinks_never_read_outside(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            root = base / "root"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            (outside / "sensitive.txt").write_text("private")
            (root / "link").symlink_to(outside, target_is_directory=True)
            (root / "alias.txt").symlink_to(outside / "sensitive.txt")
            (root / "general.txt").write_text("synthetic policy")
            receipt = admission.discover({"hr": root})
            self.assertEqual(["general.txt"], [r["relative_path"] for r in receipt["files"]])
            self.assertEqual(2, len(receipt["excluded_entries"]))

    def test_symlink_root_and_symlink_ancestor_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            real = base / "real"
            real.mkdir()
            (real / "child").mkdir()
            alias = base / "alias"
            alias.symlink_to(real, target_is_directory=True)
            for root in (alias, alias / "child"):
                with self.assertRaises(admission.AdmissionError):
                    admission.discover({"hr": root})

    def test_overlapping_roots_rejected_and_sources_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            child = root / "child"
            child.mkdir()
            original = child / "test.txt"
            original.write_bytes(b"untrusted content with shell commands")
            before = original.stat()
            admission.discover({"hr": child})
            after = original.stat()
            self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))
            with self.assertRaises(admission.AdmissionError):
                admission.discover({"hr": root, "safety": child})

    def test_directory_swap_during_hash_cannot_redirect_source_read(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            root = base / "root"
            root.mkdir()
            child = root / "child"
            child.mkdir()
            (child / "policy.txt").write_bytes(b"synthetic allowed")
            outside = base / "outside"
            outside.mkdir()
            (outside / "policy.txt").write_bytes(b"private outside")
            original_hash = admission._hash_regular_file
            def swap(name, metadata, directory_fd):
                child.rename(root / "held-original")
                child.symlink_to(outside, target_is_directory=True)
                return original_hash(name, metadata, directory_fd)
            with patch.object(admission, "_hash_regular_file", side_effect=swap):
                receipt = admission.discover({"hr": root})
            import hashlib
            self.assertEqual(hashlib.sha256(b"synthetic allowed").hexdigest(), receipt["files"][0]["source_sha256"])


class AdmissionIdentityTests(unittest.TestCase):
    def test_missing_mismatched_incomplete_and_sensitive_reviews_fail_closed(self):
        variants = ({}, {"a" * 64: reviewed("c" * 64)}, {"a" * 64: {**reviewed(), "extraction_complete": False}}, {"a" * 64: {**reviewed(), "sensitive_flags": ["PERSONAL_DATA"]}}, {"a" * 64: {**reviewed(), "external_processing_applicable": False}})
        for reviews in variants:
            item = plan([source()], reviews=reviews)["items"][0]
            self.assertEqual("QUARANTINE", item["admission_decision"])
            self.assertEqual("PROHIBITED_LOCAL_QUARANTINE", item["upload_action"])

    def test_renamed_existing_content_reuses_exact_identity_without_publishing(self):
        registry = [{"sha256": "a" * 64, "canonical_document_id": "existing", "version_id": "version-1", "relative_path": "old.txt", "department_key": "human_resources", "status": "Withdrawn", "dataset_id": "ds-old"}]
        result = plan([source(name="moved.txt")], registry=registry)
        item = result["items"][0]
        self.assertEqual(("existing", "version-1", "SKIP_EXISTING_CONTENT"), (item["canonical_document_id"], item["version_id"], item["upload_action"]))
        self.assertEqual(["Withdrawn"], item["existing_states"])
        self.assertEqual(0, result["summary"]["published"])
        self.assertEqual("Withdrawn", registry[0]["status"])

    def test_cross_department_identical_bytes_upload_once_and_keep_alias(self):
        result = plan([source(), source(alias="safety", name="renamed.txt")])
        first, second = result["items"]
        self.assertEqual(first["canonical_document_id"], second["canonical_document_id"])
        self.assertEqual("SKIP_DUPLICATE_IN_PLAN", second["upload_action"])
        self.assertEqual("safety", second["department_key"])
        self.assertEqual(1, result["summary"]["new_unique_admitted"])

    def test_same_filename_changed_bytes_does_not_overwrite_old_identity(self):
        registry = [{"sha256": "c" * 64, "canonical_document_id": "existing", "version_id": "old-version", "relative_path": "policy.txt", "department_key": "human_resources"}]
        item = plan([source()], registry=registry)["items"][0]
        self.assertEqual("CHANGED_CONTENT_REQUIRES_VERSION_RELATION", item["reason_code"])
        self.assertEqual("QUARANTINE", item["admission_decision"])
        self.assertEqual("old-version", registry[0]["version_id"])

    def test_explicit_new_version_preserves_canonical_and_requires_exact_hash(self):
        registry = [{"sha256": "c" * 64, "canonical_document_id": "existing", "version_id": "old-version", "relative_path": "policy.txt", "department_key": "human_resources"}]
        relation = {"hr:policy.txt": {"canonical_document_id": "existing", "expected_current_version": "old-version", "source_sha256": "a" * 64}}
        item = plan([source()], registry=registry, relations=relation)["items"][0]
        self.assertEqual("existing", item["canonical_document_id"])
        self.assertNotEqual("old-version", item["version_id"])
        self.assertEqual("NEW_VERSION_AFTER_GATES", item["upload_action"])
        relation["hr:policy.txt"]["source_sha256"] = "d" * 64
        self.assertEqual("QUARANTINE", plan([source()], registry=registry, relations=relation)["items"][0]["admission_decision"])

    def test_conflicting_existing_content_identities_quarantine(self):
        registry = [{"sha256": "a" * 64, "canonical_document_id": "one", "version_id": "v"}, {"sha256": "a" * 64, "canonical_document_id": "two", "version_id": "v"}]
        self.assertEqual("EXISTING_CONTENT_IDENTITY_CONFLICT", plan([source()], registry=registry)["items"][0]["reason_code"])

    def test_same_new_content_for_distinct_existing_identities_quarantines_entire_group(self):
        registry = [
            {"sha256": "c" * 64, "canonical_document_id": "existing-a", "version_id": "current-a"},
            {"sha256": "d" * 64, "canonical_document_id": "existing-b", "version_id": "current-b"},
        ]
        relations = {
            "hr:policy.txt": {"canonical_document_id": "existing-a", "expected_current_version": "current-a", "source_sha256": "a" * 64},
            "safety:policy.txt": {"canonical_document_id": "existing-b", "expected_current_version": "current-b", "source_sha256": "a" * 64},
        }
        files = [source(), source(alias="safety"), source(name="third.txt")]
        for ordered_files in (files, list(reversed(files))):
            result = plan(ordered_files, registry=registry, relations=relations)
            by_input = {(i["root_alias"], i["relative_path"]): i for i in result["items"]}
            for key, canonical, current in ((('hr', 'policy.txt'), 'existing-a', 'current-a'), (('safety', 'policy.txt'), 'existing-b', 'current-b')):
                item = by_input[key]
                self.assertEqual((canonical, current), (item["canonical_document_id"], item["expected_current_version"]))
            for item in result["items"]:
                self.assertEqual("QUARANTINE", item["admission_decision"])
                self.assertEqual("BATCH_CONTENT_VERSION_IDENTITY_CONFLICT", item["reason_code"])
                self.assertEqual("PROHIBITED_LOCAL_QUARANTINE", item["upload_action"])
                self.assertNotIn("classification_alias_of", item)
            self.assertEqual(0, result["summary"]["new_unique_admitted"])

    def test_same_explicit_identity_and_predecessor_can_keep_content_alias(self):
        registry = [{"sha256": "c" * 64, "canonical_document_id": "existing", "version_id": "current"}]
        relation = {"canonical_document_id": "existing", "expected_current_version": "current", "source_sha256": "a" * 64}
        result = plan([source(), source(alias="safety")], registry=registry, relations={"hr:policy.txt": relation, "safety:policy.txt": relation})
        first, second = result["items"]
        self.assertEqual("NEW_VERSION_AFTER_GATES", first["upload_action"])
        self.assertEqual("SKIP_DUPLICATE_IN_PLAN", second["upload_action"])
        self.assertEqual(("existing", "current"), (second["canonical_document_id"], second["expected_current_version"]))
        self.assertEqual(1, result["summary"]["new_unique_admitted"])

    def test_old_version_relation_cannot_claim_current_without_current_export(self):
        registry = [{"sha256": "c" * 64, "canonical_document_id": "existing", "version_id": "old-version"}, {"sha256": "d" * 64, "canonical_document_id": "existing", "version_id": "current-version"}]
        relation = {"hr:policy.txt": {"canonical_document_id": "existing", "expected_current_version": "old-version", "source_sha256": "a" * 64}}
        self.assertEqual("QUARANTINE", plan([source()], registry=registry, relations=relation)["items"][0]["admission_decision"])

    def test_ambiguous_dataset_never_picks_first(self):
        datasets = [{"department_key": "human_resources", "dataset_id": "ds-one"}, {"department_key": "human_resources", "dataset_id": "ds-two"}]
        item = plan([source()], datasets=datasets)["items"][0]
        self.assertEqual("DATASET_MAPPING_AMBIGUOUS", item["reason_code"])
        self.assertIsNone(item["target_dataset_id"])

    def test_frozen_plan_keeps_quarantined_items_and_is_replay_stable(self):
        files = [source(), source(name="personal.txt", sha="c" * 64)]
        first = plan(files)
        second = plan(files)
        self.assertEqual(2, len(first["items"]))
        self.assertEqual(1, first["summary"]["quarantined_paths"])
        self.assertEqual(first["batch_sha256"], second["batch_sha256"])
        self.assertEqual(0, first["summary"]["uploaded"])

    def test_duplicate_paths_and_unsafe_paths_rejected(self):
        for files in ([source(), source()], [source(name="../escape.txt")]):
            with self.assertRaises(admission.AdmissionError):
                plan(files)


class PrivateFrozenOutputTests(unittest.TestCase):
    def test_private_modes_identical_noop_and_conflicting_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            root.chmod(0o700)
            output = root / "frozen.json"
            self.assertEqual("CREATED", admission.write_private_frozen_json(output, {"count": 1}))
            self.assertEqual(0o600, output.stat().st_mode & 0o777)
            self.assertEqual("NOOP", admission.write_private_frozen_json(output, {"count": 1}))
            with self.assertRaises(admission.AdmissionError):
                admission.write_private_frozen_json(output, {"count": 2})

    def test_broad_directory_and_symlink_output_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            output = root / "frozen.json"
            root.chmod(0o755)
            with self.assertRaises(admission.AdmissionError):
                admission.write_private_frozen_json(output, {})
            root.chmod(0o700)
            target = root / "target.json"
            target.write_text("{}")
            output.symlink_to(target)
            with self.assertRaises(admission.AdmissionError):
                admission.write_private_frozen_json(output, {})


if __name__ == "__main__":
    unittest.main()
