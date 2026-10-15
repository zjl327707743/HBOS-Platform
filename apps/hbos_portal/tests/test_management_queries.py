"""Synthetic authorized query fixtures; no Site, SQL or provider I/O."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import unittest
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.management_policy import management_policy_digest, parse_management_policy
from hbos_portal.organization.management_storage import POLICY_PROVIDER, PinnedPolicyApprovalVerifier
from hbos_portal.organization.storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, POSITION, POSITION_REVISION, PROVIDER,
    canonical_json, digest, revision_key,
)
from tests import test_managed_relations as managed_fixture
from tests.test_management_policy import policy_payload, rule
from tests.test_management_storage import pin
from tests.test_organization_source_adapter import STAMP, snapshot, sources


ACTOR = managed_fixture.ACTOR
APPROVER = managed_fixture.APPROVER
NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


def query_rule(operations=("position.read", "assignment.read", "person.lookup"), *, departments=("DEPT-A",),
               person_departments=("DEPT-A",), rule_id="query-rule"):
    return rule(rule_id=rule_id, operation_ids=["hbos.organization." + operation for operation in operations],
        company_id="COMPANY-A", target_department_ids=list(departments), assignment_until_limit_utc=None,
        person_scope=None if all(operation.startswith("position.") for operation in operations) else dict(
            source_type="Employee", company_id="COMPANY-A", department_ids=list(person_departments)))


def query_policy(*, rules=None, policy_id=None, subject=ACTOR, revision=1, generation=1):
    changes = dict(subject_user=subject, revision=revision, authority_generation=generation,
                   rules=[query_rule()] if rules is None else rules)
    if policy_id is not None:
        changes["policy_id"] = policy_id
    payload = policy_payload(**changes)
    policy = parse_management_policy(payload, site_id="synthetic-site", source_provider=POLICY_PROVIDER)
    payload["approval"] = dict(approval_ref="SYNTHETIC-QUERY-APPROVAL", approved_by=APPROVER,
        approved_at_utc="2026-10-09T00:00:00Z", approved_revision=revision,
        approved_authority_generation=generation, content_digest=management_policy_digest(policy))
    return parse_management_policy(payload, site_id="synthetic-site", source_provider=POLICY_PROVIDER)


class QueryTestStore(managed_fixture.ManagedTestStore):
    def __init__(self):
        super().__init__()
        self.read_calls = []
        self.names = {}

    def list_positions(self):
        self.require_locked_source_context()
        self.read_calls.append("positions")
        return tuple(deepcopy(row) for (kind, _), row in self.masters.items() if kind == POSITION)

    def list_assignments(self):
        self.require_locked_source_context()
        self.read_calls.append("assignments")
        return super().list_assignments()

    def get_person_label(self, employee_id):
        self.require_locked_source_context()
        self.read_calls.append(("label", employee_id))
        return self.names.get(employee_id)

    def get_person_phone(self, employee_id):
        raise AssertionError("Management query must never read contact information")

    def seed(self, kind, row):
        self.masters[kind, row["record_key"]] = deepcopy(row)
        revision = dict(record_key=revision_key(kind, row["record_key"], row["revision"]),
            **{"position" if kind == POSITION else "assignment": row["record_key"]}, revision=row["revision"],
            previous_revision=row["revision"] - 1, snapshot_json=canonical_json(row), content_digest=digest(row),
            actor=ACTOR, policy_ref="SYNTHETIC-QUERY-HISTORY", reason="合成查询夹具", source_evidence_json="{}",
            recorded_at_utc="2026-10-10 00:00:00.000000")
        self.versions[revision["record_key"]] = revision


class ManagementQueryTests(unittest.TestCase):
    def setUp(self):
        self.rows = sources()
        for user in (ACTOR, APPROVER, "SYNTHETIC-USER-B", "SYNTHETIC-RELINKED"):
            self.rows["User"].append(dict(name=user, enabled=1, user_type="System User", modified=STAMP))
        other = deepcopy(self.rows["Employee"][0])
        other.update(name="SYNTHETIC-EMP-B", user_id="SYNTHETIC-USER-B", department="DEPT-B")
        self.rows["Employee"].append(other)
        self.store = QueryTestStore()
        self.store.names = {"SYNTHETIC-EMP": "A部门合成人员", "SYNTHETIC-EMP-B": "B部门合成人员"}
        self.ids = dict(position_a=str(uuid4()), position_b=str(uuid4()), assignment_a=str(uuid4()), assignment_b=str(uuid4()))
        self.store.seed(POSITION, position_row(self.ids["position_a"], title="A岗位"))
        self.store.seed(POSITION, position_row(self.ids["position_b"], "DEPT-B", title="B岗位"))
        self.store.seed(ASSIGNMENT, assignment_row(self.ids["assignment_a"], self.ids["position_a"]))
        self.store.seed(ASSIGNMENT, assignment_row(self.ids["assignment_b"], self.ids["position_b"], "SYNTHETIC-EMP-B", "SYNTHETIC-USER-B"))
        self.policy = query_policy()
        self.repo = managed_fixture.ManagedTestPolicyRepository(self.store, [self.policy])
        self.now = NOW
        self.service = self.make_service()

    def make_service(self, **changes):
        from hbos_portal.organization.management_queries import ManagementQueryService
        options = dict(source_loader=lambda: snapshot(self.rows), clock=lambda: self.now,
            approval_verifier=PinnedPolicyApprovalVerifier([pin(policy) for policy in self.repo.policies]), enabled=True)
        options.update(changes)
        return ManagementQueryService(self.store, self.repo, **options)

    def install(self, *policies):
        self.repo.policies = tuple(policies)
        self.service = self.make_service()

    def execute(self, query="list_positions", params=None):
        self.service.discard_pending()  # Each helper call models a separate read request.
        return self.service.execute(query, {} if params is None else params)

    def assert_code(self, code, action):
        before = deepcopy((self.store.masters, self.store.versions, self.store.receipts))
        with self.assertRaises(ContractError) as caught: action()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual((self.store.masters, self.store.versions, self.store.receipts), before)

    def assert_read_flags(self, result):
        self.assertTrue(result["read_only"])
        self.assertEqual(result["authorization_effect"], "none")
        self.assertFalse(result["runtime_verified"])
        self.assertFalse(result["position_authorization_connected"])

    def test_default_closed_before_source_or_repository_access(self):
        def fail(): raise AssertionError("disabled query must not load sources")
        service = self.make_service(enabled=False, source_loader=fail)
        self.assert_code("QUERY_READS_DISABLED", lambda: service.execute("list_positions", {}))
        self.assertEqual(self.store.read_calls, [])

    def test_scope_filter_precedes_total_and_pagination(self):
        for index in range(4):
            self.store.seed(POSITION, position_row(str(uuid4()), "DEPT-B", title="未授权岗位" + str(index)))
        first = self.execute(params={"page": 1, "page_size": 1})
        second = self.execute(params={"page": 2, "page_size": 1})
        self.assertEqual(first["total"], 1)
        self.assertEqual(len(first["items"]), 1)
        self.assertEqual(second["total"], 1)
        self.assertEqual(second["items"], [])
        self.assert_read_flags(first)

    def test_assignment_scope_and_person_scope_must_match_one_complete_rule(self):
        self.install(query_policy(rules=[
            query_rule(("assignment.read",), departments=("DEPT-A",), person_departments=("DEPT-B",)),
            query_rule(("assignment.read",), departments=("DEPT-B",), person_departments=("DEPT-A",), rule_id="other-rule")]))
        result = self.execute("get_person_assignments", {"employee_id": "SYNTHETIC-EMP"})
        self.assertEqual(result["items"], [])
        self.assertEqual(result["total"], 0)

    def test_assignment_scope_cannot_be_combined_across_policies(self):
        one = query_policy(rules=[query_rule(("assignment.read",), departments=("DEPT-A",), person_departments=("DEPT-B",))])
        two = query_policy(policy_id=str(uuid4()), rules=[query_rule(("assignment.read",), departments=("DEPT-B",), person_departments=("DEPT-A",))])
        self.install(one, two)
        self.assertEqual(self.execute("get_person_assignments", {"employee_id": "SYNTHETIC-EMP"})["items"], [])

    def test_read_write_and_lookup_operations_do_not_imply_each_other(self):
        for operation, position_count, lookup_count in (("position.read", 1, None), ("person.lookup", None, 1), ("position.update", None, None)):
            with self.subTest(operation=operation):
                self.install(query_policy(rules=[query_rule((operation,))]))
                if position_count is None:
                    self.assert_code("MANAGEMENT_DENIED", lambda: self.execute("list_positions"))
                else: self.assertEqual(self.execute("list_positions")["total"], position_count)
                if lookup_count is None:
                    self.assert_code("MANAGEMENT_DENIED", lambda: self.execute("lookup_people"))
                else: self.assertEqual(self.execute("lookup_people")["total"], lookup_count)

    def test_hidden_and_nonexistent_person_have_identical_empty_results(self):
        hidden = self.execute("get_person_assignments", {"employee_id": "SYNTHETIC-EMP-B"})
        absent = self.execute("get_person_assignments", {"employee_id": "SYNTHETIC-NOT-EXISTS"})
        self.assertEqual(hidden, absent)
        self.assertEqual(hidden["total"], 0)

    def test_native_role_name_or_administrator_does_not_replace_management_policy(self):
        self.install()
        for actor in (ACTOR, "Administrator", "System Manager"):
            with self.subTest(actor=actor):
                if actor != ACTOR:
                    self.rows["User"].append(dict(name=actor, enabled=1, user_type="System User", modified=STAMP))
                self.store.session.user = actor
                self.assert_code("MANAGEMENT_DENIED", lambda: self.execute("list_positions"))
                self.assert_code("MANAGEMENT_DENIED", lambda: self.execute("lookup_people"))
                self.assert_code("MANAGEMENT_DENIED", lambda: self.execute("get_management_context"))

    def test_lookup_never_reads_hidden_person_label_or_contact_data(self):
        result = self.execute("lookup_people")
        self.assertEqual(result["total"], 1)
        self.assertIn(("label", "SYNTHETIC-EMP"), self.store.read_calls)
        self.assertNotIn(("label", "SYNTHETIC-EMP-B"), self.store.read_calls)
        serialized = canonical_json(result)
        for forbidden in ("phone", "SYNTHETIC-USER", "policy", "approval", "history", "snapshot_json"):
            self.assertNotIn(forbidden, serialized)
        self.assert_read_flags(result)

    def test_literal_name_and_stable_id_search_do_not_match_phone_or_sql_wildcards(self):
        self.assertEqual(self.execute("lookup_people", {"q": "A部门"})["total"], 1)
        self.assertEqual(self.execute("lookup_people", {"q": "SYNTHETIC-EMP"})["total"], 1)
        for query in ("13800000000", "%", "_", "' OR 1=1 --"):
            with self.subTest(query=query):
                self.assertEqual(self.execute("lookup_people", {"q": query})["total"], 0)

    def test_left_or_disabled_linked_account_can_read_facts_without_grant(self):
        for unavailable in ("Left", "disabled"):
            with self.subTest(unavailable=unavailable):
                self.setUp()
                if unavailable == "Left": self.rows["Employee"][0]["status"] = "Left"
                else: self.rows["User"][0]["enabled"] = 0
                result = self.execute("get_person_assignments", {"employee_id": "SYNTHETIC-EMP"})
                self.assertEqual(result["total"], 1)
                self.assert_read_flags(result)

    def test_ambiguous_missing_or_relinked_identity_cannot_read_assignment_facts(self):
        for mismatch in ("ambiguous", "missing-user", "relinked"):
            with self.subTest(mismatch=mismatch):
                self.setUp()
                if mismatch == "ambiguous":
                    other = deepcopy(self.rows["Employee"][0]); other["name"] = "SYNTHETIC-ALIAS"
                    self.rows["Employee"].append(other)
                elif mismatch == "missing-user": self.rows["User"] = [row for row in self.rows["User"] if row["name"] != "SYNTHETIC-USER"]
                else: self.rows["Employee"][0]["user_id"] = "SYNTHETIC-RELINKED"
                result = self.execute("get_person_assignments", {"employee_id": "SYNTHETIC-EMP"})
                self.assertEqual(result["total"], 0)

    def test_invalid_query_params_are_strictly_rejected(self):
        for params in ({"page": True}, {"page": 0}, {"page": 10001}, {"page_size": 0}, {"page_size": 51},
                       {"page": "1"}, {"page_size": 1.0}, {"q": "x" * 81}, {"unknown": "ignored"}):
            with self.subTest(params=params):
                self.assert_code("INVALID_REQUEST", lambda: self.execute(params=params))
        self.assert_code("INVALID_REQUEST", lambda: self.execute("get_person_assignments", {}))

    def test_final_read_proof_is_single_use_and_copies_do_not_authorize(self):
        result = self.execute()
        proof = self.service.pending_proof
        self.assert_code("PENDING_PROOF_MISMATCH", lambda: self.service.recheck_pending(replace(proof)))
        self.assertEqual(self.service.recheck_pending(proof), result)
        self.assert_code("PENDING_PROOF_MISMATCH", lambda: self.service.recheck_pending(proof))

    def test_expiry_revocation_and_new_head_before_release_deny_old_result(self):
        for change, code in (("expiry", "MANAGEMENT_CHANGED_RETRY"), ("revoke", "MANAGEMENT_CHANGED_RETRY"), ("new-head", "MANAGEMENT_CHANGED_RETRY")):
            with self.subTest(change=change):
                self.setUp()
                self.execute()
                proof = self.service.pending_proof
                if change == "expiry": self.now = datetime(2026, 11, 1, tzinfo=timezone.utc)
                elif change == "revoke": self.repo.policies = (replace(self.policy, status="revoked", revision=2, authority_generation=2),)
                else:
                    newer = query_policy(revision=2, generation=2)
                    self.repo.policies = (newer,)
                    # Trusted deployment pin changes do not validate an old read.
                    self.service.approval_verifier = PinnedPolicyApprovalVerifier([pin(newer)])
                self.assert_code(code, lambda: self.service.recheck_pending(proof))

    def test_source_change_before_release_requires_retry(self):
        self.execute()
        proof = self.service.pending_proof
        self.rows["Department"][1]["disabled"] = 1
        self.assert_code("SOURCE_CHANGED_RETRY", lambda: self.service.recheck_pending(proof))

    def test_context_preserves_complete_scope_pairs_and_exposes_no_policy_reference(self):
        self.install(query_policy(rules=[
            query_rule(("assignment.read",), departments=("DEPT-A",), person_departments=("DEPT-B",)),
            query_rule(("assignment.read",), departments=("DEPT-B",), person_departments=("DEPT-A",), rule_id="other")]))
        result = self.execute("get_management_context")
        self.assertEqual(result["operation_ids"], ["hbos.organization.assignment.read"])
        pairs = {(tuple(scope["target_department_ids"]), tuple(scope["person_scope"]["department_ids"])) for scope in result["scopes"]}
        self.assertEqual(pairs, {(("DEPT-A",), ("DEPT-B",)), (("DEPT-B",), ("DEPT-A",))})
        self.assertNotIn(self.policy.policy_id, canonical_json(result))
        self.assertNotIn("SYNTHETIC-QUERY-APPROVAL", canonical_json(result))
        self.assert_read_flags(result)

    def test_position_and_assignment_outputs_are_minimal_whitelisted_facts(self):
        positions = self.execute()["items"]
        self.assertEqual(set(positions[0]), {"record_id", "title", "company_id", "department_id", "designation_id", "status", "revision"})
        assignments = self.execute("get_person_assignments", {"employee_id": "SYNTHETIC-EMP"})["items"]
        self.assertEqual(set(assignments[0]), {"record_id", "position_id", "person_source_id", "status", "is_primary", "valid_from_utc", "valid_until_utc", "revision"})
        self.assertNotIn("SYNTHETIC-USER", canonical_json(assignments))

    def test_empty_label_falls_back_to_stable_id_and_label_changes_block_release(self):
        self.store.names["SYNTHETIC-EMP"] = ""
        result = self.execute("lookup_people")
        self.assertEqual(result["items"][0]["display_name"], "SYNTHETIC-EMP")
        proof = self.service.pending_proof
        self.store.names["SYNTHETIC-EMP"] = "新的授权显示名称"
        self.assert_code("SOURCE_CHANGED_RETRY", lambda: self.service.recheck_pending(proof))
        self.assertIsNone(self.service.pending_proof)

    def test_actual_database_session_sid_and_actor_are_bound_to_read_proof(self):
        for change in ("database", "session", "sid", "actor"):
            with self.subTest(change=change):
                self.setUp()
                native_call = self.repo.native
                database = [object()]
                self.store.session.sid = "SYNTHETIC-QUERY-SID"
                def native():
                    current = native_call()
                    current.local.db = database[0]
                    current.local.session = self.store.session
                    return current
                self.repo.native = native
                self.execute()
                proof = self.service.pending_proof
                if change == "database": database[0] = object()
                elif change == "session": self.store.session = replace_namespace(self.store.session)
                elif change == "sid": self.store.session.sid = "SYNTHETIC-NEW-SID"
                else: self.store.session.user = "SYNTHETIC-RELINKED"
                self.assert_code("PENDING_PROOF_MISMATCH", lambda: self.service.recheck_pending(proof))
                self.assertIsNone(self.service.pending_proof)

    def test_current_position_revision_change_before_release_denies_old_rows(self):
        self.execute()
        proof = self.service.pending_proof
        self.store.seed(POSITION, position_row(self.ids["position_a"], title="当前岗位新修订", revision=2))
        self.assert_code("SOURCE_CHANGED_RETRY", lambda: self.service.recheck_pending(proof))

    def test_second_pending_read_and_foreign_service_proof_are_rejected(self):
        self.execute()
        proof = self.service.pending_proof
        self.assert_code("PENDING_PROOF_EXISTS", lambda: self.service.execute("list_positions", {}))
        other_service = self.make_service()
        self.assert_code("PENDING_PROOF_MISMATCH", lambda: other_service.recheck_pending(proof))
        self.assertTrue(self.service.recheck_pending(proof)["read_only"])


def replace_namespace(value):
    from types import SimpleNamespace
    return SimpleNamespace(**vars(value))


def position_row(identifier, department="DEPT-A", *, title="合成岗位", revision=1, status="active"):
    return dict(record_key=identifier, title=title, company="COMPANY-A", department=department,
        designation="TYPE-A", status=status, revision=revision, authorization_generation=revision,
        source_provider=PROVIDER, source_key=identifier)


def assignment_row(identifier, position, employee="SYNTHETIC-EMP", user="SYNTHETIC-USER", *, status="active"):
    return dict(record_key=identifier, person_source_type="Employee", person_source_id=employee,
        subject_user=user, position=position, is_primary=True, valid_from_utc="2026-10-10 00:00:00.000000",
        valid_until_utc="2026-10-25 00:00:00.000000", status=status, revision=1, authorization_generation=1,
        source_provider=PROVIDER, source_key=identifier)
