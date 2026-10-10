"""Controlled relationship facts. No RPC, business grant, or self-managed commit."""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from .source_adapter import (
    adapt_assignment, adapt_position, decode_utc_datetime, encode_utc_datetime,
    parse_rfc3339_utc, resolve_person,
)
from .storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, POSITION, POSITION_REVISION, PROVIDER,
    canonical_json, digest, receipt_key, require_uuid, revision_key,
)


@dataclass(frozen=True, slots=True)
class ManagementDecision:
    actor: str
    command_type: str
    company: str
    department: str
    policy_ref: str
    person_source_id: str | None = None


@dataclass(frozen=True, slots=True)
class RelationCommandResult:
    record_id: str
    revision: int
    authorization_generation: int
    replayed: bool = False
    # The caller's transaction still owns the commit. This is not a grant receipt.
    transaction_pending: bool = True
    authorization_effect: str = "none"
    runtime_verified: bool = False


def _fail(code, path):
    raise ContractError(code, path)


def _text(value, path, maximum=140):
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > maximum:
        _fail("INVALID_TEXT", path)
    return value


def _json_ready(value):
    if isinstance(value, Mapping):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _snapshot_digest(snapshot):
    return digest([snapshot.context.site_id, snapshot.context.provider_id,
                   snapshot.employee_links_complete, _json_ready(snapshot.rows)])


def _storage_time(value):
    return encode_utc_datetime(value).strftime("%Y-%m-%d %H:%M:%S.%f")


class RelationService:
    """Dependencies are trusted server code; defaults cannot enable real writes.

    source_loader runs inside the outer transaction. management_check must verify
    its independent management authority in that same transaction; Frappe roles
    and client-supplied booleans are not management decisions.
    """
    def __init__(self, repository, *, actor_resolver, source_loader, clock,
                 management_check=None, management_adapter=None, enabled=False, id_factory=uuid4):
        self.repository = repository
        self.actor_resolver = actor_resolver
        self.source_loader = source_loader
        self.clock = clock
        self.management_check = management_check
        self.management_adapter = management_adapter
        self.enabled = enabled is True
        self.id_factory = id_factory

    def execute(self, command_type, payload, *, idempotency_key, expected_revision,
                reason, record_id=None):
        if not self.enabled:
            _fail("WRITES_DISABLED", "service")
        if self.management_check is None and self.management_adapter is None:
            _fail("MANAGEMENT_DENIED", "service")
        if command_type not in ("create_position", "update_position", "create_assignment", "update_assignment"):
            _fail("UNKNOWN_COMMAND", "command")
        actor = _text(self.actor_resolver(), "actor")
        if actor == "Guest":
            _fail("MANAGEMENT_DENIED", "actor")
        create = command_type.startswith("create_")
        kind = POSITION if command_type.endswith("_position") else ASSIGNMENT
        if type(expected_revision) is not int or expected_revision < (0 if create else 1):
            _fail("INVALID_VERSION", "expected_revision")
        if create and (expected_revision != 0 or record_id is not None):
            _fail("INVALID_REQUEST", "record")
        if not create:
            require_uuid(record_id, "record_id")
        request_key = require_uuid(idempotency_key, "idempotency_key")
        reason = _text(reason, "reason", 500)
        facts = self._input(kind, payload)
        request_digest = digest([command_type, record_id, expected_revision, facts, reason])
        with self.repository.transaction():
            # One pre-existing Site lock serializes basic managed relation commands.
            # Native source writers and business transactions still need later closure.
            self.repository.lock_writer()
            if self.management_adapter is not None:
                return self.management_adapter.execute(self, actor=actor, command_type=command_type,
                    kind=kind, facts=facts, request_key=request_key, request_digest=request_digest,
                    expected_revision=expected_revision, reason=reason, record_id=record_id)
            snapshot = self.source_loader()
            if snapshot.context.site_id != self.repository.site_id or not snapshot.employee_links_complete:
                _fail("INCOMPLETE_SOURCE", "source")
            user = snapshot.rows["User"].get(actor)
            if user is None or not user["enabled"]:
                _fail("MANAGEMENT_DENIED", "actor")
            old = None if create else self.repository.get_master(kind, record_id)
            if not create and old is None:
                _fail("UNKNOWN_REFERENCE", "record")
            scope = facts if kind == POSITION else self.repository.get_master(POSITION, facts["position"])
            if scope is None:
                _fail("UNKNOWN_REFERENCE", "assignment.position")
            decision = self._authorize(actor, command_type, scope, facts)
            if old is not None:
                immutable = ("company", "department") if kind == POSITION else ("person_source_type", "person_source_id", "position")
                if any(old[key] != facts[key] for key in immutable):
                    _fail("NEW_RELATION_REQUIRED", "record")
            probe_id = record_id or require_uuid(str(self.id_factory()), "generated_id")
            now = self.clock()
            stamp = _storage_time(now)
            candidate = {**facts, "record_key": probe_id, "revision": 1 if create else old["revision"] + 1,
                         "authorization_generation": 1 if create else old["authorization_generation"],
                         "source_provider": PROVIDER, "source_key": probe_id}
            evidence, refs = self._evidence(kind, candidate, snapshot, scope, stamp)
            self.repository.lock_sources(tuple(sorted({("User", actor), *refs})))
            refreshed = self.source_loader()
            if _snapshot_digest(refreshed) != _snapshot_digest(snapshot):
                _fail("SOURCE_CHANGED_RETRY", "source")
            # Recheck authority after source locks and immediately before writes/replay.
            decision = self._authorize(actor, command_type, scope, facts)
            key = receipt_key(self.repository.site_id, actor, command_type, request_key)
            receipt = self.repository.get_receipt(key)
            if receipt is not None:
                if receipt["request_digest"] != request_digest:
                    _fail("IDEMPOTENCY_CONFLICT", "idempotency_key")
                return RelationCommandResult(**receipt["result"], replayed=True)
            if old is not None and old["revision"] != expected_revision:
                _fail("REVISION_CONFLICT", "expected_revision")
            if kind == ASSIGNMENT:
                if candidate["person_source_type"] != "Employee":
                    _fail("EMPLOYEE_SOURCE_REQUIRED", "assignment.person")
                if evidence.person.link_status in ("ambiguous", "unknown"):
                    _fail("PERSON_ASSOCIATION_UNRESOLVED", "assignment.person")
                if old is not None and old["subject_user"] != candidate["subject_user"]:
                    _fail("SOURCE_ASSOCIATION_CHANGED", "assignment.subject_user")
                if candidate["status"] == "active" and scope["status"] != "active":
                    _fail("INACTIVE_POSITION", "assignment.position")
                if old is not None and old["valid_from_utc"] != candidate["valid_from_utc"]:
                    _fail("NEW_RELATION_REQUIRED", "assignment.valid_from")
                self._check_intervals(candidate, evidence.person, snapshot)
            if old is not None:
                candidate["authorization_generation"] += self._generation_change(kind, old, candidate, now)
            version_kind = POSITION_REVISION if kind == POSITION else ASSIGNMENT_REVISION
            fingerprints = (tuple(f for f in evidence.fingerprints if f.reference.source_type != POSITION)
                            if kind == POSITION else evidence.person.fingerprints + evidence.position.fingerprints)
            source_evidence = {
                "site_id": snapshot.context.site_id, "provider_id": snapshot.context.provider_id,
                "captured_at": snapshot.context.captured_at.isoformat(), "runtime_verified": False,
                "fingerprints": [{"source_type": f.reference.source_type,
                                  "source_id": f.reference.source_id, "modified": f.modified}
                                 for f in fingerprints],
            }
            if kind == ASSIGNMENT:
                source_evidence["position"] = {
                    "position_id": scope["record_key"], "revision": scope["revision"],
                    "authorization_generation": scope["authorization_generation"],
                }
                source_evidence["person"] = {
                    "link_status": evidence.person.link_status,
                    "qualification_status": evidence.person.qualification_status,
                    "reason_codes": evidence.person.reason_codes,
                }
            version = {"record_key": revision_key(kind, probe_id, candidate["revision"]),
                       "position" if kind == POSITION else "assignment": probe_id,
                       "revision": candidate["revision"], "previous_revision": candidate["revision"] - 1,
                       "snapshot_json": canonical_json(candidate), "content_digest": digest(candidate),
                       "actor": actor, "policy_ref": decision.policy_ref, "reason": reason,
                       "source_evidence_json": canonical_json(source_evidence), "recorded_at_utc": stamp}
            result = {"record_id": probe_id, "revision": candidate["revision"],
                      "authorization_generation": candidate["authorization_generation"]}
            self.repository.save_master(kind, candidate, expected_revision=expected_revision)
            self.repository.append_revision(version_kind, version)
            self.repository.insert_receipt(key, {"site_id": self.repository.site_id, "actor": actor,
                "command_type": command_type, "request_key": request_key, "request_digest": request_digest,
                "result": result, "recorded_at_utc": stamp})
            return RelationCommandResult(**result)

    def _authorize(self, actor, command_type, scope, facts):
        person_id = facts.get("person_source_id")
        decision = self.management_check(actor, command_type, scope["company"], scope["department"], person_id)
        if not isinstance(decision, ManagementDecision) or (
            decision.actor, decision.command_type, decision.company, decision.department, decision.person_source_id
        ) != (actor, command_type, scope["company"], scope["department"], person_id):
            _fail("MANAGEMENT_DENIED", "scope")
        _text(decision.policy_ref, "management.policy_ref")
        return decision

    @staticmethod
    def _input(kind, payload):
        fields = ("title", "company", "department", "designation", "status") if kind == POSITION else (
            "person_source_type", "person_source_id", "position", "is_primary", "valid_from", "valid_until", "status")
        if not isinstance(payload, Mapping) or set(payload) != set(fields):
            _fail("INVALID_FIELDS", "payload")
        result = dict(payload)
        if result["status"] not in ("active", "inactive", "revoked"):
            _fail("INVALID_STATUS", "payload.status")
        if kind == POSITION:
            for key in ("title", "company", "department"):
                _text(result[key], "payload." + key)
            result["designation"] = None if result["designation"] in (None, "") else _text(result["designation"], "payload.designation")
        else:
            if result["person_source_type"] != "Employee":
                _fail("EMPLOYEE_SOURCE_REQUIRED", "payload.person_source_type")
            _text(result["person_source_id"], "payload.person_source_id")
            require_uuid(result["position"], "payload.position")
            if type(result["is_primary"]) is not bool:
                _fail("INVALID_TYPE", "payload.is_primary")
            start = parse_rfc3339_utc(result.pop("valid_from"))
            until = result.pop("valid_until")
            end = None if until is None else parse_rfc3339_utc(until)
            if end is not None and start >= end:
                _fail("INVALID_INTERVAL", "payload.valid_until")
            result.update(valid_from_utc=_storage_time(start), valid_until_utc=None if end is None else _storage_time(end))
        return result

    @staticmethod
    def _evidence(kind, candidate, snapshot, scope, stamp):
        if kind == POSITION:
            row = {key: candidate[key] for key in ("title", "company", "department", "designation", "status", "revision", "authorization_generation")}
            evidence = adapt_position({**row, "name": candidate["record_key"], "modified": stamp}, snapshot)
            refs = {(f.reference.source_type, f.reference.source_id) for f in evidence.fingerprints if f.reference.source_type != POSITION}
        else:
            person = resolve_person(snapshot, candidate["person_source_type"], candidate["person_source_id"])
            candidate["subject_user"] = person.subject_user
            pos = adapt_position({**{key: scope[key] for key in ("title", "company", "department", "designation", "status", "revision", "authorization_generation")},
                                  "name": scope["record_key"], "modified": scope.get("_source_modified", stamp)}, snapshot)
            row = {key: candidate[key] for key in ("person_source_type", "person_source_id", "subject_user", "position", "is_primary", "valid_from_utc", "valid_until_utc", "status", "revision", "authorization_generation")}
            evidence = adapt_assignment({**row, "name": candidate["record_key"], "modified": stamp}, snapshot, (pos,))
            refs = {(f.reference.source_type, f.reference.source_id) for f in evidence.person.fingerprints + pos.fingerprints if f.reference.source_type != POSITION}
        return evidence, refs

    def _check_intervals(self, candidate, person, snapshot):
        if candidate["status"] != "active":
            return
        start = decode_utc_datetime(candidate["valid_from_utc"])
        end = None if candidate["valid_until_utc"] is None else decode_utc_datetime(candidate["valid_until_utc"])
        for other in self.repository.list_assignments():
            if other["record_key"] == candidate["record_key"] or other["status"] != "active":
                continue
            same = (other["person_source_type"], other["person_source_id"]) == (candidate["person_source_type"], candidate["person_source_id"])
            if not same:
                alias_possible = person.subject_user is not None and (
                    other["subject_user"] == person.subject_user or
                    (other["person_source_type"] == "User" and other["person_source_id"] == person.subject_user))
                if not alias_possible:
                    continue
                alias = resolve_person(snapshot, other["person_source_type"], other["person_source_id"])
                same = person.canonical_person_ref is not None and person.canonical_person_ref == alias.canonical_person_ref
            if not same:
                continue
            other_start = decode_utc_datetime(other["valid_from_utc"])
            other_end = None if other["valid_until_utc"] is None else decode_utc_datetime(other["valid_until_utc"])
            if other_end is not None and other_start >= other_end:
                _fail("INVALID_STORED_INTERVAL", "assignment.interval")
            overlap = (end is None or other_start < end) and (other_end is None or start < other_end)
            if overlap and other["position"] == candidate["position"]:
                _fail("DUPLICATE_ASSIGNMENT", "assignment.interval")
            if overlap and other["is_primary"] and candidate["is_primary"]:
                _fail("OVERLAPPING_PRIMARY", "assignment.interval")

    @staticmethod
    def _generation_change(kind, old, candidate, now):
        if old["status"] != candidate["status"]:
            return 1
        if kind == POSITION:
            return int(old["designation"] != candidate["designation"])
        if old["is_primary"] != candidate["is_primary"]:
            return 1
        old_end, new_end = old["valid_until_utc"], candidate["valid_until_utc"]
        if old_end == new_end:
            return 0
        old_end = None if old_end is None else decode_utc_datetime(old_end)
        new_end = None if new_end is None else decode_utc_datetime(new_end)
        if new_end is None or (old_end is not None and new_end > old_end):
            return 1
        return int(new_end <= now.astimezone(timezone.utc))
