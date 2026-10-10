"""Native source binding/current-read contract without Frappe or database I/O."""
from copy import deepcopy
import hashlib
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.frappe_repository import FrappeRelationRepository
from hbos_portal.organization.frappe_source_loader import FrappeLockedSourceLoader
from hbos_portal.organization.storage_schema import LOCK_KEY, POSITION
from tests.test_organization_source_adapter import sources, STAMP


class NativeSourceLoaderTests(unittest.TestCase):
    def setUp(self):
        self.rows = sources()
        self.database = "synthetic-db"
        self.isolation = "REPEATABLE-READ"
        self.engine = "InnoDB"
        self.native = SimpleNamespace(local=SimpleNamespace(site="synthetic-site"), conf={},
                                      db=Mock(), get_all=Mock(), get_doc=Mock())
        self.native.db.sql.side_effect = self.query
        self.repo = FrappeRelationRepository(native=self.native, enabled=True)
        self.loader = FrappeLockedSourceLoader(self.repo, enabled=True, expected_site="synthetic-site",
            expected_database_sha256=hashlib.sha256(self.database.encode()).hexdigest())

    def query(self, sql, values=None, **options):
        if sql == "SELECT DATABASE(), @@tx_isolation":
            return [(self.database, self.isolation)]
        if "information_schema.tables" in sql:
            return [(table, self.engine) for table in values]
        if "FROM `tabHBOS Organization Write Lock`" in sql:
            return [(LOCK_KEY,)]
        for kind, rows in self.rows.items():
            if f"FROM `tab{kind}`" in sql:
                return deepcopy(rows)
        self.fail("Unexpected SQL")

    def assert_code(self, code, action):
        with self.assertRaises(ContractError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def locked_call(self):
        with self.repo.transaction():
            self.repo.lock_writer()
            return self.loader()

    def test_default_disabled_before_any_native_access(self):
        loader = FrappeLockedSourceLoader(self.repo)
        self.assert_code("SOURCE_READS_DISABLED", loader)
        self.native.db.sql.assert_not_called()
        self.native.db.savepoint.assert_not_called()

    def test_explicit_server_bindings_required(self):
        for site, fingerprint in ((None, None), (" site ", "f"*64), ("site", "unknown")):
            loader = FrappeLockedSourceLoader(self.repo, enabled=True, expected_site=site,
                                              expected_database_sha256=fingerprint)
            self.assert_code("SOURCE_BINDING_REQUIRED", loader)
        self.native.db.sql.assert_not_called()

    def test_active_repository_transaction_and_writer_lock_required(self):
        self.assert_code("SOURCE_TRANSACTION_REQUIRED", self.loader)
        with self.repo.transaction():
            self.assert_code("SOURCE_TRANSACTION_REQUIRED", self.loader)
            self.repo.lock_writer()
            self.assertTrue(self.loader().employee_links_complete)
        self.assert_code("SOURCE_TRANSACTION_REQUIRED", self.loader)

    def test_site_and_database_cannot_be_substituted(self):
        self.loader.expected_site = "other-site"
        self.assert_code("SOURCE_SITE_MISMATCH", self.locked_call)
        self.loader.expected_site = "synthetic-site"
        self.database = "other-db"
        self.assert_code("SOURCE_DATABASE_MISMATCH", self.locked_call)

    def test_driver_isolation_and_nontransactional_engine_rejected(self):
        self.native.conf["db_type"] = "postgres"
        self.assert_code("UNSUPPORTED_SOURCE_DATABASE", self.locked_call)
        self.native.conf.clear()
        self.isolation = "READ-COMMITTED"
        self.assert_code("UNSUPPORTED_SOURCE_ISOLATION", self.locked_call)
        self.isolation = "REPEATABLE-READ"
        self.engine = "MyISAM"
        self.assert_code("UNSUPPORTED_SOURCE_ENGINE", self.locked_call)

    def test_full_fixed_ranges_current_read_in_lock_order_without_pages_or_caches(self):
        result = self.locked_call()
        selects = [call.args[0] for call in self.native.db.sql.call_args_list
                   if "ORDER BY name FOR UPDATE" in call.args[0]]
        self.assertEqual(len(selects), 5)
        for sql, kind in zip(selects, self.rows):
            self.assertIn(f"FROM `tab{kind}`", sql)
            self.assertNotIn("LIMIT", sql)
        self.native.get_all.assert_not_called()
        self.assertTrue(result.validation_only)
        self.assertFalse(result.runtime_verified)
        self.assertEqual(result.context.provider_id, "hbos_portal.native_locked.v1")

    def test_missing_native_modified_fails_without_fabricating_freshness(self):
        self.rows["User"][0]["modified"] = None
        self.assert_code("INVALID_SOURCE_MODIFIED", self.locked_call)

    def test_each_load_reads_current_selected_rows_without_snapshot_cache(self):
        with self.repo.transaction():
            self.repo.lock_writer()
            first = self.loader()
            self.rows["Employee"][0]["status"] = "Left"
            second = self.loader()
        self.assertEqual(first.rows["Employee"]["SYNTHETIC-EMP"]["status"], "Active")
        self.assertEqual(second.rows["Employee"]["SYNTHETIC-EMP"]["status"], "Left")

    def test_scope_revoked_on_failure_and_nested_scope_restores_outer_lock(self):
        with self.repo.transaction():
            self.repo.lock_writer()
            with self.assertRaises(RuntimeError):
                with self.repo.transaction():
                    self.assert_code("SOURCE_TRANSACTION_REQUIRED", self.loader)
                    self.repo.lock_writer()
                    raise RuntimeError("synthetic")
            self.assertTrue(self.loader().employee_links_complete)
        self.assert_code("SOURCE_TRANSACTION_REQUIRED", self.loader)

    def test_database_connection_or_site_swap_invalidates_context(self):
        original = self.native.db
        with self.repo.transaction():
            self.repo.lock_writer()
            self.native.db = Mock()
            self.assert_code("SOURCE_TRANSACTION_REQUIRED", self.loader)
            self.native.db = original
            self.native.local.site = "other-site"
            self.assert_code("SOURCE_TRANSACTION_REQUIRED", self.loader)
            self.native.local.site = "synthetic-site"

    def test_aborted_transaction_uses_full_rollback_and_preserves_retry_cause(self):
        class QueryDeadlockError(Exception): pass
        self.native.QueryDeadlockError = QueryDeadlockError
        original = QueryDeadlockError("synthetic snapshot conflict")
        with self.assertRaises(ContractError) as caught:
            with self.repo.transaction():
                self.repo.lock_writer()
                raise original
        self.assertEqual(caught.exception.code, "RELATION_TRANSACTION_RETRY_REQUIRED")
        self.assertIs(caught.exception.__cause__, original)
        self.native.db.rollback.assert_called_once_with()
        self.assert_code("SOURCE_TRANSACTION_REQUIRED", self.loader)
        self.assertTrue(self.locked_call().employee_links_complete)

    def test_caught_nested_abort_cannot_restore_outer_source_lock_or_succeed(self):
        class QueryDeadlockError(Exception): pass
        self.native.QueryDeadlockError = QueryDeadlockError
        with self.assertRaises(ContractError) as caught:
            with self.repo.transaction():
                self.repo.lock_writer()
                with self.assertRaises(ContractError):
                    with self.repo.transaction():
                        self.repo.lock_writer()
                        raise QueryDeadlockError("synthetic")
                self.repo.lock_writer()
                self.assert_code("SOURCE_TRANSACTION_REQUIRED", self.loader)
        self.assertEqual(caught.exception.code, "RELATION_TRANSACTION_RETRY_REQUIRED")
        self.native.db.rollback.assert_called_once_with()

    def test_relationship_and_receipt_reads_are_current_with_parameterized_ids(self):
        record = {"record_key": "synthetic", "modified": STAMP}
        self.native.db.sql.side_effect = None
        self.native.db.sql.return_value = [record]
        self.assertEqual(self.repo.get_master(POSITION, "x' OR 1=1")["_source_modified"], STAMP)
        sql, values = self.native.db.sql.call_args.args
        self.assertIn("FOR UPDATE", sql)
        self.assertNotIn("OR 1=1", sql)
        self.assertEqual(values, ("x' OR 1=1",))
        self.native.db.sql.return_value = [{"request_digest": "synthetic", "result_json": "{}"}]
        self.assertEqual(self.repo.get_receipt("synthetic")["result"], {})
        self.assertIn("FOR UPDATE", self.native.db.sql.call_args.args[0])
        self.assert_code("UNSUPPORTED_SOURCE", lambda: self.repo.get_master("arbitrary", "synthetic"))


if __name__ == "__main__":
    unittest.main()
