"""Synthetic-only validation: no real backup, SQL, Docker or network."""
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

from scripts.release.full_site_restore import inputs
from scripts.release.full_site_restore.common import APP_NAMES, RestoreError

SECRET = "SYNTHETIC_PASSWORD_PERSON_014_NOT_FOR_OUTPUT"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def archive_bytes(entries, *, compressed=False, global_pax=None):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT, pax_headers=global_pax) as archive:
        for entry in entries:
            item = tarfile.TarInfo(entry["name"])
            item.type = entry.get("type", tarfile.REGTYPE)
            item.mode = entry.get("mode", 0o755 if item.isdir() else 0o644)
            item.uid = entry.get("uid", 1000)
            item.gid = entry.get("gid", 1000)
            item.mtime = entry.get("mtime", 1_700_000_000)
            item.pax_headers = entry.get("pax", {})
            item.linkname = entry.get("linkname", "")
            payload = entry.get("payload", b"")
            item.size = len(payload) if item.isfile() else entry.get("size", 0)
            archive.addfile(item, io.BytesIO(payload) if item.isfile() else None)
    payload = output.getvalue()
    return gzip.compress(payload, mtime=0) if compressed else payload


class InputValidationCases(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hbos-synthetic-inputs-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.directory.chmod(0o700)
        self.database_name = "entirely_synthetic_database"
        self.database_hash = sha(self.database_name.encode())
        override = patch.object(inputs, "DATABASE_SHA256", self.database_hash)
        override.start()
        self.addCleanup(override.stop)
        self.paths = {key: self.directory / (key + ".input") for key in inputs.COMPONENTS}
        self.paths["database"].write_bytes(gzip.compress(("-- " + SECRET + "\nSELECT 1;\n").encode(), mtime=0))
        self.config = {"db_name": self.database_name, "db_password": SECRET, "encryption_key": SECRET}
        self.paths["site_config"].write_text(json.dumps(self.config))
        self.public = [{"name": "./frontend/public/files/", "type": tarfile.DIRTYPE}]
        self.private = [{"name": "./frontend/private/files/", "type": tarfile.DIRTYPE},
                        {"name": "./frontend/private/files/" + SECRET + ".txt", "payload": SECRET.encode()}]
        self.auth = [{"name": name, "mode": 0o600, "payload": SECRET.encode()}
                     for name in ("hbos_feishu_app_secret", "hbos_feishu_tenant_key")]
        self.paths["public_files"].write_bytes(archive_bytes(self.public))
        self.paths["private_files"].write_bytes(archive_bytes(self.private))
        self.paths["auth_files"].write_bytes(archive_bytes(self.auth, compressed=True))
        self.before = {"site": "frontend", "database_fingerprint": self.database_hash,
                       "installed_apps": list(APP_NAMES), "user_count": 18,
                       "user_fingerprint": "1" * 64, "credential_fingerprint": "2" * 64,
                       "role_fingerprint": "3" * 64, "permission_fingerprint": "4" * 64,
                       "business_association_fingerprint": "5" * 64, "identity_fingerprint": "6" * 64,
                       "identity_table_present": True, "business_counts": {"Employee": 0},
                       "encryption_key_present": True, "legacy_feishu_social_keys": 0, "csrf_enabled": True}
        self.before_path = self.directory / "before.json"
        self.before_path.write_text(json.dumps(self.before))
        self.manifest = {key: str(path) for key, path in self.paths.items()}
        self.manifest_path = self.directory / "host-backup-prepared.json"
        self.manifest_path.write_text(json.dumps(self.manifest))
        for path in (*self.paths.values(), self.before_path, self.manifest_path):
            path.chmod(0o600)
        self.refresh_expected()

    def refresh_expected(self):
        self.expected = {key: {"sha256": sha(path.read_bytes()), "bytes": path.stat().st_size}
                         for key, path in self.paths.items()}
        self.before_hash = sha(self.before_path.read_bytes())
        self.manifest_hash = sha(self.manifest_path.read_bytes())

    def validate(self, **kwargs):
        return inputs.validate_backup_inputs(kwargs.get("manifest_path", self.manifest_path),
            kwargs.get("expected", self.expected), kwargs.get("before_hash", self.before_hash),
            kwargs.get("manifest_hash", self.manifest_hash))

    def assert_rejected(self, code=None, **kwargs):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error), self.assertRaises(RestoreError) as caught:
            self.validate(**kwargs)
        self.assertRegex(str(caught.exception), r"\A[A-Z][A-Z0-9_]{2,80}\Z")
        if code:
            self.assertEqual(str(caught.exception), code)
        for text in (str(caught.exception), output.getvalue(), error.getvalue()):
            self.assertNotIn(SECRET, text)
            self.assertNotIn(str(self.directory), text)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(error.getvalue(), "")

    def replace_archive(self, component, entries, **kwargs):
        self.paths[component].write_bytes(archive_bytes(entries, compressed=component == "auth_files", **kwargs))
        self.refresh_expected()

    def replace_manifest(self, value):
        self.manifest_path.write_text(json.dumps(value))
        self.refresh_expected()

    def replace_before(self, value):
        self.before_path.write_text(json.dumps(value))
        self.refresh_expected()

    def test_validated_only_sanitized_and_no_files_written(self):
        before = {str(path): (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in self.directory.iterdir()}
        result = self.validate()
        self.assertEqual(result["status"], "VALIDATED_ONLY")
        self.assertEqual(result["landing"], "NOT_IMPLEMENTED")
        self.assertEqual(result["components"]["private_files"]["files"], 1)
        self.assertEqual(result["components"]["auth_files"]["files"], 2)
        self.assertEqual(result["components"]["private_files"]["file_hashes"][0]["sha256"], sha(SECRET.encode()))
        for value in (SECRET, self.database_name, str(self.directory), "hbos_feishu_app_secret"):
            self.assertNotIn(value, json.dumps(result))
        after = {str(path): (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in self.directory.iterdir()}
        self.assertEqual(before, after)

    def test_manifest_hash_optional(self):
        self.assertEqual(self.validate(manifest_hash=None)["status"], "VALIDATED_ONLY")

    def test_manifest_hash_mismatch(self):
        self.assert_rejected("MANIFEST_HASH_MISMATCH", manifest_hash="0" * 64)

    def test_before_hash_mismatch(self):
        self.assert_rejected("BEFORE_HASH_MISMATCH", before_hash="0" * 64)

    def test_double_root_prefix_rejected(self):
        self.assert_rejected("INPUT_PATH_INVALID", manifest_path=Path("/" + str(self.manifest_path)))
        self.replace_manifest({**self.manifest, "database": "/" + str(self.paths["database"])})
        self.assert_rejected("MANIFEST_PATH_INVALID")

    def test_component_hash_and_bytes_mismatch(self):
        for field, value in (("sha256", "0" * 64), ("bytes", self.expected["database"]["bytes"] + 1)):
            expected = {key: dict(item) for key, item in self.expected.items()}
            expected["database"][field] = value
            with self.subTest(field=field):
                self.assert_rejected("COMPONENT_HASH_MISMATCH", expected=expected)

    def test_expectation_types_and_keys(self):
        for value in ([], {}, {**self.expected, "secret": SECRET}):
            self.assert_rejected("INPUT_EXPECTATION_INVALID", expected=value)
        expected = {key: dict(item) for key, item in self.expected.items()}
        expected["database"]["bytes"] = True
        self.assert_rejected("INPUT_EXPECTATION_INVALID", expected=expected)

    def test_manifest_exact_five_strings(self):
        for value in ({**self.manifest, "secret": SECRET}, {**self.manifest, "database": {"path": SECRET}},
                      {key: value for key, value in self.manifest.items() if key != "database"}):
            self.replace_manifest(value)
            self.assert_rejected("MANIFEST_SCHEMA_INVALID")

    def test_manifest_native_relative_escape_alias_and_reuse(self):
        for value in ("/home/frappe/frappe-bench/sites/frontend/private/backups/" + SECRET,
                      "database.input", str(self.directory / "child" / ".." / "database.input"),
                      str(self.before_path), str(self.paths["site_config"]), str(self.directory) + "//database.input"):
            self.replace_manifest({**self.manifest, "database": value})
            self.assert_rejected("MANIFEST_PATH_INVALID")

    def test_duplicate_json_keys(self):
        self.manifest_path.write_text('{"database":"' + SECRET + '","database":"' + SECRET + '"}')
        self.refresh_expected()
        self.assert_rejected("INPUT_JSON_INVALID")

    def test_json_decode_type_and_nonfinite_no_leak(self):
        for raw in (b'[]', b'{"secret":NaN}', b'{"secret":1e10000}', b'{"secret":"\xff"}', b'{"secret":'):
            self.manifest_path.write_bytes(raw)
            self.refresh_expected()
            self.assert_rejected("INPUT_JSON_INVALID")

    def test_staging_permissions_and_owner(self):
        self.directory.chmod(0o755)
        self.assert_rejected("STAGING_PERMISSIONS_INVALID")
        self.directory.chmod(0o700)
        with patch.object(inputs.os, "geteuid", return_value=os.geteuid() + 1):
            self.assert_rejected("STAGING_PERMISSIONS_INVALID")

    def test_file_modes(self):
        for path in (self.manifest_path, self.before_path, self.paths["database"]):
            path.chmod(0o644)
            self.assert_rejected("INPUT_FILE_IDENTITY_INVALID")
            path.chmod(0o600)

    def test_hardlink_and_symlink(self):
        alias = self.directory / "hardlink"
        os.link(self.paths["database"], alias)
        self.assert_rejected("INPUT_FILE_IDENTITY_INVALID")
        alias.unlink()
        self.paths["database"].unlink()
        self.paths["database"].symlink_to(self.paths["site_config"])
        self.assert_rejected("INPUT_FILE_INVALID")

    def test_ancestor_symlink(self):
        with tempfile.TemporaryDirectory(prefix="hbos-synthetic-parent-") as temporary:
            alias = Path(temporary).resolve() / "alias"
            alias.symlink_to(self.directory, target_is_directory=True)
            self.assert_rejected("INPUT_PATH_INVALID", manifest_path=alias / self.manifest_path.name)

    def test_fifo_without_blocking(self):
        self.paths["database"].unlink()
        os.mkfifo(self.paths["database"], mode=0o600)
        self.assert_rejected("INPUT_FILE_IDENTITY_INVALID")

    def test_earlier_database_mutation_during_last_archive_is_rejected(self):
        original = inputs._archive_metadata
        def metadata(stream, component):
            result = original(stream, component)
            if component == "auth_files":
                raw = self.paths["database"].read_bytes()
                self.paths["database"].write_bytes(b"!" + raw[1:])
            return result
        with patch.object(inputs, "_archive_metadata", side_effect=metadata):
            self.assert_rejected("INPUT_CHANGED")

    def test_earlier_manifest_mutation_during_last_archive_is_rejected(self):
        original = inputs._archive_metadata
        def metadata(stream, component):
            result = original(stream, component)
            if component == "auth_files":
                raw = self.manifest_path.read_bytes()
                self.manifest_path.write_bytes(b"!" + raw[1:])
            return result
        with patch.object(inputs, "_archive_metadata", side_effect=metadata):
            self.assert_rejected("INPUT_CHANGED")

    def test_file_mutation_detected_after_hash(self):
        original = inputs._fingerprint
        changed = False
        def fingerprint(stream, limit):
            nonlocal changed
            result = original(stream, limit)
            if not changed:
                changed = True
                metadata = self.paths["database"].stat()
                os.utime(self.paths["database"], ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1_000_000_000))
            return result
        with patch.object(inputs, "_fingerprint", side_effect=fingerprint):
            self.assert_rejected("INPUT_CHANGED")

    def test_file_replacement_detected_after_hash(self):
        original = inputs._fingerprint
        changed = False
        def fingerprint(stream, limit):
            nonlocal changed
            result = original(stream, limit)
            if not changed:
                changed = True
                replacement = self.directory / "replacement"
                replacement.write_bytes(self.paths["database"].read_bytes())
                replacement.chmod(0o600)
                replacement.replace(self.paths["database"])
            return result
        with patch.object(inputs, "_fingerprint", side_effect=fingerprint):
            self.assert_rejected("INPUT_CHANGED")

    def test_before_schema_types_apps_security(self):
        cases = [("user_count", True, "BEFORE_SCHEMA_INVALID"),
                 ("identity_table_present", 1, "BEFORE_SCHEMA_INVALID"),
                 ("business_counts", {"Employee": True}, "BEFORE_SCHEMA_INVALID"),
                 ("installed_apps", ["frappe"], "BEFORE_SCHEMA_INVALID"),
                 ("database_fingerprint", "0" * 64, "BEFORE_SCHEMA_INVALID"),
                 ("csrf_enabled", False, "BEFORE_SECURITY_GATE_INVALID"),
                 ("encryption_key_present", False, "BEFORE_SECURITY_GATE_INVALID"),
                 ("legacy_feishu_social_keys", 1, "BEFORE_SECURITY_GATE_INVALID")]
        for key, value, code in cases:
            self.replace_before({**self.before, key: value})
            self.assert_rejected(code)

    def test_config_fixed_database_and_string_key(self):
        for value in ({**self.config, "db_name": SECRET}, {**self.config, "encryption_key": ""},
                      {**self.config, "encryption_key": True}, {**self.config, "db_name": None}):
            self.paths["site_config"].write_text(json.dumps(value))
            self.refresh_expected()
            self.assert_rejected("SITE_CONFIG_GATE_INVALID")

    def test_config_lone_surrogate_fixed_code(self):
        self.paths["site_config"].write_text(json.dumps({**self.config, "db_name": "\ud800"}))
        self.refresh_expected()
        self.assert_rejected("SITE_CONFIG_GATE_INVALID")

    def test_gzip_crc_truncation_non_gzip(self):
        original = self.paths["database"].read_bytes()
        bad = bytearray(original)
        bad[-8] ^= 1
        for raw in (bytes(bad), original[:-3], SECRET.encode()):
            self.paths["database"].write_bytes(raw)
            self.refresh_expected()
            self.assert_rejected("GZIP_INVALID")

    def test_gzip_expansion_limit(self):
        with patch.object(inputs, "MAX_EXPANDED_BYTES", 8):
            self.assert_rejected("GZIP_EXPANSION_LIMIT")

    def test_size_limits(self):
        with patch.object(inputs, "MAX_INPUT_BYTES", 1):
            self.assert_rejected("INPUT_EXPECTATION_INVALID")
        with patch.object(inputs, "MAX_MANIFEST_BYTES", 1):
            self.assert_rejected("INPUT_SIZE_INVALID")

    def test_tar_paths_and_canonical_duplicates(self):
        for name in ("/frontend/public/files/" + SECRET, "././frontend/public/files/x",
                     "./frontend/public/files/../" + SECRET, "./frontend/public/files//x",
                     "./frontend/private/files/x", "./frontend/public/files/", "", "./frontend/public/files/a\\b"):
            self.replace_archive("public_files", [{"name": name, "payload": SECRET.encode()}])
            self.assert_rejected("TAR_PATH_INVALID")
        self.replace_archive("public_files", self.public + [{"name": "frontend/public/files", "type": tarfile.DIRTYPE}])
        self.assert_rejected("TAR_DUPLICATE_PATH")

    def test_tar_links_special_and_contiguous_types(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE, tarfile.CONTTYPE):
            self.replace_archive("public_files", [{"name": "./frontend/public/files/x", "type": kind, "linkname": "../" + SECRET}])
            self.assert_rejected("TAR_TYPE_INVALID")

    def test_tar_owner_and_modes(self):
        for field, value, code in (("uid", 0, "TAR_OWNER_INVALID"), ("gid", 0, "TAR_OWNER_INVALID"),
                                   ("mode", 0o666, "TAR_MODE_INVALID"), ("mode", 0o4755, "TAR_MODE_INVALID")):
            self.replace_archive("public_files", [{"name": "./frontend/public/files/x", field: value}])
            self.assert_rejected(code)
        self.replace_archive("public_files", self.public)
        self.replace_archive("auth_files", [{**entry, "mode": 0o644} for entry in self.auth])
        self.assert_rejected("TAR_MODE_INVALID")

    def test_tar_member_payload_and_total_quotas(self):
        for name, limit, code in (("MAX_MEMBERS", 1, "TAR_MEMBER_LIMIT"), ("MAX_MEMBER_BYTES", 1, "TAR_SIZE_INVALID"),
                                 ("MAX_ARCHIVE_PAYLOAD_BYTES", 1, "TAR_PAYLOAD_LIMIT"),
                                 ("MAX_TOTAL_PAYLOAD_BYTES", 1, "TAR_TOTAL_LIMIT"), ("MAX_TOTAL_MEMBERS", 1, "TAR_TOTAL_LIMIT")):
            with patch.object(inputs, name, limit):
                self.assert_rejected(code)

    def test_tar_file_ancestor_conflict(self):
        for entries in ([{"name": "./frontend/public/files/a"}, {"name": "./frontend/public/files/a/b"}],
                        [{"name": "./frontend/public/files/a/b"}, {"name": "./frontend/public/files/a"}]):
            self.replace_archive("public_files", entries)
            self.assert_rejected("TAR_PATH_CONFLICT")

    def test_tar_header_padding_and_trailer_corruption(self):
        original = self.paths["private_files"].read_bytes()
        bad_header, bad_padding = bytearray(original), bytearray(original)
        bad_header[0] ^= 1
        bad_padding[1024 + len(SECRET.encode())] = 1
        for raw, code in ((bytes(bad_header), "TAR_INVALID"), (bytes(bad_padding), "TAR_INVALID"),
                          (original + b"x" * 512, "TAR_TRAILER_INVALID"), (original[:-1], "TAR_INVALID")):
            self.paths["private_files"].write_bytes(raw)
            self.refresh_expected()
            self.assert_rejected(code)

    def test_pax_mtime_supported_other_overrides_rejected(self):
        self.replace_archive("public_files", [{"name": "./frontend/public/files/x", "mtime": 1_700_000_000.25}])
        self.assertEqual(self.validate()["status"], "VALIDATED_ONLY")
        for pax in ({"uid": "1000"}, {"path": "./frontend/public/files/other"},
                    {"SCHILY.xattr.secret": SECRET}, {"mtime": "NaN"}, {"mtime": "-1"}):
            self.replace_archive("public_files", [{"name": "./frontend/public/files/x", "pax": pax}])
            self.assert_rejected("TAR_PAX_INVALID")

    def test_global_pax_rejected(self):
        self.replace_archive("public_files", self.public, global_pax={"mtime": "1700000000.25"})
        self.assert_rejected("TAR_PAX_INVALID")

    def test_auth_two_or_three_names_and_crc(self):
        self.replace_archive("auth_files", self.auth + [{"name": "hbos_knowledge_gateway_token", "mode": 0o600}])
        self.assertEqual(self.validate()["components"]["auth_files"]["files"], 3)
        self.replace_archive("auth_files", self.auth[:1])
        self.assert_rejected("AUTH_ARCHIVE_INVALID")
        self.replace_archive("auth_files", self.auth + [{"name": SECRET, "mode": 0o600}])
        self.assert_rejected("TAR_PATH_INVALID")
        self.replace_archive("auth_files", self.auth)
        payload = bytearray(self.paths["auth_files"].read_bytes())
        payload[-8] ^= 1
        self.paths["auth_files"].write_bytes(payload)
        self.refresh_expected()
        self.assert_rejected("GZIP_INVALID")


if __name__ == "__main__":
    unittest.main()
