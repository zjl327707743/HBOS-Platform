"""Fresh, single-use management proofs at the owning request's commit boundary."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import json
import unittest
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.managed_relations import ManagedRelationAdapter
from hbos_portal.organization.management_storage import PinnedPolicyApprovalVerifier
from hbos_portal.organization.storage_schema import ASSIGNMENT, canonical_json, revision_key
from tests import test_managed_relations as managed_fixture
from tests.test_management_storage import pin


class PendingFinalizationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = managed_fixture.ManagedRelationTests("runTest")
        self.fixture.setUp()
        self.proofs = []
        self.fixture.adapter = ManagedRelationAdapter(self.fixture.repo,
            approval_verifier=self.fixture.verifier, pending_observer=self.proofs.append, enabled=True)
        self.fixture.service = self.fixture.make_service()

    def recheck(self, proof=None, service=None):
        f = self.fixture
        with f.store.transaction():
            f.store.lock_writer()
            return f.adapter.recheck_pending(f.service if service is None else service,
                                              self.proofs[-1] if proof is None else proof)

    def assert_code(self, code, action=None):
        f = self.fixture
        before = deepcopy((f.store.masters, f.store.versions, f.store.receipts))
        with self.assertRaises(ContractError) as caught:
            (action or self.recheck)()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual((f.store.masters, f.store.versions, f.store.receipts), before)

    def prepare(self, command="create_assignment", *, replay=False):
        f = self.fixture
        options = dict(idempotency_key=str(uuid4()))
        if command == "create_position":
            payload = f.position_payload()
        elif command == "create_assignment":
            position = f.create_position()
            payload = f.assignment_payload(position.record_id)
        elif command == "update_position":
            first = f.create_position()
            payload = f.position_payload(title="新显示字段")
            options.update(record_id=first.record_id, expected_revision=1)
        else:
            first = f.create_assignment()
            row = f.store.get_master(ASSIGNMENT, first.record_id)
            payload = f.assignment_payload(row["position"], valid_until="2026-10-24T00:00:00Z")
            options.update(record_id=first.record_id, expected_revision=1)
        self.proofs.clear()
        result = f.command(command, payload, **options)
        if replay:
            result = f.command(command, payload, **options)
        return result

    def test_four_commands_and_their_replays_have_fresh_readonly_final_proofs(self):
        for command in ("create_position", "update_position", "create_assignment", "update_assignment"):
            for replay in (False, True):
                with self.subTest(command=command, replay=replay):
                    self.setUp()
                    result = self.prepare(command, replay=replay)
                    f = self.fixture
                    before = deepcopy((f.store.masters, f.store.versions, f.store.receipts))
                    evaluation = self.recheck()
                    self.assertTrue(evaluation.matched)
                    self.assertEqual(evaluation.authorization_effect, "none")
                    self.assertTrue(evaluation.validation_only)
                    self.assertFalse(evaluation.runtime_verified)
                    self.assertTrue(result.transaction_pending)
                    self.assertEqual(result.replayed, replay)
                    self.assertEqual((f.store.masters, f.store.versions, f.store.receipts), before)
                    self.assert_code("PENDING_PROOF_REQUIRED")

    def test_proof_is_immutable_and_copy_cannot_replace_issued_object(self):
        self.prepare()
        proof = self.proofs[-1]
        with self.assertRaises(FrozenInstanceError): proof.actor = "other"
        self.assert_code("PENDING_PROOF_REQUIRED", lambda: self.recheck(replace(proof)))
        self.assertTrue(self.recheck(proof).matched)

    def test_proof_is_bound_to_exact_owning_service(self):
        self.prepare()
        self.assert_code("PENDING_PROOF_REQUIRED", lambda: self.recheck(service=self.fixture.make_service()))
        self.assertTrue(self.recheck().matched)

    def test_superseded_and_explicitly_discarded_proofs_cannot_be_used(self):
        self.prepare("create_position")
        old = self.proofs[-1]
        self.fixture.create_position(title="另一个合成岗位")
        self.assert_code("PENDING_PROOF_REQUIRED", lambda: self.recheck(old))
        self.fixture.adapter.discard_pending()
        self.assert_code("PENDING_PROOF_REQUIRED")

    def test_expiry_at_final_boundary_denies_and_consumes_proof(self):
        self.prepare()
        self.fixture.now = datetime(2026, 11, 1, tzinfo=timezone.utc)
        self.assert_code("NO_MATCHING_POLICY")
        self.assert_code("PENDING_PROOF_REQUIRED")

    def test_revoked_current_policy_head_denies_finalization(self):
        self.prepare()
        f = self.fixture
        f.repo.policies = (replace(f.policy, status="revoked", revision=2, authority_generation=2),)
        self.assert_code("NO_MATCHING_POLICY")

    def test_new_valid_policy_revision_still_requires_entire_request_retry(self):
        self.prepare()
        f = self.fixture
        newer = managed_fixture.managed_policy(revision=2, generation=2)
        f.repo.policies = (newer,)
        f.adapter.verifier = PinnedPolicyApprovalVerifier([pin(newer)])
        self.assert_code("MANAGEMENT_CHANGED_RETRY")

    def test_native_session_identity_change_denies_finalization(self):
        self.prepare()
        self.fixture.store.session.user = "SYNTHETIC-RELINKED"
        self.assert_code("MANAGEMENT_DENIED")

    def test_fresh_sources_changed_after_fact_write_require_retry(self):
        for change in ("employee-link", "account-disabled", "department-disabled"):
            with self.subTest(change=change):
                self.setUp()
                self.prepare()
                rows = self.fixture.rows
                if change == "employee-link": rows["Employee"][0]["user_id"] = "SYNTHETIC-RELINKED"
                elif change == "account-disabled": rows["User"][0]["enabled"] = 0
                else: rows["Department"][1]["disabled"] = 1
                self.assert_code("SOURCE_CHANGED_RETRY")

    def test_new_position_revision_after_fact_write_requires_retry(self):
        result = self.prepare()
        f = self.fixture
        position = f.store.get_master(ASSIGNMENT, result.record_id)["position"]
        other_adapter = ManagedRelationAdapter(f.repo, approval_verifier=f.verifier, enabled=True)
        other_service = f.make_service(management_adapter=other_adapter)
        f.command("update_position", f.position_payload(title="另一办理更新"), service=other_service,
                  record_id=position, expected_revision=1)
        self.assert_code("SOURCE_CHANGED_RETRY")

    def test_new_assignment_revision_after_fact_write_requires_retry(self):
        result = self.prepare()
        f = self.fixture
        other_adapter = ManagedRelationAdapter(f.repo, approval_verifier=f.verifier, enabled=True)
        other_service = f.make_service(management_adapter=other_adapter)
        f.update_assignment(result.record_id, service=other_service, valid_until="2026-10-23T00:00:00Z")
        self.assert_code("SOURCE_CHANGED_RETRY")

    def test_receipt_change_and_anchored_history_change_are_rejected(self):
        for change in ("receipt", "history"):
            with self.subTest(change=change):
                self.setUp()
                result = self.prepare()
                f = self.fixture
                proof = self.proofs[-1]
                if change == "receipt":
                    f.store.receipts[proof.receipt_key]["result"]["revision"] = 2
                else:
                    history = f.store.versions[revision_key(ASSIGNMENT, result.record_id, 1)]
                    evidence = json.loads(history["source_evidence_json"])
                    evidence["current_source_digest"] = "0" * 64
                    history["source_evidence_json"] = canonical_json(evidence)
                self.assert_code("HISTORY_MISMATCH")

    def test_final_check_requires_same_root_lock_and_failed_check_consumes_proof(self):
        self.prepare()
        f = self.fixture
        self.assert_code("SOURCE_TRANSACTION_REQUIRED", lambda: f.adapter.recheck_pending(f.service, self.proofs[-1]))
        self.assert_code("PENDING_PROOF_REQUIRED")

    def test_actual_native_database_replacement_is_detected_even_if_proxy_is_stable(self):
        f = self.fixture
        original_native = f.repo.native
        database = [object()]
        stable_proxy = object()
        def native():
            current = original_native()
            current.local.db = database[0]
            current.db = stable_proxy
            return current
        f.repo.native = native
        self.prepare()
        database[0] = object()
        self.assert_code("MANAGEMENT_CONTEXT_MISMATCH")
        self.assert_code("PENDING_PROOF_REQUIRED")


if __name__ == "__main__":
    unittest.main()
