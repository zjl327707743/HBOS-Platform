"""Finite tar and synthetic receipt checks; no Docker, network or restore data."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import hashlib
import io
import json
import socket
import subprocess
import tarfile
import unittest
from unittest.mock import patch

from scripts.release.full_site_restore import volumes
from scripts.release.full_site_restore.common import BENCH, DOCKER, OWNER, VOLUME_NAMES, RestoreError
from scripts.release.full_site_restore.lifecycle import LifecycleRegistry, OriginalBaseline, OwnerAuthorization
from scripts.release.full_site_restore.ownership import MountSpec, ResourceRecord, VolumeRecord
from scripts.release.tests.test_full_site_restore_ownership import inspect_fixture, volume_fixture

BASELINE = OriginalBaseline(("f" * 64,), ("original-db",), ("original-sites",), (7001,), "e" * 64)
PRIVATE_SENTINEL = "SYNTHETIC_PRIVATE_VALUE_DO_NOT_PRINT"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def empty_archive(name="mysql", *, uid=0, gid=0, mode=0o755, kind=tarfile.DIRTYPE,
                  payload=b"", linkname="", pax=None, extra=None, global_pax=None):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT, pax_headers=global_pax) as archive:
        member = tarfile.TarInfo(name)
        member.type, member.mode, member.uid, member.gid = kind, mode, uid, gid
        member.mtime = 1_700_000_000
        member.size = len(payload)
        member.linkname = linkname
        member.pax_headers = pax or {}
        archive.addfile(member, io.BytesIO(payload) if payload else None)
        if extra:
            added = tarfile.TarInfo(extra)
            added.mode, added.uid, added.gid = 0o600, 0, 0
            archive.addfile(added)
    return output.getvalue()


class SyntheticContext:
    """Mint init records through the actual ownership and lifecycle validators."""
    def __init__(self):
        self.time = 100.0
        self.registry = LifecycleRegistry(baseline=BASELINE, clock=lambda: self.time,
            authorization=OwnerAuthorization.from_confirmation(explicit=True, reference_sha256="a" * 64))
        self.volume_records, self.volume_metadata, self.volume_intents = {}, {}, {}
        self.container_records, self.container_metadata, self.container_intents = {}, {}, {}
        for name in VOLUME_NAMES:
            intent = self.registry.create_intent("volume", name)
            metadata = volume_fixture(name)
            self.volume_records[name] = self.registry.confirm_volume(intent.intent_id,
                returned_name=name, metadata=metadata)
            self.volume_metadata[name], self.volume_intents[name] = metadata, intent.intent_id
        rows = volumes.fixed_volume_matrix()["rows"]
        for role in ("db", "redis-cache", "redis-queue", "backend"):
            mounts = tuple(MountSpec("volume", row["volume"], row["destination"], False, no_copy=True)
                           for row in rows if row["role"] == role)
            old_spec, metadata = inspect_fixture(role, mounts=mounts)
            spec = replace(old_spec, phase="volume-initialize")
            metadata["Config"]["Labels"]["hbos.restore.phase"] = "volume-initialize"
            for declaration in metadata["HostConfig"]["Mounts"]:
                declaration["VolumeOptions"] = {"NoCopy": True}
            metadata["State"] = {"Running": False, "Paused": False, "Restarting": False,
                                 "Dead": False, "Status": "created"}
            intent = self.registry.create_intent("container", role)
            record = self.registry.confirm_container(intent.intent_id,
                returned_id=metadata["Id"], metadata=metadata, spec=spec)
            self.container_records[role], self.container_metadata[role] = record, metadata
            self.container_intents[role] = intent.intent_id

    def arguments(self, name=VOLUME_NAMES[0]):
        row = next(row for row in volumes.fixed_volume_matrix()["rows"] if row["volume"] == name)
        return dict(registry=self.registry, container_record=self.container_records[row["role"]],
            volume_record=self.volume_records[name], container_intent_id=self.container_intents[row["role"]],
            volume_intent_id=self.volume_intents[name],
            current_container_metadata=deepcopy(self.container_metadata[row["role"]]),
            current_volume_metadata=deepcopy(self.volume_metadata[name]))

    def observation(self, name=VOLUME_NAMES[0], **overrides):
        arguments = self.arguments(name)
        row = next(row for row in volumes.fixed_volume_matrix()["rows"] if row["volume"] == name)
        raw = empty_archive(row["tar_directory"])
        arguments.update(archive_bytes=raw, expected_archive_sha256=sha(raw), origin="SYNTHETIC",
                         parent_directory_confirmed=True)
        arguments.update(overrides)
        return volumes.EmptyVolumeObservation.from_archive(**arguments)


class VolumeInitializationTests(unittest.TestCase):
    def rejected(self, function, code=None):
        with self.assertRaises(RestoreError) as caught:
            function()
        if code:
            self.assertEqual(caught.exception.code, code)
        self.assertRegex(str(caught.exception), r"\A[A-Z][A-Z0-9_]{2,80}\Z")
        self.assertNotIn(PRIVATE_SENTINEL, str(caught.exception))

    def test_nine_fixed_rows_roles_uid_modes_and_execution_gates(self):
        matrix = volumes.fixed_volume_matrix()
        self.assertEqual(tuple(row["volume"] for row in matrix["rows"]), VOLUME_NAMES)
        self.assertEqual((matrix["extra_containers"], matrix["maximum_simultaneous_containers"],
                          matrix["container_incarnations_proposal"]), (0, 5, 10))
        self.assertFalse(matrix["executable"])
        self.assertFalse(matrix["root_exec_chown"])
        self.assertEqual(matrix["capabilities_added"], [])
        for row in matrix["rows"]:
            self.assertEqual(row["runtime_status"], "NOT_RUN")
            self.assertTrue(row["requires_volume_nocopy"])
            self.assertTrue(row["requires_writable_target_mount"])
            expected = (999, 999) if row["role"] == "db" else (999, 1000) if row["role"].startswith("redis-") else (1000, 1000)
            self.assertEqual((row["uid"], row["gid"]), expected)
        matrix["rows"][0]["uid"] = 0
        self.assertEqual(volumes.fixed_volume_matrix()["rows"][0]["uid"], 999)

    def test_owner_tar_has_one_deterministic_fixed_directory_without_payload(self):
        for row in volumes.fixed_volume_matrix()["rows"]:
            raw = volumes.build_owner_tar(row["volume"])
            self.assertEqual(raw, volumes.build_owner_tar(row["volume"]))
            self.assertEqual(len(raw), 10240)
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
                members = archive.getmembers()
            self.assertEqual(len(members), 1)
            member = members[0]
            self.assertEqual(member.name.rstrip("/"), row["tar_directory"])
            self.assertTrue(member.isdir())
            self.assertEqual((member.uid, member.gid, member.mode, member.size, member.mtime),
                             (row["uid"], row["gid"], int(row["mode"], 8), 0, 0))
            self.assertEqual(member.pax_headers, {})
            self.assertEqual(member.linkname, "")

    def test_tar_builder_cannot_accept_arbitrary_paths_volume_aliases_or_types(self):
        for name in ("original-sites", OWNER + "-db-data-extra", "../mysql", "/var/lib/mysql", None, [], True):
            self.rejected(lambda: volumes.build_owner_tar(name), "VOLUME_TARGET_DENIED")

    def test_all_empty_root_archives_validate_only_codec_not_provenance(self):
        for row in volumes.fixed_volume_matrix()["rows"]:
            raw = empty_archive(row["tar_directory"])
            result = volumes.validate_empty_volume_tar(row["volume"], raw)
            self.assertEqual(result["members"], 1)
            self.assertEqual(result["payload_bytes"], 0)
            self.assertEqual(result["capture_provenance"], "TRUSTED_CALLER_REQUIRED")
            self.assertEqual(result["sha256"], sha(raw))
            self.assertNotIn(PRIVATE_SENTINEL, json.dumps(result))

    def test_deep_absolute_escape_alias_and_wrong_root_archive_paths_are_denied(self):
        for name in ("mysql/data", "./mysql", "../mysql", "/mysql", "mysql/../escape", "data", PRIVATE_SENTINEL):
            self.rejected(lambda: volumes.validate_empty_volume_tar(VOLUME_NAMES[0], empty_archive(name)), "VOLUME_ROOT_COLLISION")

    def test_link_special_and_payload_root_types_are_denied(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.REGTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            self.rejected(lambda: volumes.validate_empty_volume_tar(VOLUME_NAMES[0], empty_archive(kind=kind, linkname=PRIVATE_SENTINEL)), "VOLUME_ROOT_COLLISION")
        self.rejected(lambda: volumes.validate_empty_volume_tar(VOLUME_NAMES[0], empty_archive(payload=b"x")), "VOLUME_ROOT_COLLISION")

    def test_nonempty_duplicate_and_prior_owner_initialization_collisions_are_denied(self):
        for raw in (empty_archive(extra="mysql/previous"), empty_archive(extra="mysql"),
                    empty_archive(uid=999, gid=999, mode=0o700), empty_archive(mode=0o777),
                    empty_archive(uid=0, gid=1000)):
            self.rejected(lambda: volumes.validate_empty_volume_tar(VOLUME_NAMES[0], raw), "VOLUME_ROOT_COLLISION")

    def test_pax_global_long_link_and_unknown_metadata_are_denied(self):
        for raw in (empty_archive(pax={"mtime": "1700000000.5"}),
                    empty_archive(pax={"path": "mysql/" + PRIVATE_SENTINEL}),
                    empty_archive(global_pax={"uid": "999"})):
            self.rejected(lambda: volumes.validate_empty_volume_tar(VOLUME_NAMES[0], raw), "VOLUME_ROOT_COLLISION")

    def test_truncated_corrupt_oversized_and_wrong_byte_types_are_denied(self):
        valid = empty_archive()
        corrupt = b"!" + valid[1:]
        for raw in (b"", valid[:512], valid[:-1], valid + b"\0" * 512, corrupt, bytearray(valid)):
            self.rejected(lambda: volumes.validate_empty_volume_tar(VOLUME_NAMES[0], raw), "VOLUME_TAR_REJECTED")

    def test_registered_init_context_produces_exact_cp_tar_plan_for_all_nine(self):
        context = SyntheticContext()
        for name in VOLUME_NAMES:
            arguments = context.arguments(name)
            observation = context.observation(name)
            plan = volumes.prepare_volume_initialization(**arguments, observation=observation)
            row = next(row for row in volumes.fixed_volume_matrix()["rows"] if row["volume"] == name)
            self.assertEqual(plan.argv, (DOCKER, "cp", "-a", "-",
                arguments["container_record"].container_id + ":" + row["copy_parent"]))
            self.assertEqual(plan.tar_bytes, volumes.build_owner_tar(name))
            self.assertEqual(plan.tar_sha256, sha(plan.tar_bytes))
            self.assertFalse(plan.executable)
            self.assertEqual(plan.public_summary()["daemon_compatibility"], "NOT_RUN")
            self.assertNotIn("tar_bytes=b", repr(plan))
            with self.assertRaises(FrozenInstanceError):
                plan.executable = True

    def test_raw_ids_and_unregistered_record_or_foreign_intent_are_denied(self):
        context = SyntheticContext()
        for field, value in (("container_record", "1" * 64), ("volume_record", VOLUME_NAMES[0]),
                             ("container_intent_id", "a" * 64), ("volume_intent_id", [])):
            arguments = context.arguments()
            arguments[field] = value
            self.rejected(lambda: volumes.prepare_volume_initialization(**arguments, observation=context.observation()))
        other = SyntheticContext()
        arguments = context.arguments()
        arguments["container_record"] = other.container_records["db"]
        self.rejected(lambda: volumes.prepare_volume_initialization(**arguments, observation=context.observation()), "VOLUME_REGISTERED_RECEIPTS_REQUIRED")

    def test_cross_run_nonce_or_volume_observation_cannot_be_reused(self):
        context, other = SyntheticContext(), SyntheticContext()
        first = context.observation()
        self.rejected(lambda: volumes.prepare_volume_initialization(**other.arguments(), observation=first), "VOLUME_CAPTURE_REJECTED")
        self.rejected(lambda: volumes.prepare_volume_initialization(**context.arguments(VOLUME_NAMES[1]), observation=first), "VOLUME_CAPTURE_REJECTED")

    def test_parent_capture_must_be_explicit_exact_boolean_and_hash(self):
        context = SyntheticContext()
        for changes in ({"parent_directory_confirmed": False}, {"parent_directory_confirmed": 1},
                        {"origin": "arbitrary"}, {"expected_archive_sha256": "b" * 64},
                        {"expected_archive_sha256": PRIVATE_SENTINEL}):
            self.rejected(lambda: context.observation(**changes))

    def test_changed_fresh_container_volume_identity_or_owner_is_denied(self):
        context = SyntheticContext()
        for mutation in (lambda args: args["current_container_metadata"].update(Id=BASELINE.container_ids[0]),
                         lambda args: args["current_container_metadata"]["Config"].update(Labels={}),
                         lambda args: args["current_volume_metadata"].update(Labels={}),
                         lambda args: args["current_volume_metadata"].update(Name="original-sites")):
            arguments = context.arguments()
            mutation(arguments)
            self.rejected(lambda: volumes.prepare_volume_initialization(**arguments, observation=context.observation()))

    def test_running_paused_restarting_dead_unknown_container_states_are_denied(self):
        context = SyntheticContext()
        for field, value in (("Running", True), ("Paused", True), ("Restarting", True), ("Dead", True),
                             ("Status", "running"), ("Running", 0), ("Paused", None)):
            arguments = context.arguments()
            arguments["current_container_metadata"]["State"][field] = value
            self.rejected(lambda: volumes.prepare_volume_initialization(**arguments, observation=context.observation()), "VOLUME_CONTAINER_NOT_STOPPED")

    def test_fresh_readonly_and_nocopy_false_or_missing_mount_are_denied(self):
        context = SyntheticContext()
        for change in (lambda args: args["current_container_metadata"]["HostConfig"]["Mounts"][0].update(ReadOnly=True),
                       lambda args: args["current_container_metadata"]["HostConfig"]["Mounts"][0].update(VolumeOptions={"NoCopy": False}),
                       lambda args: args["current_container_metadata"]["HostConfig"]["Mounts"][0].update(VolumeOptions={"NoCopy": 1}),
                       lambda args: args["current_container_metadata"]["HostConfig"]["Mounts"][0].update(VolumeOptions={"NoCopy": True, "Unknown": True}),
                       lambda args: args["current_container_metadata"]["HostConfig"]["Mounts"][0].pop("VolumeOptions"),
                       lambda args: args["current_container_metadata"]["Mounts"].clear()):
            arguments = context.arguments()
            change(arguments)
            self.rejected(lambda: volumes.prepare_volume_initialization(**arguments, observation=context.observation()))

    def test_precheck_phase_cannot_be_reused_as_volume_initialization(self):
        context = SyntheticContext()
        original = context.container_records["db"]
        metadata = context.container_metadata["db"]
        precheck = ResourceRecord.from_inspect(metadata,
            expected=replace(original.spec, phase="namespace-precheck"),
            original_ids=BASELINE.container_ids, original_names=BASELINE.container_names,
            original_volume_names=BASELINE.volume_names)
        arguments = context.arguments()
        arguments["container_record"] = precheck
        self.rejected(lambda: volumes.prepare_volume_initialization(**arguments,
            observation=context.observation()), "VOLUME_REGISTERED_RECEIPTS_REQUIRED")

    def test_record_malformed_metadata_and_unissued_observation_fail_with_fixed_errors(self):
        context = SyntheticContext()
        for field in ("current_container_metadata", "current_volume_metadata"):
            for bad in (None, [], PRIVATE_SENTINEL, {"Id": PRIVATE_SENTINEL}):
                arguments = context.arguments()
                arguments[field] = bad
                self.rejected(lambda: volumes.prepare_volume_initialization(**arguments,
                    observation=context.observation()))
        for bad in (None, PRIVATE_SENTINEL, volumes.EmptyVolumeObservation()):
            self.rejected(lambda: volumes.prepare_volume_initialization(**context.arguments(), observation=bad),
                "VOLUME_CAPTURE_REJECTED" if type(bad) is not volumes.EmptyVolumeObservation else "VOLUME_INITIALIZATION_REJECTED")
        self.rejected(lambda: volumes.VolumeInitializationPlan().public_summary())

    def test_original_baseline_volume_and_container_names_cannot_be_admitted(self):
        context = SyntheticContext()
        for mutation in (lambda args: args["current_container_metadata"].update(Name="/original-db"),
                         lambda args: args["current_volume_metadata"].update(Name="original-sites"),
                         lambda args: args["current_container_metadata"]["Mounts"][0].update(Name="original-sites")):
            arguments = context.arguments()
            mutation(arguments)
            self.rejected(lambda: volumes.prepare_volume_initialization(**arguments, observation=context.observation()))

    def test_expired_closed_or_unconfirmed_lifecycle_is_denied(self):
        for closed in (False, True):
            context = SyntheticContext()
            observation = context.observation()
            if closed:
                context.registry.cleanup_plan([])
            else:
                context.time += 2700
            self.rejected(lambda: volumes.prepare_volume_initialization(**context.arguments(), observation=observation), "VOLUME_LIFECYCLE_CLOSED")

    def test_synthetic_or_real_claim_never_opens_execution_boundary(self):
        context = SyntheticContext()
        for origin in ("SYNTHETIC", "REAL"):
            observation = context.observation(origin=origin)
            plan = volumes.prepare_volume_initialization(**context.arguments(), observation=observation)
            calls = []
            self.rejected(lambda: volumes.execute_volume_initialization(plan, callback=lambda: calls.append("called")), "VOLUME_EXECUTION_DISABLED")
            self.assertEqual(calls, [])
            self.assertFalse(plan.executable)
            self.assertFalse(context.registry.readiness()["ready"])

    def test_no_process_socket_or_host_chown_operation_is_used(self):
        with (patch.object(subprocess, "run", side_effect=AssertionError("Docker forbidden")),
              patch.object(subprocess, "Popen", side_effect=AssertionError("process forbidden")),
              patch.object(socket, "socket", side_effect=AssertionError("network forbidden"))):
            context = SyntheticContext()
            plan = volumes.prepare_volume_initialization(**context.arguments(), observation=context.observation())
            self.assertFalse(plan.executable)
            self.rejected(lambda: volumes.execute_volume_initialization(plan), "VOLUME_EXECUTION_DISABLED")


if __name__ == "__main__":
    unittest.main()
