"""Fixed cleanup sequencing and engine-adapter code; production gate closed.

Import and all unpatched public entry points perform no process or engine I/O.
The fixture adapter changes only its own copied dictionaries. Production
capture, durable intent journaling, and genuine container-exec exit evidence
must be implemented and independently admitted before the engine code runs.
OwnedLanding cleanup remains a separate audited capability.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
import math
import os
import selectors
import subprocess
import time

from .common import DOCKER, ROOT, VOLUME_NAMES, RestoreError
from .lifecycle import LifecycleRegistry
from .ownership import cleanup_plan as owned_cleanup_plan

_ISSUED = object()
_OPERATIONS = frozenset({"inspect-container", "inspect-volume", "stop", "rm", "volume-rm"})
_OUTCOMES = frozenset({"SUCCESS", "FAILED", "UNKNOWN", "TIMEOUT"})
DOCKER_ENDPOINT = "unix:///Users/hbzl/.docker/run/docker.sock"
MAX_INSPECT_BYTES = 2 * 1024 * 1024
MAX_STDERR_BYTES = 4096


def _reject(code="CLEANUP_COMPONENT_REJECTED"):
    raise RestoreError(code) from None


@dataclass(frozen=True)
class CleanupExecutionReport:
    status: str
    completed_actions: tuple[tuple[str, ...], ...] = ()
    blockers: tuple[str, ...] = ()
    residuals: tuple[tuple[str, str], ...] = ()
    origin: str = "SYNTHETIC"
    production_ready: bool = False
    landing_cleanup: str = "SEPARATE_AUDIT_REQUIRED"


@dataclass(frozen=True, init=False)
class _Observation:
    kind: str
    target: str
    present: bool
    metadata: dict | None = field(repr=False)
    _issued: object = field(repr=False, compare=False)


@dataclass(frozen=True, init=False)
class _Receipt:
    operation: str
    target: str
    outcome: str
    _issued: object = field(repr=False, compare=False)


@dataclass(frozen=True, init=False)
class _CapturedOutput:
    raw: bytes = field(repr=False)
    deadline: float
    _issued: object = field(repr=False, compare=False)


def _issue(record_type, values):
    record = object.__new__(record_type)
    for key, value in (*values, ("_issued", _ISSUED)):
        object.__setattr__(record, key, value)
    return record


def _plain(value, depth=0):
    if depth > 32:
        _reject("CLEANUP_FIXTURE_INVALID")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for child in value:
            _plain(child, depth + 1)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for child in value.values():
            _plain(child, depth + 1)
        return
    _reject("CLEANUP_FIXTURE_INVALID")


class SyntheticCleanupAdapter:
    """Exact fixture-only adapter, with no executable argv or callbacks.

    Inputs are explicitly synthetic metadata. Fault outcomes are fixed codes,
    never exception text or stderr. The adapter cannot inspect a real engine or
    mutate anything outside its copied in-memory dictionaries.
    """

    def __init__(self, *, containers=(), volumes=(), faults=None):
        self._containers = self._indexed(containers, "Id")
        self._volumes = self._indexed(volumes, "Name")
        if faults is not None and type(faults) is not dict:
            _reject("CLEANUP_FIXTURE_INVALID")
        self._faults = {} if faults is None else dict(faults)
        for key, outcome in self._faults.items():
            if (type(key) is not tuple or len(key) != 2 or type(key[0]) is not str
                    or key[0] not in _OPERATIONS or type(key[1]) is not str
                    or type(outcome) is not str or outcome not in _OUTCOMES):
                _reject("CLEANUP_FIXTURE_INVALID")
        self.events = []

    @staticmethod
    def _indexed(values, key):
        if type(values) not in (tuple, list):
            _reject("CLEANUP_FIXTURE_INVALID")
        result = {}
        for value in values:
            if (type(value) is not dict or type(value.get(key)) is not str
                    or value[key] in result):
                _reject("CLEANUP_FIXTURE_INVALID")
            _plain(value)
            result[value[key]] = deepcopy(value)
        return result

    def _fault(self, operation, target):
        return self._faults.get((operation, target), "SUCCESS")

    def _inspect(self, kind, target):
        operation = "inspect-" + kind
        self.events.append((operation, target))
        if self._fault(operation, target) != "SUCCESS":
            _reject("CLEANUP_INSPECT_FAILED")
        values = self._containers if kind == "container" else self._volumes
        return _issue(_Observation, (("kind", kind), ("target", target),
            ("present", target in values), ("metadata", deepcopy(values.get(target)))))

    def inspect_container(self, target):
        return self._inspect("container", target)

    def inspect_volume(self, target):
        return self._inspect("volume", target)

    def _operate(self, operation, target, timeout_seconds):
        if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 10:
            _reject("CLEANUP_DEADLINE_EXPIRED")
        self.events.append(("intent-" + operation, target))
        self.events.append((operation, target))
        outcome = self._fault(operation, target)
        if outcome == "SUCCESS":
            values = self._volumes if operation == "volume-rm" else self._containers
            if target not in values:
                outcome = "UNKNOWN"
            elif operation == "stop":
                values[target].setdefault("State", {})["Running"] = False
            elif operation == "rm":
                if values[target].get("State", {}).get("Running") is not False:
                    outcome = "FAILED"
                else:
                    del values[target]
            else:
                del values[target]
        self.events.append(("outcome-" + operation, target, outcome))
        return _issue(_Receipt, (("operation", operation), ("target", target), ("outcome", outcome)))

    def stop_container(self, target, *, timeout_seconds):
        return self._operate("stop", target, timeout_seconds)

    def remove_container(self, target, *, timeout_seconds):
        return self._operate("rm", target, timeout_seconds)

    def remove_volume(self, target, *, timeout_seconds):
        return self._operate("volume-rm", target, timeout_seconds)


class FixedDockerCleanupAdapter:
    """Fixed real-adapter boundary, coded but not admitted to engine I/O.

    Construction is inert. Even enabled instances require a durable trusted
    runtime journal and engine disappearance/exec-exit capture, which remain
    unimplemented. No caller command, environment, shell, or runner is accepted.
    """

    def __init__(self, registry=None, *, enabled=False):
        if type(enabled) is not bool:
            _reject("CLEANUP_ADAPTER_DISABLED")
        if enabled and (type(registry) is not LifecycleRegistry
                        or registry.authorization is None or registry.baseline is None):
            _reject("CLEANUP_AUTHORIZATION_REQUIRED")
        self.registry = registry
        self._enabled = enabled
        self._cleanup_started = None

    def _require_runtime_capture_ready(self):
        _reject("CLEANUP_DURABLE_RUNTIME_CAPTURE_NOT_IMPLEMENTED")

    def _require(self, kind, target):
        if not self._enabled or type(self.registry) is not LifecycleRegistry:
            _reject("CLEANUP_ADAPTER_DISABLED")
        if self.registry.authorization is None or self.registry.baseline is None:
            _reject("CLEANUP_AUTHORIZATION_REQUIRED")
        self.registry.scope.__post_init__()
        baseline = self.registry.baseline
        if kind == "container":
            identities = {row.container_id for row in self.registry._containers.values()}
            if type(target) is not str or target not in identities or target in baseline.container_ids:
                _reject("CLEANUP_UNREGISTERED_TARGET")
        elif kind == "volume":
            if (type(target) is not str or target not in self.registry._volumes
                    or target not in VOLUME_NAMES or target in baseline.volume_names):
                _reject("CLEANUP_UNREGISTERED_TARGET")
        else:
            _reject("CLEANUP_UNREGISTERED_TARGET")
        self._require_runtime_capture_ready()

    def _argv(self, operation, target, timeout_seconds):
        kind = "volume" if operation in ("inspect-volume", "volume-rm") else "container"
        self._require(kind, target)
        base = (DOCKER, "--host", DOCKER_ENDPOINT)
        if operation == "inspect-container":
            return base + ("container", "inspect", target)
        if operation == "inspect-volume":
            return base + ("volume", "inspect", target)
        if operation not in ("stop", "rm", "volume-rm"):
            _reject("CLEANUP_ACTION_REJECTED")
        if type(timeout_seconds) not in (int, float):
            _reject("CLEANUP_DEADLINE_EXPIRED")
        try:
            valid = math.isfinite(timeout_seconds) and 0 < timeout_seconds <= 10
        except (ValueError, OverflowError):
            valid = False
        if not valid:
            _reject("CLEANUP_DEADLINE_EXPIRED")
        if operation == "stop":
            # Floor to a finite engine grace period below the host deadline.
            return base + ("stop", "--time", str(max(0, math.floor(timeout_seconds - 1))), target)
        return base + (("rm", target) if operation == "rm" else ("volume", "rm", target))

    @staticmethod
    def _reap(process):
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=0.25)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=0.25)
            else:
                process.wait(timeout=0.25)
        except Exception:
            _reject("CLEANUP_HOST_CHILD_REAP_UNCONFIRMED")

    def _capture(self, operation, target, *, timeout_seconds=10.0):
        argv = self._argv(operation, target, timeout_seconds)
        now = time.monotonic()
        if self._cleanup_started is None:
            self._cleanup_started = now
        try:
            budget = min(float(timeout_seconds), self.registry.cleanup_remaining_seconds(),
                         self._cleanup_started + 600 - now)
        except Exception:
            _reject("CLEANUP_DEADLINE_EXPIRED")
        if not math.isfinite(budget) or budget <= 0:
            _reject("CLEANUP_DEADLINE_EXPIRED")
        deadline = now + budget
        output = bytearray()
        stderr_bytes = 0
        process = None
        try:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=False, close_fds=True, bufsize=0,
                env={"DOCKER_CONFIG": str(ROOT / "runtime/docker-cli")})
            with selectors.DefaultSelector() as selector:
                for stream, kind in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, kind)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        _reject("CLEANUP_DEADLINE_EXPIRED")
                    for key, _mask in selector.select(min(remaining, 0.1)):
                        if time.monotonic() >= deadline:
                            _reject("CLEANUP_DEADLINE_EXPIRED")
                        try:
                            chunk = os.read(key.fd, 65536)
                        except BlockingIOError:
                            continue
                        if not chunk:
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                        elif key.data == "stdout":
                            if len(output) + len(chunk) > MAX_INSPECT_BYTES:
                                _reject("CLEANUP_STDOUT_LIMIT")
                            output.extend(chunk)
                        else:
                            stderr_bytes += len(chunk)
                            if stderr_bytes > MAX_STDERR_BYTES:
                                _reject("CLEANUP_STDERR_LIMIT")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _reject("CLEANUP_DEADLINE_EXPIRED")
            if process.wait(timeout=remaining) != 0 or stderr_bytes:
                # Exit 1 or arbitrary engine stderr is never a NotFound proof.
                _reject("CLEANUP_DOCKER_COMMAND_FAILED")
            if time.monotonic() >= deadline:
                _reject("CLEANUP_DEADLINE_EXPIRED")
            # Preserve this operation's original absolute deadline through
            # child reaping, JSON decoding and receipt validation.
            return _issue(_CapturedOutput, (("raw", bytes(output)), ("deadline", deadline)))
        except RestoreError:
            raise
        except subprocess.TimeoutExpired:
            _reject("CLEANUP_DEADLINE_EXPIRED")
        except Exception:
            _reject("CLEANUP_DOCKER_COMMAND_FAILED")
        finally:
            if process is not None:
                try:
                    self._reap(process)
                finally:
                    for stream in (process.stdout, process.stderr):
                        if stream is not None:
                            try:
                                stream.close()
                            except Exception:
                                pass

    @staticmethod
    def _check_capture_deadline(capture):
        if (type(capture) is not _CapturedOutput or capture._issued is not _ISSUED
                or type(capture.raw) is not bytes or type(capture.deadline) is not float
                or not math.isfinite(capture.deadline)):
            _reject("CLEANUP_CAPTURE_INVALID")
        now = time.monotonic()
        if type(now) not in (int, float) or not math.isfinite(now) or now >= capture.deadline:
            _reject("CLEANUP_DEADLINE_EXPIRED")

    def _inspect(self, kind, target):
        capture = self._capture("inspect-" + kind, target)
        self._check_capture_deadline(capture)
        raw = capture.raw
        try:
            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result:
                        _reject("CLEANUP_CAPTURE_INVALID")
                    result[key] = value
                return result
            def constant(_value):
                _reject("CLEANUP_CAPTURE_INVALID")
            values = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                                parse_constant=constant)
            if type(values) is not list or len(values) != 1 or type(values[0]) is not dict:
                _reject("CLEANUP_CAPTURE_INVALID")
            metadata = values[0]
            _plain(metadata)
            key = "Id" if kind == "container" else "Name"
            if metadata.get(key) != target:
                _reject("CLEANUP_CAPTURE_INVALID")
            self._check_capture_deadline(capture)
        except RestoreError:
            raise
        except Exception:
            _reject("CLEANUP_CAPTURE_INVALID")
        return _issue(_Observation, (("kind", kind), ("target", target),
                                   ("present", True), ("metadata", metadata)))

    def inspect_container(self, target):
        return self._inspect("container", target)

    def inspect_volume(self, target):
        return self._inspect("volume", target)

    def _operate(self, operation, target, timeout_seconds):
        capture = self._capture(operation, target, timeout_seconds=timeout_seconds)
        self._check_capture_deadline(capture)
        raw = capture.raw
        if raw not in (target.encode("ascii"), target.encode("ascii") + b"\n"):
            _reject("CLEANUP_RECEIPT_INVALID")
        self._check_capture_deadline(capture)
        return _issue(_Receipt, (("operation", operation), ("target", target), ("outcome", "SUCCESS")))

    def stop_container(self, target, *, timeout_seconds):
        return self._operate("stop", target, timeout_seconds)

    def remove_container(self, target, *, timeout_seconds):
        return self._operate("rm", target, timeout_seconds)

    def remove_volume(self, target, *, timeout_seconds):
        return self._operate("volume-rm", target, timeout_seconds)


def _report(registry, status, *, completed=(), blockers=(), origin="SYNTHETIC"):
    residuals = registry.residuals() if type(registry) is LifecycleRegistry else ()
    return CleanupExecutionReport(status, tuple(completed), tuple(blockers), residuals, origin)


def execute_cleanup(registry=None, adapter=None, *, enabled=False):
    """Hard-closed public production facade; DTOs and a flag cannot open it."""
    if type(enabled) is not bool or not enabled:
        return _report(registry, "PRODUCTION_CLEANUP_DISABLED",
                       blockers=("CLEANUP_ADAPTER_DISABLED",), origin="NOT_RUN")
    if (type(registry) is not LifecycleRegistry or type(adapter) is not FixedDockerCleanupAdapter
            or adapter.registry is not registry):
        return _report(registry, "PRODUCTION_CLEANUP_DISABLED",
                       blockers=("CLEANUP_PRODUCTION_ADAPTER_REQUIRED",), origin="NOT_RUN")
    return _report(registry, "PRODUCTION_CLEANUP_DISABLED",
                   blockers=("CLEANUP_DURABLE_RUNTIME_CAPTURE_NOT_IMPLEMENTED",), origin="NOT_RUN")


def _observed(observation, *, kind, target, required):
    if (type(observation) is not _Observation or observation._issued is not _ISSUED
            or observation.kind != kind or observation.target != target
            or type(observation.present) is not bool):
        _reject("CLEANUP_CAPTURE_INVALID")
    if required and (not observation.present or type(observation.metadata) is not dict):
        _reject("CLEANUP_REGISTERED_RESOURCE_MISSING")
    if not required and (observation.present or observation.metadata is not None):
        _reject("CLEANUP_REMOVAL_UNCONFIRMED")
    return observation.metadata


def _metadata(registry, adapter):
    # Read the planner's issued records, never construct a replacement record
    # from a DTO. This bridge is deliberately limited to the exact registry.
    containers = tuple(registry._containers.values())
    volumes = tuple(registry._volumes.values())
    current = [_observed(adapter.inspect_container(row.container_id),
               kind="container", target=row.container_id, required=True) for row in containers]
    current_volumes = [_observed(adapter.inspect_volume(row.name),
                      kind="volume", target=row.name, required=True) for row in volumes]
    return containers, volumes, current, current_volumes


def _fresh_plan(registry, adapter):
    containers, volumes, current, current_volumes = _metadata(registry, adapter)
    baseline = registry.baseline
    actions = owned_cleanup_plan(containers, current, original_ids=baseline.container_ids,
        original_names=baseline.container_names, original_volume_names=baseline.volume_names,
        volume_records=volumes, current_volume_metadata=current_volumes, relay_stopped=True)
    return actions, current


def _failed(registry, action, completed, code, *, acknowledged=False):
    if not acknowledged:
        try:
            registry.acknowledge_cleanup(action, outcome="UNKNOWN")
        except Exception:
            return _report(registry, "FIXTURE_CLEANUP_FAILED", completed=completed,
                           blockers=(code, "CLEANUP_RECEIPT_RECORD_FAILED"))
    return _report(registry, "FIXTURE_CLEANUP_FAILED", completed=completed, blockers=(code,))


def execute_fixture_cleanup(registry, adapter, *, enabled=False):
    """Run only the exact in-memory fixture adapter, with fresh per-step guards.

    A passed flag enables synthetic mutation only. This function captures no
    process facts, never confirms task exits, and never imports a real adapter.
    An external journal must record its own intents/results before any future
    real operation; these fixture events are not a persistent runtime journal.
    """
    if type(registry) is not LifecycleRegistry or type(adapter) is not SyntheticCleanupAdapter:
        return _report(registry, "FIXTURE_CLEANUP_BLOCKED", blockers=("CLEANUP_SYNTHETIC_SCOPE_REQUIRED",))
    if type(enabled) is not bool or not enabled:
        return _report(registry, "FIXTURE_CLEANUP_BLOCKED", blockers=("CLEANUP_FIXTURE_NOT_ENABLED",))
    if any(proof.origin != "SYNTHETIC" for proof in registry._exited.values()):
        return _report(registry, "FIXTURE_CLEANUP_BLOCKED", blockers=("CLEANUP_SYNTHETIC_SCOPE_REQUIRED",))
    try:
        _containers, _volumes, current, current_volumes = _metadata(registry, adapter)
        decision = registry.cleanup_plan(current, current_volumes)
    except Exception:
        # Close the lifecycle even if capture fails, without issuing mutations.
        try:
            registry.cleanup_plan((), ())
        except Exception:
            pass
        return _report(registry, "FIXTURE_CLEANUP_BLOCKED", blockers=("CLEANUP_INSPECT_FAILED",))
    if decision.status != "PLAN_ONLY":
        return _report(registry, "FIXTURE_CLEANUP_BLOCKED", blockers=decision.blockers)
    completed = []
    for action in decision.actions:
        try:
            remaining = registry.cleanup_remaining_seconds()
            if remaining <= 0:
                _reject("CLEANUP_DEADLINE_EXPIRED")
            fresh_actions, current = _fresh_plan(registry, adapter)
            if action not in fresh_actions or action[0] != DOCKER:
                _reject("CLEANUP_FRESH_ACTION_MISMATCH")
            timeout = min(10.0, registry.cleanup_remaining_seconds())
            if timeout <= 0:
                _reject("CLEANUP_DEADLINE_EXPIRED")
            if len(action) == 3 and action[1] in ("stop", "rm"):
                target = action[2]
                operation = action[1]
                if operation == "rm":
                    metadata = next(row for row in current if row.get("Id") == target)
                    state = metadata.get("State")
                    if type(state) is not dict or state.get("Running") is not False:
                        _reject("CLEANUP_STOP_UNCONFIRMED")
                receipt = (adapter.stop_container(target, timeout_seconds=timeout) if operation == "stop"
                           else adapter.remove_container(target, timeout_seconds=timeout))
            elif len(action) == 4 and action[1:3] == ("volume", "rm") and action[3] in VOLUME_NAMES:
                target = action[3]
                operation = "volume-rm"
                receipt = adapter.remove_volume(target, timeout_seconds=timeout)
            else:
                _reject("CLEANUP_ACTION_REJECTED")
            if (type(receipt) is not _Receipt or receipt._issued is not _ISSUED
                    or receipt.operation != operation or receipt.target != target
                    or receipt.outcome not in _OUTCOMES):
                _reject("CLEANUP_RECEIPT_INVALID")
            if receipt.outcome != "SUCCESS":
                registry.acknowledge_cleanup(action, outcome="FAILED" if receipt.outcome == "FAILED" else "UNKNOWN")
                return _report(registry, "FIXTURE_CLEANUP_FAILED", completed=completed,
                               blockers=("CLEANUP_OPERATION_" + receipt.outcome,))
            if operation == "stop":
                observation = adapter.inspect_container(target)
                metadata = _observed(observation, kind="container", target=target, required=True)
                if metadata.get("State", {}).get("Running") is not False:
                    _reject("CLEANUP_STOP_UNCONFIRMED")
                _fresh_plan(registry, adapter)
            else:
                observation = adapter.inspect_volume(target) if operation == "volume-rm" else adapter.inspect_container(target)
                _observed(observation, kind="volume" if operation == "volume-rm" else "container",
                          target=target, required=False)
            acknowledgement = registry.acknowledge_cleanup(action, outcome="SUCCESS")
            if acknowledgement.status == "FAILED_CLOSED":
                return _report(registry, "FIXTURE_CLEANUP_FAILED", completed=completed,
                               blockers=acknowledgement.blockers)
            completed.append(action)
        except RestoreError as error:
            return _failed(registry, action, completed, error.code)
        except Exception:
            return _failed(registry, action, completed, "CLEANUP_OPERATION_UNKNOWN")
    return _report(registry, "FIXTURE_RECORDED_RESOURCES_CLEAN" if not registry.residuals()
                   else "FIXTURE_CLEANUP_PARTIAL", completed=completed)
