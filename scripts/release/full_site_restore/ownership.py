"""Pure ownership checks and argv plans; never inspect, execute, kill or delete.

Container admission is only for the fixed namespace-precheck sleep process;
service startup/restore transitions and compatibility remain NOT_VERIFIED.
Inputs are private inspect snapshots captured by a trusted, separately reviewed
caller. Checks prove metadata consistency, not kernel namespace or filesystem
isolation. These plans are not a complete restore lifecycle cleanup executor.
Execution must recheck identities immediately beforehand, including PID reuse.
Nonempty baselines are required but their truth depends on the trusted capture
caller. Labels/exclusion alone do not prove creation in this run; actual creation
registration and service lifecycle transitions are NOT_IMPLEMENTED.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
from functools import wraps
from pathlib import PurePosixPath
import re

from .common import (APP_NAMES, BENCH, DB_IMAGE, DOCKER, FRAPPE_IMAGE, OWNER,
                     OWNER_LABEL, REDIS_IMAGE, ROOT, ROLES, VOLUME_NAMES,
                     RestoreError)

_ISSUED = object()
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_IMAGES = {"db": DB_IMAGE, "redis-cache": REDIS_IMAGE,
           "redis-queue": REDIS_IMAGE, "backend": FRAPPE_IMAGE,
           "frontend": FRAPPE_IMAGE}
# These are independent image-inspect Id pins from the preparation evidence.
# Equality with these particular RepoDigest suffixes is incidental; it is not
# Docker's general image identity rule. Real execution must recheck the pins.
_IMAGE_IDS = {
    "db": "sha256:efb4959ef2c835cd735dbc388eb9ad6aab0c78dd64febcd51bc17481111890c4",
    "redis-cache": "sha256:ec5e187c913d422cdf60f4216a5fdfb95246792c6de6fe21ff5bed75cbfc8c23",
    "redis-queue": "sha256:ec5e187c913d422cdf60f4216a5fdfb95246792c6de6fe21ff5bed75cbfc8c23",
    "backend": "sha256:d349cceb89693d54525ef9696c29af772c05ad4f42af723742cbee4e62420583",
    "frontend": "sha256:d349cceb89693d54525ef9696c29af772c05ad4f42af723742cbee4e62420583",
}
_PRECHECK_COMMAND = ("/bin/sleep", "2700")
_RUNTIME_FILES = {
    "db.cnf": {"db": "/run/hbos-restore/db.cnf"},
    "nginx.conf": {"frontend": "/run/hbos-restore/nginx.conf"},
    "forward.py": {"backend": "/run/hbos-restore/forward.py"},
    "full_site_restore": {"backend": "/run/hbos-restore/full_site_restore"},
}


def _fixed_errors(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except RestoreError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError,
                RecursionError):
            raise RestoreError("OWNERSHIP_METADATA_INVALID") from None
    return guarded


def _check(condition, code="OWNERSHIP_METADATA_INVALID"):
    if not condition:
        raise RestoreError(code)


def _identifier(value):
    _check(type(value) is str and bool(_HEX.fullmatch(value)))
    return value


def _text(value):
    _check(type(value) is str and "\x00" not in value
           and not any(ord(c) < 32 or ord(c) == 127 for c in value))
    return value


def _path(value):
    value = _text(value)
    _check(value.startswith("/") and not value.startswith("//")
           and ":" not in value and str(PurePosixPath(value)) == value
           and ".." not in PurePosixPath(value).parts)
    return value


def _names(values):
    _check(type(values) in (tuple, list, set, frozenset))
    return frozenset(_text(value) for value in values)


def _ids(values):
    return frozenset(_identifier(value) for value in _names(values))


def _baseline(original_ids, original_names, original_volume_names):
    identities = _ids(original_ids)
    names = _names(original_names)
    volumes = _names(original_volume_names)
    _check(bool(identities) and bool(names) and bool(volumes),
           "OWNERSHIP_BASELINE_REQUIRED")
    _check(all(name for name in names) and all(name for name in volumes))
    return identities, names, volumes


def _process_baseline(values):
    _check(type(values) in (tuple, list, set, frozenset)
           and all(type(pid) is int and pid > 1 for pid in values))
    _check(bool(values), "OWNERSHIP_BASELINE_REQUIRED")
    return frozenset(values)


def _sequence(value):
    _check(type(value) in (list, tuple))
    return tuple(_text(item) for item in value)


def _digest(value):
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise RestoreError("OWNERSHIP_METADATA_INVALID") from None
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class MountSpec:
    kind: str
    source: str
    destination: str
    read_only: bool
    no_copy: bool = False


@dataclass(frozen=True)
class ContainerSpec:
    """Exact trusted matrix row, not a client-provided mount allowlist."""

    role: str
    image: str
    mounts: tuple[MountSpec, ...] = ()
    entrypoint: tuple[str, ...] = ()
    command: tuple[str, ...] = _PRECHECK_COMMAND
    user: str = "1000:1000"
    read_only_rootfs: bool = True
    phase: str = "namespace-precheck"


def _allowed_volume_mounts(role):
    if role == "db":
        return {(OWNER + "-db-data", "/var/lib/mysql")}
    if role in ("redis-cache", "redis-queue"):
        return {(OWNER + "-" + role + "-data", "/data")}
    return {(OWNER + "-sites", BENCH + "/sites"),
            (OWNER + "-logs", BENCH + "/logs"),
            (OWNER + "-assets-data", BENCH + "/assets"),
            (OWNER + "-assets-data", BENCH + "/sites/assets"),
            (OWNER + "-frappe-dist", BENCH + "/apps/frappe/frappe/public/dist"),
            (OWNER + "-erpnext-dist", BENCH + "/apps/erpnext/erpnext/public/dist"),
            (OWNER + "-hbos-lims-dist", BENCH + "/apps/hb_lims_app/hb_lims_app/public/hbos-lims")}


def _allowed_bind_mounts(role):
    result = set()
    if role in ("backend", "frontend"):
        result.update((str(ROOT) + "/snapshot/apps/" + app, BENCH + "/apps/" + app)
                      for app in APP_NAMES)
        result.update(((str(ROOT) + "/snapshot/env", BENCH + "/env"),
                       (str(ROOT) + "/snapshot/fonts", BENCH + "/fonts")))
    result.update((str(ROOT) + "/runtime/" + name, destinations[role])
                  for name, destinations in _RUNTIME_FILES.items() if role in destinations)
    return result


def _spec(spec):
    _check(type(spec) is ContainerSpec and spec.role in ROLES)
    _check(spec.image == _IMAGES[spec.role], "OWNERSHIP_IMAGE_MISMATCH")
    _check(type(spec.mounts) is tuple and type(spec.read_only_rootfs) is bool)
    _sequence(spec.entrypoint)
    _sequence(spec.command)
    _text(spec.user)
    _check(spec.entrypoint == () and spec.command == _PRECHECK_COMMAND
           and spec.user == "1000:1000" and spec.read_only_rootfs is True,
           "OWNERSHIP_UNSUPPORTED_PHASE")
    _check(type(spec.phase) is str and spec.phase in ("namespace-precheck", "volume-initialize"),
           "OWNERSHIP_UNSUPPORTED_PHASE")
    destinations = set()
    initialized_volumes = set()
    for mount in spec.mounts:
        _check(type(mount) is MountSpec and type(mount.read_only) is bool and type(mount.no_copy) is bool)
        _path(mount.destination)
        _check(mount.destination not in destinations)
        destinations.add(mount.destination)
        if mount.kind == "volume":
            _check((mount.source, mount.destination) in _allowed_volume_mounts(spec.role),
                   "OWNERSHIP_MOUNT_DENIED")
            if spec.phase == "volume-initialize":
                _check(spec.role != "frontend" and mount.no_copy is True and mount.read_only is False
                       and mount.source not in initialized_volumes
                       and mount.destination != BENCH + "/assets", "OWNERSHIP_MOUNT_DENIED")
                initialized_volumes.add(mount.source)
            elif mount.source.endswith(("assets-data", "frappe-dist", "erpnext-dist", "hbos-lims-dist")):
                _check(mount.read_only, "OWNERSHIP_MOUNT_DENIED")
        elif mount.kind == "bind":
            _check(spec.phase != "volume-initialize" and mount.no_copy is False, "OWNERSHIP_MOUNT_DENIED")
            _path(mount.source)
            _check((mount.source, mount.destination) in _allowed_bind_mounts(spec.role)
                   and mount.read_only, "OWNERSHIP_MOUNT_DENIED")
        else:
            raise RestoreError("OWNERSHIP_MOUNT_DENIED")
    return spec


def _mounts(metadata, spec, baseline_volumes):
    raw = metadata.get("Mounts")
    _check(type(raw) is list and len(raw) == len(spec.mounts))
    expected = {mount.destination: mount for mount in spec.mounts}
    seen = set()
    result = []
    for mount in raw:
        _check(type(mount) is dict)
        destination = mount.get("Destination")
        _check(destination in expected and destination not in seen,
               "OWNERSHIP_MOUNT_DENIED")
        seen.add(destination)
        allow = expected[destination]
        _check(mount.get("Type") == allow.kind
               and type(mount.get("RW")) is bool
               and mount["RW"] is (not allow.read_only),
               "OWNERSHIP_MOUNT_DENIED")
        _check(mount.get("Propagation", "") in ("", "rprivate"),
               "OWNERSHIP_MOUNT_DENIED")
        _check(mount.get("Mode", "") in (("", "ro") if allow.read_only else ("", "rw")),
               "OWNERSHIP_MOUNT_DENIED")
        if allow.kind == "volume":
            _check(mount.get("Name") == allow.source
                   and allow.source not in baseline_volumes
                   and mount.get("Driver") == "local",
                   "OWNERSHIP_MOUNT_DENIED")
            _check(mount.get("Source") == "/var/lib/docker/volumes/" + allow.source + "/_data",
                   "OWNERSHIP_MOUNT_DENIED")
        else:
            _check(mount.get("Source") == allow.source
                   and mount.get("Name", "") == "",
                   "OWNERSHIP_MOUNT_DENIED")
        result.append(mount)
    return sorted(result, key=lambda row: row["Destination"])


def _host_mounts(host, spec):
    declarations = host.get("Mounts")
    if declarations is None:
        _check(not spec.mounts, "OWNERSHIP_MOUNT_DENIED")
        return
    _check(type(declarations) is list and len(declarations) == len(spec.mounts))
    expected = {mount.destination: mount for mount in spec.mounts}
    seen = set()
    for declaration in declarations:
        _check(type(declaration) is dict)
        destination = declaration.get("Target")
        _check(destination in expected and destination not in seen,
               "OWNERSHIP_MOUNT_DENIED")
        seen.add(destination)
        allow = expected[destination]
        _check(set(declaration).issubset({"Type", "Source", "Target", "ReadOnly",
                                         "Consistency", "BindOptions", "VolumeOptions"})
               and declaration.get("Type") == allow.kind
               and declaration.get("Source") == allow.source
               and declaration.get("ReadOnly") is allow.read_only
               and declaration.get("Consistency", "") == "",
               "OWNERSHIP_MOUNT_DENIED")
        bind_options = declaration.get("BindOptions")
        volume_options = declaration.get("VolumeOptions")
        if allow.kind == "bind":
            _check(volume_options is None
                   and (bind_options is None or bind_options == {"Propagation": "rprivate"}),
                   "OWNERSHIP_MOUNT_DENIED")
        else:
            _check(bind_options is None
                   and ((volume_options is None and allow.no_copy is False) or
                        (type(volume_options) is dict and set(volume_options) == {"NoCopy"}
                         and type(volume_options["NoCopy"]) is bool
                         and volume_options["NoCopy"] is allow.no_copy)),
                   "OWNERSHIP_MOUNT_DENIED")


def _container_evidence(metadata, spec, baseline_ids, baseline_names,
                        baseline_volumes, db_id):
    _check(type(metadata) is dict)
    spec = _spec(spec)
    container_id = _identifier(metadata.get("Id"))
    _check(container_id not in baseline_ids, "OWNERSHIP_PREEXISTING_RESOURCE")
    name = OWNER + "-" + spec.role
    _check(metadata.get("Name") == "/" + name
           and name not in baseline_names and "/" + name not in baseline_names,
           "OWNERSHIP_NAME_MISMATCH")
    config = metadata.get("Config")
    host = metadata.get("HostConfig")
    network = metadata.get("NetworkSettings")
    _check(type(config) is dict and type(host) is dict and type(network) is dict)
    _check(all(key in config for key in ("Entrypoint", "Cmd", "User", "Env", "Volumes")))
    _check(config["Entrypoint"] is None or type(config["Entrypoint"]) is list)
    _check(type(config["Cmd"]) is list)
    labels = config.get("Labels")
    _check(type(labels) is dict and labels.get(OWNER_LABEL) == OWNER,
           "OWNERSHIP_LABEL_MISMATCH")
    if spec.phase == "volume-initialize":
        _check(labels.get("hbos.restore.phase") == "volume-initialize", "OWNERSHIP_LABEL_MISMATCH")
    _check(config.get("Image") == spec.image
           and metadata.get("Image") == _IMAGE_IDS[spec.role],
           "OWNERSHIP_IMAGE_MISMATCH")
    health = config.get("Healthcheck")
    _check(health is None or (type(health) is dict and health.get("Test") == ["NONE"]),
           "OWNERSHIP_AUTOMATION_DENIED")
    log = host.get("LogConfig")
    _check(type(log) is dict and set(log) == {"Type", "Config"}
           and log["Type"] == "none" and log["Config"] in (None, {}),
           "OWNERSHIP_HOST_CHANNEL_DENIED")
    restart = host.get("RestartPolicy")
    _check(type(restart) is dict and set(restart) == {"Name", "MaximumRetryCount"}
           and restart["Name"] == "no" and type(restart["MaximumRetryCount"]) is int
           and restart["MaximumRetryCount"] == 0,
           "OWNERSHIP_AUTOMATION_DENIED")
    _check(_sequence(config.get("Entrypoint") or []) == spec.entrypoint
           and _sequence(config.get("Cmd") or []) == spec.command
           and config.get("User") == spec.user,
           "OWNERSHIP_COMMAND_MISMATCH")
    environment = _sequence(config.get("Env"))
    for entry in environment:
        key, separator, value = entry.partition("=")
        _check(separator and key, "OWNERSHIP_METADATA_INVALID")
        _check(not (key.lower().endswith("_proxy") and value)
               and key not in ("DOCKER_HOST", "DOCKER_CONTEXT"),
               "OWNERSHIP_HOST_CHANNEL_DENIED")
    _check(host.get("Privileged") is False
           and host.get("PublishAllPorts") is False
           and host.get("ReadonlyRootfs") is spec.read_only_rootfs,
           "OWNERSHIP_HOST_CHANNEL_DENIED")
    _check("CapAdd" in host and host["CapAdd"] in (None, []),
           "OWNERSHIP_HOST_CHANNEL_DENIED")
    _check(host.get("CapDrop") == ["ALL"]
           and host.get("SecurityOpt") in (["no-new-privileges"], ["no-new-privileges:true"]),
           "OWNERSHIP_HOST_CHANNEL_DENIED")
    _check("PortBindings" in host and host["PortBindings"] in (None, {}),
           "OWNERSHIP_PORT_DENIED")
    for key in ("Devices", "DeviceRequests", "VolumesFrom", "Links",
                "ExtraHosts", "Tmpfs", "Binds", "Dns", "DnsOptions", "DnsSearch",
                "DeviceCgroupRules", "Sysctls", "StorageOpt"):
        _check(key in host and host[key] in (None, [], {}),
               "OWNERSHIP_HOST_CHANNEL_DENIED")
    for key in ("PidMode", "IpcMode", "UTSMode", "UsernsMode", "CgroupnsMode"):
        _check(key in host and host[key] in ("", "private"),
               "OWNERSHIP_HOST_CHANNEL_DENIED")
    _check(host.get("AutoRemove") is False, "OWNERSHIP_METADATA_INVALID")
    _check(host.get("Runtime") == "runc", "OWNERSHIP_HOST_CHANNEL_DENIED")
    _host_mounts(host, spec)
    if spec.role == "db":
        _check(db_id in (None, container_id), "OWNERSHIP_NETWORK_DENIED")
        expected_network = "none"
    else:
        db_id = _identifier(db_id)
        _check(db_id not in baseline_ids and db_id != container_id,
               "OWNERSHIP_NETWORK_DENIED")
        expected_network = "container:" + db_id
    _check(host.get("NetworkMode") == expected_network, "OWNERSHIP_NETWORK_DENIED")
    networks = network.get("Networks")
    _check(type(networks) is dict
           and (not networks or (spec.role == "db" and set(networks) == {"none"})),
           "OWNERSHIP_NETWORK_DENIED")
    for key in ("IPAddress", "Gateway", "GlobalIPv6Address", "IPv6Gateway"):
        _check(network.get(key, "") == "", "OWNERSHIP_NETWORK_DENIED")
    for attached in networks.values():
        _check(type(attached) is dict)
        for key in ("IPAddress", "Gateway", "GlobalIPv6Address", "IPv6Gateway"):
            _check(attached.get(key, "") == "", "OWNERSHIP_NETWORK_DENIED")
    ports = network.get("Ports")
    _check(ports is None or (type(ports) is dict and all(v is None for v in ports.values())),
           "OWNERSHIP_PORT_DENIED")
    mounts = _mounts(metadata, spec, baseline_volumes)
    declared_volumes = config.get("Volumes")
    _check(declared_volumes is None or (type(declared_volumes) is dict
           and set(declared_volumes).issubset({row["Destination"] for row in mounts})),
           "OWNERSHIP_MOUNT_DENIED")
    # State/log timestamps may change during authorized startup. Config/host,
    # mounts and topology are retained in full, but never emitted publicly.
    return container_id, name, _digest({"config": config, "host": host,
                                      "mounts": mounts, "network": network,
                                      "image": metadata["Image"], "name": name})


@dataclass(frozen=True, init=False)
class ResourceRecord:
    container_id: str
    name: str
    spec: ContainerSpec
    db_id: str | None
    metadata_sha256: str
    _issued: object = field(repr=False, compare=False)

    @classmethod
    @_fixed_errors
    def from_inspect(cls, metadata, *, expected, original_ids=(),
                     original_names=(), original_volume_names=(), db_id=None):
        baseline_ids, baseline_names, baseline_volumes = _baseline(
            original_ids, original_names, original_volume_names)
        identity, name, digest = _container_evidence(metadata, expected,
            baseline_ids, baseline_names, baseline_volumes, db_id)
        record = object.__new__(cls)
        for key, value in (("container_id", identity), ("name", name),
                           ("spec", expected), ("db_id", db_id),
                           ("metadata_sha256", digest), ("_issued", _ISSUED)):
            object.__setattr__(record, key, value)
        return record


def _volume_evidence(metadata, baseline_volumes):
    _check(type(metadata) is dict)
    name = metadata.get("Name")
    _check(name in VOLUME_NAMES and name not in baseline_volumes,
           "OWNERSHIP_PREEXISTING_RESOURCE")
    labels = metadata.get("Labels")
    _check(type(labels) is dict and labels.get(OWNER_LABEL) == OWNER,
           "OWNERSHIP_LABEL_MISMATCH")
    _check(metadata.get("Driver") == "local" and metadata.get("Scope") == "local"
           and metadata.get("Options") in (None, {}), "OWNERSHIP_MOUNT_DENIED")
    _check(metadata.get("Mountpoint") == "/var/lib/docker/volumes/" + name + "/_data",
           "OWNERSHIP_MOUNT_DENIED")
    return name, _digest(metadata)


@dataclass(frozen=True, init=False)
class VolumeRecord:
    name: str
    metadata_sha256: str
    _issued: object = field(repr=False, compare=False)

    @classmethod
    @_fixed_errors
    def from_inspect(cls, metadata, *, original_volume_names=()):
        baseline = _names(original_volume_names)
        _check(bool(baseline) and all(name for name in baseline),
               "OWNERSHIP_BASELINE_REQUIRED")
        name, digest = _volume_evidence(metadata, baseline)
        record = object.__new__(cls)
        for key, value in (("name", name), ("metadata_sha256", digest),
                           ("_issued", _ISSUED)):
            object.__setattr__(record, key, value)
        return record


def _indexed(current, key):
    _check(type(current) in (dict, tuple, list))
    entries = current.values() if type(current) is dict else current
    result = {}
    for item in entries:
        _check(type(item) is dict and key in item)
        identity = item[key]
        _check(type(identity) is str and identity not in result)
        result[identity] = item
    if type(current) is dict:
        _check(set(current) == set(result))
    return result


@_fixed_errors
def cleanup_plan(records, current_metadata, *, original_ids=(),
                 original_names=(), original_volume_names=(), volume_records=(),
                 current_volume_metadata=(), relay_stopped=False):
    """Validate every fresh input before returning any stop/rm argv.

    Only actually registered subsets are accepted. Containers sharing the DB
    namespace require its owned anchor record; the anchor is always last.
    Relay shutdown is a prerequisite, not an action silently included here.
    """
    _check(relay_stopped is True, "OWNERSHIP_RELAY_NOT_STOPPED")
    _check(type(records) in (tuple, list) and type(volume_records) in (tuple, list))
    baseline_ids, baseline_names, baseline_volumes = _baseline(
        original_ids, original_names, original_volume_names)
    current = _indexed(current_metadata, "Id")
    current_volumes = _indexed(current_volume_metadata, "Name")
    checked = {}
    for record in records:
        _check(type(record) is ResourceRecord and record._issued is _ISSUED)
        _check(record.spec.role not in checked and record.container_id in current)
        identity, name, digest = _container_evidence(current[record.container_id],
            record.spec, baseline_ids, baseline_names, baseline_volumes, record.db_id)
        _check((identity, name, digest) == (record.container_id, record.name,
                                          record.metadata_sha256),
               "OWNERSHIP_CHANGED")
        checked[record.spec.role] = record
    _check(set(current) == {record.container_id for record in records})
    if any(role != "db" for role in checked):
        _check("db" in checked, "OWNERSHIP_NETWORK_DENIED")
        _check(all(record.db_id == checked["db"].container_id
                   for role, record in checked.items() if role != "db"),
               "OWNERSHIP_NETWORK_DENIED")
    volumes = set()
    for record in volume_records:
        _check(type(record) is VolumeRecord and record._issued is _ISSUED)
        _check(record.name not in volumes and record.name in current_volumes)
        name, digest = _volume_evidence(current_volumes[record.name], baseline_volumes)
        _check((name, digest) == (record.name, record.metadata_sha256),
               "OWNERSHIP_CHANGED")
        volumes.add(name)
    _check(set(current_volumes) == volumes)
    plan = []
    for role in ("frontend", "backend", "redis-queue", "redis-cache", "db"):
        if role in checked:
            identity = checked[role].container_id
            plan.extend(((DOCKER, "stop", identity), (DOCKER, "rm", identity)))
    plan.extend((DOCKER, "volume", "rm", name) for name in VOLUME_NAMES if name in volumes)
    return tuple(plan)


def _process_evidence(snapshot, executable, script_sha256, original_pids,
                      kind, parent_pid):
    _check(type(snapshot) is dict and kind in ("relay", "child"))
    pid = snapshot.get("pid")
    _check(type(pid) is int and pid > 1 and pid not in original_pids,
           "OWNERSHIP_PROCESS_DENIED")
    start = snapshot.get("start_time")
    _check((type(start) is int and start > 0)
           or (type(start) is str and 0 < len(_text(start)) <= 128),
           "OWNERSHIP_PROCESS_DENIED")
    _path(executable)
    _identifier(script_sha256)
    _check(snapshot.get("executable") == executable
           and snapshot.get("script_sha256") == script_sha256,
           "OWNERSHIP_PROCESS_DENIED")
    if kind == "relay":
        _check(parent_pid is None and snapshot.get("parent_pid") is None,
               "OWNERSHIP_PROCESS_DENIED")
    else:
        _check(type(parent_pid) is int and parent_pid > 1 and parent_pid != pid
               and parent_pid not in original_pids
               and snapshot.get("parent_pid") == parent_pid,
               "OWNERSHIP_PROCESS_DENIED")
    return pid, start, _digest(snapshot)


@dataclass(frozen=True, init=False)
class ProcessRecord:
    pid: int
    start_time: int | str
    executable: str
    script_sha256: str
    kind: str
    parent_pid: int | None
    metadata_sha256: str
    _issued: object = field(repr=False, compare=False)

    @classmethod
    @_fixed_errors
    def from_snapshot(cls, snapshot, *, expected_executable,
                      expected_script_sha256, original_pids=(), kind="relay",
                      parent_pid=None):
        baseline = _process_baseline(original_pids)
        pid, start, digest = _process_evidence(snapshot, expected_executable,
            expected_script_sha256, baseline, kind, parent_pid)
        record = object.__new__(cls)
        values = {"pid": pid, "start_time": start,
                  "executable": expected_executable,
                  "script_sha256": expected_script_sha256, "kind": kind,
                  "parent_pid": parent_pid, "metadata_sha256": digest,
                  "_issued": _ISSUED}
        for key, value in values.items():
            object.__setattr__(record, key, value)
        return record


@_fixed_errors
def process_cleanup_plan(records, current_snapshots, *, original_pids=()):
    """Children first, relay last; does not kill processes or container exec tasks."""
    _check(type(records) in (tuple, list) and type(current_snapshots) in (tuple, list))
    baseline = _process_baseline(original_pids)
    current = {}
    for snapshot in current_snapshots:
        _check(type(snapshot) is dict and type(snapshot.get("pid")) is int
               and snapshot["pid"] not in current)
        current[snapshot["pid"]] = snapshot
    registered = {}
    for record in records:
        _check(type(record) is ProcessRecord and record._issued is _ISSUED
               and record.pid not in registered and record.pid in current)
        pid, start, digest = _process_evidence(current[record.pid],
            record.executable, record.script_sha256, baseline,
            record.kind, record.parent_pid)
        _check((pid, start, digest) == (record.pid, record.start_time,
                                      record.metadata_sha256), "OWNERSHIP_CHANGED")
        registered[pid] = record
    _check(set(current) == set(registered))
    relays = [record for record in records if record.kind == "relay"]
    _check(len(relays) == (1 if records else 0), "OWNERSHIP_PROCESS_DENIED")
    remaining = set(registered)
    ordered = []
    while remaining:
        leaves = sorted(pid for pid in remaining
                        if not any(registered[other].parent_pid == pid for other in remaining))
        _check(bool(leaves), "OWNERSHIP_PROCESS_DENIED")
        for pid in leaves:
            record = registered[pid]
            _check(record.kind == "relay" or record.parent_pid in registered,
                   "OWNERSHIP_PROCESS_DENIED")
            if record.kind == "relay":
                _check(len(remaining) == 1, "OWNERSHIP_PROCESS_DENIED")
            ordered.append(("/bin/kill", "-TERM", str(pid)))
            remaining.remove(pid)
    return tuple(ordered)
