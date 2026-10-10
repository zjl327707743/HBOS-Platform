"""Relationship command contract tests with an explicit transactional test store."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
from threading import RLock
import unittest
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.relation_service import ManagementDecision, RelationService
from hbos_portal.organization.source_adapter import decode_utc_datetime
from hbos_portal.organization.storage_schema import ASSIGNMENT, POSITION, digest, validate_storage_record
from tests.test_organization_source_adapter import STAMP, snapshot, sources


ACTOR = "SYNTHETIC-MANAGER"


class TransactionalTestStore:
    """Models the repository transaction/serialization contract, not MariaDB."""
    site_id = "synthetic-site"

    def __init__(self):
        self.masters, self.versions, self.receipts = {}, {}, {}
        self.mutex = RLock()
        self.fail_at = None
        self.locked_sources = []

    @contextmanager
    def transaction(self):
        with self.mutex:
            before = deepcopy((self.masters, self.versions, self.receipts))
            try:
                yield
            except BaseException:
                self.masters, self.versions, self.receipts = before
                raise

    def lock_writer(self):
        pass

    def lock_sources(self, references):
        self.locked_sources.append(references)

    def get_master(self, kind, key):
        value = self.masters.get((kind, key))
        return None if value is None else {**deepcopy(value), "_source_modified": STAMP}

    def list_assignments(self):
        return tuple(deepcopy(row) for (kind, key), row in self.masters.items() if kind == ASSIGNMENT)

    def get_receipt(self, key):
        return deepcopy(self.receipts.get(key))

    def save_master(self, kind, row, *, expected_revision):
        validate_storage_record(kind, row["record_key"], row.get)
        old = self.masters.get((kind, row["record_key"]))
        if (old is None and expected_revision != 0) or (old is not None and old["revision"] != expected_revision):
            raise ContractError("REVISION_CONFLICT", "store")
        self.masters[kind, row["record_key"]] = deepcopy(row)
        if self.fail_at == "master": raise RuntimeError("synthetic failure")

    def append_revision(self, kind, row):
        validate_storage_record(kind, row["record_key"], row.get)
        if row["record_key"] in self.versions: raise RuntimeError("duplicate revision")
        self.versions[row["record_key"]] = deepcopy(row)
        if self.fail_at == "version": raise RuntimeError("synthetic failure")

    def insert_receipt(self, key, row):
        if key in self.receipts: raise RuntimeError("duplicate receipt")
        self.receipts[key] = deepcopy(row)
        if self.fail_at == "receipt": raise RuntimeError("synthetic failure")


class RelationServiceTests(unittest.TestCase):
    def setUp(self):
        self.rows = sources()
        self.rows["User"].append({"name": ACTOR, "enabled": 1, "user_type": "System User", "modified": STAMP})
        self.snapshot = snapshot(self.rows)
        self.store = TransactionalTestStore()
        self.now = datetime(2026, 10, 9, tzinfo=timezone.utc)
        self.service = self.make_service()

    def make_service(self, **overrides):
        options = dict(actor_resolver=lambda: ACTOR, source_loader=lambda: self.snapshot,
                       clock=lambda: self.now, management_check=lambda a, c, co, de, p:
                       ManagementDecision(a, c, co, de, "SYNTHETIC-POLICY", p), enabled=True)
        options.update(overrides)
        return RelationService(self.store, **options)

    def command(self, name, payload, *, service=None, **kwargs):
        options = dict(idempotency_key=str(uuid4()), expected_revision=0 if name.startswith("create_") else 1,
                       reason="合成任职事实办理")
        options.update(kwargs)
        return (service or self.service).execute(name, payload, **options)

    def create_position(self, department="DEPT-A"):
        return self.command("create_position", self.position_payload(department))

    @staticmethod
    def position_payload(department="DEPT-A"):
        return dict(title="合成岗位", company="COMPANY-A", department=department, designation="TYPE-A", status="active")

    @staticmethod
    def assignment_payload(position):
        return dict(person_source_type="Employee", person_source_id="SYNTHETIC-EMP", position=position,
                    is_primary=True, valid_from="2026-10-10T09:00:00+08:00", valid_until=None, status="active")

    def update_position(self, key, **changes):
        old = self.store.get_master(POSITION, key)
        payload = {field: old[field] for field in ("title", "company", "department", "designation", "status")}
        payload.update(changes)
        return self.command("update_position", payload, record_id=key, expected_revision=old["revision"])

    def update_assignment(self, key, **changes):
        old = self.store.get_master(ASSIGNMENT, key)
        payload = {field: old[field] for field in ("person_source_type", "person_source_id", "position", "is_primary", "status")}
        payload["valid_from"] = decode_utc_datetime(old["valid_from_utc"]).isoformat()
        payload["valid_until"] = None if old["valid_until_utc"] is None else decode_utc_datetime(old["valid_until_utc"]).isoformat()
        payload.update(changes)
        return self.command("update_assignment", payload, record_id=key, expected_revision=old["revision"])

    def assert_code(self, code, function):
        with self.assertRaises(ContractError) as caught: function()
        self.assertEqual(caught.exception.code, code)

    def test_default_closed_and_missing_management_policy_do_not_touch_store(self):
        self.assert_code("WRITES_DISABLED", lambda: self.command("create_position", self.position_payload(), service=self.make_service(enabled=False)))
        self.assert_code("MANAGEMENT_DENIED", lambda: self.command("create_position", self.position_payload(), service=self.make_service(management_check=None)))
        self.assertEqual(self.store.masters, {})

    def test_management_decision_must_bind_actor_command_and_scope(self):
        for decision in (True, False, None, ManagementDecision("other", "create_position", "COMPANY-A", "DEPT-A", "policy"),
                         ManagementDecision(ACTOR, "create_position", "COMPANY-A", "DEPT-B", "policy")):
            service = self.make_service(management_check=lambda *args: decision)
            self.assert_code("MANAGEMENT_DENIED", lambda: self.command("create_position", self.position_payload(), service=service))
        self.assertEqual(self.store.receipts, {})

    def test_guest_disabled_or_missing_actor_is_denied(self):
        self.assert_code("MANAGEMENT_DENIED", lambda: self.command("create_position", self.position_payload(), service=self.make_service(actor_resolver=lambda: "Guest")))
        self.rows["User"][-1]["enabled"] = 0; self.snapshot = snapshot(self.rows)
        self.assert_code("MANAGEMENT_DENIED", lambda: self.create_position())

    def test_create_has_stable_identity_snapshot_and_no_grant_effect(self):
        result = self.create_position()
        master = self.store.get_master(POSITION, result.record_id)
        version = next(iter(self.store.versions.values()))
        self.assertEqual(master["revision"], 1)
        self.assertEqual(master["authorization_generation"], 1)
        self.assertEqual(json.loads(version["snapshot_json"])["record_key"], result.record_id)
        self.assertEqual(version["actor"], ACTOR)
        self.assertEqual(version["content_digest"], digest(json.loads(version["snapshot_json"])))
        self.assertTrue(result.transaction_pending)
        self.assertEqual(result.authorization_effect, "none")
        self.assertFalse(result.runtime_verified)

    def test_display_edit_increments_revision_and_preserves_old_snapshot(self):
        first = self.create_position(); old = deepcopy(self.store.versions)
        result = self.update_position(first.record_id, title="新的显示名称")
        self.assertEqual((result.revision, result.authorization_generation), (2, 1))
        self.assertEqual({key: self.store.versions[key] for key in old}, old)

    def test_disable_and_restore_advance_generation_without_reviving_grants(self):
        result = self.create_position()
        self.assertEqual(self.update_position(result.record_id, status="inactive").authorization_generation, 2)
        restored = self.update_position(result.record_id, status="active")
        self.assertEqual(restored.authorization_generation, 3)
        self.assertEqual(restored.authorization_effect, "none")

    def test_position_relocation_requires_new_identity(self):
        result = self.create_position()
        self.assert_code("NEW_RELATION_REQUIRED", lambda: self.update_position(result.record_id, department="DEPT-B"))
        self.assertEqual(self.store.get_master(POSITION, result.record_id)["revision"], 1)

    def test_stale_revision_rejected_without_partial_history(self):
        result = self.create_position(); self.update_position(result.record_id, title="新版")
        before = deepcopy(self.store.versions)
        self.assert_code("REVISION_CONFLICT", lambda: self.command("update_position", self.position_payload(), record_id=result.record_id))
        self.assertEqual(self.store.versions, before)

    def test_same_key_replays_and_changed_payload_conflicts(self):
        key = str(uuid4()); payload = self.position_payload()
        first = self.command("create_position", payload, idempotency_key=key)
        repeated = self.command("create_position", payload, idempotency_key=key)
        self.assertTrue(repeated.replayed)
        self.assertEqual(repeated.record_id, first.record_id)
        self.assertEqual(len(self.store.versions), 1)
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.command("create_position", {**payload, "title": "另一份内容"}, idempotency_key=key))

    def test_replay_rechecks_management_authority(self):
        key = str(uuid4()); self.command("create_position", self.position_payload(), idempotency_key=key)
        denied = self.make_service(management_check=lambda *args: False)
        self.assert_code("MANAGEMENT_DENIED", lambda: self.command("create_position", self.position_payload(), idempotency_key=key, service=denied))

    def test_same_request_key_is_namespaced_by_actor(self):
        self.rows["User"].append({"name": "OTHER-MANAGER", "enabled": 1, "user_type": "System User", "modified": STAMP})
        self.snapshot = snapshot(self.rows)
        key = str(uuid4()); first = self.command("create_position", self.position_payload(), idempotency_key=key)
        other = self.make_service(actor_resolver=lambda: "OTHER-MANAGER")
        second = self.command("create_position", self.position_payload(), idempotency_key=key, service=other)
        self.assertNotEqual(first.record_id, second.record_id)
        self.assertEqual(len(self.store.receipts), 2)

    def test_failure_at_each_persistence_phase_rolls_back_everything(self):
        for phase in ("master", "version", "receipt"):
            self.store.fail_at = phase
            with self.subTest(phase=phase), self.assertRaises(RuntimeError): self.create_position()
            self.assertEqual((self.store.masters, self.store.versions, self.store.receipts), ({}, {}, {}))

    def test_source_refresh_or_completeness_change_rejects_before_write(self):
        for mode in ("data", "coverage"):
            changed = deepcopy(self.rows)
            if mode == "data": changed["User"][0]["enabled"] = 0
            refreshed = snapshot(changed, complete=mode != "coverage")
            states = iter((self.snapshot, refreshed))
            service = self.make_service(source_loader=lambda: next(states))
            self.assert_code("SOURCE_CHANGED_RETRY", lambda: self.command("create_position", self.position_payload(), service=service))
        self.assertEqual(self.store.masters, {})

    def test_site_or_incomplete_source_cannot_be_used_for_writes(self):
        self.store.site_id = "another-site"
        self.assert_code("INCOMPLETE_SOURCE", lambda: self.create_position())
        self.store.site_id = "synthetic-site"; self.snapshot = snapshot(self.rows, complete=False)
        self.assert_code("INCOMPLETE_SOURCE", lambda: self.create_position())

    def test_client_cannot_set_actor_subject_generation_or_flags(self):
        for key in ("actor", "subject_user", "revision", "authorization_generation", "flags", "approved"):
            payload = self.position_payload(); payload[key] = True
            self.assert_code("INVALID_FIELDS", lambda: self.command("create_position", payload))
        self.assert_code("INVALID_VERSION", lambda: self.command("create_position", self.position_payload(), expected_revision=True))

    def test_assignment_records_fact_and_leaves_qualification_unresolved(self):
        position = self.create_position(); result = self.command("create_assignment", self.assignment_payload(position.record_id))
        row = self.store.get_master(ASSIGNMENT, result.record_id)
        self.assertEqual(row["subject_user"], "SYNTHETIC-USER")
        self.assertEqual(row["valid_from_utc"], "2026-10-10 01:00:00.000000")
        self.assertNotIn("qualification_status", row)
        self.assertEqual(result.authorization_effect, "none")

    def test_equivalent_timezone_input_replays_same_assignment(self):
        position = self.create_position(); payload = self.assignment_payload(position.record_id)
        key = str(uuid4()); first = self.command("create_assignment", payload, idempotency_key=key)
        payload["valid_from"] = "2026-10-10T01:00:00Z"
        repeated = self.command("create_assignment", payload, idempotency_key=key)
        self.assertTrue(repeated.replayed)
        self.assertEqual(first.record_id, repeated.record_id)

    def test_employee_without_account_can_have_fact_but_not_business_authorization(self):
        self.rows["Employee"][0]["user_id"] = None; self.snapshot = snapshot(self.rows)
        position = self.create_position(); result = self.command("create_assignment", self.assignment_payload(position.record_id))
        self.assertIsNone(self.store.get_master(ASSIGNMENT, result.record_id)["subject_user"])
        self.assertEqual(result.authorization_effect, "none")

    def test_user_only_and_ambiguous_person_cannot_be_accepted(self):
        position = self.create_position(); payload = self.assignment_payload(position.record_id)
        payload["person_source_type"] = "User"; payload["person_source_id"] = "SYNTHETIC-USER"
        self.assert_code("EMPLOYEE_SOURCE_REQUIRED", lambda: self.command("create_assignment", payload))
        self.rows["Employee"].append(dict(self.rows["Employee"][0], name="OTHER-EMP")); self.snapshot = snapshot(self.rows)
        self.assert_code("PERSON_ASSOCIATION_UNRESOLVED", lambda: self.command("create_assignment", self.assignment_payload(position.record_id)))

    def test_future_overlapping_primary_and_duplicate_position_are_rejected(self):
        first = self.create_position(); second = self.create_position("DEPT-B")
        self.command("create_assignment", self.assignment_payload(first.record_id))
        self.assert_code("OVERLAPPING_PRIMARY", lambda: self.command("create_assignment", self.assignment_payload(second.record_id)))
        payload = self.assignment_payload(first.record_id); payload["is_primary"] = False
        self.assert_code("DUPLICATE_ASSIGNMENT", lambda: self.command("create_assignment", payload))

    def test_adjacent_assignments_and_secondary_other_department_are_allowed(self):
        first = self.create_position(); second = self.create_position("DEPT-B")
        payload = self.assignment_payload(first.record_id); payload["valid_until"] = "2026-11-01T00:00:00+08:00"
        self.command("create_assignment", payload)
        payload = self.assignment_payload(second.record_id); payload["valid_from"] = "2026-11-01T00:00:00+08:00"
        self.command("create_assignment", payload)
        payload = self.assignment_payload(second.record_id); payload["is_primary"] = False; payload["valid_until"] = "2026-11-01T00:00:00+08:00"
        self.command("create_assignment", payload)
        self.assertEqual(self.snapshot.rows["Employee"]["SYNTHETIC-EMP"]["department"], "DEPT-A")

    def test_canonical_user_alias_cannot_bypass_overlap(self):
        first = self.create_position(); second = self.create_position("DEPT-B")
        result = self.command("create_assignment", self.assignment_payload(first.record_id))
        row = self.store.masters[ASSIGNMENT, result.record_id]
        row["person_source_type"], row["person_source_id"] = "User", "SYNTHETIC-USER"
        self.assert_code("OVERLAPPING_PRIMARY", lambda: self.command("create_assignment", self.assignment_payload(second.record_id)))

    def test_future_cutoff_does_not_early_revoke_but_extension_advances_generation(self):
        position = self.create_position(); result = self.command("create_assignment", self.assignment_payload(position.record_id))
        shortened = self.update_assignment(result.record_id, valid_until="2026-11-01T00:00:00+08:00")
        self.assertEqual(shortened.authorization_generation, 1)
        extended = self.update_assignment(result.record_id, valid_until="2026-12-01T00:00:00+08:00")
        self.assertEqual(extended.authorization_generation, 2)
        immediate = self.update_assignment(result.record_id, valid_until="2026-10-10T10:00:00+08:00")
        self.assertEqual(immediate.authorization_generation, 2)
        self.now = datetime(2026, 10, 11, tzinfo=timezone.utc)
        restored = self.update_assignment(result.record_id, valid_until=None)
        self.assertEqual(restored.authorization_generation, 3)

    def test_inactive_position_rejects_active_new_assignment(self):
        position = self.create_position(); self.update_position(position.record_id, status="inactive")
        self.assert_code("INACTIVE_POSITION", lambda: self.command("create_assignment", self.assignment_payload(position.record_id)))

    def test_immediate_cutoff_and_assignment_restore_advance_generation(self):
        position = self.create_position(); result = self.command("create_assignment", self.assignment_payload(position.record_id))
        self.now = datetime(2026, 10, 11, tzinfo=timezone.utc)
        ended = self.update_assignment(result.record_id, valid_until="2026-10-10T10:00:00+08:00")
        self.assertEqual(ended.authorization_generation, 2)
        stopped = self.update_assignment(result.record_id, status="inactive")
        self.assertEqual(stopped.authorization_generation, 3)
        restored = self.update_assignment(result.record_id, status="active", valid_until=None)
        self.assertEqual(restored.authorization_generation, 4)
        self.assertEqual(restored.authorization_effect, "none")

    def test_failed_update_keeps_previous_fact_and_history(self):
        result = self.create_position(); before = deepcopy((self.store.masters, self.store.versions, self.store.receipts))
        self.store.fail_at = "receipt"
        with self.assertRaises(RuntimeError): self.update_position(result.record_id, title="不会保存")
        self.assertEqual((self.store.masters, self.store.versions, self.store.receipts), before)

    def test_expired_or_future_intervals_are_all_scanned_beyond_a_page(self):
        first = self.create_position(); second = self.create_position("DEPT-B")
        row = self.command("create_assignment", self.assignment_payload(first.record_id))
        saved = self.store.masters.pop((ASSIGNMENT, row.record_id))
        for i in range(25):
            key = str(uuid4())
            self.store.masters[ASSIGNMENT, key] = {**saved, "record_key": key,
                "person_source_id": f"UNRELATED-LEGACY-{i}", "subject_user": None}
        self.store.masters[ASSIGNMENT, row.record_id] = saved
        self.assert_code("OVERLAPPING_PRIMARY", lambda: self.command("create_assignment", self.assignment_payload(second.record_id)))

    def test_invalid_stored_related_interval_is_rejected(self):
        first = self.create_position(); second = self.create_position("DEPT-B")
        result = self.command("create_assignment", self.assignment_payload(first.record_id))
        row = self.store.masters[ASSIGNMENT, result.record_id]
        row["valid_until_utc"] = row["valid_from_utc"]
        self.assert_code("INVALID_STORED_INTERVAL", lambda: self.command("create_assignment", self.assignment_payload(second.record_id)))

    def test_assignment_move_or_start_rewrite_requires_new_relation(self):
        first = self.create_position(); second = self.create_position("DEPT-B")
        result = self.command("create_assignment", self.assignment_payload(first.record_id))
        self.assert_code("NEW_RELATION_REQUIRED", lambda: self.update_assignment(result.record_id, position=second.record_id))
        self.assert_code("NEW_RELATION_REQUIRED", lambda: self.update_assignment(result.record_id, valid_from="2026-10-12T00:00:00Z"))

    def test_changed_native_account_link_cannot_move_existing_assignment(self):
        position = self.create_position(); result = self.command("create_assignment", self.assignment_payload(position.record_id))
        self.rows["User"].append({"name": "NEW-USER", "enabled": 1, "user_type": "System User", "modified": STAMP})
        self.rows["Employee"][0]["user_id"] = "NEW-USER"; self.snapshot = snapshot(self.rows)
        self.assert_code("SOURCE_ASSOCIATION_CHANGED", lambda: self.update_assignment(result.record_id, status="inactive"))

    def test_concurrent_replays_under_repository_serialization_create_once(self):
        key = str(uuid4())
        def execute(_): return self.command("create_position", self.position_payload(), idempotency_key=key)
        with ThreadPoolExecutor(max_workers=3) as pool: results = list(pool.map(execute, range(3)))
        self.assertEqual(len({result.record_id for result in results}), 1)
        self.assertEqual(sum(not result.replayed for result in results), 1)
        self.assertEqual(len(self.store.versions), 1)


if __name__ == "__main__": unittest.main()
