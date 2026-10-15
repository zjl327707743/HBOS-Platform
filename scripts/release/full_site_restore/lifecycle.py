"""In-memory lifecycle admission and cleanup plans; production execution closed.

The trusted caller must capture the complete pre-action baseline, obtain a new
Owner confirmation, persist intents before acting, and bind receipts to actual
operations. This module does not capture, persist, create, execute, signal, or
delete anything. Caller-supplied snapshots and test fixtures never prove real
UID/network/restore/session gates. Service admission is deliberately disabled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import re
import time
from typing import Callable
import uuid

from .common import HOST, ORIGIN, OWNER, ROOT, ROLES, SITE, VOLUME_NAMES, RestoreError
from .ownership import (ContainerSpec, ProcessRecord, ResourceRecord, VolumeRecord,
                        cleanup_plan as owned_cleanup_plan)

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUED = object()
_KINDS = ("container", "volume", "host-relay", "host-child", "container-exec")
_GATES = ("uid", "network", "restore", "session")


def _check(condition, code="LIFECYCLE_INVALID"):
    if not condition:
        raise RestoreError(code)


def _sha(value):
    return type(value) is str and bool(_SHA.fullmatch(value))


def _digest(value):
    try:
        return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
            separators=(",", ":"), allow_nan=False).encode("ascii")).hexdigest()
    except (TypeError, ValueError, RecursionError, OverflowError):
        raise RestoreError("LIFECYCLE_INVALID") from None


@dataclass(frozen=True)
class RestoreScope:
    owner: str = OWNER
    root: str = str(ROOT)
    site: str = SITE
    roles: tuple[str, ...] = ROLES
    volumes: tuple[str, ...] = VOLUME_NAMES
    networks: int = 0
    host: str = HOST
    origin: str = ORIGIN
    host_bind: str = "127.0.0.1"
    port: int = 18092
    run_seconds: int = 2700
    cleanup_seconds: int = 600
    container_incarnations: int = 10
    max_simultaneous_containers: int = 5
    phases: tuple[str, ...] = ("namespace-volume-initialize", "service")

    def __post_init__(self):
        _check(type(self.owner) is str and self.owner == OWNER
               and type(self.root) is str and self.root == str(ROOT)
               and type(self.site) is str and self.site == SITE
               and type(self.roles) is tuple and self.roles == ROLES
               and type(self.volumes) is tuple and self.volumes == VOLUME_NAMES
               and type(self.networks) is int and self.networks == 0
               and type(self.host) is str and self.host == HOST
               and type(self.origin) is str and self.origin == ORIGIN
               and type(self.host_bind) is str and self.host_bind == "127.0.0.1"
               and type(self.port) is int and self.port == 18092
               and type(self.run_seconds) is int and self.run_seconds == 2700
               and type(self.cleanup_seconds) is int and self.cleanup_seconds == 600
               and type(self.container_incarnations) is int and self.container_incarnations == 10
               and type(self.max_simultaneous_containers) is int and self.max_simultaneous_containers == 5
               and type(self.phases) is tuple and all(type(value) is str for value in self.phases)
               and self.phases == ("namespace-volume-initialize", "service"),
               "LIFECYCLE_SCOPE_DENIED")

    @property
    def relay_name(self):
        return self.owner + "-http-relay"


@dataclass(frozen=True, init=False)
class OwnerAuthorization:
    """Trusted-caller recording of human confirmation, not an approval detector."""
    scope: RestoreScope
    reference_sha256: str
    _issued: object = field(repr=False, compare=False)

    @classmethod
    def from_confirmation(cls, *, explicit=False, reference_sha256=None, scope=None):
        scope = RestoreScope() if scope is None else scope
        _check(type(scope) is RestoreScope and explicit is True and _sha(reference_sha256),
               "LIFECYCLE_OWNER_AUTHORIZATION_REQUIRED")
        scope.__post_init__()
        record = object.__new__(cls)
        for key, value in (("scope", scope), ("reference_sha256", reference_sha256), ("_issued", _ISSUED)):
            object.__setattr__(record, key, value)
        return record


@dataclass(frozen=True)
class OriginalBaseline:
    """Complete pre-action resource/PID exclusion captured outside this module."""
    container_ids: tuple[str, ...]
    container_names: tuple[str, ...]
    volume_names: tuple[str, ...]
    pids: tuple[int, ...]
    evidence_sha256: str

    def __post_init__(self):
        for values in (self.container_ids, self.container_names, self.volume_names, self.pids):
            _check(type(values) is tuple and bool(values), "LIFECYCLE_BASELINE_REQUIRED")
        _check(all(_sha(value) for value in self.container_ids) and _sha(self.evidence_sha256),
               "LIFECYCLE_BASELINE_REQUIRED")
        _check(all(type(value) is str and value and not any(ord(c) < 32 or ord(c) == 127 for c in value)
                   for value in (*self.container_names, *self.volume_names)), "LIFECYCLE_BASELINE_REQUIRED")
        _check(all(type(pid) is int and pid > 1 for pid in self.pids), "LIFECYCLE_BASELINE_REQUIRED")
        for values in (self.container_ids, self.container_names, self.volume_names, self.pids):
            _check(len(values) == len(set(values)), "LIFECYCLE_BASELINE_REQUIRED")
        proposed = {OWNER + "-" + role for role in ROLES}
        _check(not proposed.intersection(value.lstrip("/") for value in self.container_names)
               and not set(VOLUME_NAMES).intersection(self.volume_names), "LIFECYCLE_TARGET_COLLISION")


@dataclass(frozen=True)
class GateProof:
    """A verifier's assertion; this DTO cannot make production ready."""
    gate: str
    run_id: str
    origin: str
    verified: bool
    evidence_sha256: str

    def __post_init__(self):
        _check(type(self.gate) is str and self.gate in _GATES and _sha(self.run_id)
               and type(self.origin) is str and self.origin in ("REAL", "SYNTHETIC")
               and type(self.verified) is bool and _sha(self.evidence_sha256), "LIFECYCLE_PROOF_INVALID")


@dataclass(frozen=True)
class CreationIntent:
    intent_id: str
    run_id: str
    kind: str
    target: str
    created_at: float


@dataclass(frozen=True)
class IntentOutcome:
    intent: CreationIntent
    status: str = "PENDING"
    observed_identity: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class TaskHandle:
    handle_id: str
    run_id: str
    intent_id: str
    kind: str
    pid: int
    start_time: int | str
    backend_id: str
    exec_id: str | None
    parent_handle_id: str | None
    identity_sha256: str


@dataclass(frozen=True)
class TaskExitProof:
    handle_id: str
    identity_sha256: str
    exited: bool
    origin: str
    evidence_sha256: str

    def __post_init__(self):
        _check(_sha(self.handle_id) and _sha(self.identity_sha256) and self.exited is True
               and type(self.origin) is str and self.origin in ("REAL", "SYNTHETIC") and _sha(self.evidence_sha256),
               "LIFECYCLE_TASK_EXIT_UNCONFIRMED")


@dataclass(frozen=True)
class CleanupDecision:
    status: str
    actions: tuple[tuple[str, ...], ...] = ()
    blockers: tuple[str, ...] = ()
    residuals: tuple[tuple[str, str], ...] = ()
    executable: bool = False

    def __post_init__(self):
        _check(type(self.status) is str and bool(re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", self.status))
               and self.executable is False and type(self.actions) is tuple
               and all(type(action) is tuple and action and all(type(arg) is str for arg in action)
                       for action in self.actions)
               and type(self.blockers) is tuple
               and all(type(code) is str and re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", code) for code in self.blockers)
               and type(self.residuals) is tuple
               and all(type(item) is tuple and len(item) == 2 and all(type(value) is str for value in item)
                       for item in self.residuals), "LIFECYCLE_INVALID")


class LifecycleRegistry:
    """Pure planner/state recorder; no adapter is ever executed by this class."""

    def __init__(self, *, scope=None, authorization=None, baseline=None, clock: Callable = time.monotonic):
        self._scope = RestoreScope() if scope is None else scope
        _check(type(self.scope) is RestoreScope and callable(clock))
        self.scope.__post_init__()
        _check(authorization is None or (type(authorization) is OwnerAuthorization
               and authorization._issued is _ISSUED and authorization.scope == self.scope),
               "LIFECYCLE_OWNER_AUTHORIZATION_REQUIRED")
        _check(baseline is None or type(baseline) is OriginalBaseline, "LIFECYCLE_BASELINE_REQUIRED")
        self._authorization = authorization
        self._baseline = baseline
        self._run_id = _digest({"scope": OWNER, "nonce": uuid.uuid4().hex})
        self._clock = clock
        self._last_time = None
        self._started_at = None
        self._cleanup_at = None
        self._closed = False
        self._intents = {}
        self._containers = {}
        self._volumes = {}
        self._tasks = {}
        self._exited = {}
        self._proofs = {}
        self._ingress_closed = True
        self._ingress_evidence = None
        self._cleanup_actions = ()
        self._cleanup_index = 0
        self._failure_code = None

    @property
    def scope(self):
        return self._scope

    @property
    def authorization(self):
        return self._authorization

    @property
    def baseline(self):
        return self._baseline

    @property
    def run_id(self):
        return self._run_id

    def _now(self):
        try:
            value = self._clock()
            valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
        except Exception:
            raise RestoreError("LIFECYCLE_CLOCK_INVALID") from None
        _check(valid, "LIFECYCLE_CLOCK_INVALID")
        _check(self._last_time is None or value >= self._last_time, "LIFECYCLE_CLOCK_INVALID")
        self._last_time = float(value)
        return float(value)

    def _admit(self):
        _check(self.authorization is not None, "LIFECYCLE_OWNER_AUTHORIZATION_REQUIRED")
        _check(self.baseline is not None, "LIFECYCLE_BASELINE_REQUIRED")
        _check(not self._closed, "LIFECYCLE_CLOSED")
        _check(self.remaining_seconds() > 0, "LIFECYCLE_DEADLINE_EXPIRED")

    def remaining_seconds(self):
        now = self._now()
        return float(self.scope.run_seconds) if self._started_at is None else max(0.0, self._started_at + self.scope.run_seconds - now)

    def cleanup_remaining_seconds(self):
        now = self._now()
        return float(self.scope.cleanup_seconds) if self._cleanup_at is None else max(0.0, self._cleanup_at + self.scope.cleanup_seconds - now)

    def note_owned_action(self):
        """Must be recorded before a separately authorized first owned action."""
        self._admit()
        if self._started_at is None:
            self._started_at = self._now()

    def create_intent(self, kind, target):
        self._admit()
        _check(type(kind) is str and kind in _KINDS and type(target) is str, "LIFECYCLE_INTENT_DENIED")
        if kind == "container":
            _check(target in ROLES, "LIFECYCLE_INTENT_DENIED")
            if target != "db":
                _check("db" in self._containers, "LIFECYCLE_DB_ANCHOR_REQUIRED")
        elif kind == "volume":
            _check(target in VOLUME_NAMES, "LIFECYCLE_INTENT_DENIED")
        elif kind == "host-relay":
            _check(target == self.scope.relay_name and "backend" in self._containers, "LIFECYCLE_INTENT_DENIED")
        else:
            _check("backend" in self._containers and target == self._containers["backend"].container_id,
                   "LIFECYCLE_INTENT_DENIED")
        if kind in ("container", "volume", "host-relay"):
            _check(not any(row.intent.kind == kind and row.intent.target == target for row in self._intents.values()),
                   "LIFECYCLE_DUPLICATE_INTENT")
        self.note_owned_action()
        now = self._now()
        intent = CreationIntent(_digest({"run": self.run_id, "sequence": len(self._intents) + 1}),
                                self.run_id, kind, target, now)
        self._intents[intent.intent_id] = IntentOutcome(intent)
        return intent

    def _pending(self, intent_id, kind=None):
        _check(type(intent_id) is str and intent_id in self._intents, "LIFECYCLE_INTENT_REQUIRED")
        row = self._intents[intent_id]
        _check(row.status == "PENDING" and (kind is None or row.intent.kind == kind), "LIFECYCLE_INTENT_MISMATCH")
        return row.intent

    def mark_unknown(self, intent_id, observed_identity=None, error_code="LIFECYCLE_CREATE_OUTCOME_UNKNOWN"):
        intent = self._pending(intent_id)
        safe_identity = observed_identity if _sha(observed_identity) and observed_identity not in self.baseline.container_ids else None
        _check(type(error_code) is str and re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", error_code), "LIFECYCLE_INVALID")
        self._intents[intent_id] = IntentOutcome(intent, "UNKNOWN", safe_identity, error_code)
        self._closed = True
        self._failure_code = error_code

    def mark_not_created(self, intent_id, *, confirmed=False):
        intent = self._pending(intent_id)
        _check(confirmed is True, "LIFECYCLE_CREATE_OUTCOME_UNKNOWN")
        self._intents[intent_id] = IntentOutcome(intent, "NOT_CREATED")

    def confirm_container(self, intent_id, *, returned_id, metadata, spec):
        intent = self._pending(intent_id, "container")
        try:
            _check(_sha(returned_id) and type(metadata) is dict and metadata.get("Id") == returned_id
                   and type(spec) is ContainerSpec and spec.role == intent.target, "LIFECYCLE_RECEIPT_MISMATCH")
            for mount in spec.mounts:
                _check(mount.kind != "volume" or mount.source in self._volumes, "LIFECYCLE_VOLUME_REGISTRATION_REQUIRED")
            db_id = None if spec.role == "db" else self._containers["db"].container_id
            record = ResourceRecord.from_inspect(metadata, expected=spec, original_ids=self.baseline.container_ids,
                original_names=self.baseline.container_names, original_volume_names=self.baseline.volume_names, db_id=db_id)
        except (RestoreError, KeyError, TypeError, AttributeError) as error:
            code = error.code if isinstance(error, RestoreError) else "LIFECYCLE_RECEIPT_MISMATCH"
            self.mark_unknown(intent_id, returned_id, code)
            raise RestoreError(code) from None
        self._containers[spec.role] = record
        self._intents[intent_id] = IntentOutcome(intent, "CONFIRMED", record.container_id)
        return record

    def confirm_volume(self, intent_id, *, returned_name, metadata):
        intent = self._pending(intent_id, "volume")
        try:
            _check(returned_name == intent.target and type(metadata) is dict and metadata.get("Name") == returned_name,
                   "LIFECYCLE_RECEIPT_MISMATCH")
            record = VolumeRecord.from_inspect(metadata, original_volume_names=self.baseline.volume_names)
        except RestoreError as error:
            self.mark_unknown(intent_id, error_code=error.code)
            raise
        self._volumes[record.name] = record
        self._intents[intent_id] = IntentOutcome(intent, "CONFIRMED")
        return record

    def registered_container(self, role):
        _check(type(role) is str and role in ROLES and role in self._containers, "LIFECYCLE_CONTAINER_NOT_REGISTERED")
        return self._containers[role]

    def obtain_precheck_backend(self):
        return self.registered_container("backend")

    def register_host_task(self, intent_id, *, snapshot, expected_executable, expected_script_sha256,
                           backend_id, parent_handle_id=None):
        self._pending(intent_id)
        try:
            return self._register_host_task(intent_id, snapshot=snapshot,
                expected_executable=expected_executable, expected_script_sha256=expected_script_sha256,
                backend_id=backend_id, parent_handle_id=parent_handle_id)
        except (RestoreError, TypeError, AttributeError, KeyError) as error:
            code = error.code if isinstance(error, RestoreError) else "LIFECYCLE_TASK_DENIED"
            self.mark_unknown(intent_id, error_code=code)
            raise RestoreError(code) from None

    def _register_host_task(self, intent_id, *, snapshot, expected_executable, expected_script_sha256,
                            backend_id, parent_handle_id=None):
        intent = self._pending(intent_id)
        _check(intent.kind in ("host-relay", "host-child"), "LIFECYCLE_INTENT_MISMATCH")
        backend = self.obtain_precheck_backend()
        _check(_sha(backend_id) and backend_id == backend.container_id, "LIFECYCLE_TASK_DENIED")
        parent = None
        if intent.kind == "host-child":
            _check(type(parent_handle_id) is str and parent_handle_id in self._tasks
                   and self._tasks[parent_handle_id].kind in ("host-relay", "host-child")
                   and parent_handle_id not in self._exited, "LIFECYCLE_TASK_PARENT_REQUIRED")
            parent = self._tasks[parent_handle_id]
        else:
            _check(parent_handle_id is None, "LIFECYCLE_TASK_DENIED")
        process = ProcessRecord.from_snapshot(snapshot, expected_executable=expected_executable,
            expected_script_sha256=expected_script_sha256, original_pids=self.baseline.pids,
            kind="relay" if parent is None else "child", parent_pid=None if parent is None else parent.pid)
        identity = _digest({"run": self.run_id, "intent": intent_id, "process": process.metadata_sha256,
                            "backend": backend_id, "parent": parent_handle_id})
        _check(not any(task.pid == process.pid for task in self._tasks.values()), "LIFECYCLE_TASK_DUPLICATE")
        handle = TaskHandle(identity, self.run_id, intent_id, intent.kind, process.pid, process.start_time,
                            backend_id, None, parent_handle_id, identity)
        self._tasks[identity] = handle
        self._intents[intent_id] = IntentOutcome(intent, "CONFIRMED", identity)
        if intent.kind == "host-relay":
            self._ingress_closed = False
        return handle

    def register_exec_task(self, intent_id, *, exec_id, backend_id, pid, start_time, parent_handle_id):
        self._pending(intent_id, "container-exec")
        try:
            return self._register_exec_task(intent_id, exec_id=exec_id, backend_id=backend_id,
                pid=pid, start_time=start_time, parent_handle_id=parent_handle_id)
        except (RestoreError, TypeError, AttributeError, KeyError) as error:
            code = error.code if isinstance(error, RestoreError) else "LIFECYCLE_TASK_DENIED"
            self.mark_unknown(intent_id, error_code=code)
            raise RestoreError(code) from None

    def _register_exec_task(self, intent_id, *, exec_id, backend_id, pid, start_time, parent_handle_id):
        intent = self._pending(intent_id, "container-exec")
        _check(_sha(exec_id) and _sha(backend_id) and backend_id == self.obtain_precheck_backend().container_id
               and type(pid) is int and pid > 1
               and (type(start_time) is int and start_time > 0 or type(start_time) is str and bool(start_time)
                    and len(start_time) <= 128 and not any(ord(c) < 32 or ord(c) == 127 for c in start_time)),
               "LIFECYCLE_TASK_DENIED")
        _check(type(parent_handle_id) is str and parent_handle_id in self._tasks and parent_handle_id not in self._exited
               and self._tasks[parent_handle_id].kind in ("host-relay", "host-child"), "LIFECYCLE_TASK_PARENT_REQUIRED")
        _check(not any(task.exec_id == exec_id for task in self._tasks.values()), "LIFECYCLE_TASK_DUPLICATE")
        identity = _digest({"run": self.run_id, "intent": intent_id, "exec": exec_id, "backend": backend_id,
                            "pid": pid, "start": start_time, "parent": parent_handle_id})
        handle = TaskHandle(identity, self.run_id, intent_id, intent.kind, pid, start_time,
                            backend_id, exec_id, parent_handle_id, identity)
        self._tasks[identity] = handle
        self._intents[intent_id] = IntentOutcome(intent, "CONFIRMED", identity)
        return handle

    def pending_shutdown_tasks(self):
        """Child/exec handles first; no signalling action is executed or inferred."""
        remaining = {key: task for key, task in self._tasks.items() if key not in self._exited}
        ordered = []
        while remaining:
            leaves = sorted(key for key in remaining if not any(task.parent_handle_id == key for task in remaining.values()))
            _check(bool(leaves), "LIFECYCLE_TASK_INVALID")
            for key in leaves:
                ordered.append(remaining.pop(key))
        return tuple(ordered)

    def confirm_ingress_closed(self, *, origin, evidence_sha256):
        _check(origin == ORIGIN and _sha(evidence_sha256), "LIFECYCLE_INGRESS_UNCONFIRMED")
        self._ingress_closed = True
        self._ingress_evidence = evidence_sha256

    def confirm_task_exit(self, proof):
        _check(type(proof) is TaskExitProof and proof.handle_id in self._tasks
               and proof.identity_sha256 == self._tasks[proof.handle_id].identity_sha256,
               "LIFECYCLE_TASK_EXIT_UNCONFIRMED")
        _check(not any(task.parent_handle_id == proof.handle_id and key not in self._exited
                       for key, task in self._tasks.items()), "LIFECYCLE_TASK_CHILDREN_ACTIVE")
        self._exited[proof.handle_id] = proof

    def add_gate_proof(self, proof):
        _check(type(proof) is GateProof and proof.run_id == self.run_id, "LIFECYCLE_PROOF_INVALID")
        self._proofs[proof.gate] = proof

    def readiness(self):
        missing = tuple(gate for gate in _GATES if gate not in self._proofs
                        or not self._proofs[gate].verified or self._proofs[gate].origin != "REAL")
        return {"ready": False, "status": "PRODUCTION_EXECUTION_CLOSED", "missing_real_gates": missing,
                "service_phase": "HARD_BLOCKED", "stage_transition": "HARD_BLOCKED",
                "container_generations": "NOT_IMPLEMENTED", "proof_capture": "TRUSTED_CALLER_NOT_IMPLEMENTED"}

    def stage_transition(self, *args, **kwargs):
        """Immutable create settings require new identities; no rebuild is admitted."""
        raise RestoreError("LIFECYCLE_STAGE_TRANSITION_HARD_BLOCKED")

    def require_service_ready(self):
        raise RestoreError("LIFECYCLE_SERVICE_NOT_READY")

    def service_plan(self, *args, **kwargs):
        self.require_service_ready()

    def execute(self, *args, **kwargs):
        """No injected callback, adapter, or argv can open production execution."""
        raise RestoreError("LIFECYCLE_PRODUCTION_EXECUTION_DISABLED")

    def residuals(self):
        values = [("container", record.container_id) for record in self._containers.values()]
        values.extend(("volume", name) for name in self._volumes)
        values.extend(("task", key) for key in self._tasks if key not in self._exited)
        values.extend(("intent", key) for key, row in self._intents.items() if row.status in ("PENDING", "UNKNOWN"))
        return tuple(sorted(values))

    def cleanup_plan(self, current_metadata, current_volume_metadata=()):
        """Fresh validation is atomic: any blocker yields zero delete argv."""
        self._closed = True
        if self._cleanup_at is None:
            self._cleanup_at = self._now()
        self._cleanup_actions = ()
        self._cleanup_index = 0
        blockers = []
        if self.authorization is None:
            blockers.append("LIFECYCLE_OWNER_AUTHORIZATION_REQUIRED")
        if self.baseline is None:
            blockers.append("LIFECYCLE_BASELINE_REQUIRED")
        if not self._ingress_closed:
            blockers.append("LIFECYCLE_INGRESS_UNCONFIRMED")
        if any(key not in self._exited for key in self._tasks):
            blockers.append("LIFECYCLE_TASK_EXIT_UNCONFIRMED")
        if any(row.status in ("PENDING", "UNKNOWN") for row in self._intents.values()):
            blockers.append("LIFECYCLE_INTENT_UNRESOLVED")
        if self.cleanup_remaining_seconds() <= 0:
            blockers.append("LIFECYCLE_CLEANUP_DEADLINE_EXPIRED")
        if blockers:
            return CleanupDecision("BLOCKED_CLOSED", blockers=tuple(blockers), residuals=self.residuals())
        try:
            actions = owned_cleanup_plan(tuple(self._containers.values()), current_metadata,
                original_ids=self.baseline.container_ids, original_names=self.baseline.container_names,
                original_volume_names=self.baseline.volume_names, volume_records=tuple(self._volumes.values()),
                current_volume_metadata=current_volume_metadata, relay_stopped=True)
        except RestoreError as error:
            self._failure_code = error.code
            return CleanupDecision("FAILED_GUARD_CLOSED", blockers=(error.code,), residuals=self.residuals())
        self._cleanup_actions = actions
        return CleanupDecision("PLAN_ONLY", actions=actions, residuals=self.residuals())

    def acknowledge_cleanup(self, action, *, outcome):
        _check(self._closed and self._cleanup_index < len(self._cleanup_actions)
               and type(action) is tuple and action == self._cleanup_actions[self._cleanup_index], "LIFECYCLE_CLEANUP_RECEIPT_INVALID")
        _check(type(outcome) is str and outcome in ("SUCCESS", "FAILED", "UNKNOWN"), "LIFECYCLE_CLEANUP_RECEIPT_INVALID")
        if self.cleanup_remaining_seconds() <= 0:
            self._cleanup_actions = ()
            self._failure_code = "LIFECYCLE_CLEANUP_DEADLINE_EXPIRED"
            return CleanupDecision("FAILED_CLOSED", blockers=(self._failure_code,), residuals=self.residuals())
        if outcome != "SUCCESS":
            self._cleanup_actions = ()
            self._failure_code = "LIFECYCLE_CLEANUP_" + outcome
            return CleanupDecision("FAILED_CLOSED", blockers=(self._failure_code,), residuals=self.residuals())
        self._cleanup_index += 1
        if len(action) == 3 and action[1] == "rm":
            for role, record in tuple(self._containers.items()):
                if record.container_id == action[2]:
                    del self._containers[role]
        elif len(action) == 4 and action[1:3] == ("volume", "rm"):
            self._volumes.pop(action[3], None)
        done = self._cleanup_index == len(self._cleanup_actions)
        return CleanupDecision("RECORDED_CLEAN" if done and not self.residuals() else "RECEIPT_RECORDED",
                               residuals=self.residuals())

    def snapshot(self):
        return {"status": "CLOSED" if self._closed else "PLAN_ONLY", "run_id": self.run_id,
                "owner_authorization_recorded": self.authorization is not None,
                "production_execution": "DISABLED", "service_phase": "HARD_BLOCKED",
                "stage_transition": "HARD_BLOCKED", "container_generations": "NOT_IMPLEMENTED",
                "intent_statuses": tuple((key, row.status) for key, row in self._intents.items()),
                "residuals": self.residuals(), "failure_code": self._failure_code}
