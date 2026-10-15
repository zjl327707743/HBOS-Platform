"""Fixed-schema durable intent evidence; never a recovery execution authority.

Import and the default constructor perform no I/O. Explicit creation requires
an existing private OwnedLanding and previously recorded human authorization.
The chain is integrity evidence under trusted same-euid control, not a signature
or proof of an actual Docker/process operation. Reopening is read-only and
always reports crash outcome UNKNOWN and execution HARD_BLOCKED.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import asdict, dataclass, field
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import threading

from .common import OWNER, ROOT, ROLES, VOLUME_NAMES, RestoreError
from . import landing
from .lifecycle import (
    CleanupDecision, CreationIntent, IntentOutcome, LifecycleRegistry, RestoreScope,
)

MAX_RECORDS = 256
MAX_RECORD_BYTES = 32 * 1024 - 1  # Include the LF within the 32 KiB line quota.
MAX_JOURNAL_BYTES = 1024 * 1024
_ZERO = "0" * 64
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
_NS = 1_000_000_000
_ISSUED = object()


def _check(condition, code="JOURNAL_INVALID"):
    if not condition:
        raise RestoreError(code) from None


def _sha(value):
    return type(value) is str and bool(_SHA.fullmatch(value))


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"), allow_nan=False).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise RestoreError("JOURNAL_INVALID") from None


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _ns(seconds):
    try:
        _check(type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0)
        value = int(seconds * _NS)
        _check(0 <= value <= 2**63 - 1 - 3300 * _NS)
        return value
    except (OverflowError, ValueError):
        raise RestoreError("JOURNAL_INVALID") from None


def _scope_sha():
    return _digest(asdict(RestoreScope()))


def _target(kind, value):
    _check(type(kind) is str and type(value) is str)
    valid = (kind == "container" and value in ROLES
             or kind == "volume" and value in VOLUME_NAMES
             or kind == "host-relay" and value == OWNER + "-http-relay"
             or kind in ("host-child", "container-exec") and _sha(value))
    _check(valid, "JOURNAL_INTENT_INVALID")


@dataclass(frozen=True)
class JournalBinding:
    run_id: str
    baseline_sha256: str
    baseline_evidence_sha256: str
    authorization_reference_sha256: str
    scope_sha256: str
    clock_id_sha256: str
    started_at_ns: int
    run_deadline_ns: int

    def __post_init__(self):
        _check(all(_sha(value) for value in (self.run_id, self.baseline_sha256,
               self.baseline_evidence_sha256, self.authorization_reference_sha256,
               self.scope_sha256, self.clock_id_sha256)) and self.scope_sha256 == _scope_sha())
        _check(type(self.started_at_ns) is int and 0 <= self.started_at_ns <= 2**63 - 1 - 3300 * _NS
               and type(self.run_deadline_ns) is int
               and self.run_deadline_ns == self.started_at_ns + 2700 * _NS)

    @classmethod
    def from_registry(cls, registry, *, clock_id_sha256):
        _check(type(registry) is LifecycleRegistry and registry.authorization is not None
               and registry.baseline is not None, "JOURNAL_OWNER_AUTHORIZATION_REQUIRED")
        _check(registry._started_at is not None, "JOURNAL_FIRST_ACTION_REQUIRED")
        started = _ns(registry._started_at)
        return cls(registry.run_id, _digest(asdict(registry.baseline)),
            registry.baseline.evidence_sha256, registry.authorization.reference_sha256,
            _scope_sha(), clock_id_sha256, started, started + 2700 * _NS)


@dataclass(frozen=True, init=False)
class DurableIntentReceipt:
    """Evidence of a fsynced event, explicitly not permission to perform it."""
    run_id: str
    intent_id: str
    sequence: int
    entry_sha256: str
    _issued: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class JournalReview:
    integrity: str
    reason: str | None = None
    run_id: str | None = None
    records: int = 0
    tip_sha256: str | None = None
    run_deadline_ns: int | None = None
    cleanup_deadline_ns: int | None = None
    unknown_intents: tuple[str, ...] = ()
    execution: str = "HARD_BLOCKED"
    crash_outcome: str = "UNKNOWN"

    def __post_init__(self):
        _check(self.integrity in ("VALIDATED_RECORDS_ONLY", "UNKNOWN")
               and self.execution == "HARD_BLOCKED" and self.crash_outcome == "UNKNOWN"
               and self.reason in (None, "JOURNAL_INVALID", "JOURNAL_ROOT_INVALID", "JOURNAL_PIN_MISMATCH",
                   "JOURNAL_INCOMPLETE_UNKNOWN", "JOURNAL_RECORD_LIMIT", "JOURNAL_RECORD_INVALID",
                   "JOURNAL_CHAIN_INVALID", "JOURNAL_INTENT_INVALID", "JOURNAL_RECEIPT_INVALID",
                   "JOURNAL_CLEANUP_INVALID", "JOURNAL_FILE_INVALID", "JOURNAL_FILE_CHANGED",
                   "JOURNAL_ANCESTOR_CHANGED", "JOURNAL_DIRECTORY_INVALID", "JOURNAL_UNREGISTERED_CHILD",
                   "JOURNAL_IO_FAILED")
               and (self.run_id is None or _sha(self.run_id))
               and (self.tip_sha256 is None or _sha(self.tip_sha256))
               and type(self.records) is int and 0 <= self.records <= MAX_RECORDS
               and type(self.unknown_intents) is tuple and len(self.unknown_intents) <= MAX_RECORDS
               and all(_sha(value) for value in self.unknown_intents)
               and all(value is None or type(value) is int and 0 <= value <= 2**63-1
                       for value in (self.run_deadline_ns, self.cleanup_deadline_ns)))


def _strict_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            _check(key not in result, "JOURNAL_RECORD_INVALID")
            result[key] = value
        return result

    def invalid(_value):
        raise RestoreError("JOURNAL_RECORD_INVALID")

    try:
        value = json.loads(raw.decode("ascii", errors="strict"),
                           object_pairs_hook=pairs, parse_constant=invalid)
        _check(type(value) is dict and _canonical(value) == raw, "JOURNAL_RECORD_INVALID")
        return value
    except (ValueError, UnicodeError, TypeError, RecursionError, OverflowError):
        raise RestoreError("JOURNAL_RECORD_INVALID") from None


class _Chain:
    def __init__(self):
        self.binding = None
        self.tip = _ZERO
        self.records = 0
        self.intents = {}
        self.cleanup_deadline_ns = None

    def apply(self, envelope):
        _check(type(envelope) is dict and set(envelope) == {
            "version", "sequence", "previous_sha256", "event", "data", "sha256"}, "JOURNAL_RECORD_INVALID")
        _check(type(envelope["version"]) is int and envelope["version"] == 1
               and type(envelope["sequence"]) is int and envelope["sequence"] == self.records
               and envelope["previous_sha256"] == self.tip and _sha(envelope["sha256"]), "JOURNAL_CHAIN_INVALID")
        content = {key: value for key, value in envelope.items() if key != "sha256"}
        _check(_digest(content) == envelope["sha256"], "JOURNAL_CHAIN_INVALID")
        event, data = envelope["event"], envelope["data"]
        _check(type(event) is str and type(data) is dict, "JOURNAL_RECORD_INVALID")
        if self.records == 0:
            _check(event == "BINDING" and set(data) == set(JournalBinding.__dataclass_fields__), "JOURNAL_RECORD_INVALID")
            try:
                self.binding = JournalBinding(**data)
            except (TypeError, ValueError, OverflowError):
                raise RestoreError("JOURNAL_RECORD_INVALID") from None
        elif event == "INTENT":
            _check(set(data) == {"intent_id", "kind", "target", "created_at_ns"}
                   and _sha(data["intent_id"]) and data["intent_id"] not in self.intents
                   and type(data["created_at_ns"]) is int
                   and self.binding.started_at_ns <= data["created_at_ns"] < self.binding.run_deadline_ns
                   and self.cleanup_deadline_ns is None, "JOURNAL_INTENT_INVALID")
            _target(data["kind"], data["target"])
            self.intents[data["intent_id"]] = dict(data, status="PENDING")
        elif event == "RECEIPT":
            _check(set(data) == {"intent_id", "status", "observed_identity", "error_sha256"}
                   and _sha(data["intent_id"]) and data["intent_id"] in self.intents
                   and self.intents[data["intent_id"]]["status"] == "PENDING"
                   and type(data["status"]) is str and data["status"] in ("CONFIRMED", "UNKNOWN", "NOT_CREATED")
                   and (data["observed_identity"] is None or _sha(data["observed_identity"]))
                   and (data["error_sha256"] is None or _sha(data["error_sha256"])), "JOURNAL_RECEIPT_INVALID")
            _check(data["status"] != "NOT_CREATED" or data["observed_identity"] is None,
                   "JOURNAL_RECEIPT_INVALID")
            kind = self.intents[data["intent_id"]]["kind"]
            _check(data["status"] != "CONFIRMED" or data["error_sha256"] is None
                   and (kind == "volume" and data["observed_identity"] is None
                        or kind != "volume" and _sha(data["observed_identity"])), "JOURNAL_RECEIPT_INVALID")
            _check(data["status"] != "UNKNOWN" or _sha(data["error_sha256"]), "JOURNAL_RECEIPT_INVALID")
            self.intents[data["intent_id"]]["status"] = data["status"]
        elif event == "CLEANUP_STARTED":
            _check(set(data) == {"started_at_ns", "deadline_ns"} and self.cleanup_deadline_ns is None
                   and type(data["started_at_ns"]) is int
                   and self.binding.started_at_ns <= data["started_at_ns"] <= 2**63 - 1 - 600 * _NS
                   and type(data["deadline_ns"]) is int
                   and data["deadline_ns"] == data["started_at_ns"] + 600 * _NS,
                   "JOURNAL_CLEANUP_INVALID")
            self.cleanup_deadline_ns = data["deadline_ns"]
        elif event == "CLEANUP_RESULT":
            _check(set(data) == {"status", "residuals", "blocker_sha256"}
                   and self.cleanup_deadline_ns is not None and type(data["status"]) is str
                   and data["status"] in ("PLAN_ONLY", "BLOCKED_CLOSED", "FAILED_GUARD_CLOSED",
                       "FAILED_CLOSED", "RECEIPT_RECORDED", "RECORDED_CLEAN")
                   and type(data["residuals"]) is list and len(data["residuals"]) <= MAX_RECORDS
                   and type(data["blocker_sha256"]) is list and len(data["blocker_sha256"]) <= 32
                   and all(_sha(value) for value in data["blocker_sha256"]), "JOURNAL_CLEANUP_INVALID")
            seen = set()
            for item in data["residuals"]:
                _check(type(item) is list and len(item) == 2 and type(item[0]) is str
                       and (item[0] == "volume" and item[1] in VOLUME_NAMES
                            or item[0] in ("container", "task", "intent") and _sha(item[1])), "JOURNAL_CLEANUP_INVALID")
                _check(tuple(item) not in seen, "JOURNAL_CLEANUP_INVALID")
                seen.add(tuple(item))
            _check(data["status"] != "RECORDED_CLEAN" or not data["residuals"]
                   and not any(row["status"] in ("PENDING", "UNKNOWN") for row in self.intents.values()),
                   "JOURNAL_CLEANUP_INVALID")
        else:
            raise RestoreError("JOURNAL_RECORD_INVALID")
        self.tip = envelope["sha256"]
        self.records += 1

    def review(self):
        _check(self.binding is not None, "JOURNAL_INCOMPLETE_UNKNOWN")
        return JournalReview("VALIDATED_RECORDS_ONLY", run_id=self.binding.run_id,
            records=self.records, tip_sha256=self.tip, run_deadline_ns=self.binding.run_deadline_ns,
            cleanup_deadline_ns=self.cleanup_deadline_ns,
            unknown_intents=tuple(sorted(key for key, row in self.intents.items()
                                        if row["status"] in ("PENDING", "UNKNOWN"))))


def _read_chain(raw_log):
    _check(type(raw_log) is bytes and 1 <= len(raw_log) <= MAX_JOURNAL_BYTES
           and raw_log.endswith(b"\n"), "JOURNAL_INCOMPLETE_UNKNOWN")
    _check(raw_log.count(b"\n") <= MAX_RECORDS, "JOURNAL_RECORD_LIMIT")
    raw_records = raw_log[:-1].split(b"\n")
    _check(1 <= len(raw_records) <= MAX_RECORDS, "JOURNAL_RECORD_LIMIT")
    chain = _Chain()
    for raw in raw_records:
        _check(type(raw) is bytes and 1 <= len(raw) <= MAX_RECORD_BYTES, "JOURNAL_RECORD_LIMIT")
        chain.apply(_strict_json(raw))
    return chain


def _private_directory(descriptor):
    metadata = os.fstat(descriptor)
    _check(stat.S_ISDIR(metadata.st_mode) and metadata.st_uid == os.geteuid()
           and stat.S_IMODE(metadata.st_mode) == 0o700, "JOURNAL_DIRECTORY_INVALID")
    return metadata


class OwnedJournal:
    """Explicit owned writes only; no adapter or automatic resume exists."""
    def __init__(self):
        self._landing = None
        self._registry = None
        self._binding = None
        self._chain = None
        self._closed = True
        self._audit_open = False
        self._lock = threading.Lock()

    @classmethod
    def create(cls, capability, registry, *, clock_id_sha256):
        _check(type(capability) is landing.OwnedLanding, "JOURNAL_LANDING_CAPABILITY_REQUIRED")
        binding = JournalBinding.from_registry(registry, clock_id_sha256=clock_id_sha256)
        result = cls()
        result._landing, result._registry, result._binding = capability, registry, binding
        result._closed = False
        try:
            result._require_active()
            descriptor = capability.journal_directory_fd(create=True)
            try:
                _private_directory(descriptor)
            finally:
                os.close(descriptor)
            capability.journal_create_log()
            result._chain = _Chain()
            result._audit_open = True
            result._append("BINDING", asdict(binding))
            # No active object may escape if fsync crossed the original
            # deadline, invalidated the clock, or started failure cleanup.
            result._require_active()
            return result
        except RestoreError:
            result._closed = True
            result._audit_open = False
            raise
        except (OSError, ValueError, TypeError, AttributeError):
            result._closed = True
            result._audit_open = False
            raise RestoreError("JOURNAL_IO_FAILED") from None

    def __repr__(self):
        return "<OwnedJournal closed execution capability>"

    def _require_active(self):
        try:
            _check(not self._closed and self._registry is not None
                   and not self._registry._closed and self._registry._cleanup_at is None,
                   "JOURNAL_RUN_CLOSED")
            _check(self._registry.remaining_seconds() > 0, "JOURNAL_DEADLINE_EXPIRED")
        except RestoreError:
            # Admission is permanently closed, including on invalid clocks.
            # A still-intact chain may record terminal receipts and cleanup;
            # these events never grant permission for another owned action.
            self._closed = True
            raise

    def _verify_chain(self):
        _check(self._landing is not None and self._audit_open, "JOURNAL_DISABLED")
        raw = self._landing.journal_read_log()
        _check(type(raw) is bytes, "JOURNAL_CHAIN_CHANGED")
        if self._chain.records:
            chain = _read_chain(raw)
            _check(chain.tip == self._chain.tip and chain.binding == self._binding, "JOURNAL_CHAIN_CHANGED")
        else:
            _check(raw == b"", "JOURNAL_CHAIN_CHANGED")
        return raw

    def _append(self, event, data):
        with self._lock:
            try:
                _check(not self._closed or event in ("RECEIPT", "CLEANUP_STARTED", "CLEANUP_RESULT"),
                       "JOURNAL_DISABLED")
                previous_raw = self._verify_chain()
                _check(self._chain.records < MAX_RECORDS, "JOURNAL_RECORD_LIMIT")
                content = {"version": 1, "sequence": self._chain.records,
                           "previous_sha256": self._chain.tip, "event": event, "data": data}
                envelope = dict(content, sha256=_digest(content))
                raw = _canonical(envelope)
                _check(len(raw) <= MAX_RECORD_BYTES
                       and len(previous_raw) + len(raw) + 1 <= MAX_JOURNAL_BYTES, "JOURNAL_RECORD_LIMIT")
                # Validate on a disposable replay before committing immutable
                # bytes. The current chain is only advanced after file+dir fsync.
                checked = _Chain()
                if self._chain.records:
                    checked = _read_chain(previous_raw)
                checked.apply(envelope)
                self._landing.journal_append_bytes(raw + b"\n")
                descriptor = self._landing.journal_directory_fd()
                try:
                    _private_directory(descriptor)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                _check(self._landing.journal_read_log() == previous_raw + raw + b"\n", "JOURNAL_CHAIN_CHANGED")
                self._chain = checked
                return envelope["sequence"], envelope["sha256"]
            except RestoreError:
                self._closed = True
                self._audit_open = False
                raise
            except (OSError, ValueError, TypeError, AttributeError):
                self._closed = True
                self._audit_open = False
                raise RestoreError("JOURNAL_IO_FAILED") from None

    def append_intent(self, intent):
        _check(self._registry is not None and type(intent) is CreationIntent
               and _sha(intent.intent_id) and intent.run_id == self._binding.run_id, "JOURNAL_INTENT_INVALID")
        self._require_active()
        row = self._registry._intents.get(intent.intent_id)
        _check(row is not None and row.intent == intent and row.status == "PENDING", "JOURNAL_INTENT_INVALID")
        sequence, digest = self._append("INTENT", {"intent_id": intent.intent_id,
            "kind": intent.kind, "target": intent.target, "created_at_ns": _ns(intent.created_at)})
        self._require_active()
        receipt = object.__new__(DurableIntentReceipt)
        for name, value in (("run_id", self._binding.run_id), ("intent_id", intent.intent_id),
                            ("sequence", sequence), ("entry_sha256", digest), ("_issued", _ISSUED)):
            object.__setattr__(receipt, name, value)
        return receipt

    def append_receipt(self, outcome):
        _check(self._registry is not None and type(outcome) is IntentOutcome
               and type(outcome.intent) is CreationIntent and _sha(outcome.intent.intent_id)
               and outcome.intent.run_id == self._binding.run_id
               and self._registry._intents.get(outcome.intent.intent_id) == outcome,
               "JOURNAL_RECEIPT_INVALID")
        _check(outcome.error_code is None or type(outcome.error_code) is str and len(outcome.error_code) <= 80,
               "JOURNAL_RECEIPT_INVALID")
        return self._append("RECEIPT", {"intent_id": outcome.intent.intent_id, "status": outcome.status,
            "observed_identity": outcome.observed_identity,
            "error_sha256": None if outcome.error_code is None else _digest(outcome.error_code)})

    def append_cleanup_started(self):
        _check(self._registry is not None and self._registry._cleanup_at is not None, "JOURNAL_CLEANUP_INVALID")
        started = _ns(self._registry._cleanup_at)
        return self._append("CLEANUP_STARTED", {"started_at_ns": started, "deadline_ns": started + 600 * _NS})

    def append_cleanup_result(self, decision):
        _check(type(decision) is CleanupDecision and decision.executable is False, "JOURNAL_CLEANUP_INVALID")
        return self._append("CLEANUP_RESULT", {"status": decision.status,
            "residuals": [list(item) for item in decision.residuals],
            "blocker_sha256": [_digest(value) for value in decision.blockers]})

    def public_summary(self):
        """Last acknowledged in-memory evidence; no new filesystem assertion."""
        if self._chain is None:
            return {"status": "DISABLED", "execution": "HARD_BLOCKED"}
        review = self._chain.review()
        admission_closed = (self._closed or self._registry._closed or self._registry._cleanup_at is not None)
        return dict(asdict(review), status="CLOSED" if admission_closed else "RECORDING_ONLY")

    def require_execution_ready(self):
        raise RestoreError("JOURNAL_RESUME_HARD_BLOCKED")

    def close(self):
        self._closed = True
        self._audit_open = False


def _stat_snapshot(metadata):
    return (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_uid,
            stat.S_IMODE(metadata.st_mode), metadata.st_nlink, metadata.st_mtime_ns, metadata.st_ctime_ns)


def _read_existing_log():
    """Read only the fixed log through held no-follow ancestor descriptors."""
    _check(type(ROOT) is Path or isinstance(ROOT, Path), "JOURNAL_ROOT_INVALID")
    _check(ROOT.is_absolute() and ROOT.anchor == "/" and str(ROOT).startswith("/")
           and not str(ROOT).startswith("//") and ".." not in ROOT.parts and len(ROOT.parts) >= 3,
           "JOURNAL_ROOT_INVALID")
    with ExitStack() as stack:
        descriptor = os.open("/", _DIR_FLAGS)
        stack.callback(os.close, descriptor)
        anchors = []
        parts = (*ROOT.parts[1:], "runtime", "journal")
        for index, name in enumerate(parts):
            child = os.open(name, _DIR_FLAGS, dir_fd=descriptor)
            stack.callback(os.close, child)
            current = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            held = os.fstat(child)
            _check(stat.S_ISDIR(current.st_mode) and (current.st_dev, current.st_ino) == (held.st_dev, held.st_ino),
                   "JOURNAL_ANCESTOR_CHANGED")
            if index >= len(ROOT.parts) - 2:
                _private_directory(child)
            anchors.append((descriptor, name, child))
            descriptor = child
        _check(os.listdir(descriptor) == ["events.jsonl"], "JOURNAL_UNREGISTERED_CHILD")
        file_descriptor = os.open("events.jsonl", _FILE_FLAGS, dir_fd=descriptor)
        stack.callback(os.close, file_descriptor)
        fcntl.flock(file_descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        stack.callback(fcntl.flock, file_descriptor, fcntl.LOCK_UN)
        before = os.fstat(file_descriptor)
        current = os.stat("events.jsonl", dir_fd=descriptor, follow_symlinks=False)
        _check(stat.S_ISREG(before.st_mode) and stat.S_ISREG(current.st_mode)
               and _stat_snapshot(before) == _stat_snapshot(current)
               and before.st_uid == os.geteuid() and stat.S_IMODE(before.st_mode) == 0o600
               and before.st_nlink == 1 and 0 < before.st_size <= MAX_JOURNAL_BYTES,
               "JOURNAL_FILE_INVALID")
        output = bytearray()
        while len(output) < before.st_size:
            chunk = os.read(file_descriptor, min(65536, before.st_size - len(output)))
            _check(bool(chunk), "JOURNAL_FILE_CHANGED")
            output.extend(chunk)
        _check(os.read(file_descriptor, 1) == b"", "JOURNAL_FILE_CHANGED")
        _check(_stat_snapshot(os.fstat(file_descriptor)) == _stat_snapshot(before)
               and _stat_snapshot(os.stat("events.jsonl", dir_fd=descriptor, follow_symlinks=False)) == _stat_snapshot(before)
               and os.listdir(descriptor) == ["events.jsonl"], "JOURNAL_FILE_CHANGED")
        for parent, name, child in anchors:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            held = os.fstat(child)
            _check(stat.S_ISDIR(current.st_mode) and (current.st_dev, current.st_ino) == (held.st_dev, held.st_ino),
                   "JOURNAL_ANCESTOR_CHANGED")
        for _, _, child in anchors[len(ROOT.parts) - 2:]:
            _private_directory(child)
        return bytes(output)


def review_existing(*, expected_run_id=None, expected_tip_sha256=None,
                    expected_authorization_reference_sha256=None, expected_baseline_sha256=None):
    """Explicit fixed-path review; no write, adoption, timer reset or execution.

    Optional independent pins can detect a fully rewritten self-consistent
    chain. Without such external evidence this only validates recorded bytes.
    Filesystem, partial-tail and schema failures have outcome UNKNOWN.
    """
    for value in (expected_run_id, expected_tip_sha256,
                  expected_authorization_reference_sha256, expected_baseline_sha256):
        _check(value is None or _sha(value), "JOURNAL_PIN_INVALID")
    try:
        chain = _read_chain(_read_existing_log())
        for expected, actual in ((expected_run_id, chain.binding.run_id), (expected_tip_sha256, chain.tip),
                                (expected_authorization_reference_sha256, chain.binding.authorization_reference_sha256),
                                (expected_baseline_sha256, chain.binding.baseline_sha256)):
            _check(expected is None or expected == actual, "JOURNAL_PIN_MISMATCH")
        return chain.review()
    except RestoreError as error:
        return JournalReview("UNKNOWN", reason=error.code)
    except (OSError, ValueError, TypeError, OverflowError):
        return JournalReview("UNKNOWN", reason="JOURNAL_IO_FAILED")
