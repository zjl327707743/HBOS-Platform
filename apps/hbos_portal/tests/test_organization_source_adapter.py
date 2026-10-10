"""Synthetic source snapshots only: no Frappe, Site, credentials or I/O."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import unittest

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.source_adapter import (
    adapt_assignment, adapt_position, build_source_snapshot,
    decode_utc_datetime, encode_utc_datetime, interval_contains,
    parse_rfc3339_utc, resolve_person,
)


STAMP = "2026-10-09 08:00:00.123456"
UTC = timezone.utc


def sources():
    return {
        "User": [{"name": "SYNTHETIC-USER", "enabled": 1,
                  "user_type": "Website User", "modified": STAMP}],
        "Employee": [{"name": "SYNTHETIC-EMP", "user_id": "SYNTHETIC-USER",
                      "company": "COMPANY-A", "department": "DEPT-A",
                      "designation": "TYPE-A", "status": "Active",
                      "date_of_joining": "2026-01-01", "relieving_date": None,
                      "modified": STAMP}],
        "Company": [{"name": "COMPANY-A", "modified": STAMP}],
        "Department": [
            {"name": "ROOT", "company": None, "parent_department": None,
             "is_group": 1, "disabled": 0, "modified": STAMP},
            {"name": "DEPT-A", "company": "COMPANY-A", "parent_department": "ROOT",
             "is_group": 0, "disabled": 0, "modified": STAMP},
            {"name": "DEPT-B", "company": "COMPANY-A", "parent_department": "ROOT",
             "is_group": 0, "disabled": 0, "modified": STAMP},
        ],
        "Designation": [{"name": "TYPE-A", "modified": STAMP}],
    }


def snapshot(rows=None, complete=True):
    return build_source_snapshot(
        site_id="synthetic-site", provider_id="synthetic-provider",
        captured_at="2026-10-09T08:00:00+08:00",
        rows_by_type=sources() if rows is None else rows,
        employee_links_complete=complete,
    )


def position(identifier="POSITION-A", department="DEPT-A"):
    return {"name": identifier, "title": "合成检验岗位", "company": "COMPANY-A",
            "department": department, "designation": "TYPE-A", "status": "active",
            "revision": 2, "authorization_generation": 3, "modified": STAMP}


def assignment():
    return {"name": "ASSIGNMENT-A", "person_source_type": "Employee",
            "person_source_id": "SYNTHETIC-EMP", "subject_user": "SYNTHETIC-USER",
            "position": "POSITION-A", "is_primary": 1,
            "valid_from_utc": "2026-10-10 01:00:00.000000",
            "valid_until_utc": "2026-10-31 16:00:00.000000", "status": "active",
            "revision": 4, "authorization_generation": 5, "modified": STAMP}


class SourceSnapshotTests(unittest.TestCase):
    def test_snapshots_are_copies_and_deeply_immutable(self):
        rows = sources()
        result = snapshot(rows)
        rows["User"][0]["enabled"] = 0
        self.assertTrue(result.rows["User"]["SYNTHETIC-USER"]["enabled"])
        with self.assertRaises(TypeError):
            result.rows["User"]["SYNTHETIC-USER"]["enabled"] = False
        with self.assertRaises(TypeError):
            result.rows["User"] = {}
        with self.assertRaises(FrozenInstanceError):
            result.employee_links_complete = False
        self.assertTrue(result.validation_only)
        self.assertFalse(result.runtime_verified)
        self.assertEqual(result.coverage, "provided_set_only")

    def test_completeness_is_a_separate_explicit_declaration(self):
        rows = sources()
        partial = build_source_snapshot(site_id="synthetic", provider_id="synthetic",
                                        captured_at="2026-10-09T00:00:00Z", rows_by_type=rows)
        result = resolve_person(partial, "Employee", "SYNTHETIC-EMP")
        self.assertEqual(result.link_status, "unknown")
        self.assertIsNone(result.subject_user)
        self.assertIn("INCOMPLETE_LINK_SET", result.reason_codes)
        self.assertFalse(snapshot().runtime_verified)

    def test_duplicate_ids_missing_fields_and_unknown_types_rejected(self):
        for mode in ("duplicate", "missing", "unknown_type", "missing_table"):
            with self.subTest(mode=mode):
                rows = sources()
                if mode == "duplicate": rows["User"].append(dict(rows["User"][0]))
                elif mode == "missing": del rows["User"][0]["modified"]
                elif mode == "unknown_type": rows["arbitrary.secret"] = []
                else: del rows["Employee"]
                with self.assertRaises(ContractError): snapshot(rows)

    def test_native_check_fields_accept_only_boolean_or_integer_zero_one(self):
        for value in ("0", "1", 2, -1, 1.0, None):
            rows = sources(); rows["User"][0]["enabled"] = value
            with self.subTest(value=value), self.assertRaises(ContractError): snapshot(rows)
        for value in (0, 1, False, True):
            rows = sources(); rows["User"][0]["enabled"] = value
            self.assertIs(type(snapshot(rows).rows["User"]["SYNTHETIC-USER"]["enabled"]), bool)

    def test_unknown_fields_and_errors_never_echo_sensitive_payload(self):
        rows = sources(); rows["User"][0]["SECRET-SYNTHETIC-KEY"] = "SECRET-SYNTHETIC-VALUE"
        with self.assertRaises(ContractError) as caught: snapshot(rows)
        self.assertNotIn("SECRET-SYNTHETIC", str(caught.exception))
        self.assertEqual(caught.exception.code, "UNKNOWN_FIELD")

    def test_modified_is_preserved_without_becoming_an_integer_version(self):
        result = resolve_person(snapshot(), "Employee", "SYNTHETIC-EMP")
        self.assertEqual({f.modified for f in result.fingerprints}, {STAMP})
        self.assertFalse(hasattr(result, "authorization_generation"))
        self.assertEqual(snapshot().context.captured_at, datetime(2026, 10, 9, tzinfo=UTC))

    def test_completeness_flag_and_employee_dates_use_strict_types(self):
        with self.assertRaises(ContractError): snapshot(complete=1)
        for value in ("20260101", "2026-01-01T00:00:00Z", datetime(2026, 1, 1), None):
            rows = sources(); rows["Employee"][0]["date_of_joining"] = value
            with self.subTest(value=value), self.assertRaises(ContractError): snapshot(rows)

    def test_fresh_process_import_and_adaptation_have_no_runtime_io(self):
        script = r'''
import builtins, os, sys
def blocked(*args, **kwargs):
    raise AssertionError("runtime side effect")
class BlockEnvironment(dict):
    __getitem__ = get = __iter__ = __contains__ = blocked
os.environ = BlockEnvironment()
os.getenv = blocked
original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name.split(".")[0] in {"frappe", "socket", "sqlite3", "pymysql"}:
        blocked()
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
def audit(event, args):
    if event.startswith(("socket.", "subprocess.", "os.mkdir", "os.remove", "os.rename")):
        blocked()
    if event == "open":
        path, mode, flags = args
        if (mode and any(c in mode for c in "wa+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)):
            blocked()
        if not str(path).endswith((".py", ".pyc")):
            blocked()
sys.addaudithook(audit)
from tests.test_organization_source_adapter import snapshot, position, assignment
from hbos_portal.organization.source_adapter import adapt_position, adapt_assignment
snap = snapshot()
result = adapt_assignment(assignment(), snap, (adapt_position(position(), snap),))
assert result.runtime_verified is False
assert result.projection.qualification_status == "unknown"
assert "frappe" not in sys.modules
print("SOURCE IO PASS")
'''
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "SOURCE IO PASS")


class PersonSourceTests(unittest.TestCase):
    def test_unique_website_user_link_is_not_employee_qualification(self):
        result = resolve_person(snapshot(), "Employee", "SYNTHETIC-EMP")
        self.assertEqual(result.link_status, "linked")
        self.assertEqual(result.subject_user, "SYNTHETIC-USER")
        self.assertEqual(result.qualification_status, "unknown")
        self.assertIn("EMPLOYEE_DATE_POLICY_UNRESOLVED", result.reason_codes)
        self.assertFalse(result.runtime_verified)

    def test_user_and_employee_aliases_resolve_to_same_canonical_reference(self):
        employee = resolve_person(snapshot(), "Employee", "SYNTHETIC-EMP")
        user = resolve_person(snapshot(), "User", "SYNTHETIC-USER")
        self.assertEqual(employee.canonical_person_ref, user.canonical_person_ref)
        self.assertEqual(user.canonical_person_ref.source_type, "Employee")
        self.assertNotEqual(employee.requested_ref, user.requested_ref)

    def test_empty_employee_source_never_fabricates_employee(self):
        rows = sources(); rows["Employee"] = []
        result = resolve_person(snapshot(rows), "User", "SYNTHETIC-USER")
        self.assertEqual(result.link_status, "unlinked")
        self.assertIsNone(result.subject_user)
        self.assertIsNone(result.canonical_person_ref)
        self.assertIn("EMPLOYEE_MISSING", result.reason_codes)
        self.assertEqual(len(snapshot(rows).rows["Employee"]), 0)

    def test_employee_without_user_preserves_source_and_unlinked_state(self):
        rows = sources(); rows["Employee"][0]["user_id"] = ""
        result = resolve_person(snapshot(rows), "Employee", "SYNTHETIC-EMP")
        self.assertEqual(result.qualification_status, "unlinked")
        self.assertIsNone(result.subject_user)
        self.assertEqual(result.canonical_person_ref, result.requested_ref)

    def test_multiple_links_including_inactive_history_are_ambiguous(self):
        for status in ("Active", "Inactive", "Suspended", "Left"):
            rows = sources(); other = dict(rows["Employee"][0], name="EMP-OTHER", status=status)
            rows["Employee"].append(other)
            for kind, key in (("User", "SYNTHETIC-USER"), ("Employee", "SYNTHETIC-EMP")):
                with self.subTest(status=status, kind=kind):
                    result = resolve_person(snapshot(rows), kind, key)
                    self.assertEqual(result.qualification_status, "ambiguous")
                    self.assertIsNone(result.subject_user)
                    self.assertIsNone(result.canonical_person_ref)

    def test_one_visible_link_does_not_prove_global_uniqueness(self):
        result = resolve_person(snapshot(complete=False), "User", "SYNTHETIC-USER")
        self.assertEqual(result.link_status, "unknown")
        self.assertIsNone(result.subject_user)
        rows = sources(); rows["Employee"].append(dict(rows["Employee"][0], name="OTHER"))
        self.assertEqual(resolve_person(snapshot(rows, False), "User", "SYNTHETIC-USER").link_status, "ambiguous")

    def test_dangling_and_reserved_users_do_not_become_subjects(self):
        rows = sources(); rows["User"] = []
        result = resolve_person(snapshot(rows), "Employee", "SYNTHETIC-EMP")
        self.assertIn("USER_MISSING", result.reason_codes)
        self.assertIsNone(result.subject_user)
        for reserved in ("Guest", "Administrator"):
            rows = sources(); rows["User"][0]["name"] = reserved
            rows["Employee"][0]["user_id"] = reserved
            result = resolve_person(snapshot(rows), "Employee", "SYNTHETIC-EMP")
            self.assertIn("RESERVED_ACCOUNT", result.reason_codes)
            self.assertIsNone(result.subject_user)

    def test_disabled_account_and_nonactive_employee_remain_unqualified(self):
        rows = sources(); rows["User"][0]["enabled"] = 0
        self.assertIn("ACCOUNT_DISABLED", resolve_person(snapshot(rows), "Employee", "SYNTHETIC-EMP").reason_codes)
        for status in ("Inactive", "Suspended", "Left"):
            rows = sources(); rows["Employee"][0]["status"] = status
            result = resolve_person(snapshot(rows), "Employee", "SYNTHETIC-EMP")
            self.assertEqual(result.qualification_status, "unknown")
            self.assertIn("EMPLOYEE_NOT_ACTIVE", result.reason_codes)

    def test_employee_dates_are_dates_without_implicit_midnight_policy(self):
        rows = sources(); rows["Employee"][0]["relieving_date"] = date(2026, 11, 1)
        result = resolve_person(snapshot(rows), "Employee", "SYNTHETIC-EMP")
        self.assertEqual(result.joining_date, date(2026, 1, 1))
        self.assertEqual(result.relieving_date, date(2026, 11, 1))
        self.assertIs(type(result.relieving_date), date)
        self.assertEqual(result.qualification_status, "unknown")

    def test_unknown_source_type_or_primary_key_is_rejected_without_guessing(self):
        for kind, key in (("Employee", "EMPLOYEE-NUMBER"), ("email", "SYNTHETIC-USER"), ("User", "missing")):
            with self.subTest(kind=kind), self.assertRaises(ContractError): resolve_person(snapshot(), kind, key)

    def test_ambiguity_is_preserved_even_when_linked_user_is_missing(self):
        rows = sources(); rows["User"] = []
        rows["Employee"].append(dict(rows["Employee"][0], name="OTHER"))
        result = resolve_person(snapshot(rows), "Employee", "SYNTHETIC-EMP")
        self.assertEqual(result.qualification_status, "ambiguous")
        self.assertIn("USER_MISSING", result.reason_codes)

    def test_organization_dependencies_and_inconsistent_dates_are_visible(self):
        rows = sources(); rows["Employee"][0]["relieving_date"] = "2025-12-31"
        result = resolve_person(snapshot(rows), "Employee", "SYNTHETIC-EMP")
        self.assertIn("EMPLOYEE_DATES_INCONSISTENT", result.reason_codes)
        self.assertEqual({f.reference.source_type for f in result.fingerprints},
                         {"Employee", "User", "Company", "Department", "Designation"})
        rows["Department"][1]["disabled"] = 1
        self.assertIn("EMPLOYEE_ORGANIZATION_UNRESOLVED",
                      resolve_person(snapshot(rows), "Employee", "SYNTHETIC-EMP").reason_codes)


class RelationshipMappingTests(unittest.TestCase):
    def test_same_labels_keep_distinct_ids_and_department_references(self):
        first = adapt_position(position(), snapshot())
        second = adapt_position(position("POSITION-B", "DEPT-B"), snapshot())
        self.assertEqual(first.projection.label, second.projection.label)
        self.assertNotEqual(first.projection.position_id, second.projection.position_id)
        self.assertNotEqual(first.projection.department_ref, second.projection.department_ref)
        self.assertEqual(first.authorization_generation, 3)
        self.assertFalse(hasattr(first.projection, "authorization_generation"))
        self.assertFalse(first.runtime_verified)

    def test_position_requires_real_department_company_and_category_references(self):
        for field, value in (("department", "ROOT"), ("department", "missing"),
                             ("company", "OTHER"), ("designation", "missing")):
            data = position(); data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ContractError): adapt_position(data, snapshot())
        rows = sources(); rows["Company"].append({"name": "OTHER", "modified": STAMP})
        data = position(); data["company"] = "OTHER"
        with self.assertRaises(ContractError): adapt_position(data, snapshot(rows))

    def test_disabled_dangling_cyclic_or_cross_company_ancestors_are_rejected(self):
        for mode in ("disabled", "parent_missing", "cycle", "cross_company", "unowned_nonroot"):
            rows = sources()
            if mode == "disabled": rows["Department"][0]["disabled"] = 1
            elif mode == "parent_missing": rows["Department"][1]["parent_department"] = "MISSING"
            elif mode == "cycle": rows["Department"][0]["parent_department"] = "DEPT-A"
            elif mode == "cross_company": rows["Department"][0]["company"] = "OTHER"
            else: rows["Department"][1]["company"] = None
            with self.subTest(mode=mode), self.assertRaises(ContractError): adapt_position(position(), snapshot(rows))

    def test_bool_or_missing_generations_are_not_replaced_with_modified(self):
        for field in ("revision", "authorization_generation"):
            for value in (True, 0, -1, "1", None):
                data = position(); data[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ContractError): adapt_position(data, snapshot())

    def test_assignment_maps_stable_source_revisions_and_explicit_utc_fields(self):
        snap = snapshot(); pos = adapt_position(position(), snap)
        result = adapt_assignment(assignment(), snap, (pos,))
        self.assertEqual(result.projection.person_ref.source_id, "SYNTHETIC-EMP")
        self.assertEqual(result.projection.valid_from, datetime(2026, 10, 10, 1, tzinfo=UTC))
        self.assertEqual(result.projection.authorization_generation, 5)
        self.assertEqual(result.projection.revision, 4)
        self.assertEqual(result.projection.qualification_status, "unknown")
        self.assertFalse(result.runtime_verified)
        self.assertFalse(result.projection.runtime_verified)

    def test_assignment_subject_claim_cannot_override_source_resolution(self):
        for mode in ("other_user", "ambiguous", "partial"):
            rows = sources(); data = assignment()
            if mode == "other_user": data["subject_user"] = "ANOTHER-USER"
            elif mode == "ambiguous": rows["Employee"].append(dict(rows["Employee"][0], name="OTHER"))
            snap = snapshot(rows, complete=mode != "partial")
            with self.subTest(mode=mode), self.assertRaises(ContractError):
                adapt_assignment(data, snap, (adapt_position(position(), snap),))

    def test_unlinked_assignment_stays_unlinked_without_creating_account(self):
        rows = sources(); rows["Employee"][0]["user_id"] = None
        snap = snapshot(rows); data = assignment(); data["subject_user"] = None
        result = adapt_assignment(data, snap, (adapt_position(position(), snap),))
        self.assertIsNone(result.projection.subject_user)
        self.assertEqual(result.projection.qualification_status, "unlinked")

    def test_assignment_rejects_unknown_position_or_cross_company_employee(self):
        snap = snapshot()
        with self.assertRaises(ContractError): adapt_assignment(assignment(), snap, ())
        rows = sources(); rows["Company"].append({"name": "OTHER", "modified": STAMP})
        rows["Employee"][0]["company"] = "OTHER"; rows["Employee"][0]["department"] = None
        snap = snapshot(rows)
        with self.assertRaises(ContractError): adapt_assignment(assignment(), snap, (adapt_position(position(), snap),))

    def test_secondary_assignment_does_not_require_employee_department_to_match(self):
        rows = sources(); before = deepcopy(rows); snap = snapshot(rows)
        data = assignment(); data["position"] = "POSITION-B"; data["is_primary"] = 0
        result = adapt_assignment(data, snap, (adapt_position(position("POSITION-B", "DEPT-B"), snap),))
        self.assertFalse(result.projection.is_primary)
        self.assertEqual(snap.rows["Employee"]["SYNTHETIC-EMP"]["department"], "DEPT-A")
        self.assertEqual(rows, before)

    def test_evidence_from_different_snapshot_cannot_be_mixed(self):
        original = snapshot(); rows = sources(); rows["Department"][1]["modified"] = "changed-opaque"
        newer = snapshot(rows)
        with self.assertRaises(ContractError): adapt_assignment(assignment(), newer, (adapt_position(position(), original),))

    def test_assignment_invalid_intervals_versions_and_extra_fields_are_rejected(self):
        snap = snapshot(); pos = adapt_position(position(), snap)
        for mode in ("empty", "reversed", "generation", "revision", "extra"):
            data = assignment()
            if mode == "empty": data["valid_until_utc"] = data["valid_from_utc"]
            elif mode == "reversed": data["valid_until_utc"] = "2026-01-01 00:00:00"
            elif mode == "extra": data["approved"] = True
            else: data["authorization_generation" if mode == "generation" else "revision"] = True
            with self.subTest(mode=mode), self.assertRaises(ContractError): adapt_assignment(data, snap, (pos,))
        data = assignment(); data["valid_until_utc"] = None
        self.assertIsNone(adapt_assignment(data, snap, (pos,)).projection.valid_until)

    def test_optional_designation_is_not_replaced_with_a_concrete_position(self):
        data = position(); data["designation"] = None
        result = adapt_position(data, snapshot())
        self.assertIsNone(result.designation_ref)
        self.assertEqual(result.projection.position_id, "POSITION-A")


class TimeCodecTests(unittest.TestCase):
    def test_offsets_normalize_and_preserve_microseconds(self):
        expected = datetime(2026, 10, 10, 1, 2, 3, 123456, tzinfo=UTC)
        self.assertEqual(parse_rfc3339_utc("2026-10-10T09:02:03.123456+08:00"), expected)
        self.assertEqual(parse_rfc3339_utc("2026-10-10T01:02:03.123456Z"), expected)
        self.assertEqual(parse_rfc3339_utc("2026-10-09T20:02:03.123456-05:00"), expected)

    def test_naive_dates_invalid_offsets_and_precision_loss_are_rejected(self):
        for value in ("2026-10-10", "2026-10-10T01:00:00", "2026-10-10 01:00:00Z",
                      "2026-02-30T00:00:00Z", "2026-10-10T00:00:00+24:00",
                      "2026-10-10T00:00:00+08:60", "2026-10-10T00:00:00-00:00",
                      "2026-10-10T00:00:00.1234567Z", None, True):
            with self.subTest(value=value), self.assertRaises(ContractError): parse_rfc3339_utc(value)

    def test_explicit_utc_storage_round_trip_does_not_assume_local_timezone(self):
        value = datetime(2026, 10, 10, 9, 1, 2, 3, timezone(timedelta(hours=8)))
        encoded = encode_utc_datetime(value)
        self.assertIsNone(encoded.tzinfo)
        self.assertEqual(encoded, datetime(2026, 10, 10, 1, 1, 2, 3))
        self.assertEqual(decode_utc_datetime(encoded), value.astimezone(UTC))
        self.assertEqual(decode_utc_datetime("2026-10-10 01:01:02.000003"), value.astimezone(UTC))

    def test_codec_rejects_aware_storage_and_naive_protocol_datetime(self):
        for value in (datetime(2026, 10, 10, tzinfo=UTC), "2026-10-10T00:00:00Z", "2026-10-10", ""):
            with self.subTest(value=value), self.assertRaises(ContractError): decode_utc_datetime(value)
        with self.assertRaises(ContractError): encode_utc_datetime(datetime(2026, 10, 10))

    def test_half_open_expiry_is_independent_of_scheduler_or_browser_clock(self):
        start = parse_rfc3339_utc("2026-10-10T09:00:00+08:00")
        end = parse_rfc3339_utc("2026-11-01T00:00:00+08:00")
        self.assertTrue(interval_contains(start, start, end))
        self.assertTrue(interval_contains(end - timedelta(microseconds=1), start, end))
        self.assertFalse(interval_contains(end, start, end))
        self.assertFalse(interval_contains(start - timedelta(microseconds=1), start, None))
        self.assertTrue(interval_contains(end, start, None))
        with self.assertRaises(ContractError): interval_contains(start, end, start)


if __name__ == "__main__":
    unittest.main()
