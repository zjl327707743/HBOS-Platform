"""Offline structural diagnostics; the fake DB has only SELECT capability."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.management_preflight import preflight_management_structure


SITE = "synthetic-structure.localhost"
DATABASE = "SYNTHETIC-PRIVATE-DATABASE"
DATABASE_HASH = hashlib.sha256(DATABASE.encode()).hexdigest()
SLUGS = (
    "hbos_position", "hbos_personnel_assignment", "hbos_position_revision",
    "hbos_personnel_assignment_revision", "hbos_organization_command_receipt",
    "hbos_organization_write_lock", "hbos_organization_management_policy",
    "hbos_organization_management_policy_revision",
)
NATIVE_FIELDS = {
    "User": {"name": "varchar", "enabled": "int", "user_type": "varchar", "modified": "datetime"},
    "Employee": {
        "name": "varchar", "employee_name": "varchar", "user_id": "varchar", "company": "varchar",
        "department": "varchar", "designation": "varchar", "status": "varchar",
        "date_of_joining": "date", "relieving_date": "date", "modified": "datetime",
    },
    "Company": {"name": "varchar", "modified": "datetime"},
    "Department": {"name": "varchar", "company": "varchar", "parent_department": "varchar",
                   "is_group": "int", "disabled": "int", "modified": "datetime"},
    "Designation": {"name": "varchar", "modified": "datetime"},
}
SQL_TYPES = {"Data": "varchar", "Link": "varchar", "Select": "varchar", "Int": "int",
             "Check": "int", "Datetime": "datetime", "Long Text": "longtext", "Small Text": "text"}


def schema_fixture():
    # The repository's actual eight DocType JSON sources independently define
    # the fixture. An omitted preflight field cannot silently remove the test
    # fixture's corresponding physical source field.
    base = Path(__file__).resolve().parents[1] / "hbos_portal" / "hbos_portal" / "doctype"
    columns, indexes, doctypes, tables = [], [], [], []
    for slug in SLUGS:
        spec = json.loads((base / slug / (slug + ".json")).read_text())
        name, table = spec["name"], "tab" + spec["name"]
        fields = {"name": "varchar", "modified": "datetime"}
        fields.update({f["fieldname"]: SQL_TYPES[f["fieldtype"]] for f in spec["fields"]})
        tables.append({"table_name": table, "engine": "InnoDB"})
        columns.extend({"table_name": table, "column_name": key, "data_type": value,
                        "datetime_precision": 6 if value == "datetime" else None}
                       for key, value in fields.items())
        unique = {"name"} | {f["fieldname"] for f in spec["fields"] if f.get("unique")}
        indexes.extend({"table_name": table, "index_name": key + "_unique", "column_name": key,
                        "non_unique": 0, "seq_in_index": 1, "sub_part": None} for key in sorted(unique))
        doctypes.append({"name": name, "module": spec["module"], "autoname": spec["autoname"],
                         "allow_import": spec["allow_import"], "allow_rename": spec["allow_rename"]})
    for name, fields in NATIVE_FIELDS.items():
        table = "tab" + name
        tables.append({"table_name": table, "engine": "InnoDB"})
        columns.extend({"table_name": table, "column_name": key, "data_type": value,
                        "datetime_precision": 6 if value == "datetime" else None}
                       for key, value in fields.items())
    return tables, columns, indexes, doctypes


class SelectOnlyDB:
    def __init__(self):
        self.tables, self.columns, self.indexes, self.doctypes = schema_fixture()
        self.database, self.isolation = DATABASE, "REPEATABLE-READ"
        self.identity = None
        self.docperm, self.custom_docperm, self.setters, self.custom_fields = [], [], [], []
        self.roots = [{"name": "relations-v1", "record_key": "relations-v1"}]
        self.calls, self.fail_on = [], None

    def sql(self, statement, values=(), *, as_dict=False):
        if not statement.startswith("SELECT ") or "FOR UPDATE" in statement:
            raise AssertionError("This fixture cannot write or own transactions")
        self.calls.append((statement, values, as_dict))
        if self.fail_on is not None and self.fail_on in statement:
            raise RuntimeError("SYNTHETIC-PRIVATE-SQL-ERROR " + DATABASE)
        if statement == "SELECT DATABASE(), @@tx_isolation":
            return deepcopy(self.identity if self.identity is not None else [(self.database, self.isolation)])
        for marker, rows in (
            ("information_schema.tables", self.tables), ("information_schema.columns", self.columns),
            ("information_schema.statistics", self.indexes), ("FROM `tabDocType`", self.doctypes),
            ("FROM `tabDocPerm`", self.docperm), ("FROM `tabCustom DocPerm`", self.custom_docperm),
            ("FROM `tabProperty Setter`", self.setters), ("FROM `tabCustom Field`", self.custom_fields),
            ("FROM `tabHBOS Organization Write Lock`", self.roots),
        ):
            if marker in statement:
                return deepcopy(rows)
        raise AssertionError("Unexpected SQL, including policies or personnel records")


class ManagementPreflightTest(unittest.TestCase):
    def setUp(self):
        self.db = SelectOnlyDB()
        self.native = SimpleNamespace(local=SimpleNamespace(site=SITE, db=self.db), conf={"db_type": "mariadb"})

    def run_preflight(self, **binding):
        return preflight_management_structure(self.native, expected_site=binding.get("expected_site", SITE),
            expected_database_sha256=binding.get("expected_database_sha256", DATABASE_HASH))

    def assert_code(self, code, *, path=None, **binding):
        with self.assertRaises(ContractError) as caught:
            self.run_preflight(**binding)
        self.assertEqual(caught.exception.code, code)
        if path is not None:
            self.assertEqual(caught.exception.path, path)
        self.assertNotIn(DATABASE, str(caught.exception))
        return caught.exception

    def column(self, table, field):
        return next(row for row in self.db.columns if row["table_name"] == table and row["column_name"] == field)

    def test_valid_structure_does_not_claim_production_authority_or_runtime_checks(self):
        result = self.run_preflight()
        self.assertTrue(result["structure_validated"])
        self.assertTrue(result["root_lock_validated"])
        self.assertFalse(result["production_ready"])
        self.assertTrue(result["read_only"])
        self.assertFalse(result["runtime_verified"])
        self.assertEqual(result["authorization_effect"], "none")
        self.assertFalse(result["position_authorization_connected"])
        self.assertEqual(result["managed_tables_checked"], 8)
        self.assertEqual(result["native_tables_checked"], 5)
        for check in ("policy", "runtime_hooks", "origin", "restore"):
            self.assertEqual(result[check], "NOT_RUN")
        self.assertNotIn(DATABASE, json.dumps(result))

    def test_invalid_binding_is_rejected_without_a_database_call(self):
        for binding in ({"expected_site": ""}, {"expected_site": " " + SITE}, {"expected_site": None},
                        {"expected_site": "x" * 141}, {"expected_database_sha256": "0" * 63},
                        {"expected_database_sha256": "A" * 64}, {"expected_database_sha256": False}):
            with self.subTest(binding=binding):
                self.assert_code("SOURCE_PREFLIGHT_BINDING_REQUIRED", **binding)
        self.assertEqual(self.db.calls, [])

    def test_actual_site_and_database_type_are_checked_before_database_access(self):
        self.native.local.site = "synthetic-other-site"
        self.assert_code("SOURCE_PREFLIGHT_TARGET_MISMATCH")
        self.native.local.site = SITE
        self.native.conf["db_type"] = "postgres"
        self.assert_code("SOURCE_PREFLIGHT_DATABASE_UNSUPPORTED")
        self.assertEqual(self.db.calls, [])

    def test_missing_bound_native_database_does_not_create_a_connection(self):
        self.native.local.db = None
        self.assert_code("SOURCE_PREFLIGHT_CONTEXT_REQUIRED")
        self.assertEqual(self.db.calls, [])

    def test_database_hash_mismatch_stops_before_schema_or_root_reads(self):
        self.db.database = "synthetic-other-database"
        self.assert_code("SOURCE_PREFLIGHT_TARGET_MISMATCH")
        self.assertEqual(len(self.db.calls), 1)

    def test_wrong_isolation_stops_before_schema_or_root_reads(self):
        for isolation in ("READ-COMMITTED", "SERIALIZABLE", None):
            with self.subTest(isolation=isolation):
                self.db.calls = []
                self.db.isolation = isolation
                self.assert_code("SOURCE_PREFLIGHT_DATABASE_UNSUPPORTED")
                self.assertEqual(len(self.db.calls), 1)

    def test_malformed_native_identity_response_is_closed(self):
        for rows in ([], [(DATABASE,)], [(DATABASE, "REPEATABLE-READ", "extra")],
                     [(None, "REPEATABLE-READ")], [(DATABASE, "REPEATABLE-READ")] * 2):
            with self.subTest(rows=rows):
                self.db.identity, self.db.calls = rows, []
                self.assert_code("SOURCE_PREFLIGHT_CONTEXT_REQUIRED")
                self.assertEqual(len(self.db.calls), 1)

    def test_every_managed_and_native_table_must_exist(self):
        original = deepcopy(self.db.tables)
        for table in original:
            with self.subTest(table=table["table_name"]):
                self.db.tables = [row for row in original if row["table_name"] != table["table_name"]]
                self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.tables")

    def test_non_innodb_and_duplicate_table_metadata_are_refused(self):
        self.db.tables[0]["engine"] = "MyISAM"
        self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.tables")
        self.db.tables[0]["engine"] = "InnoDB"
        self.db.tables.append(deepcopy(self.db.tables[0]))
        self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.tables")

    def test_missing_physical_source_or_storage_column_is_not_an_empty_success(self):
        original = deepcopy(self.db.columns)
        for table, column in (("tabEmployee", "employee_name"), ("tabEmployee", "date_of_joining"),
                              ("tabUser", "modified"), ("tabHBOS Position", "source_key"),
                              ("tabHBOS Organization Management Policy", "policy_json"),
                              ("tabHBOS Personnel Assignment", "valid_until_utc")):
            with self.subTest(table=table, column=column):
                self.db.columns = [row for row in original if (row["table_name"], row["column_name"]) != (table, column)]
                self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.columns")

    def test_storage_integer_text_and_native_date_types_are_explicit(self):
        for table, field, bad_type in (("tabHBOS Position", "revision", "decimal"),
                                     ("tabHBOS Position", "authorization_generation", "varchar"),
                                     ("tabHBOS Organization Management Policy", "schema_version", "float"),
                                     ("tabHBOS Organization Management Policy", "policy_json", "varchar"),
                                     ("tabHBOS Position Revision", "reason", "int"),
                                     ("tabEmployee", "date_of_joining", "datetime")):
            with self.subTest(table=table, field=field):
                row = self.column(table, field)
                original, row["data_type"] = row["data_type"], bad_type
                self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.columns")
                row["data_type"] = original

    def test_all_explicit_utc_columns_require_datetime_microseconds(self):
        utc = [row for row in self.db.columns if row["column_name"].endswith("_utc")]
        self.assertTrue(utc)
        for row in utc:
            for precision in (None, 0, 3, 5, True):
                with self.subTest(field=row["column_name"], precision=precision):
                    row["datetime_precision"] = precision
                    self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.utc_precision")
            row["datetime_precision"] = 6
        utc[0]["data_type"] = "timestamp"
        self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.columns")

    def test_composite_unique_columns_cannot_replace_a_single_column_unique(self):
        table = "tabHBOS Position"
        self.db.indexes = [row for row in self.db.indexes if not (row["table_name"] == table and row["column_name"] == "record_key")]
        self.db.indexes.extend({"table_name": table, "index_name": "composite_only", "column_name": column,
                                "seq_in_index": i, "non_unique": 0, "sub_part": None}
                               for i, column in enumerate(("name", "record_key"), 1))
        self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.indexes")

    def test_prefix_nonunique_or_wrong_sequence_indexes_do_not_count_as_unique(self):
        row = next(row for row in self.db.indexes if row["column_name"] == "record_key")
        for field, invalid in (("sub_part", 20), ("non_unique", 1), ("non_unique", False),
                               ("seq_in_index", 2), ("seq_in_index", True)):
            with self.subTest(field=field, invalid=invalid):
                original, row[field] = row[field], invalid
                self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.indexes")
                row[field] = original

    def test_position_and_assignment_source_key_uniqueness_is_required(self):
        original = deepcopy(self.db.indexes)
        for table in ("tabHBOS Position", "tabHBOS Personnel Assignment"):
            with self.subTest(table=table):
                self.db.indexes = [row for row in original if not (row["table_name"] == table and row["column_name"] == "source_key")]
                self.assert_code("STORAGE_PREFLIGHT_SCHEMA_INVALID", path="preflight.indexes")

    def test_missing_duplicate_or_mutated_doctype_metadata_is_rejected(self):
        original = deepcopy(self.db.doctypes)
        self.db.doctypes.pop()
        self.assert_code("STORAGE_PREFLIGHT_METADATA_INVALID", path="preflight.metadata")
        self.db.doctypes = original + [deepcopy(original[0])]
        self.assert_code("STORAGE_PREFLIGHT_METADATA_INVALID", path="preflight.metadata")
        self.db.doctypes = original
        for key, value in (("module", "synthetic-other-module"), ("autoname", "prompt"),
                           ("allow_import", 1), ("allow_rename", True), ("allow_import", "0"),
                           ("allow_rename", None)):
            with self.subTest(key=key, value=value):
                row = self.db.doctypes[0]
                old, row[key] = row[key], value
                self.assert_code("STORAGE_PREFLIGHT_METADATA_INVALID", path="preflight.metadata")
                row[key] = old

    def test_docperm_and_custom_docperm_rows_are_not_read_or_write_allowances(self):
        for field in ("docperm", "custom_docperm"):
            with self.subTest(field=field):
                setattr(self.db, field, [("HBOS Position",)])
                self.assert_code("STORAGE_PREFLIGHT_METADATA_INVALID", path="preflight.permissions")
                setattr(self.db, field, [])

    def test_any_protected_property_setter_or_custom_field_requires_separate_review(self):
        for field in ("setters", "custom_fields"):
            with self.subTest(field=field):
                # Even a cosmetic override is not silently assumed to be safe.
                setattr(self.db, field, [("HBOS Position",)])
                self.assert_code("STORAGE_PREFLIGHT_METADATA_INVALID", path="preflight.overrides")
                setattr(self.db, field, [])

    def test_root_is_existing_single_row_with_matching_stable_name_and_key(self):
        for rows in ([], [{"name": "relations-v1", "record_key": "synthetic-other"}],
                     [{"name": "synthetic-other", "record_key": "relations-v1"}],
                     [{"name": "relations-v1", "record_key": "relations-v1"}] * 2,
                     [{"name": "relations-v1", "record_key": "relations-v1"},
                      {"name": "synthetic-extra", "record_key": "synthetic-extra"}]):
            with self.subTest(rows=rows):
                self.db.roots = rows
                self.assert_code("STORAGE_PREFLIGHT_ROOT_LOCK_REQUIRED", path="preflight.root_lock")

    def test_sql_failures_are_sanitized_and_never_changed_into_readiness(self):
        for marker in ("SELECT DATABASE()", "information_schema.tables", "information_schema.columns",
                       "information_schema.statistics", "FROM `tabDocType`", "FROM `tabDocPerm`",
                       "FROM `tabCustom DocPerm`", "FROM `tabProperty Setter`", "FROM `tabCustom Field`",
                       "FROM `tabHBOS Organization Write Lock`"):
            with self.subTest(marker=marker):
                self.db.fail_on = marker
                error = self.assert_code("STORAGE_PREFLIGHT_UNAVAILABLE", path="preflight")
                self.assertTrue(error.__suppress_context__)
                self.assertNotIn("SYNTHETIC-PRIVATE-SQL-ERROR", str(error))

    def test_additional_source_columns_do_not_invent_new_required_authority(self):
        self.db.columns.append({"table_name": "tabEmployee", "column_name": "synthetic_future_field",
                                "data_type": "varchar", "datetime_precision": None})
        self.assertFalse(self.run_preflight()["production_ready"])

    def test_preflight_uses_only_fixed_selects_and_reads_no_policy_or_personnel_rows(self):
        self.run_preflight()
        self.assertFalse(hasattr(self.db, "commit"))
        self.assertFalse(hasattr(self.db, "rollback"))
        self.assertFalse(hasattr(self.native, "init"))
        self.assertFalse(hasattr(self.native, "get_meta"))
        self.assertEqual(len(self.db.calls), 10)
        for statement, values, _ in self.db.calls:
            self.assertTrue(statement.startswith("SELECT "))
            for forbidden in ("FOR UPDATE", "SHOW ", "SAVEPOINT", "INSERT ", "UPDATE ", "DELETE ",
                              "CREATE ", "ALTER ", "FROM `tabUser`", "FROM `tabEmployee`",
                              "FROM `tabHBOS Organization Management Policy`"):
                self.assertNotIn(forbidden, statement)
            self.assertNotIn(SITE, statement)
            self.assertNotIn(DATABASE_HASH, statement)


if __name__ == "__main__":
    unittest.main()
