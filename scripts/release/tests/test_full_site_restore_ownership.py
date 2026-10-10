"""Offline hostile metadata tests; no Docker, SQL, network or real secrets."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import os
import shutil
import socket
import subprocess
import unittest
from unittest.mock import patch

from scripts.release.full_site_restore.common import (
    BENCH, DB_IMAGE, DOCKER, FRAPPE_IMAGE, OWNER, OWNER_LABEL, REDIS_IMAGE,
    ROOT, ROLES, VOLUME_NAMES, RestoreError,
)
from scripts.release.full_site_restore.ownership import (
    ContainerSpec, MountSpec, ProcessRecord, ResourceRecord, VolumeRecord,
    cleanup_plan as raw_cleanup_plan, process_cleanup_plan as raw_process_cleanup_plan,
)

IMAGES = {"db": DB_IMAGE, "redis-cache": REDIS_IMAGE,
          "redis-queue": REDIS_IMAGE, "backend": FRAPPE_IMAGE,
          "frontend": FRAPPE_IMAGE}
ORIGINAL_ID = "f" * 64
DB_ID = "1".zfill(64)
BASELINE = {"original_ids": (ORIGINAL_ID,), "original_names": ("original-db",),
            "original_volume_names": ("original-sites-volume",)}
ORIGINAL_PIDS = (7001,)


def cleanup_plan(*args, **kwargs):
    for key, value in BASELINE.items():
        kwargs.setdefault(key, value)
    return raw_cleanup_plan(*args, **kwargs)


def process_cleanup_plan(*args, **kwargs):
    kwargs.setdefault("original_pids", ORIGINAL_PIDS)
    return raw_process_cleanup_plan(*args, **kwargs)


def register_volume(metadata, **kwargs):
    kwargs.setdefault("original_volume_names", BASELINE["original_volume_names"])
    return VolumeRecord.from_inspect(metadata, **kwargs)


def inspect_fixture(role="db", *, mounts=(), number=None):
    """Synthetic complete standard inspect fields, not a runtime claim."""
    identity = f"{number or (ROLES.index(role) + 1):064x}"
    spec = ContainerSpec(role, IMAGES[role], tuple(mounts))
    actual_mounts = []
    declarations = []
    for mount in mounts:
        actual = {"Type": mount.kind, "Destination": mount.destination,
                  "RW": not mount.read_only, "Mode": "", "Propagation": "rprivate"}
        if mount.kind == "volume":
            actual.update({"Name": mount.source, "Driver": "local",
                           "Source": "/var/lib/docker/volumes/" + mount.source + "/_data"})
        else:
            actual["Source"] = mount.source
        actual_mounts.append(actual)
        declarations.append({"Type": mount.kind, "Source": mount.source,
                             "Target": mount.destination, "ReadOnly": mount.read_only})
        if mount.kind == "volume" and mount.no_copy:
            declarations[-1]["VolumeOptions"] = {"NoCopy": True}
    host = {"NetworkMode": "none" if role == "db" else "container:" + DB_ID,
            "Privileged": False, "PublishAllPorts": False, "ReadonlyRootfs": True,
            "CapAdd": None, "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"],
            "PortBindings": {}, "AutoRemove": False, "Runtime": "runc",
            "PidMode": "", "IpcMode": "private", "UTSMode": "", "UsernsMode": "",
            "CgroupnsMode": "private", "Mounts": declarations}
    host.update({"LogConfig": {"Type": "none", "Config": {}},
                 "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0}})
    for key in ("Devices", "DeviceRequests", "VolumesFrom", "Links", "ExtraHosts",
                "Tmpfs", "Binds", "Dns", "DnsOptions", "DnsSearch",
                "DeviceCgroupRules", "Sysctls", "StorageOpt"):
        host[key] = None
    metadata = {"Id": identity, "Name": "/" + OWNER + "-" + role,
                "Image": "sha256:" + IMAGES[role].split("@sha256:")[1],
                "Config": {"Image": IMAGES[role], "Labels": {OWNER_LABEL: OWNER},
                           "Entrypoint": [], "Cmd": ["/bin/sleep", "2700"],
                           "User": "1000:1000", "Env": ["PATH=/usr/bin:/bin"],
                           "Volumes": None},
                "HostConfig": host, "Mounts": actual_mounts,
                "NetworkSettings": {"Networks": {"none": {}} if role == "db" else {},
                                    "IPAddress": "", "Gateway": "", "GlobalIPv6Address": "",
                                    "IPv6Gateway": "", "Ports": {}},
                "State": {"Running": True}}
    return spec, metadata


def register(spec, metadata, **kwargs):
    for key, value in BASELINE.items():
        kwargs.setdefault(key, value)
    return ResourceRecord.from_inspect(metadata, expected=spec,
        db_id=None if spec.role == "db" else DB_ID, **kwargs)


class VolumeInitializeOwnershipTests(unittest.TestCase):
    def fixture(self, *, mounts=None):
        if mounts is None:
            mounts = (MountSpec("volume", OWNER + "-assets-data", BENCH + "/sites/assets", False, True),)
        spec, metadata = inspect_fixture("backend", mounts=mounts)
        spec = replace(spec, phase="volume-initialize")
        metadata["Config"]["Labels"]["hbos.restore.phase"] = "volume-initialize"
        return spec, metadata

    def test_fixed_initialization_nonroot_sleep_nocopy_rw_admitted(self):
        spec, metadata = self.fixture()
        record = register(spec, metadata)
        self.assertEqual(record.spec.phase, "volume-initialize")
        self.assertEqual(record.spec.user, "1000:1000")

    def test_nocopy_declaration_absent_false_or_wrong_type_rejected(self):
        for options in (None, {"NoCopy": False}, {"NoCopy": 1}, {"NoCopy": True, "Labels": {}}):
            spec, metadata = self.fixture()
            metadata["HostConfig"]["Mounts"][0]["VolumeOptions"] = options
            with self.assertRaises(RestoreError):
                register(spec, metadata)

    def test_phase_cannot_add_bind_root_capability_service_or_missing_label(self):
        spec, metadata = self.fixture()
        for changed in (replace(spec, user="0:0"), replace(spec, command=("/usr/sbin/nginx",)),
                        replace(spec, phase="service"), replace(spec, read_only_rootfs=False)):
            with self.assertRaises(RestoreError):
                register(changed, metadata)
        metadata["Config"]["Labels"].pop("hbos.restore.phase")
        with self.assertRaises(RestoreError):
            register(spec, metadata)
        spec, metadata = self.fixture(mounts=(MountSpec("bind", str(ROOT / "runtime/forward.py"),
                                                     "/run/hbos-restore/forward.py", True),))
        with self.assertRaises(RestoreError):
            register(spec, metadata)

    def test_alias_and_readonly_volume_initialization_rejected(self):
        for mounts in ((MountSpec("volume", OWNER + "-assets-data", BENCH + "/sites/assets", True, True),),
                       (MountSpec("volume", OWNER + "-assets-data", BENCH + "/assets", False, True),),
                       (MountSpec("volume", OWNER + "-logs", BENCH + "/logs", False, False),)):
            spec, metadata = self.fixture(mounts=mounts)
            with self.assertRaises(RestoreError):
                register(spec, metadata)

    def test_legacy_namespace_phase_keeps_content_volumes_readonly(self):
        spec, metadata = self.fixture()
        with self.assertRaises(RestoreError):
            register(replace(spec, phase="namespace-precheck"), metadata)


def volume_fixture(name=VOLUME_NAMES[0]):
    return {"Name": name, "Driver": "local", "Scope": "local", "Options": None,
            "Labels": {OWNER_LABEL: OWNER},
            "Mountpoint": "/var/lib/docker/volumes/" + name + "/_data",
            "CreatedAt": "2026-10-10T00:00:00Z"}


def process_fixture(pid=4001, *, parent=None):
    return {"pid": pid, "start_time": 123456, "executable": "/usr/bin/python3",
            "script_sha256": "a" * 64, "parent_pid": parent}


def register_process(snapshot, *, kind="relay", parent=None):
    return ProcessRecord.from_snapshot(snapshot, expected_executable="/usr/bin/python3",
        expected_script_sha256="a" * 64, original_pids=ORIGINAL_PIDS,
        kind=kind, parent_pid=parent)


class OwnershipTests(unittest.TestCase):
    def assert_denied(self, function, code=None):
        with self.assertRaises(RestoreError) as caught:
            function()
        if code:
            self.assertEqual(caught.exception.code, code)
        self.assertRegex(str(caught.exception), r"^[A-Z][A-Z0-9_]+$")
        self.assertNotIn("SYNTHETIC_PRIVATE_VALUE", str(caught.exception))

    def test_partial_created_db_only_yields_exact_id_plan(self):
        spec, metadata = inspect_fixture()
        record = register(spec, metadata)
        self.assertEqual(cleanup_plan([record], [metadata], relay_stopped=True),
                         ((DOCKER, "stop", DB_ID), (DOCKER, "rm", DB_ID)))
        with self.assertRaises(FrozenInstanceError):
            record.name = "unowned"
        with self.assertRaises(FrozenInstanceError):
            spec.user = "0:0"

    def test_partial_volume_only_failure_can_be_planned(self):
        metadata = volume_fixture()
        record = register_volume(metadata)
        self.assertEqual(cleanup_plan([], [], volume_records=[record],
            current_volume_metadata=[metadata], relay_stopped=True),
            ((DOCKER, "volume", "rm", metadata["Name"]),))

    def test_all_registered_roles_are_stopped_and_removed_before_db_anchor(self):
        records, current = [], []
        for role in reversed(ROLES):
            spec, metadata = inspect_fixture(role)
            records.append(register(spec, metadata))
            current.append(metadata)
        plan = cleanup_plan(records, current, relay_stopped=True)
        self.assertEqual([argv[-1] for argv in plan[::2]],
                         [f"{n:064x}" for n in (5, 4, 3, 2, 1)])
        self.assertTrue(all(argv[1] in ("stop", "rm") for argv in plan))
        self.assertFalse(any(OWNER in argv[-1] for argv in plan))

    def test_relay_not_stopped_rejects_whole_container_cleanup(self):
        spec, metadata = inspect_fixture()
        self.assert_denied(lambda: cleanup_plan([register(spec, metadata)], [metadata]),
                           "OWNERSHIP_RELAY_NOT_STOPPED")

    def test_original_ids_and_exact_names_cannot_be_reclaimed_by_owner_label(self):
        spec, metadata = inspect_fixture()
        self.assert_denied(lambda: register(spec, metadata, original_ids=[DB_ID]),
                           "OWNERSHIP_PREEXISTING_RESOURCE")
        self.assert_denied(lambda: register(spec, metadata,
            original_names=[OWNER + "-db"]), "OWNERSHIP_NAME_MISMATCH")
        for identity in (DB_ID[:12], "G" * 64, ORIGINAL_ID + "\n", None):
            changed = deepcopy(metadata)
            changed["Id"] = identity
            with self.subTest(identity=identity):
                self.assert_denied(lambda: register(spec, changed))

    def test_name_prefix_label_and_image_spoofing_are_denied(self):
        spec, metadata = inspect_fixture()
        changes = [("Name", "/" + OWNER + "-db-extra"),
                   ("Name", "/preexisting"), ("Image", "sha256:" + "e" * 64)]
        for field, value in changes:
            changed = deepcopy(metadata)
            changed[field] = value
            with self.subTest(field=field, value=value):
                self.assert_denied(lambda: register(spec, changed))
        for value in ({}, {OWNER_LABEL: "another-run"}, None):
            changed = deepcopy(metadata)
            changed["Config"]["Labels"] = value
            self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_LABEL_MISMATCH")
        changed = deepcopy(metadata)
        changed["Config"]["Image"] = DB_IMAGE.replace("@sha256:", ":latest@sha256:")
        self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_IMAGE_MISMATCH")

    def test_custom_spec_cannot_admit_service_root_uid_or_unsafe_image(self):
        spec, metadata = inspect_fixture()
        for custom in (replace(spec, command=("mariadbd",)), replace(spec, user="0:0"),
                       replace(spec, entrypoint=("sh",)), replace(spec, read_only_rootfs=False),
                       replace(spec, image="mariadb:latest")):
            with self.subTest(custom=custom):
                self.assert_denied(lambda: register(custom, metadata))

    def test_security_host_side_channels_are_denied(self):
        spec, metadata = inspect_fixture()
        hostile = {"Privileged": True, "PublishAllPorts": True, "ReadonlyRootfs": False,
                   "CapAdd": ["NET_ADMIN"], "CapDrop": [],
                   "SecurityOpt": ["apparmor=unconfined"], "PidMode": "host",
                   "IpcMode": "host", "UsernsMode": "host", "CgroupnsMode": "host",
                   "ExtraHosts": ["host.docker.internal:host-gateway"],
                   "VolumesFrom": ["original"], "Devices": [{"PathOnHost": "/dev/sda"}],
                   "DeviceRequests": [{"Driver": "nvidia"}], "Tmpfs": {"/run": "rw"},
                   "Dns": ["192.0.2.1"], "Runtime": "untrusted", "AutoRemove": True,
                   "Binds": ["/var/run/docker.sock:/var/run/docker.sock:ro"]}
        for field, value in hostile.items():
            changed = deepcopy(metadata)
            changed["HostConfig"][field] = value
            with self.subTest(field=field):
                self.assert_denied(lambda: register(spec, changed))

    def test_healthcheck_cannot_execute_commands_outside_fixed_precheck(self):
        spec, metadata = inspect_fixture()
        for health in ({"Test": ["CMD", "/bin/sh", "-c", "SYNTHETIC_PRIVATE_VALUE"]},
                       {"Test": ["CMD-SHELL", "SYNTHETIC_PRIVATE_VALUE"]},
                       {"Test": []}, {"Test": ["NONE", "extra"]}, "NONE"):
            changed = deepcopy(metadata)
            changed["Config"]["Healthcheck"] = health
            self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_AUTOMATION_DENIED")
        metadata["Config"]["Healthcheck"] = {"Test": ["NONE"]}
        self.assertEqual(register(spec, metadata).container_id, DB_ID)

    def test_daemon_log_channels_are_denied(self):
        spec, metadata = inspect_fixture()
        for log in (None, {"Type": "syslog", "Config": {"syslog-address": "tcp://192.0.2.1:514"}},
                    {"Type": "fluentd", "Config": {}}, {"Type": "json-file", "Config": {}},
                    {"Type": "none", "Config": {"unexpected": "SYNTHETIC_PRIVATE_VALUE"}}):
            changed = deepcopy(metadata)
            changed["HostConfig"]["LogConfig"] = log
            self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_HOST_CHANNEL_DENIED")

    def test_auto_restart_cannot_extend_lifecycle(self):
        spec, metadata = inspect_fixture()
        for restart in (None, {"Name": "always", "MaximumRetryCount": 0},
                        {"Name": "unless-stopped", "MaximumRetryCount": 0},
                        {"Name": "on-failure", "MaximumRetryCount": 1},
                        {"Name": "no", "MaximumRetryCount": True}):
            changed = deepcopy(metadata)
            changed["HostConfig"]["RestartPolicy"] = restart
            self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_AUTOMATION_DENIED")

    def test_missing_security_fields_fail_closed_with_fixed_code(self):
        spec, metadata = inspect_fixture()
        for parent, field in (("HostConfig", "Privileged"), ("HostConfig", "CapAdd"),
                              ("HostConfig", "PortBindings"), ("HostConfig", "Devices"),
                              ("Config", "Volumes"), ("Config", "Entrypoint"),
                              ("NetworkSettings", "Networks")):
            changed = deepcopy(metadata)
            del changed[parent][field]
            with self.subTest(parent=parent, field=field):
                self.assert_denied(lambda: register(spec, changed))

    def test_original_network_fake_db_anchor_and_extra_attached_network_denied(self):
        spec, metadata = inspect_fixture("backend")
        for mode in ("host", "bridge", "container:original", "container:" + ORIGINAL_ID):
            changed = deepcopy(metadata)
            changed["HostConfig"]["NetworkMode"] = mode
            self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_NETWORK_DENIED")
        changed = deepcopy(metadata)
        changed["NetworkSettings"]["Networks"] = {"original": {}}
        self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_NETWORK_DENIED")
        self.assert_denied(lambda: ResourceRecord.from_inspect(metadata, expected=spec,
            db_id=ORIGINAL_ID, **BASELINE), "OWNERSHIP_NETWORK_DENIED")

    def test_published_ports_and_external_route_fields_denied(self):
        spec, metadata = inspect_fixture()
        for container, field, value in (("HostConfig", "PortBindings",
                                        {"3306/tcp": [{"HostIp": "0.0.0.0", "HostPort": "3306"}]}),
                                       ("NetworkSettings", "Ports",
                                        {"3306/tcp": [{"HostIp": "127.0.0.1", "HostPort": "3306"}]}),
                                       ("NetworkSettings", "Gateway", "192.0.2.1"),
                                       ("NetworkSettings", "GlobalIPv6Address", "2001:db8::1")):
            changed = deepcopy(metadata)
            changed[container][field] = value
            self.assert_denied(lambda: register(spec, changed))

    def test_unexpected_anonymous_volume_or_uncovered_image_volume_denied(self):
        spec, metadata = inspect_fixture()
        changed = deepcopy(metadata)
        changed["Config"]["Volumes"] = {"/var/lib/mysql": {}}
        self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_MOUNT_DENIED")
        changed = deepcopy(metadata)
        changed["Mounts"] = [{"Name": "a" * 64, "Type": "volume", "Destination": "/var/lib/mysql"}]
        self.assert_denied(lambda: register(spec, changed))

    def test_owned_volume_covers_image_declaration_original_volume_refused(self):
        mount = MountSpec("volume", VOLUME_NAMES[0], "/var/lib/mysql", False)
        spec, metadata = inspect_fixture(mounts=(mount,))
        metadata["Config"]["Volumes"] = {"/var/lib/mysql": {}}
        self.assertEqual(register(spec, metadata).container_id, DB_ID)
        self.assert_denied(lambda: register(spec, metadata,
            original_volume_names=[VOLUME_NAMES[0]]), "OWNERSHIP_MOUNT_DENIED")
        self.assert_denied(lambda: register(replace(spec, mounts=(replace(mount,
            source=OWNER + "-sites"),)), metadata), "OWNERSHIP_MOUNT_DENIED")

    def test_only_fixed_snapshot_sources_and_destinations_can_be_bound(self):
        mount = MountSpec("bind", str(ROOT) + "/snapshot/env", BENCH + "/env", True)
        spec, metadata = inspect_fixture("backend", mounts=(mount,))
        self.assertEqual(register(spec, metadata).spec.mounts, (mount,))
        for hostile in (replace(mount, source="/original/env"),
                        replace(mount, source=str(ROOT) + "/snapshot/../../original"),
                        replace(mount, source=str(ROOT) + "/runtime/docker.sock"),
                        replace(mount, destination="/var/run/docker.sock"),
                        replace(mount, read_only=False)):
            self.assert_denied(lambda: register(replace(spec, mounts=(hostile,)), metadata),
                               "OWNERSHIP_MOUNT_DENIED" if ".." not in hostile.source else None)

    def test_host_mount_declaration_cannot_disagree_with_effective_mount(self):
        mount = MountSpec("bind", str(ROOT) + "/runtime/db.cnf", "/run/hbos-restore/db.cnf", True)
        spec, metadata = inspect_fixture(mounts=(mount,))
        register(spec, metadata)
        changed = deepcopy(metadata)
        changed["HostConfig"]["Mounts"][0]["Source"] = "/original/site_config.json"
        self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_MOUNT_DENIED")
        changed = deepcopy(metadata)
        changed["Mounts"][0]["Propagation"] = "rshared"
        self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_MOUNT_DENIED")

    def test_fresh_cleanup_compares_full_security_evidence_before_any_plan(self):
        spec, metadata = inspect_fixture()
        record = register(spec, metadata)
        for parent, field, value in (("Config", "Env", ["PASSWORD=SYNTHETIC_PRIVATE_VALUE"]),
                                    ("Config", "Labels", {OWNER_LABEL: "tampered"}),
                                    ("HostConfig", "SecurityOpt", ["no-new-privileges:true"])):
            changed = deepcopy(metadata)
            changed[parent][field] = value
            with self.subTest(parent=parent, field=field):
                self.assert_denied(lambda: cleanup_plan([record], [changed], relay_stopped=True))
        changed = deepcopy(metadata)
        changed["State"] = {"Running": False}
        self.assertEqual(len(cleanup_plan([record], [changed], relay_stopped=True)), 2)

    def test_missing_unknown_duplicate_ids_and_unregistered_anchor_denied(self):
        spec, metadata = inspect_fixture()
        record = register(spec, metadata)
        other_spec, other = inspect_fixture("backend")
        for current in ([], [metadata, metadata], [metadata, other]):
            self.assert_denied(lambda: cleanup_plan([record], current, relay_stopped=True))
        other_record = register(other_spec, other)
        self.assert_denied(lambda: cleanup_plan([other_record], [other], relay_stopped=True),
                           "OWNERSHIP_NETWORK_DENIED")
        self.assert_denied(lambda: cleanup_plan([record, record], [metadata], relay_stopped=True))

    def test_named_volume_label_driver_options_baseline_and_fresh_identity(self):
        metadata = volume_fixture()
        for field, value in (("Name", OWNER + "-extra"), ("Driver", "external-driver"),
                             ("Options", {"device": "/original", "type": "none", "o": "bind"}),
                             ("Labels", {OWNER_LABEL: "other"})):
            changed = deepcopy(metadata)
            changed[field] = value
            self.assert_denied(lambda: register_volume(changed))
        self.assert_denied(lambda: register_volume(metadata,
            original_volume_names=[metadata["Name"]]), "OWNERSHIP_PREEXISTING_RESOURCE")
        record = register_volume(metadata)
        changed = deepcopy(metadata)
        changed["Mountpoint"] = "/another/canonical/path"
        self.assert_denied(lambda: cleanup_plan([], [], volume_records=[record],
            current_volume_metadata=[changed], relay_stopped=True), "OWNERSHIP_MOUNT_DENIED")

    def test_cleanup_uses_current_baseline_exclusions_not_only_registration(self):
        spec, metadata = inspect_fixture()
        record = register(spec, metadata)
        self.assert_denied(lambda: cleanup_plan([record], [metadata], original_ids=[DB_ID],
            relay_stopped=True), "OWNERSHIP_PREEXISTING_RESOURCE")

    def test_omitted_or_empty_baselines_are_not_accepted_as_original_exclusion(self):
        spec, metadata = inspect_fixture()
        self.assert_denied(lambda: ResourceRecord.from_inspect(metadata, expected=spec),
                           "OWNERSHIP_BASELINE_REQUIRED")
        for field in BASELINE:
            changed = dict(BASELINE)
            changed[field] = ()
            self.assert_denied(lambda: ResourceRecord.from_inspect(metadata,
                expected=spec, **changed), "OWNERSHIP_BASELINE_REQUIRED")
        self.assert_denied(lambda: VolumeRecord.from_inspect(volume_fixture()),
                           "OWNERSHIP_BASELINE_REQUIRED")
        self.assert_denied(lambda: raw_cleanup_plan([], [], relay_stopped=True),
                           "OWNERSHIP_BASELINE_REQUIRED")
        self.assert_denied(lambda: ProcessRecord.from_snapshot(process_fixture(),
            expected_executable="/usr/bin/python3", expected_script_sha256="a" * 64),
            "OWNERSHIP_BASELINE_REQUIRED")
        self.assert_denied(lambda: raw_process_cleanup_plan([], []),
                           "OWNERSHIP_BASELINE_REQUIRED")

    def test_private_malformed_metadata_never_escapes_in_error_text(self):
        spec, metadata = inspect_fixture()
        for malformed in ("SYNTHETIC_PRIVATE_VALUE", None, [], {"Id": "SYNTHETIC_PRIVATE_VALUE"}):
            self.assert_denied(lambda: register(spec, malformed))
        changed = deepcopy(metadata)
        changed["NetworkSettings"]["Networks"] = {"none": "SYNTHETIC_PRIVATE_VALUE"}
        self.assert_denied(lambda: register(spec, changed))
        changed = deepcopy(metadata)
        changed["Mounts"] = [{"Destination": {"SYNTHETIC_PRIVATE_VALUE": 1}}]
        self.assert_denied(lambda: register(spec, changed))

    def test_proxy_environment_and_actual_service_command_are_denied(self):
        spec, metadata = inspect_fixture()
        changed = deepcopy(metadata)
        changed["Config"]["Env"].append("HTTP_PROXY=http://original:8080")
        self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_HOST_CHANNEL_DENIED")
        changed = deepcopy(metadata)
        changed["Config"]["Cmd"] = ["mariadbd"]
        self.assert_denied(lambda: register(spec, changed), "OWNERSHIP_COMMAND_MISMATCH")

    def test_process_children_first_relay_last_and_frozen_identity(self):
        relay = process_fixture()
        child = process_fixture(4002, parent=4001)
        grandchild = process_fixture(4003, parent=4002)
        records = [register_process(relay), register_process(child, kind="child", parent=4001),
                   register_process(grandchild, kind="child", parent=4002)]
        self.assertEqual(process_cleanup_plan(records, [relay, child, grandchild]),
                         tuple(("/bin/kill", "-TERM", str(pid)) for pid in (4003, 4002, 4001)))
        with self.assertRaises(FrozenInstanceError):
            records[0].pid = 1

    def test_process_pid_reuse_exec_script_and_original_identity_rejected(self):
        snapshot = process_fixture()
        record = register_process(snapshot)
        for field, value in (("start_time", 98765), ("executable", "/bin/sh"),
                             ("script_sha256", "b" * 64), ("pid", True)):
            changed = deepcopy(snapshot)
            changed[field] = value
            self.assert_denied(lambda: process_cleanup_plan([record], [changed]))
        self.assert_denied(lambda: process_cleanup_plan([record], [snapshot],
            original_pids=[4001]), "OWNERSHIP_PROCESS_DENIED")

    def test_orphan_duplicate_and_unknown_processes_refused(self):
        relay = process_fixture()
        orphan = process_fixture(4002, parent=9999)
        records = [register_process(relay), register_process(orphan, kind="child", parent=9999)]
        self.assert_denied(lambda: process_cleanup_plan(records, [relay, orphan]),
                           "OWNERSHIP_PROCESS_DENIED")
        record = register_process(relay)
        for current in ([], [relay, relay], [relay, process_fixture(4003)]):
            self.assert_denied(lambda: process_cleanup_plan([record], current))

    def test_planners_have_no_process_filesystem_docker_or_network_effects(self):
        spec, metadata = inspect_fixture()
        process = process_fixture()
        forbidden = AssertionError("offline tool attempted an external effect")
        with patch.object(subprocess, "run", side_effect=forbidden), \
             patch.object(os, "kill", side_effect=forbidden), \
             patch.object(os, "remove", side_effect=forbidden), \
             patch.object(shutil, "rmtree", side_effect=forbidden), \
             patch.object(socket, "socket", side_effect=forbidden):
            self.assertEqual(len(cleanup_plan([register(spec, metadata)], [metadata],
                relay_stopped=True)), 2)
            self.assertEqual(process_cleanup_plan([register_process(process)], [process]),
                             (("/bin/kill", "-TERM", "4001"),))


if __name__ == "__main__":
    unittest.main()
