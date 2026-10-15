"""Explicit CLI acceptance for the existing empty Preview; never auto-discovered.

Run from frappe-bench/sites with the bench Python. This file is not an RPC or a
migration hook. prepare only reloads the six fixed DocTypes after checking a
private backup; test fixtures are rolled back. It never calls Employee.save.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
from threading import Barrier
import unittest
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.frappe_repository import FrappeRelationRepository
from hbos_portal.organization.relation_service import ManagementDecision, RelationService
from hbos_portal.organization.source_adapter import build_source_snapshot, decode_utc_datetime
from hbos_portal.organization.storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, LOCK_KEY, POSITION, POSITION_REVISION, RECEIPT, WRITE_LOCK,
    receipt_key,
)

SITE = "portal-preview.localhost"
DB_HASH = "c1278fd11beed36c90a5d0b507015749e5c14a4627249507aeef9b95a726f953"
KINDS = (WRITE_LOCK, POSITION, ASSIGNMENT, POSITION_REVISION, ASSIGNMENT_REVISION, RECEIPT)
SOURCE_FIELDS = {
    "User": ("name", "enabled", "user_type", "modified"),
    "Employee": ("name", "user_id", "company", "department", "designation", "status",
                 "date_of_joining", "relieving_date", "modified"),
    "Company": ("name", "modified"),
    "Department": ("name", "company", "parent_department", "is_group", "disabled", "modified"),
    "Designation": ("name", "modified"),
}


def check_target(native, expected_hash):
    """A test-site flag alone is insufficient; bind the exact audited database."""
    info = native.db.sql("SELECT DATABASE(), @@hostname, VERSION(), @@tx_isolation")[0]
    actual = hashlib.sha256(info[0].encode()).hexdigest()
    if (native.local.site != SITE or expected_hash != DB_HASH or actual != expected_hash
            or native.conf.get("hbos_account_test_site") != 1):
        raise RuntimeError("PREVIEW_TARGET_MISMATCH")
    return {"site": SITE, "database_sha256": actual, "server": info[1],
            "database_version": info[2], "isolation": info[3]}


def native_fingerprints(native):
    # Hash in memory only. Never print User, credential, or role rows.
    result = {}
    for table in ("tabUser", "__Auth", "tabHas Role", "tabUser Permission", "tabEmployee",
                  "tabCompany", "tabDepartment", "tabDesignation"):
        rows = native.db.sql(f"SELECT * FROM `{table}`", as_dict=True)
        encoded = sorted(json.dumps(dict(row), sort_keys=True, default=str) for row in rows)
        result[table] = hashlib.sha256(json.dumps(encoded).encode()).hexdigest()
    return result


def preflight(native):
    counts = {kind: native.db.sql(f"SELECT COUNT(*) FROM `tab{kind}`")[0][0] for kind in SOURCE_FIELDS}
    names = {row[0] for row in native.db.sql("SELECT name FROM `tabUser`")}
    if names != {"Guest", "Administrator"} or any(counts[kind] for kind in SOURCE_FIELDS if kind != "User"):
        raise RuntimeError("PREVIEW_NOT_EMPTY")
    presence = {kind: bool(native.db.sql(
        "SELECT 1 FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=%s",
        ("tab" + kind,))) for kind in KINDS}
    return {"native_counts": counts, "tables_present": presence}


def verify_backup(native, stem):
    if not stem or Path(stem).name != stem or not stem.endswith("-portal-preview_localhost"):
        raise RuntimeError("BACKUP_STEM_REQUIRED")
    base = Path(native.get_site_path("private", "backups")).resolve()
    files = [base / (stem + suffix) for suffix in (
        "-site_config_backup.json", "-database.sql.gz", "-files.tar", "-private-files.tar")]
    if any(not path.is_file() or path.is_symlink() for path in files):
        raise RuntimeError("BACKUP_INCOMPLETE")
    config = json.loads(files[0].read_text())
    if hashlib.sha256(str(config.get("db_name", "")).encode()).hexdigest() != DB_HASH:
        raise RuntimeError("BACKUP_DATABASE_MISMATCH")
    # Read all compressed bytes to validate gzip CRC, without emitting SQL.
    with gzip.open(files[1], "rb") as handle:
        sql = handle.read()
    if b"CREATE TABLE `tabUser`" not in sql or b"INSERT INTO `tabUser`" not in sql:
        raise RuntimeError("BACKUP_SQL_INCOMPLETE")
    for path in files[2:]:
        with tarfile.open(path) as handle:
            handle.getmembers()  # No extraction or path execution.
    return {"backup_stem": stem, "files": [
        {"name": path.name, "bytes": path.stat().st_size,
         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in files],
        "archive_integrity": "PASS", "full_restore": "NOT_RUN"}


def schema_check(native):
    result = {}
    for kind in KINDS:
        table = "tab" + kind
        rows = native.db.sql(
            "SELECT engine FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=%s", (table,))
        if not rows or rows[0][0] != "InnoDB":
            raise RuntimeError("STORAGE_ENGINE_MISMATCH")
        indexes = native.db.sql(f"SHOW INDEX FROM `{table}`", as_dict=True)
        unique_keys = {row["Column_name"] for row in indexes if not row["Non_unique"]}
        if not {"name", "record_key"} <= unique_keys:
            raise RuntimeError("STORAGE_UNIQUE_KEY_MISSING")
        times = native.db.sql(
            "SELECT column_name, datetime_precision FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=%s AND column_name LIKE %s",
            (table, "%\\_utc"))
        if any(precision != 6 for name, precision in times):
            raise RuntimeError("UTC_PRECISION_MISMATCH")
        meta = native.get_meta(kind)
        if meta.permissions or meta.allow_rename or meta.allow_import:
            raise RuntimeError("GENERAL_RELATION_WRITE_PERMISSION")
        result[kind] = {"engine": "InnoDB", "unique_columns": sorted(unique_keys),
                        "utc_precision": dict(times), "permissions": []}
    return result


def source_loader(native):
    selected = {}
    for kind, fields in SOURCE_FIELDS.items():
        # Fixed table/field names; full unpaginated fixture Site, no client input.
        rows = native.db.sql("SELECT " + ",".join("`" + field + "`" for field in fields)
                             + f" FROM `tab{kind}`", as_dict=True)
        selected[kind] = [{**dict(row), "modified": str(row.modified)} for row in rows]
    return build_source_snapshot(site_id=native.local.site, provider_id="s02.preview.acceptance",
        captured_at=datetime.now(timezone.utc).isoformat(), rows_by_type=selected, employee_links_complete=True)


class DatabaseCases(unittest.TestCase):
    native = None

    def setUp(self):
        f = self.native
        f.db.rollback()
        self.before = native_fingerprints(f)
        self.prefix = "S02-CHECK-" + uuid4().hex[:12]
        self.company, self.department, self.designation, self.employee = (
            self.prefix + suffix for suffix in ("-CO", "-DEPT", "-TYPE", "-EMP"))
        # Fixtures deliberately avoid business controllers and their side effects;
        # these INSERTs are allowed only in the exact empty Preview and rolled back.
        f.db.sql("INSERT INTO `tabCompany` (name,modified) VALUES (%s,NOW(6))", (self.company,))
        f.db.sql("INSERT INTO `tabDepartment` (name,company,is_group,disabled,modified) VALUES (%s,%s,0,0,NOW(6))", (self.department, self.company))
        f.db.sql("INSERT INTO `tabDesignation` (name,modified) VALUES (%s,NOW(6))", (self.designation,))
        f.db.sql("INSERT INTO `tabEmployee` (name,company,department,designation,status,date_of_joining,modified) VALUES (%s,%s,%s,%s,'Active','2026-01-01',NOW(6))", (self.employee, self.company, self.department, self.designation))
        self.repo = FrappeRelationRepository(enabled=True, native=f)
        self.repo.initialize_write_lock()
        self.service = RelationService(self.repo, enabled=True, actor_resolver=lambda: "Administrator",
            source_loader=lambda: source_loader(f), clock=lambda: datetime(2026, 10, 9, tzinfo=timezone.utc),
            management_check=lambda a, c, co, de, p: ManagementDecision(a, c, co, de, "S02-SYNTHETIC-ONLY", p))

    def tearDown(self):
        self.native.db.rollback()
        self.assertEqual(native_fingerprints(self.native), self.before)
        for kind in KINDS:
            self.assertEqual(self.native.db.sql(f"SELECT COUNT(*) FROM `tab{kind}`")[0][0], 0)
        self.native.db.rollback()

    def command(self, command, payload, **options):
        args = {"idempotency_key": str(uuid4()), "expected_revision": 0,
                "reason": "S02 隔离合成存储验收"}
        args.update(options)
        return self.service.execute(command, payload, **args)

    def position_payload(self):
        return dict(title="合成岗位", company=self.company, department=self.department,
                    designation=self.designation, status="active")

    def position(self):
        return self.command("create_position", self.position_payload())

    def assignment_payload(self, position):
        return dict(person_source_type="Employee", person_source_id=self.employee, position=position,
                    is_primary=True, valid_from="2026-10-10T09:00:00.123456+08:00", valid_until=None, status="active")

    def test_position_revision_and_idempotency(self):
        key = str(uuid4())
        first = self.command("create_position", self.position_payload(), idempotency_key=key)
        replay = self.command("create_position", self.position_payload(), idempotency_key=key)
        self.assertEqual(first.record_id, replay.record_id)
        self.assertTrue(replay.replayed)
        changed = self.command("update_position", {**self.position_payload(), "title": "合成改名"},
                               record_id=first.record_id, expected_revision=1)
        self.assertEqual((changed.revision, changed.authorization_generation), (2, 1))
        self.assertEqual(self.native.db.count(POSITION_REVISION), 2)
        with self.assertRaises(ContractError) as caught:
            self.command("update_position", self.position_payload(), record_id=first.record_id, expected_revision=1)
        self.assertEqual(caught.exception.code, "REVISION_CONFLICT")

    def test_assignment_utc_roundtrip_and_primary_conflict(self):
        first = self.position()
        result = self.command("create_assignment", self.assignment_payload(first.record_id))
        row = self.repo.get_master(ASSIGNMENT, result.record_id)
        self.assertEqual(row["valid_from_utc"], "2026-10-10 01:00:00.123456")
        self.assertIsNone(row["subject_user"])
        self.assertEqual(decode_utc_datetime(row["valid_from_utc"]).microsecond, 123456)
        second = self.position()
        with self.assertRaises(ContractError) as caught:
            self.command("create_assignment", self.assignment_payload(second.record_id))
        self.assertEqual(caught.exception.code, "OVERLAPPING_PRIMARY")
        self.assertEqual(self.native.db.count(ASSIGNMENT), 1)

    def test_failed_receipt_rolls_back_master_and_revision(self):
        original = self.repo.insert_receipt
        def fail(*args):
            original(*args)
            raise RuntimeError("S02_INJECTED_RECEIPT_FAILURE")
        self.repo.insert_receipt = fail
        with self.assertRaisesRegex(RuntimeError, "S02_INJECTED_RECEIPT_FAILURE"):
            self.position()
        for kind in (POSITION, POSITION_REVISION, RECEIPT):
            self.assertEqual(self.native.db.count(kind), 0)

    def test_direct_orm_flags_and_partial_writes_rejected(self):
        key = str(uuid4())
        doc = self.native.get_doc({"doctype": POSITION, **self.position_payload(), "record_key": key,
            "revision": 1, "authorization_generation": 1,
            "source_provider": "hbos_portal.organization.v1", "source_key": key})
        doc.flags.ignore_validate = True
        with self.assertRaises(self.native.PermissionError):
            doc.insert(ignore_permissions=True)
        result = self.position()
        doc = self.native.get_doc(POSITION, result.record_id)
        doc.flags.ignore_validate = True
        doc.title = "绕过修改"
        for action in (lambda: doc.save(ignore_permissions=True), doc.db_update,
                       lambda: doc.db_set("title", "绕过修改"),
                       lambda: self.native.delete_doc(POSITION, doc.name, ignore_permissions=True),
                       lambda: self.native.rename_doc(POSITION, doc.name, str(uuid4()), force=True)):
            with self.assertRaises(self.native.PermissionError):
                action()
        self.assertEqual(self.repo.get_master(POSITION, result.record_id)["title"], "合成岗位")

    def test_history_cannot_be_overwritten(self):
        self.position()
        row = self.native.get_all(POSITION_REVISION, fields=["name"])[0]
        doc = self.native.get_doc(POSITION_REVISION, row.name)
        doc.flags.ignore_validate = True
        doc.reason = "绕过历史修改"
        with self.assertRaises(self.native.PermissionError):
            doc.save(ignore_permissions=True)

    def test_physical_uniqueness(self):
        result = self.position()
        # Raw SQL is used only to prove the physical key, not as an allowed writer.
        with self.assertRaises(Exception) as caught:
            self.native.db.sql("INSERT INTO `tabHBOS Position` (name,record_key) VALUES (%s,%s)",
                               (str(uuid4()), result.record_id))
        self.assertTrue(self.native.db.is_unique_key_violation(caught.exception))


def concurrency_check(native):
    """Separate native connections, with bounded committed fixtures and exact cleanup.

    Only controlled-command races are covered. This does not prove closure with
    native Employee writers, Grant revocation, business writes or phantom links.
    """
    before = native_fingerprints(native)
    if any(native.db.count(kind) for kind in KINDS):
        raise RuntimeError("RELATION_TABLES_NOT_EMPTY")
    native.db.rollback()
    fixture = DatabaseCases()
    fixture.native = native
    fixture.setUp()
    known_receipts = set()
    outcomes = {}

    def race(jobs):
        barrier = Barrier(len(jobs), timeout=15)
        for command, payload, options in jobs:
            known_receipts.add(receipt_key(SITE, "Administrator", command, options["idempotency_key"]))

        def worker(job):
            import frappe
            frappe.init(site=SITE, sites_path=".")
            frappe.connect()
            try:
                frappe.set_user("Administrator")
                frappe.db.sql("SET SESSION innodb_lock_wait_timeout=15")
                frappe.db.rollback()
                repo = FrappeRelationRepository(enabled=True, native=frappe)
                service = RelationService(repo, enabled=True, actor_resolver=lambda: "Administrator",
                    source_loader=lambda: source_loader(frappe), clock=lambda: datetime(2026, 10, 9, tzinfo=timezone.utc),
                    management_check=lambda a, c, co, de, p: ManagementDecision(a, c, co, de, "S02-SYNTHETIC-ONLY", p))
                barrier.wait()
                command, payload, options = job
                try:
                    result = service.execute(command, payload, **options)
                    frappe.db.commit()  # Only these exact synthetic concurrency commands.
                    return {"status": "success", **asdict(result)}
                except ContractError as error:
                    return {"status": error.code}
            finally:
                frappe.db.rollback()
                frappe.destroy()

        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            results = list(pool.map(worker, jobs))
        native.db.rollback()  # Refresh main-connection REPEATABLE READ snapshot.
        return results

    def options(**extra):
        return {"idempotency_key": str(uuid4()), "expected_revision": 0,
                "reason": "S02 隔离并发验收", **extra}

    try:
        native.db.commit()  # Minimal native fixture + writer root, Preview only.
        shared = options()
        job = ("create_position", fixture.position_payload(), shared)
        replay_results = race([job, job])
        if (len({row.get("record_id") for row in replay_results}) != 1
                or sorted(row.get("replayed") for row in replay_results) != [False, True]
                or native.db.count(POSITION) != 1 or native.db.count(POSITION_REVISION) != 1
                or native.db.count(RECEIPT) != 1):
            raise RuntimeError("CONCURRENT_IDEMPOTENCY_FAILED")
        outcomes["same_key_create"] = "PASS"
        original_id = replay_results[0]["record_id"]

        ids = []
        for _ in range(2):
            request = options()
            known_receipts.add(receipt_key(SITE, "Administrator", "create_position", request["idempotency_key"]))
            ids.append(fixture.service.execute("create_position", fixture.position_payload(), **request).record_id)
        native.db.commit()
        primary_results = race([("create_assignment", fixture.assignment_payload(key), options()) for key in ids])
        if sorted(row["status"] for row in primary_results) != ["OVERLAPPING_PRIMARY", "success"]:
            raise RuntimeError("CONCURRENT_PRIMARY_FAILED")
        if native.db.count(ASSIGNMENT) != 1 or native.db.count(ASSIGNMENT_REVISION) != 1:
            raise RuntimeError("CONCURRENT_PRIMARY_COUNT_FAILED")
        outcomes["overlapping_primary"] = "PASS"

        update_results = race([("update_position", {**fixture.position_payload(), "title": title},
            options(expected_revision=1, record_id=original_id)) for title in ("并发改名甲", "并发改名乙")])
        if sorted(row["status"] for row in update_results) != ["REVISION_CONFLICT", "success"]:
            raise RuntimeError("CONCURRENT_REVISION_FAILED")
        if fixture.repo.get_master(POSITION, original_id)["revision"] != 2:
            raise RuntimeError("CONCURRENT_REVISION_COUNT_FAILED")
        outcomes["same_revision_update"] = "PASS"
    finally:
        # DML cleanup uses only this run's exact generated company / IDs / keys.
        # It deliberately bypasses immutable controllers solely to remove fixtures.
        native.db.rollback()
        position_ids = [row[0] for row in native.db.sql("SELECT name FROM `tabHBOS Position` WHERE company=%s", (fixture.company,))]
        for key in position_ids:
            assignment_ids = [row[0] for row in native.db.sql("SELECT name FROM `tabHBOS Personnel Assignment` WHERE position=%s", (key,))]
            for assignment in assignment_ids:
                native.db.sql("DELETE FROM `tabHBOS Personnel Assignment Revision` WHERE assignment=%s", (assignment,))
                native.db.sql("DELETE FROM `tabHBOS Personnel Assignment` WHERE name=%s", (assignment,))
            native.db.sql("DELETE FROM `tabHBOS Position Revision` WHERE position=%s", (key,))
            native.db.sql("DELETE FROM `tabHBOS Position` WHERE name=%s", (key,))
        for key in known_receipts:
            native.db.sql("DELETE FROM `tabHBOS Organization Command Receipt` WHERE name=%s", (key,))
        native.db.sql("DELETE FROM `tabHBOS Organization Write Lock` WHERE name=%s", (LOCK_KEY,))
        for kind, key in (("Employee", fixture.employee), ("Designation", fixture.designation),
                          ("Department", fixture.department), ("Company", fixture.company)):
            native.db.sql(f"DELETE FROM `tab{kind}` WHERE name=%s", (key,))
        native.db.commit()
        if native_fingerprints(native) != before or any(native.db.count(kind) for kind in KINDS):
            raise RuntimeError("CONCURRENCY_CLEANUP_FAILED")
        native.db.rollback()
    return {"cases": outcomes, "independent_database_connections": True,
            "native_preservation": "PASS", "relation_tables_empty": True,
            "native_writer_and_business_closure": "NOT_RUN"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("preflight", "prepare", "test", "concurrency"), default="preflight")
    parser.add_argument("--expected-database-sha256", required=True)
    parser.add_argument("--backup-stem")
    args = parser.parse_args()
    import frappe
    frappe.init(site=SITE, sites_path=".")
    frappe.connect()
    try:
        frappe.db.sql("START TRANSACTION READ ONLY")
        report = check_target(frappe, args.expected_database_sha256)
        report["preflight"] = preflight(frappe)
        frappe.db.rollback()
        if args.phase == "prepare":
            if any(report["preflight"]["tables_present"].values()):
                raise RuntimeError("SCHEMA_ALREADY_PRESENT_REVIEW_REQUIRED")
            report["backup"] = verify_backup(frappe, args.backup_stem)
            before = native_fingerprints(frappe)
            frappe.set_user("Administrator")
            for kind in KINDS:
                frappe.reload_doc("hbos_portal", "doctype", kind.lower().replace(" ", "_"), force=True)
            frappe.db.commit()  # Explicit Preview-only DDL phase, never in service.
            report["schema"] = schema_check(frappe)
            if native_fingerprints(frappe) != before:
                raise RuntimeError("NATIVE_PRESERVATION_FAILED")
            report["native_preservation"] = "PASS"
        elif args.phase in ("test", "concurrency"):
            report["schema"] = schema_check(frappe)
            if any(frappe.db.count(kind) for kind in KINDS):
                raise RuntimeError("RELATION_TABLES_NOT_EMPTY")
            frappe.set_user("Administrator")
            if args.phase == "concurrency":
                report["concurrency"] = concurrency_check(frappe)
            else:
                DatabaseCases.native = frappe
                result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DatabaseCases))
                report["tests_run"] = result.testsRun
                report["test_status"] = "PASS" if result.wasSuccessful() else "FAIL"
                if not result.wasSuccessful():
                    raise SystemExit(1)
        print(json.dumps(report, ensure_ascii=False, default=str))
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
