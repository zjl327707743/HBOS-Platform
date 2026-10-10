"""Fixed volume-root metadata proposals and bounded empty-volume tar checks.

Importing this module performs no I/O. No function executes Docker, creates a
volume/container, calls chown, or reads restoration payloads. All initialization
plans are non-executable. Docker daemon archive/no-copy/read-only-rootfs behavior
and the actual UID/mode result remain NOT_RUN, including after fixture success.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from functools import wraps
import io
import re
import tarfile
from types import MappingProxyType

from .common import BENCH, DOCKER, OWNER, VOLUME_NAMES, RestoreError
from .lifecycle import LifecycleRegistry
from .ownership import ResourceRecord, VolumeRecord

MAX_VOLUME_TAR_BYTES = 10 * 1024
MAX_INITIAL_MTIME = 4_102_444_800
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_OBSERVATION_ISSUED = object()
_PLAN_ISSUED = object()


@dataclass(frozen=True)
class VolumeTarget:
    volume: str
    role: str
    destination: str
    uid: int
    gid: int
    mode: int

    @property
    def parent(self):
        return self.destination.rsplit("/", 1)[0] or "/"

    @property
    def member(self):
        return self.destination.rsplit("/", 1)[1]


_ROWS = (
    VolumeTarget(OWNER + "-db-data", "db", "/var/lib/mysql", 999, 999, 0o700),
    VolumeTarget(OWNER + "-redis-cache-data", "redis-cache", "/data", 999, 1000, 0o700),
    VolumeTarget(OWNER + "-redis-queue-data", "redis-queue", "/data", 999, 1000, 0o700),
    VolumeTarget(OWNER + "-sites", "backend", BENCH + "/sites", 1000, 1000, 0o755),
    VolumeTarget(OWNER + "-logs", "backend", BENCH + "/logs", 1000, 1000, 0o700),
    VolumeTarget(OWNER + "-assets-data", "backend", BENCH + "/sites/assets", 1000, 1000, 0o755),
    VolumeTarget(OWNER + "-frappe-dist", "backend", BENCH + "/apps/frappe/frappe/public/dist", 1000, 1000, 0o755),
    VolumeTarget(OWNER + "-erpnext-dist", "backend", BENCH + "/apps/erpnext/erpnext/public/dist", 1000, 1000, 0o755),
    VolumeTarget(OWNER + "-hbos-lims-dist", "backend", BENCH + "/apps/hb_lims_app/hb_lims_app/public/hbos-lims", 1000, 1000, 0o755),
)
_TARGETS = MappingProxyType({row.volume: row for row in _ROWS})


def _check(condition, code="VOLUME_INITIALIZATION_REJECTED"):
    if not condition:
        raise RestoreError(code) from None


def _fixed_errors(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except RestoreError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError, RecursionError):
            raise RestoreError("VOLUME_INITIALIZATION_REJECTED") from None
    return guarded


def _target(volume_name):
    _check(type(volume_name) is str and volume_name in _TARGETS, "VOLUME_TARGET_DENIED")
    return _TARGETS[volume_name]


def fixed_volume_matrix() -> dict:
    """Return the exact nine non-executable rows; never admit a caller path."""
    return {
        "status": "OFFLINE_VOLUME_INITIALIZATION_PROPOSAL", "executable": False,
        "daemon_archive_compatibility": "NOT_RUN", "volume_nocopy_compatibility": "NOT_RUN",
        "actual_uid_mode_verification": "NOT_RUN", "extra_containers": 0,
        "root_exec_chown": False, "capabilities_added": [],
        "initialization_phase": "volume-initialize", "maximum_simultaneous_containers": 5,
        "container_incarnations_proposal": 10, "service_recreation": "NOT_RUN",
        "rows": [{"volume": row.volume, "role": row.role, "destination": row.destination,
                  "copy_parent": row.parent, "tar_directory": row.member, "uid": row.uid,
                  "gid": row.gid, "mode": format(row.mode, "04o"),
                  "requires_fresh_registered_receipts": True, "requires_stopped_container": True,
                  "requires_volume_nocopy": True, "requires_writable_target_mount": True,
                  "requires_empty_volume_root_capture": True, "requires_existing_parent_directory": True,
                  "runtime_status": "NOT_RUN", "executable": False}
                 for row in _ROWS],
        "pending_gates": ["NO_COPY_AND_RW_INITIALIZATION_PHASE_DAEMON_COMPATIBILITY_NOT_RUN",
                          "NESTED_MOUNT_EMPTY_VOLUME_CAPTURE_NOT_VERIFIED",
                          "STOPPED_CONTAINER_PARENT_PATH_AND_VOLUME_ARCHIVE_CAPTURE_NOT_RUN",
                          "DOCKER_DAEMON_ARCHIVE_UID_MODE_AND_RO_ROOTFS_COMPATIBILITY_NOT_RUN",
                          "ACTUAL_VOLUME_ROOT_UID_MODE_AND_NO_UNEXPECTED_FILES_NOT_RUN"],
    }


def build_owner_tar(volume_name: str) -> bytes:
    """Produce one fixed root-directory header, no payload or caller members."""
    row = _target(volume_name)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        member = tarfile.TarInfo(row.member)
        member.type = tarfile.DIRTYPE
        member.mode = row.mode
        member.uid, member.gid = row.uid, row.gid
        member.mtime = 0
        member.uname = member.gname = ""
        member.size = 0
        archive.addfile(member)
    raw = stream.getvalue()
    _check(len(raw) == MAX_VOLUME_TAR_BYTES, "VOLUME_TAR_REJECTED")
    return raw


def validate_empty_volume_tar(volume_name: str, raw: bytes) -> dict:
    """Validate a bounded root-only archive captured from a fresh empty volume.

    This is a codec check, not a capture or provenance assertion. Initial root
    UID0/GID0/mode0755 is a strict proposal requiring real daemon compatibility
    verification. Any existing child, prior owner initialization, or alternate
    layout is a collision and is never overwritten by this component.
    """
    row = _target(volume_name)
    _check(type(raw) is bytes and 1536 <= len(raw) <= MAX_VOLUME_TAR_BYTES
           and len(raw) % 512 == 0, "VOLUME_TAR_REJECTED")
    try:
        member = tarfile.TarInfo.frombuf(raw[:512], "utf-8", "strict")
        name = member.name[:-1] if member.name.endswith("/") else member.name
        _check(member.type == tarfile.DIRTYPE and member.size == 0 and member.sparse is None
               and name == row.member and not member.linkname and not member.pax_headers,
               "VOLUME_ROOT_COLLISION")
        _check(member.uid == 0 and member.gid == 0 and member.mode == 0o755,
               "VOLUME_ROOT_COLLISION")
        _check(type(member.mtime) is int and 0 <= member.mtime < MAX_INITIAL_MTIME,
               "VOLUME_TAR_REJECTED")
        # No PAX/global/header override or second member can hide in this tail.
        _check(not any(raw[512:]), "VOLUME_ROOT_COLLISION")
    except RestoreError:
        raise
    except (tarfile.TarError, ValueError, TypeError, UnicodeError, OverflowError):
        raise RestoreError("VOLUME_TAR_REJECTED") from None
    return {"status": "EMPTY_ROOT_TAR_CODEC_VALIDATED", "members": 1, "payload_bytes": 0,
            "uid": 0, "gid": 0, "mode": "0755", "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "capture_provenance": "TRUSTED_CALLER_REQUIRED"}


def _registered_context(registry, container_record, volume_record, container_intent_id,
                        volume_intent_id, current_container_metadata, current_volume_metadata):
    _check(type(registry) is LifecycleRegistry and type(container_record) is ResourceRecord
           and type(volume_record) is VolumeRecord, "VOLUME_REGISTERED_RECEIPTS_REQUIRED")
    _check(registry.authorization is not None and registry.baseline is not None
           and not registry._closed and registry.remaining_seconds() > 0,
           "VOLUME_LIFECYCLE_CLOSED")
    row = _target(volume_record.name)
    _check(container_record.spec.role == row.role
           and container_record.spec.phase == "volume-initialize"
           and registry.registered_container(row.role) is container_record
           and registry._volumes.get(row.volume) is volume_record,
           "VOLUME_REGISTERED_RECEIPTS_REQUIRED")
    for intent_id, kind, target, observed in (
        (container_intent_id, "container", row.role, container_record.container_id),
        (volume_intent_id, "volume", row.volume, None),
    ):
        _check(type(intent_id) is str and intent_id in registry._intents,
               "VOLUME_REGISTERED_RECEIPTS_REQUIRED")
        receipt = registry._intents[intent_id]
        _check(receipt.status == "CONFIRMED" and receipt.intent.run_id == registry.run_id
               and receipt.intent.kind == kind and receipt.intent.target == target
               and receipt.observed_identity == observed,
               "VOLUME_REGISTERED_RECEIPTS_REQUIRED")
    baseline = registry.baseline
    refreshed = ResourceRecord.from_inspect(current_container_metadata, expected=container_record.spec,
        original_ids=baseline.container_ids, original_names=baseline.container_names,
        original_volume_names=baseline.volume_names, db_id=container_record.db_id)
    current_volume = VolumeRecord.from_inspect(current_volume_metadata, original_volume_names=baseline.volume_names)
    _check(refreshed == container_record and current_volume == volume_record,
           "VOLUME_REGISTERED_IDENTITY_CHANGED")
    state = current_container_metadata.get("State")
    _check(type(state) is dict and state.get("Running") is False and state.get("Paused") is False
           and state.get("Restarting") is False and state.get("Dead") is False
           and state.get("Status") in ("created", "exited"), "VOLUME_CONTAINER_NOT_STOPPED")
    candidates = [mount for mount in container_record.spec.mounts
                  if mount.kind == "volume" and mount.source == row.volume and mount.destination == row.destination]
    _check(len(candidates) == 1 and candidates[0].read_only is False and candidates[0].no_copy is True
           and sum(mount.kind == "volume" and mount.source == row.volume
                   for mount in container_record.spec.mounts) == 1,
           "VOLUME_WRITABLE_TARGET_REQUIRED")
    declarations = [mount for mount in current_container_metadata["HostConfig"]["Mounts"]
                    if mount.get("Type") == "volume" and mount.get("Source") == row.volume
                    and mount.get("Target") == row.destination]
    options = declarations[0].get("VolumeOptions") if len(declarations) == 1 else None
    _check(len(declarations) == 1 and declarations[0].get("ReadOnly") is False
           and type(options) is dict and set(options) == {"NoCopy"}
           and options["NoCopy"] is True, "VOLUME_NOCOPY_REQUIRED")
    return row


@dataclass(frozen=True, init=False)
class EmptyVolumeObservation:
    run_id: str
    container_id: str
    volume_name: str
    container_intent_id: str
    volume_intent_id: str
    capture_sha256: str
    origin: str
    parent_directory_confirmed: bool
    _issued: object = field(repr=False, compare=False)

    @classmethod
    @_fixed_errors
    def from_archive(cls, registry, container_record, volume_record, *, container_intent_id,
                     volume_intent_id, current_container_metadata, current_volume_metadata,
                     archive_bytes, expected_archive_sha256, origin, parent_directory_confirmed=False):
        row = _registered_context(registry, container_record, volume_record, container_intent_id,
            volume_intent_id, current_container_metadata, current_volume_metadata)
        _check(type(origin) is str and origin in ("SYNTHETIC", "REAL")
               and parent_directory_confirmed is True
               and type(expected_archive_sha256) is str and _SHA.fullmatch(expected_archive_sha256),
               "VOLUME_CAPTURE_REJECTED")
        result = validate_empty_volume_tar(row.volume, archive_bytes)
        _check(result["sha256"] == expected_archive_sha256, "VOLUME_CAPTURE_HASH_MISMATCH")
        observation = object.__new__(cls)
        for key, value in (("run_id", registry.run_id), ("container_id", container_record.container_id),
            ("volume_name", row.volume), ("container_intent_id", container_intent_id),
            ("volume_intent_id", volume_intent_id), ("capture_sha256", expected_archive_sha256),
            ("origin", origin), ("parent_directory_confirmed", True), ("_issued", _OBSERVATION_ISSUED)):
            object.__setattr__(observation, key, value)
        return observation


@dataclass(frozen=True, init=False)
class VolumeInitializationPlan:
    volume_name: str
    role: str
    run_id: str
    argv: tuple[str, ...]
    tar_sha256: str
    tar_bytes: bytes = field(repr=False)
    executable: bool = False
    _issued: object = field(repr=False, compare=False)

    def __post_init__(self):
        row = _target(self.volume_name)
        _check(self.role == row.role and type(self.run_id) is str and _SHA.fullmatch(self.run_id)
               and type(self.argv) is tuple and len(self.argv) == 5
               and self.argv[:4] == (DOCKER, "cp", "-a", "-")
               and type(self.argv[4]) is str and ":" in self.argv[4]
               and self.argv[4].rsplit(":", 1)[1] == row.parent
               and _SHA.fullmatch(self.argv[4].split(":", 1)[0])
               and type(self.tar_bytes) is bytes and self.tar_bytes == build_owner_tar(self.volume_name)
               and self.tar_sha256 == hashlib.sha256(self.tar_bytes).hexdigest()
               and self.executable is False and self._issued is _PLAN_ISSUED, "VOLUME_PLAN_REJECTED")

    @_fixed_errors
    def public_summary(self):
        self.__post_init__()
        return {"status": "VOLUME_INITIALIZATION_PLAN_ONLY", "volume": self.volume_name,
                "role": self.role, "run_id": self.run_id, "tar_sha256": self.tar_sha256,
                "tar_bytes": len(self.tar_bytes), "executable": False,
                "daemon_compatibility": "NOT_RUN", "actual_uid_mode": "NOT_RUN"}


@_fixed_errors
def prepare_volume_initialization(registry, container_record, volume_record, *, container_intent_id,
        volume_intent_id, current_container_metadata, current_volume_metadata, observation):
    """Bind the fixed proposal to fresh registered receipts; never execute it."""
    row = _registered_context(registry, container_record, volume_record, container_intent_id,
        volume_intent_id, current_container_metadata, current_volume_metadata)
    _check(type(observation) is EmptyVolumeObservation and observation._issued is _OBSERVATION_ISSUED
           and observation.run_id == registry.run_id and observation.container_id == container_record.container_id
           and observation.volume_name == row.volume and observation.container_intent_id == container_intent_id
           and observation.volume_intent_id == volume_intent_id and observation.parent_directory_confirmed is True,
           "VOLUME_CAPTURE_REJECTED")
    tar_bytes = build_owner_tar(row.volume)
    plan = object.__new__(VolumeInitializationPlan)
    values = {"volume_name": row.volume, "role": row.role, "run_id": registry.run_id,
        "argv": (DOCKER, "cp", "-a", "-", container_record.container_id + ":" + row.parent),
        "tar_sha256": hashlib.sha256(tar_bytes).hexdigest(), "tar_bytes": tar_bytes,
        "executable": False, "_issued": _PLAN_ISSUED}
    for key, value in values.items():
        object.__setattr__(plan, key, value)
    plan.__post_init__()
    return plan


def execute_volume_initialization(*args, **kwargs):
    """Neither injected argv nor callbacks can open the Docker write boundary."""
    raise RestoreError("VOLUME_EXECUTION_DISABLED")
