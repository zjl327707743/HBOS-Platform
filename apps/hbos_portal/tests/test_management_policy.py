"""Synthetic security invariants for the pure management-policy boundary."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from itertools import product
import os
from pathlib import Path
import subprocess
import sys
import unittest

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.management_contracts import MANAGEMENT_OPERATIONS
from hbos_portal.organization.management_policy import (
    evaluate_management_policy, management_policy_digest,
    parse_management_context, parse_management_policy,
)
from hbos_portal.organization.relation_service import ManagementDecision


SITE, PROVIDER = "synthetic-site", "synthetic-management-provider.v1"
ACTOR, PERSON_USER = "synthetic-manager@example.invalid", "synthetic-employee@example.invalid"
POLICY_ID = "00000000-0000-4000-8000-000000000001"
POSITION_ID = "00000000-0000-4000-8000-000000000002"
ASSIGNMENT_ID = "00000000-0000-4000-8000-000000000003"
PREFIX = "hbos.organization."


def rule(**changes):
    result = dict(rule_id="rule-a", operation_schema_version=1,
        operation_ids=[PREFIX + "assignment." + verb for verb in ("create", "update", "read")],
        company_id="CO-A", target_department_ids=["DEPT-A"], include_children=False,
        assignment_until_limit_utc="2026-10-31T00:00:00Z",
        person_scope=dict(source_type="Employee", company_id="CO-A", department_ids=["DEPT-A"]))
    result.update(changes)
    return result


def policy_payload(**changes):
    result = dict(policy_id=POLICY_ID, subject_user=ACTOR, status="active", revision=1,
        authority_generation=1, schema_version=1, valid_from_utc="2026-10-09T00:00:00Z",
        valid_until_utc="2026-11-01T00:00:00Z", approval=None, rules=[rule()])
    result.update(changes)
    return result


def parse_policy(payload):
    return parse_management_policy(payload, site_id=SITE, source_provider=PROVIDER)


def approved_policy(**changes):
    payload = policy_payload(**changes)
    policy = parse_policy(payload)
    payload["approval"] = dict(approval_ref="SYNTHETIC-APPROVAL", approved_by="synthetic-owner@example.invalid",
        approved_at_utc="2026-10-08T00:00:00Z", approved_revision=policy.revision,
        approved_authority_generation=policy.authority_generation, content_digest=management_policy_digest(policy))
    return parse_policy(payload)


def position(**changes):
    result = dict(record_id=POSITION_ID, company_id="CO-A", department_id="DEPT-A", title="合成岗位",
                  designation_id=None, status="active", revision=1)
    result.update(changes)
    return result


def assignment(**changes):
    result = dict(record_id=ASSIGNMENT_ID, position_id=POSITION_ID, person_source_id="EMP-A",
        subject_user=PERSON_USER, status="active", is_primary=True,
        valid_from_utc="2026-10-10T00:00:00Z", valid_until_utc="2026-10-30T00:00:00Z", revision=1)
    result.update(changes)
    return result


def context_payload(operation="assignment.create", **changes):
    family, verb = operation.split(".")
    person = dict(source_type="Employee", source_id="EMP-A", company_id="CO-A", department_id="DEPT-A",
        link_status="linked", subject_user=PERSON_USER, employee_status="Active", user_enabled=True)
    result = dict(operation_id=PREFIX + operation, operation_schema_version=1, now_utc="2026-10-10T00:00:00Z",
        expected_revision=0 if verb in ("create", "lookup") else 1, organization_status="active",
        position_before=None if family == "person" or family == "position" and verb == "create" else position(),
        position_after=position(revision=2 if verb == "update" else 1) if family == "position" and verb != "read" else None,
        assignment_before=assignment() if family == "assignment" and verb != "create" else None,
        assignment_after=assignment(revision=2 if verb == "update" else 1) if family == "assignment" and verb != "read" else None,
        person=None if family == "position" else person)
    result.update(changes)
    return result


def context(operation="assignment.create", *, actor=ACTOR, actor_enabled=True, **changes):
    return parse_management_context(context_payload(operation, **changes), site_id=SITE,
        policy_provider_id=PROVIDER, actor_user=actor, actor_enabled=actor_enabled)


class ManagementPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy, self.context = approved_policy(), context()

    def evaluate(self, policies=None, candidate=None):
        return evaluate_management_policy([self.policy] if policies is None else policies,
                                          self.context if candidate is None else candidate, enabled=True)

    def assert_denied(self, policies=None, candidate=None, code=None):
        result = self.evaluate(policies, candidate)
        self.assertFalse(result.matched)
        self.assertIsNone(result.match)
        if code:
            self.assertIn(code, result.reason_codes)
        return result

    def assert_invalid(self, action, code=None):
        with self.assertRaises(ContractError) as caught:
            action()
        if code:
            self.assertEqual(caught.exception.code, code)

    def test_default_closed_without_evaluating_inputs(self):
        result = evaluate_management_policy(None, None)
        self.assertFalse(result.matched)
        self.assertEqual(result.reason_codes, ("EVALUATION_DISABLED",))
        self.assertIsNone(result.context_digest)
        self.assertFalse(evaluate_management_policy(None, None, enabled=1).matched)

    def test_complete_match_is_immutable_offline_evidence_not_runtime_decision(self):
        result = self.evaluate()
        self.assertTrue(result.matched)
        self.assertTrue(result.validation_only)
        self.assertFalse(result.runtime_verified)
        self.assertEqual(result.authorization_effect, "none")
        self.assertNotIsInstance(result, ManagementDecision)
        self.assertEqual(result.match.policy_id, POLICY_ID)
        self.assertEqual(result.match.policy_revision, 1)
        self.assertEqual(result.match.authority_generation, 1)
        self.assertEqual(result.match.policy_digest, management_policy_digest(self.policy))
        with self.assertRaises(FrozenInstanceError): result.matched = False

    def test_parser_copies_nested_collections_and_freezes_all_levels(self):
        payload = policy_payload()
        parsed = parse_policy(payload)
        original_digest = management_policy_digest(parsed)
        payload["rules"][0]["target_department_ids"].append("DEPT-B")
        payload["rules"][0]["person_scope"]["department_ids"].append("DEPT-B")
        self.assertEqual(management_policy_digest(parsed), original_digest)
        self.assertEqual(parsed.rules[0].target_department_ids, ("DEPT-A",))
        with self.assertRaises(FrozenInstanceError): parsed.rules[0].company_id = "CO-B"
        with self.assertRaises(FrozenInstanceError): parsed.rules[0].person_scope.company_id = "CO-B"
        with self.assertRaises(TypeError): MANAGEMENT_OPERATIONS["unknown"] = object()

    def test_no_policy_does_not_infer_management_from_native_identity(self):
        for actor in (ACTOR, "Administrator", "HR Manager", "System Manager", "Guest"):
            with self.subTest(actor=actor):
                self.assert_denied([], context(actor=actor))

    def test_actor_mismatch_and_disabled_actor_denied(self):
        self.assert_denied(candidate=context(actor="other@example.invalid"))
        self.assert_denied(candidate=context(actor_enabled=False), code="ACTOR_UNAVAILABLE")

    def test_site_and_source_provider_are_part_of_binding(self):
        self.assert_denied(candidate=replace(self.context, site_id="other-site"))
        self.assert_denied(candidate=replace(self.context, policy_provider_id="other-provider"))

    def test_scope_dimensions_all_required_without_cross_products(self):
        for company, department, person_department in product(("CO-A", "CO-B"), ("DEPT-A", "DEPT-B"), ("DEPT-A", "DEPT-B")):
            row = context_payload()
            row["position_before"].update(company_id=company, department_id=department)
            row["person"]["department_id"] = person_department
            candidate = parse_management_context(row, site_id=SITE, policy_provider_id=PROVIDER, actor_user=ACTOR, actor_enabled=True)
            with self.subTest(company=company, department=department, person_department=person_department):
                self.assertEqual(self.evaluate(candidate=candidate).matched,
                    (company, department, person_department) == ("CO-A", "DEPT-A", "DEPT-A"))

    def test_explicit_employee_department_can_differ_from_position_department(self):
        policy = approved_policy(rules=[rule(person_scope=dict(source_type="Employee",company_id="CO-A",department_ids=["DEPT-B"]))])
        person = context_payload()["person"]
        person["department_id"] = "DEPT-B"
        self.assertTrue(self.evaluate([policy], context(person=person)).matched)

    def test_action_and_scope_cannot_be_combined_across_policies(self):
        a = approved_policy(rules=[rule(target_department_ids=["DEPT-B"])])
        b = approved_policy(policy_id="00000000-0000-4000-8000-000000000004",
                            rules=[rule(operation_ids=[PREFIX+"assignment.read"],assignment_until_limit_utc=None)])
        self.assert_denied([a,b])

    def test_action_and_scope_cannot_be_combined_across_rules(self):
        policy = approved_policy(rules=[rule(target_department_ids=["DEPT-B"]),
            rule(rule_id="rule-b",operation_ids=[PREFIX+"assignment.read"],assignment_until_limit_utc=None)])
        self.assert_denied([policy])

    def test_assignment_duration_cannot_be_borrowed_from_another_rule(self):
        policy = approved_policy(rules=[rule(assignment_until_limit_utc="2026-10-20T00:00:00Z"),
            rule(rule_id="rule-b",operation_ids=[PREFIX+"assignment.update"],
                 assignment_until_limit_utc="2026-12-01T00:00:00Z")])
        self.assert_denied([policy])

    def test_sql_like_reference_is_literal_and_does_not_expand_scope(self):
        policy = approved_policy(rules=[rule(target_department_ids=["DEPT-A' OR 1=1 --"])])
        self.assert_denied([policy])

    def test_complete_policy_alternatives_and_deterministic_rule_evidence(self):
        unavailable = approved_policy(policy_id="00000000-0000-4000-8000-000000000004",status="revoked")
        policy = approved_policy(rules=[rule(rule_id="rule-z"),rule(rule_id="rule-a")])
        one, two = self.evaluate([unavailable,policy]), self.evaluate([policy,unavailable])
        self.assertTrue(one.matched)
        self.assertEqual(one.match, two.match)
        self.assertEqual(one.match.rule_id, "rule-a")

    def test_policy_half_open_time_interval(self):
        start, end = self.policy.valid_from_utc, self.policy.valid_until_utc
        self.assertTrue(self.evaluate(candidate=replace(self.context, now_utc=start)).matched)
        self.assert_denied(candidate=replace(self.context, now_utc=end))
        self.assert_denied(candidate=replace(self.context, now_utc=datetime(2026,10,8,tzinfo=timezone.utc)))

    def test_missing_approval_and_nonactive_states_denied(self):
        self.assert_denied([parse_policy(policy_payload())])
        for state in ("draft", "inactive", "revoked"):
            with self.subTest(state=state): self.assert_denied([replace(self.policy,status=state)])

    def test_approval_actor_time_revision_generation_and_digest_checked(self):
        approval = self.policy.approval
        changes = [dict(approved_by=ACTOR), dict(approved_by="Guest"), dict(approved_revision=2),
            dict(approved_authority_generation=2),dict(content_digest="0"*64),
            dict(approved_at_utc=datetime(2026,10,11,tzinfo=timezone.utc))]
        for change in changes:
            with self.subTest(change=change):
                self.assert_denied([replace(self.policy,approval=replace(approval,**change))])

    def test_changes_in_fixed_content_invalidate_existing_approval(self):
        for change in (dict(revision=2),dict(authority_generation=2),dict(subject_user="new@example.invalid"),
                       dict(valid_until_utc=datetime(2026,11,2,tzinfo=timezone.utc)),
                       dict(rules=(replace(self.policy.rules[0],target_department_ids=("DEPT-A","DEPT-B")),))):
            with self.subTest(change=change): self.assert_denied([replace(self.policy,**change)])

    def test_normalized_content_digest_stable_across_input_order_and_timezone(self):
        raw = policy_payload()
        raw["rules"][0]["operation_ids"].reverse()
        raw["valid_from_utc"] = "2026-10-09T08:00:00+08:00"
        self.assertEqual(management_policy_digest(parse_policy(raw)), management_policy_digest(parse_policy(policy_payload())))
        self.assertEqual(management_policy_digest(self.policy), management_policy_digest(replace(self.policy,status="revoked",approval=None)))

    def test_duplicate_heads_cannot_resurrect_old_active_policy(self):
        revoked = replace(self.policy, status="revoked", authority_generation=2)
        for policies in ([self.policy,revoked],[revoked,self.policy]):
            self.assert_invalid(lambda: self.evaluate(policies), "DUPLICATE_POLICY")

    def test_new_known_operation_or_new_department_does_not_expand_old_policy(self):
        policy = approved_policy(rules=[rule(operation_ids=[PREFIX+"assignment.create"])])
        self.assert_denied([policy],context("assignment.read"))
        self.assert_denied(candidate=context(position_before=position(department_id="NEW-CHILD-DEPT")))

    def test_unknown_operations_and_versions_rejected(self):
        for change in (dict(operation_ids=[PREFIX+"assignment.delete"]),dict(operation_schema_version=2),dict(operation_schema_version=True)):
            self.assert_invalid(lambda: parse_policy(policy_payload(rules=[rule(**change)])))
        self.assert_invalid(lambda: context(operation_id=PREFIX+"assignment.delete"),"UNKNOWN_OPERATION")
        self.assert_invalid(lambda: context(operation_schema_version=2),"UNSUPPORTED_VERSION")
        self.assert_invalid(lambda: parse_policy(policy_payload(schema_version=True)),"UNSUPPORTED_VERSION")

    def test_empty_wildcard_descendant_and_duplicate_scope_rejected(self):
        for change in (dict(target_department_ids=[]), dict(target_department_ids=["*"]),dict(company_id="ALL"),
                       dict(include_children=True),dict(include_children=0),dict(operation_ids=[]),
                       dict(target_department_ids=["DEPT-A","DEPT-A"]),dict(person_scope=None)):
            with self.subTest(change=change): self.assert_invalid(lambda: parse_policy(policy_payload(rules=[rule(**change)])))
        self.assert_invalid(lambda: parse_policy(policy_payload(rules=[rule(),rule()])),"DUPLICATE_ID")

    def test_cross_company_person_rule_is_not_an_implicit_exception(self):
        bad = dict(source_type="Employee",company_id="CO-B",department_ids=["DEPT-A"])
        self.assert_invalid(lambda: parse_policy(policy_payload(rules=[rule(person_scope=bad)])),"UNSUPPORTED_SCOPE")
        self.assert_invalid(lambda: parse_policy(policy_payload(rules=[rule(person_scope={**bad,"source_type":"User"})])))

    def test_explicit_finite_times_required_with_microsecond_precision(self):
        for value in (None,"","2026-11-01T00:00:00","2026-11-01T00:00:00-00:00","2026-11-01T00:00:00.1234567Z"):
            with self.subTest(value=value): self.assert_invalid(lambda: parse_policy(policy_payload(valid_until_utc=value)))
        self.assert_invalid(lambda: parse_policy(policy_payload(valid_until_utc="2026-10-09T00:00:00Z")),"INVALID_INTERVAL")
        self.assert_invalid(lambda: context(actor_enabled=1),"INVALID_TYPE")

    def test_assignment_end_limit_in_same_rule_and_null_end_denied(self):
        self.assertTrue(self.evaluate(candidate=context(assignment_after=assignment(valid_until_utc="2026-10-31T00:00:00Z"))).matched)
        self.assert_denied(candidate=context(assignment_after=assignment(valid_until_utc="2026-11-01T00:00:00Z")))
        self.assert_denied(candidate=context(assignment_after=assignment(valid_until_utc=None)),code="ASSIGNMENT_LIMIT_REQUIRED")
        self.assert_invalid(lambda: parse_policy(policy_payload(rules=[rule(assignment_until_limit_utc=None)])),"INCOMPLETE_SCOPE")

    def test_update_without_increase_limit_can_only_reduce(self):
        policy = approved_policy(rules=[rule(operation_ids=[PREFIX+"assignment.update"],assignment_until_limit_utc=None)])
        self.assert_denied([policy],context("assignment.update"))
        reduced = context("assignment.update", assignment_after=assignment(status="inactive",revision=2))
        self.assertTrue(self.evaluate([policy],reduced).matched)

    def test_self_assignment_creation_restoration_and_extension_denied(self):
        person = context_payload()["person"]
        person["subject_user"] = ACTOR
        scenarios = [context(person=person,assignment_after=assignment(subject_user=ACTOR)),
            context("assignment.update",person=person,assignment_before=assignment(subject_user=ACTOR,status="inactive"),
                    assignment_after=assignment(subject_user=ACTOR,revision=2)),
            context("assignment.update",person=person,assignment_before=assignment(subject_user=ACTOR,valid_until_utc="2026-10-20T00:00:00Z"),
                    assignment_after=assignment(subject_user=ACTOR,revision=2))]
        for candidate in scenarios:
            self.assert_denied(candidate=candidate,code="SELF_BENEFIT_DENIED")

    def test_self_strict_reduction_still_requires_complete_management_policy(self):
        person = context_payload()["person"]
        person["subject_user"] = ACTOR
        candidate = context("assignment.update",person=person,assignment_before=assignment(subject_user=ACTOR),
            assignment_after=assignment(subject_user=ACTOR,status="inactive",revision=2))
        self.assertTrue(self.evaluate(candidate=candidate).matched)
        self.assert_denied([],candidate)

    def test_shortening_cannot_disguise_restoration_extension_or_primary_change(self):
        person = context_payload()["person"]
        person["subject_user"] = ACTOR
        scenarios = [
            (assignment(subject_user=ACTOR,status="inactive"),assignment(subject_user=ACTOR,valid_until_utc="2026-10-20T00:00:00Z",revision=2)),
            (assignment(subject_user=ACTOR,valid_until_utc="2026-10-20T00:00:00Z"),assignment(subject_user=ACTOR,status="inactive",revision=2)),
            (assignment(subject_user=ACTOR),assignment(subject_user=ACTOR,status="inactive",is_primary=False,revision=2)),
        ]
        for before, after in scenarios:
            self.assert_denied(candidate=context("assignment.update",person=person,assignment_before=before,assignment_after=after),code="SELF_BENEFIT_DENIED")

    def test_unknown_unlinked_and_ambiguous_beneficiary_not_assumed_other(self):
        for link in ("unlinked","unknown","ambiguous"):
            person = context_payload()["person"]
            person.update(link_status=link,subject_user=None,user_enabled=None)
            self.assert_denied(candidate=context(person=person,assignment_after=assignment(subject_user=None)),code="PERSON_UNAVAILABLE")

    def test_left_employee_or_disabled_subject_cannot_increase_facts(self):
        for change in (dict(employee_status="Left"),dict(employee_status="Suspended"),dict(user_enabled=False)):
            person = context_payload()["person"]
            person.update(change)
            self.assert_denied(candidate=context(person=person),code="PERSON_UNAVAILABLE")

    def test_cleanup_does_not_transfer_old_subject_after_native_relink(self):
        person = context_payload()["person"]
        person.update(employee_status="Left",subject_user="relinked@example.invalid")
        candidate = context("assignment.update",person=person,assignment_after=assignment(status="inactive",revision=2))
        self.assertTrue(self.evaluate(candidate=candidate).matched)
        changed = replace(candidate,assignment_after=replace(candidate.assignment_after,subject_user=person["subject_user"]))
        self.assert_denied(candidate=changed,code="NEW_RELATION_REQUIRED")

    def test_disabled_organization_cleanup_requires_later_historical_scope_proof(self):
        candidate = context("assignment.update",organization_status="disabled",assignment_after=assignment(status="inactive",revision=2))
        self.assert_denied(candidate=candidate,code="HISTORICAL_SCOPE_REQUIRED")
        self.assert_denied(candidate=context(organization_status="unknown"),code="SOURCE_UNAVAILABLE")

    def test_removing_an_unbounded_old_end_is_a_reduction_not_a_long_term_grant(self):
        candidate = context("assignment.update",assignment_before=assignment(valid_until_utc=None),
            assignment_after=assignment(valid_until_utc="2026-10-20T00:00:00Z",revision=2))
        self.assertTrue(self.evaluate(candidate=candidate).matched)

    def test_record_references_and_versions_must_match_full_change_context(self):
        self.assert_denied(candidate=context(assignment_after=assignment(position_id=ASSIGNMENT_ID)),code="INCONSISTENT_PERSON")
        self.assert_denied(candidate=context(assignment_after=assignment(person_source_id="EMP-B")),code="INCONSISTENT_PERSON")
        self.assert_denied(candidate=context("assignment.update",expected_revision=2),code="REVISION_CONFLICT")
        self.assert_denied(candidate=context("assignment.update",assignment_after=assignment(revision=3)),code="REVISION_CONFLICT")
        self.assert_denied(candidate=context("assignment.update",assignment_after=assignment(valid_from_utc="2026-10-11T00:00:00Z",revision=2)),code="NEW_RELATION_REQUIRED")

    def test_position_create_update_and_read_use_only_their_own_operation(self):
        for verb in ("create","update","read"):
            policy = approved_policy(rules=[rule(operation_ids=[PREFIX+"position."+verb],person_scope=None,assignment_until_limit_utc=None)])
            self.assertTrue(self.evaluate([policy],context("position."+verb)).matched)
        policy = approved_policy(rules=[rule(operation_ids=[PREFIX+"position.update"],person_scope=None,assignment_until_limit_utc=None)])
        self.assert_denied([policy],context("position.update",position_after=position(company_id="CO-B",revision=2)),code="NEW_RELATION_REQUIRED")

    def test_person_lookup_is_separate_from_assignment_write(self):
        self.assert_denied(candidate=context("person.lookup"))
        policy = approved_policy(rules=[rule(operation_ids=[PREFIX+"person.lookup"],assignment_until_limit_utc=None)])
        self.assertTrue(self.evaluate([policy],context("person.lookup")).matched)

    def test_assignment_read_does_not_require_new_assignment_end_or_active_employee(self):
        policy = approved_policy(rules=[rule(operation_ids=[PREFIX+"assignment.read"],assignment_until_limit_utc=None)])
        person = context_payload()["person"]
        person["employee_status"] = "Left"
        self.assertTrue(self.evaluate([policy],context("assignment.read",person=person,assignment_before=assignment(valid_until_utc=None))).matched)

    def test_context_digest_binds_time_actor_and_entire_proposed_facts(self):
        first = self.evaluate()
        changed = self.evaluate(candidate=context(now_utc="2026-10-10T00:00:00.000001Z"))
        self.assertNotEqual(first.context_digest, changed.context_digest)
        changed = self.evaluate(candidate=context(assignment_after=assignment(is_primary=False)))
        self.assertNotEqual(first.context_digest, changed.context_digest)
        self.assert_denied([replace(self.policy,status="revoked")])
        self.assertTrue(first.matched)  # Old evidence is not reused by evaluation.

    def test_unknown_fields_and_wrong_types_not_silently_ignored(self):
        for key in ("actor","approved","policy_ref","ignore_permissions","sql","method"):
            self.assert_invalid(lambda: parse_policy(policy_payload(**{key:True})),"INVALID_FIELDS")
            self.assert_invalid(lambda: parse_management_context(context_payload(**{key:True}),
                site_id=SITE,policy_provider_id=PROVIDER,actor_user=ACTOR,actor_enabled=True),"INVALID_FIELDS")
        self.assert_invalid(lambda: parse_policy(policy_payload(revision=True)),"INVALID_VERSION")
        self.assert_invalid(lambda: context(assignment_after=assignment(is_primary=1)),"INVALID_TYPE")
        self.assert_invalid(lambda: self.evaluate([True]),"INVALID_TYPE")

    def test_direct_dataclass_construction_is_revalidated_before_matching(self):
        forged = replace(self.policy,rules=(replace(self.policy.rules[0],include_children=True),))
        self.assert_invalid(lambda: self.evaluate([forged]),"UNSUPPORTED_SCOPE")
        forged = replace(self.context,now_utc=datetime(2026,10,10))
        self.assert_invalid(lambda: self.evaluate(candidate=forged),"INVALID_TIME")

    def test_inconsistent_person_or_context_shape_cannot_match(self):
        person = context_payload()["person"]
        self.assert_invalid(lambda: context(person={**person,"link_status":"unknown"}),"INCONSISTENT_PERSON")
        self.assert_denied(candidate=context(position_after=position()),code="INVALID_CONTEXT")
        self.assert_denied(candidate=context("assignment.read",assignment_after=assignment()),code="INVALID_CONTEXT")
        self.assert_denied(candidate=context("person.lookup",position_before=position()),code="INVALID_CONTEXT")

    def test_clean_process_imports_and_evaluation_without_runtime_io(self):
        root = Path(__file__).resolve().parents[1]
        script = '''
import builtins, socket, subprocess, sys
from unittest.mock import patch
real_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name.split('.')[0] in ('frappe', 'requests', 'httpx'):
        raise AssertionError('runtime import forbidden')
    return real_import(name, *args, **kwargs)
with patch('builtins.__import__', side_effect=guarded_import), patch('builtins.open', side_effect=AssertionError('file I/O')), patch.object(socket, 'socket', side_effect=AssertionError('network I/O')), patch.object(subprocess, 'Popen', side_effect=AssertionError('process I/O')):
    from hbos_portal.organization.management_policy import evaluate_management_policy
    from tests.test_management_policy import parse_policy, policy_payload, approved_policy, parse_management_context, context_payload, SITE, PROVIDER, ACTOR
    policy = parse_policy(policy_payload())
    candidate = parse_management_context(context_payload(),site_id=SITE,policy_provider_id=PROVIDER,actor_user=ACTOR,actor_enabled=True)
    result = evaluate_management_policy([policy],candidate,enabled=True)
    assert not result.matched and not result.runtime_verified
    result = evaluate_management_policy([approved_policy()],candidate,enabled=True)
    assert result.matched and result.validation_only and not result.runtime_verified
'''
        env = {**os.environ,"PYTHONPATH":str(root),"PYTHONDONTWRITEBYTECODE":"1"}
        process = subprocess.run([sys.executable,"-c",script],env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(process.returncode,0,process.stderr)


if __name__ == "__main__":
    unittest.main()
