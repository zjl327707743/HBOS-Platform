"""Explicit existing-Preview acceptance for locked native sources/management.

No migration, production activation or public API. Committed synthetic fixtures
are removed by exact generated IDs, followed by native preservation checks.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
import json
import unittest
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.frappe_repository import FrappeRelationRepository
from hbos_portal.organization.frappe_source_loader import FrappeLockedSourceLoader
from hbos_portal.organization.relation_service import ManagementDecision, RelationService
from hbos_portal.organization.source_adapter import resolve_person
from hbos_portal.organization.storage_schema import (
    ASSIGNMENT, LOCK_KEY, POSITION, RECEIPT, receipt_key,
)
if __package__:
    from .integration_organization_storage import (
        SITE, DB_HASH, KINDS, DatabaseCases, check_target, native_fingerprints, preflight, schema_check,
    )
else:
    from integration_organization_storage import (
        SITE, DB_HASH, KINDS, DatabaseCases, check_target, native_fingerprints, preflight, schema_check,
    )


class NativeSourceCases(unittest.TestCase):
    native = None

    def setUp(self):
        f = self.native
        f.db.rollback()
        self.before = native_fingerprints(f)
        self.fixture = DatabaseCases()
        self.fixture.native = f
        self.fixture.setUp()
        self.repo = self.fixture.repo
        self.loader = FrappeLockedSourceLoader(self.repo, enabled=True, expected_site=SITE,
                                               expected_database_sha256=DB_HASH)
        self.service = self.fixture.service
        self.service.source_loader = self.loader
        self.users = tuple(self.fixture.prefix.lower() + suffix + "@example.invalid" for suffix in ("-a", "-b"))
        self.employees = (self.fixture.employee, self.fixture.prefix + "-EMP-SECOND")
        self.requests = set()
        for user in self.users:
            f.db.sql("INSERT INTO `tabUser` (name,email,enabled,user_type,modified) VALUES (%s,%s,1,'System User',NOW(6))", (user, user))
        f.db.sql("UPDATE `tabEmployee` SET user_id=%s,modified=NOW(6) WHERE name=%s", (self.users[0], self.fixture.employee))
        f.db.commit()  # Required for separate source-writer connections; Preview only.

    def tearDown(self):
        f = self.native
        f.db.rollback()
        ids = [row[0] for row in f.db.sql("SELECT name FROM `tabHBOS Position` WHERE company=%s", (self.fixture.company,))]
        for key in ids:
            assignments = [row[0] for row in f.db.sql("SELECT name FROM `tabHBOS Personnel Assignment` WHERE position=%s", (key,))]
            for assignment in assignments:
                f.db.sql("DELETE FROM `tabHBOS Personnel Assignment Revision` WHERE assignment=%s", (assignment,))
                f.db.sql("DELETE FROM `tabHBOS Personnel Assignment` WHERE name=%s", (assignment,))
            f.db.sql("DELETE FROM `tabHBOS Position Revision` WHERE position=%s", (key,))
            f.db.sql("DELETE FROM `tabHBOS Position` WHERE name=%s", (key,))
        for key in self.requests:
            f.db.sql("DELETE FROM `tabHBOS Organization Command Receipt` WHERE name=%s", (key,))
        for employee in self.employees:
            f.db.sql("DELETE FROM `tabEmployee` WHERE name=%s", (employee,))
        for user in self.users:
            f.db.sql("DELETE FROM `tabUser` WHERE name=%s", (user,))
        for kind, key in (("Designation", self.fixture.designation), ("Department", self.fixture.department),
                          ("Company", self.fixture.company)):
            f.db.sql(f"DELETE FROM `tab{kind}` WHERE name=%s", (key,))
        f.db.sql("DELETE FROM `tabHBOS Organization Write Lock` WHERE name=%s", (LOCK_KEY,))
        f.db.commit()
        self.assertEqual(native_fingerprints(f), self.before)
        self.assertTrue(all(f.db.count(kind) == 0 for kind in KINDS))
        f.db.rollback()

    def command(self, command, payload, **options):
        args = dict(idempotency_key=str(uuid4()), expected_revision=0, reason="来源与管理边界合成验收")
        args.update(options)
        self.requests.add(receipt_key(SITE, "Administrator", command, args["idempotency_key"]))
        return self.service.execute(command, payload, **args)

    def position(self):
        return self.command("create_position", self.fixture.position_payload()).record_id

    def load(self):
        with self.repo.transaction():
            self.repo.lock_writer()
            return self.loader()

    def assert_code(self, code, action):
        with self.assertRaises(ContractError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def restart_stale_request(self, action):
        # This Preview enables innodb_snapshot_isolation: stale locking reads
        # abort the whole transaction. The adapter must fail closed, without a
        # savepoint error or automatic replay. Model an explicit new request.
        self.assert_code("RELATION_TRANSACTION_RETRY_REQUIRED", action)
        self.native.db.rollback()
        return action()

    def external(self, action):
        # Each action receives its own Frappe local + native database connection.
        def worker():
            import frappe
            frappe.init(site=SITE, sites_path=".")
            frappe.connect()
            try:
                check_target(frappe, DB_HASH)
                frappe.db.rollback()
                frappe.set_user("Administrator")
                frappe.db.sql("SET SESSION innodb_lock_wait_timeout=2")
                result = action(frappe)
                frappe.db.commit()
                return result
            finally:
                frappe.db.rollback()
                frappe.destroy()
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(worker).result(timeout=12)

    def external_command(self, command, payload, **options):
        args = dict(idempotency_key=str(uuid4()), expected_revision=0, reason="来源与管理边界合成验收")
        args.update(options)
        self.requests.add(receipt_key(SITE, "Administrator", command, args["idempotency_key"]))
        def execute(f):
            repo = FrappeRelationRepository(native=f, enabled=True)
            loader = FrappeLockedSourceLoader(repo, enabled=True, expected_site=SITE, expected_database_sha256=DB_HASH)
            service = RelationService(repo, enabled=True, actor_resolver=lambda: "Administrator", source_loader=loader,
                clock=lambda: datetime(2026, 10, 9, tzinfo=timezone.utc),
                management_check=lambda a,c,co,de,p: ManagementDecision(a,c,co,de,"SYNTHETIC-MANAGEMENT",p))
            return service.execute(command, payload, **args)
        return self.external(execute)

    def test_current_source_overrides_established_repeatable_read_snapshot(self):
        f = self.native
        self.assertEqual(f.db.sql("SELECT status FROM `tabEmployee` WHERE name=%s", (self.fixture.employee,))[0][0], "Active")
        self.external(lambda other: other.db.sql("UPDATE `tabEmployee` SET status='Left',modified=NOW(6) WHERE name=%s", (self.fixture.employee,)))
        self.assertEqual(f.db.sql("SELECT status FROM `tabEmployee` WHERE name=%s", (self.fixture.employee,))[0][0], "Active")
        snapshot = self.restart_stale_request(self.load)
        person = resolve_person(snapshot, "Employee", self.fixture.employee)
        self.assertEqual(person.employee_status, "Left")
        self.assertEqual(person.qualification_status, "unknown")
        self.assertFalse(person.runtime_verified)

    def test_employee_link_phantom_insert_blocked_then_ambiguity_detected(self):
        def insert(other):
            try:
                other.db.sql("INSERT INTO `tabEmployee` (name,user_id,company,department,designation,status,date_of_joining,modified) VALUES (%s,%s,%s,%s,%s,'Active','2026-01-01',NOW(6))",
                    (self.employees[1], self.users[0], self.fixture.company, self.fixture.department, self.fixture.designation))
                return "inserted"
            except Exception as error:
                current = error
                while current is not None:
                    if (current.args and current.args[0] == 1205) or type(current).__name__ == "QueryTimeoutError":
                        return "lock_timeout"
                    current = current.__cause__ or current.__context__
                raise
        with self.repo.transaction():
            self.repo.lock_writer()
            self.loader()
            self.assertEqual(self.external(insert), "lock_timeout")
        self.native.db.rollback()
        self.assertEqual(self.external(insert), "inserted")
        person = resolve_person(self.load(), "User", self.users[0])
        self.assertEqual(person.link_status, "ambiguous")
        self.assertIsNone(person.subject_user)
        self.native.db.rollback()
        position = self.position()
        self.assert_code("PERSON_ASSOCIATION_UNRESOLVED", lambda: self.command("create_assignment", self.fixture.assignment_payload(position)))

    def test_disabled_actor_rejected_even_with_management_callback(self):
        self.external(lambda other: other.db.sql("UPDATE `tabUser` SET enabled=0,modified=NOW(6) WHERE name=%s", (self.users[0],)))
        self.service.actor_resolver = lambda: self.users[0]
        self.assert_code("MANAGEMENT_DENIED", lambda: self.position())
        self.assertEqual(self.native.db.count(POSITION), 0)

    def test_relinked_employee_does_not_transfer_existing_assignment_subject(self):
        position = self.position()
        payload = self.fixture.assignment_payload(position)
        assignment = self.command("create_assignment", payload)
        self.native.db.commit()
        self.external(lambda other: other.db.sql("UPDATE `tabEmployee` SET user_id=%s,modified=NOW(6) WHERE name=%s", (self.users[1], self.fixture.employee)))
        self.assert_code("SOURCE_ASSOCIATION_CHANGED", lambda: self.command("update_assignment", payload,
            record_id=assignment.record_id, expected_revision=1))
        self.assertEqual(self.repo.get_master(ASSIGNMENT, assignment.record_id)["subject_user"], self.users[0])

    def test_boolean_cross_company_department_and_person_decisions_rejected(self):
        position = self.position()
        payload = self.fixture.assignment_payload(position)
        for change in ("boolean", "company", "department", "person_source_id"):
            def policy(a,c,co,de,p):
                decision = ManagementDecision(a,c,co,de,"SYNTHETIC-MANAGEMENT",p)
                return True if change == "boolean" else replace(decision, **{change:"wrong-scope"})
            self.service.management_check = policy
            with self.subTest(change=change):
                self.assert_code("MANAGEMENT_DENIED", lambda: self.command("create_assignment", payload))
        self.assertEqual(self.native.db.count(ASSIGNMENT), 0)

    def test_second_management_check_denies_new_write_and_receipt_replay(self):
        key = str(uuid4())
        self.command("create_position", self.fixture.position_payload(), idempotency_key=key)
        def revoking_policy():
            calls = [0]
            def policy(a,c,co,de,p):
                calls[0] += 1
                return ManagementDecision(a,c,co,de,"SYNTHETIC-MANAGEMENT",p) if calls[0] == 1 else None
            return policy
        self.service.management_check = revoking_policy()
        self.assert_code("MANAGEMENT_DENIED", lambda: self.command("create_position", self.fixture.position_payload(), idempotency_key=key))
        self.service.management_check = revoking_policy()
        self.assert_code("MANAGEMENT_DENIED", self.position)
        self.assertEqual(self.native.db.count(POSITION), 1)
        self.assertEqual(self.native.db.count(RECEIPT), 1)

    def test_receipt_replay_sees_commit_after_old_snapshot(self):
        f = self.native
        self.assertEqual(f.db.count(RECEIPT), 0)
        key = str(uuid4())
        original = self.external_command("create_position", self.fixture.position_payload(), idempotency_key=key)
        self.assertEqual(f.db.count(RECEIPT), 0)  # Existing consistent view remains old.
        result = self.restart_stale_request(lambda: self.command("create_position", self.fixture.position_payload(), idempotency_key=key))
        self.assertTrue(result.replayed)
        self.assertEqual(result.record_id, original.record_id)

    def test_position_disable_after_old_snapshot_prevents_active_assignment(self):
        f = self.native
        position = self.position()
        f.db.commit()
        self.assertEqual(f.db.sql("SELECT status FROM `tabHBOS Position` WHERE name=%s", (position,))[0][0], "active")
        self.external_command("update_position", {**self.fixture.position_payload(),"status":"inactive"},
                              record_id=position,expected_revision=1)
        self.assertEqual(f.db.sql("SELECT status FROM `tabHBOS Position` WHERE name=%s", (position,))[0][0], "active")
        self.assert_code("INACTIVE_POSITION", lambda: self.restart_stale_request(
            lambda: self.command("create_assignment", self.fixture.assignment_payload(position))))

    def test_assignment_overlap_detects_commit_after_old_snapshot(self):
        f = self.native
        first, second = self.position(), self.position()
        f.db.commit()
        self.assertEqual(f.db.count(ASSIGNMENT), 0)
        self.external_command("create_assignment", self.fixture.assignment_payload(first))
        self.assertEqual(f.db.count(ASSIGNMENT), 0)
        self.assert_code("OVERLAPPING_PRIMARY", lambda: self.restart_stale_request(
            lambda: self.command("create_assignment", self.fixture.assignment_payload(second))))

    def test_disabled_department_is_not_hidden_by_old_snapshot(self):
        f = self.native
        self.assertEqual(f.db.sql("SELECT disabled FROM `tabDepartment` WHERE name=%s", (self.fixture.department,))[0][0], 0)
        self.external(lambda other: other.db.sql("UPDATE `tabDepartment` SET disabled=1,modified=NOW(6) WHERE name=%s", (self.fixture.department,)))
        self.assert_code("DISABLED_ORGANIZATION", lambda: self.restart_stale_request(self.position))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("preflight","test"), default="preflight")
    parser.add_argument("--expected-database-sha256", required=True)
    args = parser.parse_args()
    import frappe
    frappe.init(site=SITE,sites_path=".")
    frappe.connect()
    try:
        frappe.db.sql("START TRANSACTION READ ONLY")
        report = check_target(frappe,args.expected_database_sha256)
        report["preflight"] = preflight(frappe)
        report["schema"] = schema_check(frappe)
        if any(frappe.db.count(kind) for kind in KINDS):
            raise RuntimeError("RELATION_TABLES_NOT_EMPTY")
        frappe.db.rollback()
        if args.phase == "test":
            frappe.set_user("Administrator")
            NativeSourceCases.native = frappe
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeSourceCases))
            report["tests_run"] = result.testsRun
            report["test_status"] = "PASS" if result.wasSuccessful() else "FAIL"
            report["final_native_counts"] = preflight(frappe)["native_counts"]
            report["final_relation_counts"] = {kind:frappe.db.count(kind) for kind in KINDS}
            print(json.dumps(report,ensure_ascii=False,default=str))
            if not result.wasSuccessful(): raise SystemExit(1)
        else:
            print(json.dumps(report,ensure_ascii=False,default=str))
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__": main()
