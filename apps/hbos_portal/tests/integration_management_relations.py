"""Explicit exact-Preview acceptance for managed position/assignment writes.

No RPC, schema reload, real operator configuration or production activation.
Every committed fixture is synthetic and is removed by exact generated IDs.
Run from the existing frappe-bench/sites with the bench Python only.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
import json
import unittest
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.frappe_management_repository import (
    FrappeManagementPolicyRepository, ManagementPolicyStore,
)
from hbos_portal.organization.frappe_repository import FrappeRelationRepository
from hbos_portal.organization.frappe_source_loader import FrappeLockedSourceLoader
from hbos_portal.organization.managed_relations import ManagedRelationAdapter
from hbos_portal.organization.management_policy import management_policy_digest, parse_management_policy
from hbos_portal.organization.management_storage import (
    POLICY, POLICY_PROVIDER, POLICY_REVISION, PolicyApprovalPin, PinnedPolicyApprovalVerifier, policy_data,
)
from hbos_portal.organization.relation_service import RelationService
from hbos_portal.organization.storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, LOCK_KEY, POSITION, POSITION_REVISION,
    RECEIPT, canonical_json, receipt_key,
)
if __package__:
    from .integration_management_storage import policy_presence, policy_schema_check
    from .integration_organization_storage import (
        SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check,
    )
else:
    from integration_management_storage import policy_presence, policy_schema_check
    from integration_organization_storage import (
        SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check,
    )


POLICY_KINDS = (POLICY, POLICY_REVISION)
NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
OPERATIONS = (
    "hbos.organization.position.read", "hbos.organization.position.create",
    "hbos.organization.position.update", "hbos.organization.assignment.read",
    "hbos.organization.assignment.create", "hbos.organization.assignment.update",
    "hbos.organization.person.lookup",
)


class NativeManagedRelationCases(unittest.TestCase):
    native = None

    def setUp(self):
        f = self.native
        f.db.rollback()
        self.before = native_fingerprints(f)
        self.prefix = "MR-CHECK-" + uuid4().hex[:12]
        self.manager, self.approver, self.beneficiary = (
            self.prefix.lower() + suffix + "@example.invalid"
            for suffix in ("-manager", "-owner", "-person"))
        self.company = self.prefix + "-CO"
        self.department, self.other_department = (self.prefix + suffix for suffix in ("-DEPT", "-OTHER"))
        self.designation = self.prefix + "-TYPE"
        self.employee, self.manager_employee = (self.prefix + suffix for suffix in ("-EMP", "-MANAGER-EMP"))
        self.policy_id = str(uuid4())
        self.policy_ids = {self.policy_id}
        self.requests = set()
        self.pins = []
        self.addCleanup(self.cleanup)
        for user in (self.manager, self.approver, self.beneficiary):
            f.db.sql("INSERT INTO `tabUser` (name,email,enabled,user_type,modified) "
                     "VALUES (%s,%s,1,'System User',NOW(6))", (user, user))
        f.db.sql("INSERT INTO `tabCompany` (name,modified) VALUES (%s,NOW(6))", (self.company,))
        for department in (self.department, self.other_department):
            f.db.sql("INSERT INTO `tabDepartment` (name,company,is_group,disabled,modified) "
                     "VALUES (%s,%s,0,0,NOW(6))", (department, self.company))
        f.db.sql("INSERT INTO `tabDesignation` (name,modified) VALUES (%s,NOW(6))", (self.designation,))
        for employee, user in ((self.employee, self.beneficiary), (self.manager_employee, self.manager)):
            f.db.sql("INSERT INTO `tabEmployee` (name,user_id,company,department,designation,status,date_of_joining,modified) "
                     "VALUES (%s,%s,%s,%s,%s,'Active','2026-01-01',NOW(6))",
                     (employee, user, self.company, self.department, self.designation))
        self.repo = FrappeRelationRepository(native=f, enabled=True)
        self.repo.initialize_write_lock()
        f.db.commit()
        self.policy = self.make_policy()
        self.install(self.policy)
        f.db.commit()
        f.set_user(self.manager)
        self.service = self.make_service(f)

    def cleanup(self):
        f = self.native
        f.db.rollback()
        f.set_user("Administrator")
        position_ids = [row[0] for row in f.db.sql(
            "SELECT name FROM `tabHBOS Position` WHERE company=%s", (self.company,))]
        for position in position_ids:
            assignment_ids = [row[0] for row in f.db.sql(
                "SELECT name FROM `tabHBOS Personnel Assignment` WHERE position=%s", (position,))]
            for assignment in assignment_ids:
                f.db.sql("DELETE FROM `tabHBOS Personnel Assignment Revision` WHERE assignment=%s", (assignment,))
                f.db.sql("DELETE FROM `tabHBOS Personnel Assignment` WHERE name=%s", (assignment,))
            f.db.sql("DELETE FROM `tabHBOS Position Revision` WHERE position=%s", (position,))
            f.db.sql("DELETE FROM `tabHBOS Position` WHERE name=%s", (position,))
        for key in self.requests:
            f.db.sql("DELETE FROM `tabHBOS Organization Command Receipt` WHERE name=%s", (key,))
        for key in self.policy_ids:
            f.db.sql("DELETE FROM `tabHBOS Organization Management Policy Revision` WHERE policy=%s", (key,))
            f.db.sql("DELETE FROM `tabHBOS Organization Management Policy` WHERE name=%s", (key,))
        for employee in (self.employee, self.manager_employee):
            f.db.sql("DELETE FROM `tabEmployee` WHERE name=%s", (employee,))
        for user in (self.manager, self.approver, self.beneficiary):
            f.db.sql("DELETE FROM `tabUser` WHERE name=%s", (user,))
        for kind, key in (("Designation", self.designation), ("Department", self.department),
                          ("Department", self.other_department), ("Company", self.company)):
            f.db.sql(f"DELETE FROM `tab{kind}` WHERE name=%s", (key,))
        f.db.sql("DELETE FROM `tabHBOS Organization Write Lock` WHERE name=%s", (LOCK_KEY,))
        f.db.commit()
        self.assertEqual(native_fingerprints(f), self.before)
        self.assertTrue(all(f.db.count(kind) == 0 for kind in (*KINDS, *POLICY_KINDS)))
        f.db.rollback()

    def policy_repository(self, native, relations=None):
        return FrappeManagementPolicyRepository(
            relations or FrappeRelationRepository(native=native, enabled=True), enabled=True,
            expected_site=SITE, expected_database_sha256=DB_HASH)

    def approvals(self):
        return PinnedPolicyApprovalVerifier(tuple(self.pins))

    def make_policy(self, *, subject=None, policy_id=None, revision=1, generation=1, rules=None):
        subject = subject or self.manager
        rules = rules or [dict(rule_id="synthetic-complete-rule", operation_schema_version=1,
            operation_ids=list(OPERATIONS), company_id=self.company,
            target_department_ids=[self.department], include_children=False,
            assignment_until_limit_utc="2026-10-25T00:00:00Z",
            person_scope=dict(source_type="Employee", company_id=self.company,
                              department_ids=[self.department]))]
        payload = dict(policy_id=policy_id or self.policy_id, subject_user=subject, status="active",
            revision=revision, authority_generation=generation, schema_version=1,
            valid_from_utc="2026-10-09T00:00:00Z", valid_until_utc="2026-11-01T00:00:00Z",
            approval=None, rules=rules)
        row = parse_management_policy(payload, site_id=SITE, source_provider=POLICY_PROVIDER)
        payload["approval"] = dict(approval_ref="SYNTHETIC-PREVIEW-APPROVAL",
            approved_by=self.approver if subject != self.approver else self.manager,
            approved_at_utc="2026-10-09T00:00:00Z", approved_revision=revision,
            approved_authority_generation=generation, content_digest=management_policy_digest(row))
        return parse_management_policy(payload, site_id=SITE, source_provider=POLICY_PROVIDER)

    def install(self, policy, *, native=None, expected=0, approved=True):
        f = native or self.native
        previous = f.session.user
        self.policy_ids.add(policy.policy_id)
        if approved:
            self.pins.append(PolicyApprovalPin(SITE, DB_HASH, policy.policy_id, policy.revision,
                policy.authority_generation, policy.subject_user, management_policy_digest(policy),
                canonical_json(policy_data(policy)["approval"]), "SYNTHETIC-PREVIEW-ONLY"))
        try:
            f.set_user("Administrator")
            store = ManagementPolicyStore(self.policy_repository(f), clock=lambda: NOW,
                operator_users=("Administrator",), approval_verifier=self.approvals() if approved else None,
                enabled=True)
            return store.write(policy, expected_revision=expected, reason="管理事实写入隔离合成验收")
        finally:
            f.set_user(previous)

    def make_service(self, native, *, actor=None):
        repo = self.repo if native is self.native else FrappeRelationRepository(native=native, enabled=True)
        policies = self.policy_repository(native, repo)
        adapter = ManagedRelationAdapter(policies, approval_verifier=self.approvals(), enabled=True)
        loader = FrappeLockedSourceLoader(repo, enabled=True, expected_site=SITE,
                                          expected_database_sha256=DB_HASH)
        return RelationService(repo, enabled=True, actor_resolver=lambda: actor or native.session.user,
            source_loader=loader, clock=lambda: NOW, management_adapter=adapter)

    def options(self, command, *, actor=None, **extra):
        args = dict(idempotency_key=str(uuid4()), expected_revision=0, reason="管理事实写入隔离合成验收")
        args.update(extra)
        self.requests.add(receipt_key(SITE, actor or self.native.session.user, command, args["idempotency_key"]))
        return args

    def command(self, command, payload, **extra):
        return self.service.execute(command, payload, **self.options(command, **extra))

    def position_payload(self, **extra):
        return dict(title="合成管理岗位", company=self.company, department=self.department,
                    designation=self.designation, status="active") | extra

    def position(self):
        return self.command("create_position", self.position_payload()).record_id

    def assignment_payload(self, position, *, employee=None):
        return dict(person_source_type="Employee", person_source_id=employee or self.employee,
            position=position, is_primary=False, valid_from="2026-10-10T00:00:00Z",
            valid_until="2026-10-20T00:00:00Z", status="active")

    def counts(self):
        return tuple(self.native.db.count(kind) for kind in (
            POSITION, POSITION_REVISION, ASSIGNMENT, ASSIGNMENT_REVISION, RECEIPT))

    def denied_without_write(self, action, *, codes=None):
        before = self.counts()
        with self.assertRaises(ContractError) as caught:
            action()
        if codes is not None:
            self.assertIn(caught.exception.code, codes)
        self.assertEqual(self.counts(), before)
        return caught.exception.code

    def external(self, action, *, actor="Administrator"):
        def worker():
            import frappe
            frappe.init(site=SITE, sites_path=".")
            frappe.connect()
            try:
                check_target(frappe, DB_HASH)
                frappe.db.rollback()
                frappe.set_user(actor)
                frappe.db.sql("SET SESSION innodb_lock_wait_timeout=2")
                result = action(frappe)
                frappe.db.commit()
                return result
            finally:
                frappe.db.rollback()
                frappe.destroy()
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(worker).result(timeout=15)

    def test_complete_policy_writes_facts_and_records_protected_history(self):
        position = self.position()
        changed = self.command("update_position", {**self.position_payload(), "title": "合成改名"},
                               record_id=position, expected_revision=1)
        payload = self.assignment_payload(position)
        assignment = self.command("create_assignment", payload)
        ended = self.command("update_assignment", {**payload, "status": "revoked"},
                             record_id=assignment.record_id, expected_revision=1)
        self.assertEqual((changed.revision, ended.revision), (2, 2))
        self.assertEqual(self.repo.get_master(ASSIGNMENT, assignment.record_id)["subject_user"], self.beneficiary)
        evidence_rows = self.native.db.sql(
            "SELECT source_evidence_json FROM `tabHBOS Personnel Assignment Revision` WHERE assignment=%s",
            (assignment.record_id,))
        self.assertEqual(len(evidence_rows), 2)
        self.assertTrue(all("management_scope_v1" in json.loads(row[0]) for row in evidence_rows))
        self.assertTrue(ended.transaction_pending)
        self.assertEqual(ended.authorization_effect, "none")
        self.assertFalse(ended.runtime_verified)

    def test_create_and_update_receipt_replay_after_later_revision_has_no_new_write(self):
        create_args = self.options("create_position")
        first = self.service.execute("create_position", self.position_payload(), **create_args)
        update_payload = {**self.position_payload(), "title": "合成第一次改名"}
        update_args = self.options("update_position", record_id=first.record_id, expected_revision=1)
        second = self.service.execute("update_position", update_payload, **update_args)
        self.command("update_position", {**self.position_payload(), "title": "合成后续改名"},
                     record_id=first.record_id, expected_revision=2)
        before = self.counts()
        for command, payload, args, original in (
                ("create_position", self.position_payload(), create_args, first),
                ("update_position", update_payload, update_args, second)):
            replay = self.service.execute(command, payload, **args)
            self.assertTrue(replay.replayed)
            self.assertEqual((replay.record_id, replay.revision), (original.record_id, original.revision))
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.repo.get_master(POSITION, first.record_id)["revision"], 3)

    def test_finite_limit_and_cross_rule_scope_cannot_be_borrowed(self):
        position = self.position()
        payload = self.assignment_payload(position)
        for end in (None, "2026-10-26T00:00:00Z"):
            with self.subTest(end=end):
                self.denied_without_write(lambda: self.command("create_assignment", {**payload, "valid_until": end}))
        first = dict(rule_id="wrong-target-create", operation_schema_version=1,
            operation_ids=["hbos.organization.assignment.create"], company_id=self.company,
            target_department_ids=[self.other_department], include_children=False,
            assignment_until_limit_utc="2026-10-25T00:00:00Z",
            person_scope=dict(source_type="Employee", company_id=self.company, department_ids=[self.department]))
        second = {**first, "rule_id": "right-target-read", "operation_ids": ["hbos.organization.assignment.read"],
                  "target_department_ids": [self.department]}
        self.policy = self.make_policy(revision=2, generation=2, rules=[first, second])
        self.install(self.policy, expected=1)
        self.service = self.make_service(self.native)
        self.denied_without_write(lambda: self.command("create_assignment", payload))

    def test_self_creation_restore_extension_denied_but_strict_reduction_allowed(self):
        position = self.position()
        payload = self.assignment_payload(position, employee=self.manager_employee)
        self.denied_without_write(lambda: self.command("create_assignment", payload))
        owner_policy = self.make_policy(subject=self.approver, policy_id=str(uuid4()))
        self.install(owner_policy)
        self.native.set_user(self.approver)
        self.service = self.make_service(self.native)
        assignment = self.command("create_assignment", payload)
        self.native.set_user(self.manager)
        self.service = self.make_service(self.native)
        self.denied_without_write(lambda: self.command("update_assignment", {**payload, "valid_until": "2026-10-24T00:00:00Z"},
            record_id=assignment.record_id, expected_revision=1))
        self.native.set_user(self.approver)
        self.service = self.make_service(self.native)
        self.command("update_assignment", {**payload, "status": "inactive"}, record_id=assignment.record_id, expected_revision=1)
        self.native.set_user(self.manager)
        self.service = self.make_service(self.native)
        self.denied_without_write(lambda: self.command("update_assignment", payload,
            record_id=assignment.record_id, expected_revision=2))
        ended = self.command("update_assignment", {**payload, "status": "revoked"},
                             record_id=assignment.record_id, expected_revision=2)
        self.assertEqual(ended.revision, 3)

    def test_invalid_native_sources_allow_only_historical_strict_reduction(self):
        f = self.native
        for source in ("employee_relinked", "employee_left", "user_disabled", "department_disabled", "position_inactive"):
            with self.subTest(source=source):
                position = self.position()
                payload = self.assignment_payload(position)
                assignment = self.command("create_assignment", payload)
                f.db.commit()
                if source == "employee_relinked":
                    f.db.sql("UPDATE `tabEmployee` SET user_id=%s,modified=NOW(6) WHERE name=%s", (self.approver, self.employee))
                elif source == "employee_left":
                    f.db.sql("UPDATE `tabEmployee` SET status='Left',modified=NOW(6) WHERE name=%s", (self.employee,))
                elif source == "user_disabled":
                    f.db.sql("UPDATE `tabUser` SET enabled=0,modified=NOW(6) WHERE name=%s", (self.beneficiary,))
                elif source == "department_disabled":
                    f.db.sql("UPDATE `tabDepartment` SET disabled=1,modified=NOW(6) WHERE name=%s", (self.department,))
                else:
                    self.command("update_position", {**self.position_payload(), "status": "inactive"}, record_id=position, expected_revision=1)
                f.db.commit()
                self.denied_without_write(lambda: self.command("update_assignment", {**payload, "valid_until": "2026-10-24T00:00:00Z"},
                    record_id=assignment.record_id, expected_revision=1))
                ended = self.command("update_assignment", {**payload, "status": "revoked"},
                                     record_id=assignment.record_id, expected_revision=1)
                row = self.repo.get_master(ASSIGNMENT, assignment.record_id)
                self.assertEqual((row["status"], row["subject_user"], ended.revision), ("revoked", self.beneficiary, 2))
                f.db.sql("UPDATE `tabEmployee` SET user_id=%s,status='Active',modified=NOW(6) WHERE name=%s", (self.beneficiary, self.employee))
                f.db.sql("UPDATE `tabUser` SET enabled=1,modified=NOW(6) WHERE name=%s", (self.beneficiary,))
                f.db.sql("UPDATE `tabDepartment` SET disabled=0,modified=NOW(6) WHERE name=%s", (self.department,))
                f.db.commit()

    def test_reduction_cannot_hide_extension_or_request_injected_history(self):
        position = self.position()
        payload = self.assignment_payload(position)
        assignment = self.command("create_assignment", payload)
        self.denied_without_write(lambda: self.command("update_assignment",
            {**payload, "status": "revoked", "valid_until": "2026-10-26T00:00:00Z"},
            record_id=assignment.record_id, expected_revision=1))
        self.denied_without_write(lambda: self.command("update_assignment",
            {**payload, "status": "revoked", "management_scope_v1": {"company": self.company}},
            record_id=assignment.record_id, expected_revision=1), codes={"INVALID_FIELDS"})

    def test_missing_historical_scope_refuses_disabled_source_cleanup(self):
        position = self.position()
        payload = self.assignment_payload(position)
        assignment = self.command("create_assignment", payload)
        self.native.db.commit()
        rows = self.native.db.sql("SELECT name,source_evidence_json FROM `tabHBOS Personnel Assignment Revision` WHERE assignment=%s",
                                  (assignment.record_id,))
        for key, raw in rows:
            evidence = json.loads(raw)
            evidence.pop("management_scope_v1", None)
            self.native.db.sql("UPDATE `tabHBOS Personnel Assignment Revision` SET source_evidence_json=%s WHERE name=%s",
                               (canonical_json(evidence), key))
        self.native.db.sql("UPDATE `tabDepartment` SET disabled=1,modified=NOW(6) WHERE name=%s", (self.department,))
        self.native.db.commit()
        self.denied_without_write(lambda: self.command("update_assignment", {**payload, "status": "revoked"},
            record_id=assignment.record_id, expected_revision=1), codes={"HISTORICAL_SCOPE_REQUIRED", "HISTORY_MISMATCH"})

    def test_disabled_or_resolver_mismatched_actor_cannot_write(self):
        self.service = self.make_service(self.native, actor=self.approver)
        self.denied_without_write(self.position)
        self.service = self.make_service(self.native)
        self.native.db.sql("UPDATE `tabUser` SET enabled=0,modified=NOW(6) WHERE name=%s", (self.manager,))
        self.denied_without_write(self.position)

    def test_receipt_failure_rolls_back_master_revision_and_receipt(self):
        original = self.repo.insert_receipt

        def fail(*args):
            original(*args)
            raise RuntimeError("SYNTHETIC_MANAGED_RECEIPT_FAILURE")

        before = self.counts()
        self.repo.insert_receipt = fail
        try:
            with self.assertRaisesRegex(RuntimeError, "SYNTHETIC_MANAGED_RECEIPT_FAILURE"):
                self.position()
        finally:
            self.repo.insert_receipt = original
        self.assertEqual(self.counts(), before)

    def test_policy_revocation_refuses_old_receipt_replay(self):
        args = self.options("create_position")
        self.service.execute("create_position", self.position_payload(), **args)
        self.native.db.commit()
        revoked = replace(self.policy, status="revoked", revision=2, authority_generation=2)
        self.install(revoked, expected=1, approved=False)
        self.native.db.commit()
        self.denied_without_write(lambda: self.service.execute("create_position", self.position_payload(), **args))

    def test_revoke_first_old_snapshot_requires_whole_request_restart_then_denies(self):
        self.native.db.commit()
        self.assertEqual(self.native.db.sql("SELECT status FROM `tabHBOS Organization Management Policy` WHERE name=%s",
                                           (self.policy_id,))[0][0], "active")
        revoked = replace(self.policy, status="revoked", revision=2, authority_generation=2)
        self.external(lambda f: self.install(revoked, native=f, expected=1, approved=False))
        self.assertEqual(self.native.db.sql("SELECT status FROM `tabHBOS Organization Management Policy` WHERE name=%s",
                                           (self.policy_id,))[0][0], "active")
        with self.assertRaises(ContractError) as caught:
            self.position()
        self.assertEqual(caught.exception.code, "RELATION_TRANSACTION_RETRY_REQUIRED")
        self.native.db.rollback()
        self.denied_without_write(self.position)

    def test_write_first_root_lock_blocks_revoke_and_next_request_denies(self):
        self.position()
        revoked = replace(self.policy, status="revoked", revision=2, authority_generation=2)

        def attempt(f):
            try:
                self.install(revoked, native=f, expected=1, approved=False)
            except Exception as error:
                current = error
                while current is not None:
                    if (current.args and current.args[0] == 1205) or type(current).__name__ == "QueryTimeoutError":
                        return "BLOCKED_BY_ROOT"
                    current = current.__cause__ or current.__context__
                raise
            return "UNEXPECTED_WRITE"

        self.assertEqual(self.external(attempt), "BLOCKED_BY_ROOT")
        self.native.db.commit()
        self.external(lambda f: self.install(revoked, native=f, expected=1, approved=False))
        self.native.db.rollback()
        self.denied_without_write(self.position)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("preflight", "test"), default="preflight")
    parser.add_argument("--expected-database-sha256", required=True)
    args = parser.parse_args()
    import frappe
    frappe.init(site=SITE, sites_path=".")
    frappe.connect()
    try:
        frappe.db.sql("START TRANSACTION READ ONLY")
        report = check_target(frappe, args.expected_database_sha256)
        report["preflight"] = preflight(frappe)
        report["policy_tables_present"] = policy_presence(frappe)
        if not all(report["preflight"]["tables_present"].values()):
            raise RuntimeError("RELATION_SCHEMA_REQUIRED")
        if not all(report["policy_tables_present"].values()):
            raise RuntimeError("POLICY_SCHEMA_REQUIRED")
        if any(frappe.db.count(kind) for kind in (*KINDS, *POLICY_KINDS)):
            raise RuntimeError("MANAGED_TABLES_NOT_EMPTY")
        report["relation_schema"] = schema_check(frappe)
        report["policy_schema"] = policy_schema_check(frappe)
        frappe.db.rollback()
        if args.phase == "test":
            before = native_fingerprints(frappe)
            NativeManagedRelationCases.native = frappe
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeManagedRelationCases)
            names = [test.id().rsplit(".", 1)[1] for test in suite]
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            report["tests_run"] = result.testsRun
            report["test_names"] = names
            report["test_status"] = "PASS" if result.wasSuccessful() else "FAIL"
            report["native_preservation"] = "PASS" if native_fingerprints(frappe) == before else "FAIL"
            report["final_native_counts"] = preflight(frappe)["native_counts"]
            report["final_managed_counts"] = {kind: frappe.db.count(kind) for kind in (*KINDS, *POLICY_KINDS)}
            report["tables_empty"] = not any(report["final_managed_counts"].values())
            report["limits"] = "Synthetic managed facts only; HTTP/session/CSRF, real management approval, Date qualification and business grants NOT_RUN."
            if not result.wasSuccessful() or not report["tables_empty"] or report["native_preservation"] != "PASS":
                print(json.dumps(report, ensure_ascii=False, default=str))
                raise SystemExit(1)
        print(json.dumps(report, ensure_ascii=False, default=str))
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
