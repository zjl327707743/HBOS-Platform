"""Fail-closed target and backup guards for the explicit Preview CLI."""
import hashlib
import json
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tests import integration_organization_storage as acceptance


class AcceptanceSafetyTests(unittest.TestCase):
    def test_site_flag_expected_fingerprint_and_actual_database_all_must_match(self):
        database = "synthetic-acceptance-database"
        fingerprint = hashlib.sha256(database.encode()).hexdigest()
        native = SimpleNamespace(local=SimpleNamespace(site=acceptance.SITE),
            conf={"hbos_account_test_site": 1}, db=Mock())
        native.db.sql.return_value = [(database, "synthetic-server", "synthetic-version", "REPEATABLE-READ")]
        with patch.object(acceptance, "DB_HASH", fingerprint):
            self.assertEqual(acceptance.check_target(native, fingerprint)["database_sha256"], fingerprint)
            for site, flag, expected, actual_database in (
                ("frontend", 1, fingerprint, database),
                (acceptance.SITE, 0, fingerprint, database),
                (acceptance.SITE, 1, "wrong", database),
                (acceptance.SITE, 1, fingerprint, "other-database"),
            ):
                with self.subTest(site=site, flag=flag, expected=expected, actual=actual_database):
                    native.local.site = site
                    native.conf["hbos_account_test_site"] = flag
                    native.db.sql.return_value = [(actual_database, "server", "version", "isolation")]
                    with self.assertRaisesRegex(RuntimeError, "PREVIEW_TARGET_MISMATCH"):
                        acceptance.check_target(native, expected)

    def test_preflight_rejects_any_business_master_or_additional_user(self):
        for occupied in ("Employee", "Company", "Department", "Designation", "User"):
            def query(sql, *args):
                if sql == "SELECT name FROM `tabUser`":
                    return [("Guest",), ("Administrator",)] + ([("synthetic-user",)] if occupied == "User" else [])
                for kind in acceptance.SOURCE_FIELDS:
                    if sql == f"SELECT COUNT(*) FROM `tab{kind}`":
                        return [(2 if kind == "User" else int(kind == occupied),)]
                self.fail("preflight must reject before schema queries")
            native = SimpleNamespace(db=SimpleNamespace(sql=query))
            with self.subTest(occupied=occupied), self.assertRaisesRegex(RuntimeError, "PREVIEW_NOT_EMPTY"):
                acceptance.preflight(native)

    def test_backup_path_escape_or_incomplete_backup_cannot_be_accepted(self):
        native = SimpleNamespace(get_site_path=Mock())
        for stem in (None, "", "../x-portal-preview_localhost", "/x-portal-preview_localhost", "other-site"):
            with self.subTest(stem=stem), self.assertRaisesRegex(RuntimeError, "BACKUP_STEM_REQUIRED"):
                acceptance.verify_backup(native, stem)
        native.get_site_path.assert_not_called()
        with TemporaryDirectory() as folder:
            native.get_site_path.return_value = folder
            with self.assertRaisesRegex(RuntimeError, "BACKUP_INCOMPLETE"):
                acceptance.verify_backup(native, "synthetic-portal-preview_localhost")

    def test_preservation_fingerprints_hide_rows_and_ignore_query_order(self):
        rows = [{"name": "synthetic-a", "secret": "synthetic-private-value"}, {"name": "synthetic-b"}]
        native = SimpleNamespace(db=Mock())
        native.db.sql.return_value = rows
        first = acceptance.native_fingerprints(native)
        native.db.sql.return_value = list(reversed(rows))
        self.assertEqual(first, acceptance.native_fingerprints(native))
        encoded = json.dumps(first)
        self.assertNotIn("synthetic-private-value", encoded)
        self.assertNotIn("synthetic-a", encoded)
        self.assertEqual(len(first), 8)


if __name__ == "__main__":
    unittest.main()
