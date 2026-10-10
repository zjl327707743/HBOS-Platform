"""Synthetic private landing only; no Docker, SQL, real backup or service."""
from contextlib import redirect_stderr, redirect_stdout
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scripts.release.full_site_restore import inputs, landing
from scripts.release.full_site_restore.common import APP_NAMES, RestoreError
from scripts.release.tests.test_full_site_restore_inputs import archive_bytes

SECRET = "SYNTHETIC_LANDING_SECRET_PERSON_DO_NOT_PRINT"


def sha(value):
    return hashlib.sha256(value).hexdigest()


class LandingCases(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hbos-synthetic-landing-")
        self.addCleanup(temporary.cleanup)
        self.fixture = Path(temporary.name).resolve()
        self.source = self.fixture / "source"
        self.source.mkdir(mode=0o700)
        self.root = self.fixture / "new-owned-root"
        override = patch.object(landing, "ROOT", self.root)
        override.start()
        self.addCleanup(override.stop)
        self.database_name = "synthetic_owned_landing_database"
        database_hash = sha(self.database_name.encode())
        override = patch.object(inputs, "DATABASE_SHA256", database_hash)
        override.start()
        self.addCleanup(override.stop)
        self.paths = {key: self.source / (key + ".input") for key in inputs.COMPONENTS}
        self.database = gzip.compress(("-- " + SECRET + "\nSELECT 1;\n").encode(), mtime=0)
        self.config = json.dumps({"db_name": self.database_name, "db_password": SECRET,
                                  "encryption_key": SECRET}).encode()
        self.public = [{"name": "./frontend/public/files/", "type": tarfile.DIRTYPE},
                       {"name": "./frontend/public/files/document.bin", "payload": b"public bytes"}]
        self.private = [{"name": "./frontend/private/files/", "type": tarfile.DIRTYPE},
                        {"name": "./frontend/private/files/nested/", "type": tarfile.DIRTYPE},
                        {"name": "./frontend/private/files/nested/" + SECRET, "payload": SECRET.encode()}]
        self.auth = [{"name": name, "mode": 0o600, "payload": (SECRET + name).encode()}
                     for name in ("hbos_feishu_app_secret", "hbos_feishu_tenant_key")]
        values = {"database": self.database, "site_config": self.config,
                  "public_files": archive_bytes(self.public), "private_files": archive_bytes(self.private),
                  "auth_files": archive_bytes(self.auth, compressed=True)}
        for key, value in values.items():
            self.paths[key].write_bytes(value)
        before = {"site": "frontend", "database_fingerprint": database_hash,
                  "installed_apps": list(APP_NAMES), "user_count": 18,
                  "user_fingerprint": "1" * 64, "credential_fingerprint": "2" * 64,
                  "role_fingerprint": "3" * 64, "permission_fingerprint": "4" * 64,
                  "business_association_fingerprint": "5" * 64, "identity_fingerprint": "6" * 64,
                  "identity_table_present": True, "business_counts": {"Employee": 0},
                  "encryption_key_present": True, "legacy_feishu_social_keys": 0, "csrf_enabled": True}
        self.before = self.source / "before.json"
        self.before.write_text(json.dumps(before))
        self.manifest = self.source / "host-backup-prepared.json"
        self.manifest.write_text(json.dumps({key: str(path) for key, path in self.paths.items()}))
        for path in self.source.iterdir():
            path.chmod(0o600)
        self.refresh()
        self.capabilities = []
        self.addCleanup(self.release_capabilities)

    def release_capabilities(self):
        for capability in self.capabilities:
            capability.close()

    def refresh(self):
        self.expected = {key: {"sha256": sha(path.read_bytes()), "bytes": path.stat().st_size}
                         for key, path in self.paths.items()}
        self.before_sha = sha(self.before.read_bytes())
        self.manifest_sha = sha(self.manifest.read_bytes())

    def land(self):
        capability = landing.land_backup_inputs(self.manifest, self.expected, self.before_sha, self.manifest_sha)
        self.capabilities.append(capability)
        return capability

    def assert_rejected(self, code=None):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors), self.assertRaises(RestoreError) as caught:
            self.land()
        if code:
            self.assertEqual(str(caught.exception), code)
        self.assertRegex(str(caught.exception), r"\A[A-Z][A-Z0-9_]{2,80}\Z")
        for value in (str(caught.exception), output.getvalue(), errors.getvalue()):
            self.assertNotIn(SECRET, value)
            self.assertNotIn(str(self.fixture), value)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(errors.getvalue(), "")

    def assert_cleanup_refused(self, capability, code):
        with self.assertRaises(RestoreError) as caught:
            capability.cleanup()
        self.assertEqual(str(caught.exception), code)
        self.assertTrue(self.root.exists())

    def test_exact_original_layout_bytes_modes_and_private_summary(self):
        original = {path.name: (path.read_bytes(), path.stat()) for path in self.source.iterdir()}
        capability = self.land()
        self.assertEqual((self.root / "input/database.sql.gz").read_bytes(), self.database)
        self.assertEqual((self.root / "input/site_config.json").read_bytes(), self.config)
        self.assertEqual((self.root / "sites/frontend/site_config.json").read_bytes(), self.config)
        self.assertEqual((self.root / "input/before.json").read_bytes(), self.before.read_bytes())
        for key, filename in (("public_files", "public_files.tar"), ("private_files", "private_files.tar"),
                              ("auth_files", "auth_files.tar.gz")):
            self.assertEqual((self.root / "input" / filename).read_bytes(), self.paths[key].read_bytes())
        self.assertEqual((self.root / "sites/frontend/public/files/document.bin").read_bytes(), b"public bytes")
        self.assertEqual((self.root / "sites/frontend/private/files/nested" / SECRET).read_bytes(), SECRET.encode())
        for item in self.auth:
            self.assertEqual((self.root / "sites/frontend/private" / item["name"]).read_bytes(), item["payload"])
            self.assertFalse((self.root / "sites/frontend" / item["name"]).exists())
        for path in [self.root, *self.root.rglob("*")]:
            metadata = path.lstat()
            self.assertEqual(metadata.st_uid, os.geteuid())
            self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o700 if path.is_dir() else 0o600)
            self.assertFalse(path.is_symlink())
            if path.is_file():
                self.assertEqual(metadata.st_nlink, 1)
        summary = capability.public_summary()
        self.assertEqual(summary["status"], "LANDED_PRIVATE_BYTES_ONLY")
        self.assertEqual(summary["sql_restore"], "NOT_RUN")
        self.assertEqual(summary["container_uid_mode_restore"], "NOT_RUN")
        self.assertEqual(summary["host_uid_matches_archive"], os.geteuid() == 1000)
        for value in (SECRET, str(self.fixture), self.database_name, "hbos_feishu_app_secret"):
            self.assertNotIn(value, json.dumps(summary) + repr(capability))
        for name, (raw, metadata) in original.items():
            self.assertEqual((self.source / name).read_bytes(), raw)
            after = (self.source / name).stat()
            self.assertEqual((after.st_ino, after.st_mtime_ns, after.st_mode),
                             (metadata.st_ino, metadata.st_mtime_ns, metadata.st_mode))

    def test_summary_is_not_mutable_capability(self):
        capability = self.land()
        summary = capability.public_summary()
        summary["host_mode"]["files"] = "0777"
        summary["components"]["database"]["sha256"] = SECRET
        self.assertEqual(capability.public_summary()["host_mode"]["files"], "0600")
        self.assertEqual(capability.public_summary()["components"]["database"]["sha256"], sha(self.database))

    def test_cleanup_exact_new_objects_only_and_idempotent(self):
        sentinel = self.fixture / "unrelated-existing"
        sentinel.write_text(SECRET)
        capability = self.land()
        result = capability.cleanup()
        self.assertEqual(result["status"], "LANDING_CLEANED")
        self.assertFalse(self.root.exists())
        self.assertTrue(self.manifest.exists())
        self.assertEqual(sentinel.read_text(), SECRET)
        self.assertEqual(capability.cleanup()["removed_entries"], 0)

    def test_existing_root_collision_preserves_everything(self):
        self.root.mkdir(mode=0o700)
        sentinel = self.root / "existing"
        sentinel.write_text(SECRET)
        self.assert_rejected("LANDING_COLLISION")
        self.assertEqual(sentinel.read_text(), SECRET)
        self.assertEqual(set(path.name for path in self.root.iterdir()), {"existing"})

    def test_destination_root_symlink_collision_preserves_target(self):
        other = self.fixture / "existing-target"
        other.mkdir(mode=0o700)
        (other / "existing").write_text(SECRET)
        self.root.symlink_to(other, target_is_directory=True)
        self.assert_rejected("LANDING_COLLISION")
        self.assertTrue(self.root.is_symlink())
        self.assertEqual((other / "existing").read_text(), SECRET)

    def test_ancestor_symlink_cannot_create_destination(self):
        alias = self.fixture / "alias"
        alias.symlink_to(self.fixture, target_is_directory=True)
        with patch.object(landing, "ROOT", alias / "new-owned-root"):
            self.assert_rejected("LANDING_FAILED")
        self.assertFalse(self.root.exists())

    def test_partial_write_failure_cleans_registered_files_only(self):
        original = landing.OwnedLanding._write
        count = 0
        def write(capability, relative, payload):
            nonlocal count
            original(capability, relative, payload)
            count += 1
            if count == 2:
                raise OSError(SECRET)
        with patch.object(landing.OwnedLanding, "_write", write):
            self.assert_rejected("LANDING_FAILED")
        self.assertFalse(self.root.exists())
        self.assertEqual(self.paths["database"].read_bytes(), self.database)

    def test_zero_byte_write_cleans_created_empty_file(self):
        with patch.object(landing.os, "write", return_value=0):
            self.assert_rejected("LANDING_WRITE_FAILED")
        self.assertFalse(self.root.exists())

    def test_hash_readback_failure_cleans_new_objects(self):
        original = landing.os.read
        corrupted = False
        def read(descriptor, limit):
            nonlocal corrupted
            raw = original(descriptor, limit)
            if raw and not corrupted:
                corrupted = True
                return b"!" + raw[1:]
            return raw
        with patch.object(landing.os, "read", side_effect=read):
            self.assert_rejected("LANDING_HASH_MISMATCH")
        self.assertFalse(self.root.exists())

    def test_changed_input_between_validation_and_freeze_rejected(self):
        original = inputs.validate_backup_inputs
        def validate(*args):
            result = original(*args)
            self.paths["database"].write_bytes(b"!" + self.database[1:])
            return result
        with patch.object(inputs, "validate_backup_inputs", side_effect=validate):
            self.assert_rejected("COMPONENT_HASH_MISMATCH")
        self.assertFalse(self.root.exists())

    def test_mutating_caller_pins_cannot_admit_changed_frozen_bytes(self):
        original = inputs.validate_backup_inputs
        def validate(*args):
            result = original(*args)
            changed = b"!" + self.database[1:]
            self.paths["database"].write_bytes(changed)
            self.expected["database"]["sha256"] = sha(changed)
            return result
        with patch.object(inputs, "validate_backup_inputs", side_effect=validate):
            self.assert_rejected("COMPONENT_HASH_MISMATCH")
        self.assertFalse(self.root.exists())

    def test_late_input_mutation_during_freeze_rejected(self):
        original = landing._freeze_inputs
        real_read = inputs._read_bytes
        def freeze(*args):
            def read(stream, limit):
                raw = real_read(stream, limit)
                if raw == self.paths["auth_files"].read_bytes():
                    self.paths["database"].write_bytes(b"!" + self.database[1:])
                return raw
            with patch.object(inputs, "_read_bytes", side_effect=read):
                return original(*args)
        with patch.object(landing, "_freeze_inputs", side_effect=freeze):
            self.assert_rejected("INPUT_CHANGED")
        self.assertFalse(self.root.exists())

    def test_source_changes_after_freeze_do_not_change_landed_bytes(self):
        original = landing._new_landing
        def create():
            self.paths["database"].write_bytes(b"!" + self.database[1:])
            return original()
        with patch.object(landing, "_new_landing", side_effect=create):
            capability = self.land()
        self.assertEqual((self.root / "input/database.sql.gz").read_bytes(), self.database)
        self.assertEqual(capability.public_summary()["components"]["database"]["sha256"], sha(self.database))

    def test_archive_path_override_pax_refused_before_creation(self):
        self.private[2]["pax"] = {"path": "../../" + SECRET}
        self.paths["private_files"].write_bytes(archive_bytes(self.private))
        self.refresh()
        self.assert_rejected()
        self.assertFalse(self.root.exists())

    def test_valid_mtime_pax_retains_content_but_not_host_archive_mode(self):
        self.private[2]["pax"] = {"mtime": "1700000000.125"}
        self.private[2]["mode"] = 0o644
        self.paths["private_files"].write_bytes(archive_bytes(self.private))
        self.refresh()
        capability = self.land()
        path = self.root / "sites/frontend/private/files/nested" / SECRET
        self.assertEqual(path.read_bytes(), SECRET.encode())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(capability.public_summary()["container_uid_mode_restore"], "NOT_RUN")

    def test_archive_link_traversal_duplicate_and_special_refused_before_creation(self):
        variants = [{"name": "./frontend/private/files/link", "type": tarfile.SYMTYPE, "linkname": SECRET},
                    {"name": "./frontend/private/files/../escape", "payload": b"x"},
                    dict(self.private[2]),
                    {"name": "./frontend/private/files/fifo", "type": tarfile.FIFOTYPE}]
        for variant in variants:
            with self.subTest(kind=variant.get("type", "regular")):
                self.paths["private_files"].write_bytes(archive_bytes(self.private + [variant]))
                self.refresh()
                self.assert_rejected()
                self.assertFalse(self.root.exists())

    def test_landing_entry_quota_refused_before_any_output(self):
        with patch.object(landing, "MAX_LANDING_ENTRIES", 32):
            self.assert_rejected("LANDING_ENTRY_LIMIT")
        self.assertFalse(self.root.exists())

    def test_landing_byte_quota_refused_before_any_output(self):
        with patch.object(landing, "MAX_FROZEN_BYTES", 1):
            self.assert_rejected("LANDING_BYTE_LIMIT")
        with patch.object(landing, "MAX_ARCHIVE_EXPANDED_BYTES", 1):
            self.assert_rejected("LANDING_BYTE_LIMIT")
        self.assertFalse(self.root.exists())

    def test_cleanup_unknown_child_refuses_without_partial_deletion(self):
        capability = self.land()
        intruder = self.root / "sites/unregistered"
        intruder.write_text(SECRET)
        self.assert_cleanup_refused(capability, "LANDING_UNREGISTERED_CHILD")
        self.assertTrue((self.root / "input/database.sql.gz").exists())
        self.assertEqual(intruder.read_text(), SECRET)
        intruder.unlink()
        self.assertEqual(capability.cleanup()["status"], "LANDING_CLEANED")

    def test_cleanup_hardlink_refuses_without_deleting_source_or_alias(self):
        capability = self.land()
        source = self.root / "input/database.sql.gz"
        alias = self.fixture / "outside-alias"
        os.link(source, alias)
        self.assert_cleanup_refused(capability, "LANDING_IDENTITY_CHANGED")
        self.assertEqual(alias.read_bytes(), self.database)
        self.assertTrue(source.exists())
        alias.unlink()
        self.assertEqual(capability.cleanup()["status"], "LANDING_CLEANED")

    def test_cleanup_replaced_file_refuses_and_preserves_replacement(self):
        capability = self.land()
        path = self.root / "input/site_config.json"
        path.unlink()
        path.write_bytes(SECRET.encode())
        path.chmod(0o600)
        self.assert_cleanup_refused(capability, "LANDING_IDENTITY_CHANGED")
        self.assertEqual(path.read_bytes(), SECRET.encode())
        self.assertTrue((self.root / "input/database.sql.gz").exists())

    def test_cleanup_symlink_refuses_and_does_not_touch_target(self):
        capability = self.land()
        path = self.root / "input/site_config.json"
        path.unlink()
        path.symlink_to(self.paths["site_config"])
        self.assert_cleanup_refused(capability, "LANDING_IDENTITY_CHANGED")
        self.assertTrue(path.is_symlink())
        self.assertEqual(self.paths["site_config"].read_bytes(), self.config)

    def test_cleanup_changed_mode_refuses(self):
        capability = self.land()
        path = self.root / "input/database.sql.gz"
        path.chmod(0o644)
        self.assert_cleanup_refused(capability, "LANDING_IDENTITY_CHANGED")
        path.chmod(0o600)
        self.assertEqual(capability.cleanup()["status"], "LANDING_CLEANED")

    def test_close_releases_capability_and_never_claims_cleaned(self):
        capability = self.land()
        summary = capability.close()
        self.assertEqual(summary, {"status": "LANDING_CAPABILITY_CLOSED", "files_removed": False})
        self.assertTrue(self.root.exists())
        self.assert_cleanup_refused(capability, "LANDING_CAPABILITY_INVALID")

    def test_injected_target_link_failure_cleanup_refuses_and_preserves_target(self):
        other = self.fixture / "outside"
        other.mkdir(mode=0o700)
        sentinel = other / "sentinel"
        sentinel.write_text(SECRET)
        original = landing.OwnedLanding._write
        def write(capability, relative, payload):
            (self.root / "input").symlink_to(other, target_is_directory=True)
            original(capability, relative, payload)
        with patch.object(landing.OwnedLanding, "_write", write):
            self.assert_rejected("LANDING_FAILURE_CLEANUP_REFUSED")
        self.assertTrue((self.root / "input").is_symlink())
        self.assertEqual(sentinel.read_text(), SECRET)
        self.assertEqual(set(path.name for path in other.iterdir()), {"sentinel"})

    def test_create_then_unanchorable_root_reports_cleanup_refused(self):
        original = landing.os.open
        def open_file(path, flags, *args, **kwargs):
            if path == self.root.name:
                raise OSError(SECRET)
            return original(path, flags, *args, **kwargs)
        with patch.object(landing.os, "open", side_effect=open_file):
            self.assert_rejected("LANDING_FAILURE_CLEANUP_REFUSED")
        self.assertTrue(self.root.is_dir())

    def test_umask_cannot_weaken_private_modes(self):
        previous = os.umask(0)
        try:
            capability = self.land()
        finally:
            os.umask(previous)
        capability.verify_private_tree()
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)

    def test_no_host_chown_is_used(self):
        with patch.object(landing.os, "chown", side_effect=AssertionError("host chown forbidden")):
            capability = self.land()
        self.assertEqual(capability.public_summary()["container_uid_mode_restore"], "NOT_RUN")

    def test_internal_writer_rejects_escape_and_absolute_paths(self):
        capability = self.land()
        for relative in ("../outside", "input/../../outside", "/outside", "input//outside", "input/./outside"):
            with self.subTest(relative=relative), self.assertRaises(RestoreError) as caught:
                capability._write(relative, SECRET.encode())
            self.assertEqual(str(caught.exception), "LANDING_RELATIVE_PATH_INVALID")
        capability.verify_private_tree()
        self.assertFalse((self.fixture / "outside").exists())

    def test_missing_owned_file_has_fixed_error_without_private_name(self):
        capability = self.land()
        path = self.root / "sites/frontend/private/files/nested" / SECRET
        path.unlink()
        with self.assertRaises(RestoreError) as caught:
            capability.verify_private_tree()
        self.assertEqual(str(caught.exception), "LANDING_IDENTITY_CHANGED")
        self.assertNotIn(SECRET, str(caught.exception))

    def test_same_inode_same_size_payload_mutation_is_rejected(self):
        capability = self.land()
        path = self.root / "input/database.sql.gz"
        original_inode = path.stat().st_ino
        with path.open("r+b") as stream:
            stream.write(b"!")
        self.assertEqual(path.stat().st_ino, original_inode)
        self.assertEqual(path.stat().st_size, len(self.database))
        with self.assertRaises(RestoreError) as caught:
            capability.verify_private_tree()
        self.assertEqual(str(caught.exception), "LANDING_PAYLOAD_CHANGED")
        self.assert_cleanup_refused(capability, "LANDING_PAYLOAD_CHANGED")

    def test_final_batch_verification_rejects_earlier_output_mutation(self):
        original = landing.OwnedLanding._write
        def write(capability, relative, payload):
            original(capability, relative, payload)
            if relative == "sites/frontend/private/hbos_feishu_tenant_key":
                with (self.root / "input/database.sql.gz").open("r+b") as stream:
                    stream.write(b"!")
        with patch.object(landing.OwnedLanding, "_write", write):
            self.assert_rejected("LANDING_FAILURE_CLEANUP_REFUSED")
        self.assertTrue(self.root.exists())

    def test_replace_race_before_atomic_move_preserves_unowned_replacement(self):
        capability = self.land()
        replacement = self.fixture / "existing-replacement"
        replacement.write_bytes(SECRET.encode())
        replacement.chmod(0o600)
        original = landing._move_no_replace
        triggered = False
        def move(source_parent, source_name, destination_parent, destination_name):
            nonlocal triggered
            if not triggered:
                triggered = True
                os.unlink(source_name, dir_fd=source_parent)
                os.link(replacement, source_name, dst_dir_fd=source_parent)
            original(source_parent, source_name, destination_parent, destination_name)
        with patch.object(landing, "_move_no_replace", side_effect=move):
            self.assert_cleanup_refused(capability, "LANDING_IDENTITY_CHANGED")
        self.assertEqual(replacement.read_bytes(), SECRET.encode())
        slot = self.root / ".owned-cleanup"
        moved = list(slot.iterdir())
        self.assertEqual(len(moved), 1)
        self.assertEqual(moved[0].stat().st_ino, replacement.stat().st_ino)
        self.assertEqual(moved[0].read_bytes(), SECRET.encode())

    def test_atomic_private_slot_collision_never_overwrites_existing_object(self):
        capability = self.land()
        original = landing._move_no_replace
        def move(source_parent, source_name, destination_parent, destination_name):
            descriptor = os.open(destination_name, os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                                 0o600, dir_fd=destination_parent)
            try:
                os.write(descriptor, SECRET.encode())
            finally:
                os.close(descriptor)
            original(source_parent, source_name, destination_parent, destination_name)
        with patch.object(landing, "_move_no_replace", side_effect=move):
            self.assert_cleanup_refused(capability, "LANDING_ATOMIC_MOVE_FAILED")
        moved = list((self.root / ".owned-cleanup").iterdir())
        self.assertEqual(len(moved), 1)
        self.assertEqual(moved[0].read_bytes(), SECRET.encode())
        self.assertTrue((self.root / "sites/frontend/private/hbos_feishu_tenant_key").exists())

    def test_unsupported_atomic_move_platform_has_no_unsafe_fallback(self):
        capability = self.land()
        with patch.object(landing.sys, "platform", "unsupported"):
            self.assert_cleanup_refused(capability, "LANDING_ATOMIC_MOVE_UNAVAILABLE")
        self.assertEqual((self.root / "input/database.sql.gz").read_bytes(), self.database)
        self.assertEqual(list((self.root / ".owned-cleanup").iterdir()), [])

    def test_failed_slot_creation_cleans_only_the_new_empty_root(self):
        original = landing.os.mkdir
        def mkdir(name, *args, **kwargs):
            if name == ".owned-cleanup":
                raise OSError(SECRET)
            return original(name, *args, **kwargs)
        with patch.object(landing.os, "mkdir", side_effect=mkdir):
            self.assert_rejected("LANDING_FAILED")
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
