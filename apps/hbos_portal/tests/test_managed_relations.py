"""Managed fact writes against synthetic locked sources and immutable history.

This exercises the policy/service boundary without a Frappe Site or database.
Native MariaDB serialization is covered by a separate acceptance program.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.management_policy import management_policy_digest, parse_management_policy
from hbos_portal.organization.management_storage import (
    POLICY_PROVIDER, PinnedPolicyApprovalVerifier,
)
from hbos_portal.organization.managed_relations import ManagedRelationAdapter
from hbos_portal.organization.relation_service import RelationService
from hbos_portal.organization.source_adapter import decode_utc_datetime
from hbos_portal.organization.storage_schema import ASSIGNMENT, POSITION, canonical_json, digest, revision_key
from tests.test_management_policy import policy_payload, rule
from tests.test_management_storage import DB_HASH, pin
from tests.test_organization_relation_service import ACTOR, TransactionalTestStore
from tests.test_organization_source_adapter import STAMP, snapshot, sources


APPROVER = "SYNTHETIC-OWNER"
TARGET_USER = "SYNTHETIC-USER"
NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


def managed_policy(*, rules=None, revision=1, generation=1, subject=ACTOR):
    operations = ["hbos.organization." + name for name in (
        "position.create", "position.update", "assignment.create", "assignment.update")]
    selected = [rule(operation_ids=operations, company_id="COMPANY-A",
        person_scope=dict(source_type="Employee", company_id="COMPANY-A", department_ids=["DEPT-A"]))]
    raw = policy_payload(subject_user=subject, revision=revision, authority_generation=generation,
                         rules=selected if rules is None else rules)
    policy = parse_management_policy(raw, site_id="synthetic-site", source_provider=POLICY_PROVIDER)
    raw["approval"] = dict(approval_ref="SYNTHETIC-APPROVAL", approved_by=APPROVER,
        approved_at_utc="2026-10-09T00:00:00Z", approved_revision=revision,
        approved_authority_generation=generation, content_digest=management_policy_digest(policy))
    return parse_management_policy(raw, site_id="synthetic-site", source_provider=POLICY_PROVIDER)


class ManagedTestStore(TransactionalTestStore):
    """Tracks the same-root capability, not native database locking semantics."""
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.locked = False
        self.session = SimpleNamespace(user=ACTOR)

    @contextmanager
    def transaction(self):
        with super().transaction():
            self.depth += 1
            try:
                yield
            finally:
                self.depth -= 1
                if self.depth == 0:
                    self.locked = False

    def lock_writer(self):
        if self.depth == 0:
            raise ContractError("SOURCE_TRANSACTION_REQUIRED", "test.root")
        self.locked = True

    def require_locked_source_context(self):
        if self.depth == 0 or not self.locked:
            raise ContractError("SOURCE_TRANSACTION_REQUIRED", "test.root")
        return SimpleNamespace(local=SimpleNamespace(site=self.site_id), session=self.session)

    def get_revision(self, kind, identifier, revision):
        self.require_locked_source_context()
        row = self.versions.get(revision_key(kind, identifier, revision))
        if row is None:
            raise ContractError("HISTORICAL_SCOPE_REQUIRED", "revision")
        return deepcopy(row)


class ManagedTestPolicyRepository:
    enabled = True
    expected_site = "synthetic-site"
    expected_database_sha256 = DB_HASH

    def __init__(self, relations, policies):
        self.relations = relations
        self.policies = tuple(policies)
        self.read_count = 0
        self.after_read = None

    def native(self):
        return self.relations.require_locked_source_context()

    def current_for_subject(self, subject):
        self.native()
        result = tuple(policy for policy in self.policies if policy.subject_user == subject)
        self.read_count += 1
        if self.after_read is not None:
            self.after_read(self.read_count)
        return result


class ManagedRelationTests(unittest.TestCase):
    def setUp(self):
        self.rows = sources()
        for user in (ACTOR, APPROVER, "SYNTHETIC-RELINKED"):
            self.rows["User"].append(dict(name=user, enabled=1, user_type="System User", modified=STAMP))
        self.store = ManagedTestStore()
        self.policy = managed_policy()
        self.repo = ManagedTestPolicyRepository(self.store, [self.policy])
        self.now = NOW
        self.verifier = PinnedPolicyApprovalVerifier([pin(self.policy)])
        self.adapter = ManagedRelationAdapter(self.repo, approval_verifier=self.verifier, enabled=True)
        self.service = self.make_service()

    def make_service(self, **changes):
        options = dict(actor_resolver=lambda: ACTOR, source_loader=lambda: snapshot(self.rows),
            clock=lambda: self.now, management_adapter=self.adapter, enabled=True)
        options.update(changes)
        return RelationService(self.store, **options)

    def command(self, name, payload, *, service=None, **changes):
        options = dict(idempotency_key=str(uuid4()), expected_revision=0 if name.startswith("create_") else 1,
                       reason="合成管理政策写入验收")
        options.update(changes)
        return (service or self.service).execute(name, payload, **options)

    @staticmethod
    def position_payload(**changes):
        payload = dict(title="合成岗位", company="COMPANY-A", department="DEPT-A", designation="TYPE-A", status="active")
        payload.update(changes)
        return payload

    @staticmethod
    def assignment_payload(position, **changes):
        payload = dict(person_source_type="Employee", person_source_id="SYNTHETIC-EMP", position=position,
            is_primary=True, valid_from="2026-10-10T00:00:00Z", valid_until="2026-10-25T00:00:00Z", status="active")
        payload.update(changes)
        return payload

    def create_position(self, **changes):
        return self.command("create_position", self.position_payload(**changes))

    def create_assignment(self, **changes):
        position = self.create_position()
        return self.command("create_assignment", self.assignment_payload(position.record_id, **changes))

    def update_position(self, identifier, **changes):
        old = self.store.get_master(POSITION, identifier)
        payload = {key: old[key] for key in ("title", "company", "department", "designation", "status")}
        payload.update(changes)
        return self.command("update_position", payload, record_id=identifier, expected_revision=old["revision"])

    def update_assignment(self, identifier, *, service=None, **changes):
        old = self.store.get_master(ASSIGNMENT, identifier)
        payload = {key: old[key] for key in ("person_source_type", "person_source_id", "position", "is_primary", "status")}
        payload["valid_from"] = decode_utc_datetime(old["valid_from_utc"]).isoformat()
        payload["valid_until"] = None if old["valid_until_utc"] is None else decode_utc_datetime(old["valid_until_utc"]).isoformat()
        payload.update(changes)
        return self.command("update_assignment", payload, service=service, record_id=identifier, expected_revision=old["revision"])

    def assert_code(self, code, action):
        before = deepcopy((self.store.masters, self.store.versions, self.store.receipts))
        with self.assertRaises(ContractError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual((self.store.masters, self.store.versions, self.store.receipts), before)

    def install_policy(self, policy):
        self.policy = policy
        self.repo.policies = (policy,)
        self.verifier = PinnedPolicyApprovalVerifier([pin(policy)])
        self.adapter = ManagedRelationAdapter(self.repo, approval_verifier=self.verifier, enabled=True)
        self.service = self.make_service()

    def test_complete_policy_writes_fact_history_without_grant_effect(self):
        result = self.create_assignment()
        self.assertEqual((result.revision, result.authorization_generation), (1, 1))
        self.assertEqual(result.authorization_effect, "none")
        self.assertTrue(result.transaction_pending)
        self.assertFalse(result.runtime_verified)
        history = deepcopy(self.store.versions[revision_key(ASSIGNMENT, result.record_id, 1)])
        evidence = json.loads(history["source_evidence_json"])
        self.assertIn("management_scope_v1", evidence)
        self.assertEqual(self.store.get_master(ASSIGNMENT, result.record_id)["subject_user"], TARGET_USER)
        self.assertGreaterEqual(self.repo.read_count, 4)

    def test_long_match_evidence_uses_schema_sized_reference_without_truncation(self):
        long_rule, long_approval = "R" * 140, "A" * 140
        candidate = managed_policy(rules=[rule(rule_id=long_rule,
            operation_ids=["hbos.organization." + name for name in (
                "position.create", "position.update", "assignment.create", "assignment.update")],
            company_id="COMPANY-A", person_scope=dict(source_type="Employee", company_id="COMPANY-A",
                                                       department_ids=["DEPT-A"]))])
        candidate = replace(candidate, approval=replace(candidate.approval, approval_ref=long_approval))
        self.install_policy(candidate)
        result = self.create_assignment()
        position = self.store.get_master(ASSIGNMENT, result.record_id)["position"]
        schemas = Path(__file__).resolve().parents[1] / "hbos_portal/hbos_portal/doctype"
        for kind, identifier in ((POSITION, position), (ASSIGNMENT, result.record_id)):
            with self.subTest(kind=kind):
                slug = (kind + " Revision").lower().replace(" ", "_")
                schema = json.loads((schemas / slug / (slug + ".json")).read_text())
                field = next(item for item in schema["fields"] if item["fieldname"] == "policy_ref")
                self.assertEqual(field["fieldtype"], "Data")
                capacity = field.get("length") or 140  # Existing native Data default.
                history = self.store.versions[revision_key(kind, identifier, 1)]
                evidence = json.loads(history["source_evidence_json"])
                match = evidence["management_match"]["match"]
                self.assertEqual(match["rule_id"], long_rule)
                self.assertEqual(match["approval_ref"], long_approval)
                self.assertEqual(match["policy_digest"], management_policy_digest(candidate))
                self.assertGreater(len(canonical_json(match)), capacity)
                self.assertEqual(history["policy_ref"], "management-match-v1:" + digest(match))
                self.assertLessEqual(len(history["policy_ref"]), capacity)
                self.assertLessEqual(len(history["policy_ref"]), 140)
                self.assertEqual(json.loads(history["snapshot_json"])["_management_evidence_digest"], digest(evidence))

    def test_default_closed_adapter_does_not_write(self):
        adapter = ManagedRelationAdapter(self.repo, approval_verifier=self.verifier)
        self.assert_code("MANAGEMENT_ADAPTER_DISABLED", lambda: self.command("create_position", self.position_payload(),
            service=self.make_service(management_adapter=adapter)))

    def test_exact_native_session_cannot_be_replaced_by_actor_resolver(self):
        self.store.session.user = "SYNTHETIC-RELINKED"
        self.assert_code("MANAGEMENT_DENIED", self.create_position)

    def test_policy_repository_must_share_relation_root(self):
        repo = ManagedTestPolicyRepository(ManagedTestStore(), [self.policy])
        adapter = ManagedRelationAdapter(repo, approval_verifier=self.verifier, enabled=True)
        self.assert_code("MANAGEMENT_CONTEXT_MISMATCH", lambda: self.command("create_position", self.position_payload(),
            service=self.make_service(management_adapter=adapter)))

    def test_approval_pin_is_required_for_active_policy(self):
        self.adapter = ManagedRelationAdapter(self.repo, enabled=True)
        self.service = self.make_service()
        self.assert_code("POLICY_APPROVAL_REQUIRED", self.create_position)

    def test_unknown_client_fields_cannot_inject_management_context(self):
        for key, value in (("actor_user", ACTOR), ("approved", True), ("policy_id", self.policy.policy_id),
                           ("management_scope_v1", {}), ("subject_user", TARGET_USER)):
            with self.subTest(field=key):
                payload = self.position_payload(**{key: value})
                self.assert_code("INVALID_FIELDS", lambda: self.command("create_position", payload))

    def test_self_assignment_create_cannot_benefit_manager(self):
        position = self.create_position()
        self.rows["Employee"][0]["user_id"] = ACTOR
        self.assert_code("SELF_BENEFIT_DENIED", lambda: self.command("create_assignment", self.assignment_payload(position.record_id)))

    def test_duration_cap_and_finite_limit_apply_to_create(self):
        position = self.create_position()
        for end in (None, "2026-11-01T00:00:00Z"):
            with self.subTest(end=end):
                self.assert_code("ASSIGNMENT_LIMIT_REQUIRED" if end is None else "NO_MATCHING_POLICY",
                    lambda: self.command("create_assignment", self.assignment_payload(position.record_id, valid_until=end)))

    def test_rule_action_and_scope_cannot_be_borrowed_across_rules(self):
        self.install_policy(managed_policy(rules=[
            rule(operation_ids=["hbos.organization.position.create"], company_id="COMPANY-A",
                 target_department_ids=["DEPT-B"], person_scope=None, assignment_until_limit_utc=None),
            rule(rule_id="second", operation_ids=["hbos.organization.position.update"], company_id="COMPANY-A",
                 target_department_ids=["DEPT-A"], person_scope=None, assignment_until_limit_utc=None)]))
        self.assert_code("NO_MATCHING_POLICY", self.create_position)

    def test_replay_requires_current_policy_head_after_revocation(self):
        key = str(uuid4())
        payload = self.position_payload()
        first = self.command("create_position", payload, idempotency_key=key)
        replay = self.command("create_position", payload, idempotency_key=key)
        self.assertEqual(replay.record_id, first.record_id)
        self.assertTrue(replay.replayed)
        self.repo.policies = (replace(self.policy, status="revoked", revision=2, authority_generation=2),)
        self.assert_code("NO_MATCHING_POLICY", lambda: self.command("create_position", payload, idempotency_key=key))

    def test_assignment_create_replay_is_stable_after_later_update(self):
        position = self.create_position()
        key = str(uuid4())
        payload = self.assignment_payload(position.record_id)
        first = self.command("create_assignment", payload, idempotency_key=key)
        self.update_assignment(first.record_id, valid_until="2026-10-24T00:00:00Z")
        replay = self.command("create_assignment", payload, idempotency_key=key)
        self.assertTrue(replay.replayed)
        self.assertEqual((replay.record_id, replay.revision), (first.record_id, 1))
        self.assertEqual(self.store.get_master(ASSIGNMENT, first.record_id)["revision"], 2)

    def test_assignment_update_replay_uses_original_before_after_history(self):
        first = self.create_assignment()
        key = str(uuid4())
        payload = self.assignment_payload(self.store.get_master(ASSIGNMENT, first.record_id)["position"],
                                          valid_until="2026-10-24T00:00:00Z")
        updated = self.command("update_assignment", payload, record_id=first.record_id,
                               expected_revision=1, idempotency_key=key)
        self.update_assignment(first.record_id, valid_until="2026-10-23T00:00:00Z")
        replay = self.command("update_assignment", payload, record_id=first.record_id,
                              expected_revision=1, idempotency_key=key)
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.revision, updated.revision)
        self.assertEqual(self.store.get_master(ASSIGNMENT, first.record_id)["revision"], 3)

    def test_changed_payload_with_same_idempotency_key_is_conflict(self):
        key = str(uuid4())
        self.command("create_position", self.position_payload(), idempotency_key=key)
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.command("create_position",
            self.position_payload(title="不同事实"), idempotency_key=key))

    def test_fresh_clock_expiry_between_checks_rolls_back_everything(self):
        expiry = datetime(2026, 11, 1, tzinfo=timezone.utc)
        service = self.make_service(clock=lambda: NOW if self.repo.read_count < 2 else expiry)
        self.assert_code("NO_MATCHING_POLICY", lambda: self.command("create_position", self.position_payload(), service=service))

    def test_expiry_after_fact_write_rolls_back_history_and_receipt(self):
        expiry = datetime(2026, 11, 1, tzinfo=timezone.utc)
        service = self.make_service(clock=lambda: expiry if self.store.receipts else NOW)
        self.assert_code("NO_MATCHING_POLICY", lambda: self.command("create_position", self.position_payload(), service=service))

    def test_changed_policy_generation_between_checks_requires_retry(self):
        newer = managed_policy(revision=2, generation=2)
        verifier = PinnedPolicyApprovalVerifier([pin(self.policy), pin(newer)])
        adapter = ManagedRelationAdapter(self.repo, approval_verifier=verifier, enabled=True)
        self.repo.after_read = lambda count: setattr(self.repo, "policies", (newer,)) if count == 1 else None
        self.assert_code("MANAGEMENT_CHANGED_RETRY", lambda: self.command("create_position", self.position_payload(),
            service=self.make_service(management_adapter=adapter)))

    def test_current_source_change_between_checks_rejects_before_write(self):
        count = 0
        def load():
            nonlocal count
            count += 1
            if count == 2:
                self.rows["User"][0]["enabled"] = 0
            return snapshot(self.rows)
        self.assert_code("SOURCE_CHANGED_RETRY", lambda: self.command("create_position", self.position_payload(),
            service=self.make_service(source_loader=load)))

    def test_left_disabled_user_and_relinked_employee_only_allow_strict_reduction(self):
        for state in ("Left", "disabled-user", "relinked", "unlinked"):
            with self.subTest(state=state):
                self.setUp()
                first = self.create_assignment()
                if state == "Left": self.rows["Employee"][0]["status"] = "Left"
                elif state == "disabled-user": self.rows["User"][0]["enabled"] = 0
                elif state == "relinked": self.rows["Employee"][0]["user_id"] = "SYNTHETIC-RELINKED"
                else: self.rows["Employee"][0]["user_id"] = None
                self.assert_code("SOURCE_ASSOCIATION_CHANGED" if state in ("relinked", "unlinked") else "PERSON_UNAVAILABLE",
                    lambda: self.update_assignment(first.record_id,
                    valid_until="2026-10-26T00:00:00Z"))
                reduced = self.update_assignment(first.record_id, status="revoked")
                self.assertEqual(reduced.revision, 2)
                stored = self.store.get_master(ASSIGNMENT, first.record_id)
                self.assertEqual(stored["subject_user"], TARGET_USER)
                self.assertEqual(stored["status"], "revoked")

    def test_inactive_position_allows_reduction_without_restoring_assignment(self):
        first = self.create_assignment()
        position = self.store.get_master(ASSIGNMENT, first.record_id)["position"]
        self.update_position(position, status="inactive")
        self.assert_code("INACTIVE_POSITION", lambda: self.update_assignment(first.record_id,
            valid_until="2026-10-26T00:00:00Z"))
        self.assertEqual(self.update_assignment(first.record_id, status="inactive").revision, 2)
        self.assert_code("INACTIVE_POSITION", lambda: self.update_assignment(first.record_id, status="active"))

    def test_disabled_department_requires_history_and_only_allows_strict_reduction(self):
        first = self.create_assignment()
        self.rows["Department"][1]["disabled"] = 1
        self.assert_code("DISABLED_ORGANIZATION", lambda: self.update_assignment(first.record_id,
            valid_until="2026-10-26T00:00:00Z"))
        self.assertEqual(self.update_assignment(first.record_id, status="revoked").revision, 2)
        self.assertEqual(self.store.get_master(ASSIGNMENT, first.record_id)["subject_user"], TARGET_USER)

    def test_disabled_department_position_cleanup_preserves_original_metadata(self):
        first = self.create_position()
        self.rows["Department"][1]["disabled"] = 1
        self.assert_code("DISABLED_ORGANIZATION", lambda: self.update_position(first.record_id,
            status="revoked", title="同时改动显示字段"))
        self.assertEqual(self.update_position(first.record_id, status="revoked").revision, 2)
        self.assertEqual(self.store.get_master(POSITION, first.record_id)["title"], "合成岗位")
        self.assert_code("DISABLED_ORGANIZATION", lambda: self.update_position(first.record_id, status="active"))

    def test_disabled_approver_cannot_authorize_historical_cleanup(self):
        first = self.create_assignment()
        self.rows["Employee"][0]["status"] = "Left"
        next(row for row in self.rows["User"] if row["name"] == APPROVER)["enabled"] = 0
        self.assert_code("POLICY_SOURCE_UNAVAILABLE", lambda: self.update_assignment(first.record_id, status="revoked"))

    def test_person_department_move_uses_original_scope_for_strict_cleanup(self):
        first = self.create_assignment()
        self.rows["Employee"][0]["department"] = "DEPT-B"
        self.assert_code("NO_MATCHING_POLICY", lambda: self.update_assignment(first.record_id,
            valid_until="2026-10-26T00:00:00Z"))
        self.assertEqual(self.update_assignment(first.record_id, status="revoked").revision, 2)
        proof = json.loads(self.store.versions[revision_key(ASSIGNMENT, first.record_id, 2)]["source_evidence_json"])
        self.assertEqual(proof["management_scope_v1"]["person_department_id"], "DEPT-A")

    def test_missing_employee_still_allows_only_immutable_history_cleanup(self):
        first = self.create_assignment()
        self.rows["Employee"] = []
        self.assert_code("UNKNOWN_REFERENCE", lambda: self.update_assignment(first.record_id,
            valid_until="2026-10-26T00:00:00Z"))
        self.assertEqual(self.update_assignment(first.record_id, status="revoked").revision, 2)
        self.assertEqual(self.store.get_master(ASSIGNMENT, first.record_id)["subject_user"], TARGET_USER)

    def test_missing_history_cannot_recover_disabled_organization_scope(self):
        first = self.create_assignment()
        self.rows["Department"][1]["disabled"] = 1
        del self.store.versions[revision_key(ASSIGNMENT, first.record_id, 1)]
        self.assert_code("HISTORICAL_SCOPE_REQUIRED", lambda: self.update_assignment(first.record_id, status="revoked"))

    def test_tampered_history_cannot_recover_old_beneficiary_or_scope(self):
        first = self.create_assignment()
        self.rows["Employee"][0]["user_id"] = "SYNTHETIC-RELINKED"
        history = self.store.versions[revision_key(ASSIGNMENT, first.record_id, 1)]
        evidence = json.loads(history["source_evidence_json"])
        evidence["management_scope_v1"] = {}
        history["source_evidence_json"] = json.dumps(evidence)
        self.assert_code("HISTORY_MISMATCH", lambda: self.update_assignment(first.record_id, status="revoked"))

    def test_source_evidence_change_cannot_reuse_unchanged_snapshot_digest(self):
        first = self.create_assignment()
        self.rows["Employee"][0]["user_id"] = "SYNTHETIC-RELINKED"
        history = self.store.versions[revision_key(ASSIGNMENT, first.record_id, 1)]
        evidence = json.loads(history["source_evidence_json"])
        evidence["current_source_digest"] = "0" * 64
        history["source_evidence_json"] = canonical_json(evidence)
        self.assert_code("HISTORY_MISMATCH", lambda: self.update_assignment(first.record_id, status="revoked"))

    def test_compound_revoke_and_extend_is_not_a_strict_reduction(self):
        first = self.create_assignment()
        self.rows["Employee"][0]["status"] = "Left"
        self.assert_code("PERSON_UNAVAILABLE", lambda: self.update_assignment(first.record_id,
            status="revoked", valid_until="2026-10-26T00:00:00Z"))

    def test_self_benefit_restore_and_extension_denied_but_shrink_allowed(self):
        position = self.create_position()
        self.rows["Employee"][0]["user_id"] = ACTOR
        other = "SYNTHETIC-RELINKED"
        other_policy = managed_policy(subject=other)
        self.repo.policies = (other_policy,)
        adapter = ManagedRelationAdapter(self.repo,
            approval_verifier=PinnedPolicyApprovalVerifier([pin(other_policy)]), enabled=True)
        self.store.session.user = other
        first = self.command("create_assignment", self.assignment_payload(position.record_id),
            service=self.make_service(actor_resolver=lambda: other, management_adapter=adapter))
        self.assertEqual(self.store.get_master(ASSIGNMENT, first.record_id)["subject_user"], ACTOR)
        self.store.session.user = ACTOR
        self.repo.policies = (self.policy,)
        self.assertEqual(self.update_assignment(first.record_id, status="inactive").revision, 2)
        self.assert_code("SELF_BENEFIT_DENIED", lambda: self.update_assignment(first.record_id, status="active"))
        self.assert_code("SELF_BENEFIT_DENIED", lambda: self.update_assignment(first.record_id,
            valid_until="2026-10-26T00:00:00Z"))


if __name__ == "__main__":
    unittest.main()
