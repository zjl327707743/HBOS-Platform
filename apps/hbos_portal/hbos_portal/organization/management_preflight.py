"""SELECT-only structural diagnostics in an already bound native context.

This does not initialize a Site, create a root lock, validate human approval,
load personnel records, refresh hooks, own a transaction or authorize a query.
Each managed request must still perform current policy/source checks under its
root lock. Protected metadata overrides are conservatively unsupported.
"""
import re

from hbos_portal.authorization.errors import ContractError
from .management_storage import POLICY, POLICY_REVISION
from .storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, LOCK_KEY, POSITION, POSITION_REVISION,
    RECEIPT, WRITE_LOCK,
)


_MANAGED_COLUMNS = {
    POSITION: {
        "record_key": "string", "title": "string", "company": "string",
        "department": "string", "designation": "string", "status": "string",
        "revision": "version", "authorization_generation": "version",
        "source_provider": "string", "source_key": "string",
    },
    ASSIGNMENT: {
        "record_key": "string", "person_source_type": "string", "person_source_id": "string",
        "subject_user": "string", "position": "string", "is_primary": "check",
        "valid_from_utc": "utc", "valid_until_utc": "utc", "status": "string",
        "revision": "version", "authorization_generation": "version",
        "source_provider": "string", "source_key": "string",
    },
    POSITION_REVISION: {
        "record_key": "string", "position": "string", "revision": "version",
        "previous_revision": "version", "snapshot_json": "long_text",
        "content_digest": "string", "actor": "string", "policy_ref": "string",
        "reason": "small_text", "source_evidence_json": "long_text", "recorded_at_utc": "utc",
    },
    ASSIGNMENT_REVISION: {
        "record_key": "string", "assignment": "string", "revision": "version",
        "previous_revision": "version", "snapshot_json": "long_text",
        "content_digest": "string", "actor": "string", "policy_ref": "string",
        "reason": "small_text", "source_evidence_json": "long_text", "recorded_at_utc": "utc",
    },
    RECEIPT: {
        "record_key": "string", "site_id": "string", "actor": "string", "command_type": "string",
        "request_key": "string", "request_digest": "string", "result_json": "long_text",
        "recorded_at_utc": "utc",
    },
    WRITE_LOCK: {"record_key": "string"},
    POLICY: {
        "record_key": "string", "site_id": "string", "source_provider": "string",
        "subject_user": "string", "status": "string", "revision": "version",
        "authority_generation": "version", "schema_version": "version",
        "valid_from_utc": "utc", "valid_until_utc": "utc", "content_digest": "string",
        "policy_json": "long_text",
    },
    POLICY_REVISION: {
        "record_key": "string", "policy": "string", "revision": "version",
        "previous_revision": "version", "snapshot_json": "long_text", "snapshot_digest": "string",
        "actor": "string", "reason": "small_text", "approval_source_ref": "string",
        "recorded_at_utc": "utc",
    },
}
_NATIVE_COLUMNS = {
    "User": {"name": "string", "enabled": "check", "user_type": "string", "modified": "datetime"},
    "Employee": {
        "name": "string", "employee_name": "string", "user_id": "string", "company": "string",
        "department": "string", "designation": "string", "status": "string",
        "date_of_joining": "date", "relieving_date": "date", "modified": "datetime",
    },
    "Company": {"name": "string", "modified": "datetime"},
    "Department": {
        "name": "string", "company": "string", "parent_department": "string",
        "is_group": "check", "disabled": "check", "modified": "datetime",
    },
    "Designation": {"name": "string", "modified": "datetime"},
}
_COLUMN_TYPES = {
    "string": frozenset(("varchar",)), "version": frozenset(("int",)),
    "check": frozenset(("int", "tinyint")), "small_text": frozenset(("text",)),
    "long_text": frozenset(("longtext",)), "date": frozenset(("date",)),
    "datetime": frozenset(("datetime",)), "utc": frozenset(("datetime",)),
}
_TABLE_COLUMNS = {
    **{"tab" + kind: {"name": "string", "modified": "datetime", **fields}
       for kind, fields in _MANAGED_COLUMNS.items()},
    **{"tab" + kind: fields for kind, fields in _NATIVE_COLUMNS.items()},
}
_MANAGED_TABLES = tuple("tab" + kind for kind in _MANAGED_COLUMNS)
_TABLES = tuple(_TABLE_COLUMNS)
_MANAGED_TYPES = tuple(_MANAGED_COLUMNS)
_TABLE_MARKERS = ",".join(("%s",) * len(_TABLES))
_MANAGED_MARKERS = ",".join(("%s",) * len(_MANAGED_TYPES))
_INDEX_MARKERS = ",".join(("%s",) * len(_MANAGED_TABLES))


def _fail(code, path):
    raise ContractError(code, path)


def _select(db, sql, values=(), *, as_dict=False):
    try:
        rows = db.sql(sql, values, as_dict=as_dict)
        if not isinstance(rows, (list, tuple)):
            raise TypeError
        return rows
    except Exception:
        # SQL exceptions can contain server details or substituted parameters.
        raise ContractError("STORAGE_PREFLIGHT_UNAVAILABLE", "preflight") from None


def _tables(db):
    rows = _select(db,
        "SELECT table_name AS table_name,engine AS engine FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_name IN (" + _TABLE_MARKERS + ")",
        _TABLES, as_dict=True)
    seen = set()
    for row in rows:
        table = row.get("table_name")
        if table not in _TABLE_COLUMNS or table in seen or row.get("engine") != "InnoDB":
            _fail("STORAGE_PREFLIGHT_SCHEMA_INVALID", "preflight.tables")
        seen.add(table)
    if seen != set(_TABLES):
        _fail("STORAGE_PREFLIGHT_SCHEMA_INVALID", "preflight.tables")


def _columns(db):
    rows = _select(db,
        "SELECT table_name AS table_name,column_name AS column_name,data_type AS data_type,"
        "datetime_precision AS datetime_precision "
        "FROM information_schema.columns WHERE table_schema=DATABASE() "
        "AND table_name IN (" + _TABLE_MARKERS + ")", _TABLES, as_dict=True)
    selected = {}
    for row in rows:
        table, column = row.get("table_name"), row.get("column_name")
        if table not in _TABLE_COLUMNS or not isinstance(column, str) or (table, column) in selected:
            _fail("STORAGE_PREFLIGHT_SCHEMA_INVALID", "preflight.columns")
        selected[table, column] = row
    for table, fields in _TABLE_COLUMNS.items():
        for column, family in fields.items():
            row = selected.get((table, column))
            if row is None or row.get("data_type") not in _COLUMN_TYPES[family]:
                _fail("STORAGE_PREFLIGHT_SCHEMA_INVALID", "preflight.columns")
            if family == "utc" and (type(row.get("datetime_precision")) is not int
                                     or row["datetime_precision"] != 6):
                _fail("STORAGE_PREFLIGHT_SCHEMA_INVALID", "preflight.utc_precision")


def _indexes(db):
    rows = _select(db,
        "SELECT table_name AS table_name,index_name AS index_name,non_unique AS non_unique,"
        "seq_in_index AS seq_in_index,column_name AS column_name,sub_part AS sub_part "
        "FROM information_schema.statistics WHERE table_schema=DATABASE() "
        "AND table_name IN (" + _INDEX_MARKERS + ")", _MANAGED_TABLES, as_dict=True)
    grouped = {}
    for row in rows:
        table, name = row.get("table_name"), row.get("index_name")
        if table not in _MANAGED_TABLES or not isinstance(name, str) or not name:
            _fail("STORAGE_PREFLIGHT_SCHEMA_INVALID", "preflight.indexes")
        grouped.setdefault((table, name), []).append(row)
    for table in _MANAGED_TABLES:
        required = {"name", "record_key"}
        if table in ("tab" + POSITION, "tab" + ASSIGNMENT):
            required.add("source_key")
        unique = set()
        for (kind, _), index in grouped.items():
            if kind != table or len(index) != 1:
                continue
            row = index[0]
            if (type(row.get("non_unique")) is int and row["non_unique"] == 0
                    and type(row.get("seq_in_index")) is int and row["seq_in_index"] == 1
                    and row.get("sub_part") is None):
                unique.add(row.get("column_name"))
        if not required <= unique:
            _fail("STORAGE_PREFLIGHT_SCHEMA_INVALID", "preflight.indexes")


def _metadata(db):
    rows = _select(db,
        "SELECT name,module,autoname,allow_import,allow_rename FROM `tabDocType` "
        "WHERE name IN (" + _MANAGED_MARKERS + ")", _MANAGED_TYPES, as_dict=True)
    seen = set()
    for row in rows:
        name = row.get("name")
        if (name not in _MANAGED_TYPES or name in seen or row.get("module") != "HBOS Portal"
                or row.get("autoname") != "field:record_key"
                or any(type(row.get(flag)) not in (int, bool) or row[flag] != 0
                       for flag in ("allow_import", "allow_rename"))):
            _fail("STORAGE_PREFLIGHT_METADATA_INVALID", "preflight.metadata")
        seen.add(name)
    if seen != set(_MANAGED_TYPES):
        _fail("STORAGE_PREFLIGHT_METADATA_INVALID", "preflight.metadata")
    for sql in (
        "SELECT parent FROM `tabDocPerm` WHERE parent IN (" + _MANAGED_MARKERS + ")",
        "SELECT parent FROM `tabCustom DocPerm` WHERE parent IN (" + _MANAGED_MARKERS + ")",
    ):
        if _select(db, sql, _MANAGED_TYPES):
            _fail("STORAGE_PREFLIGHT_METADATA_INVALID", "preflight.permissions")
    # Do not classify a new or seemingly cosmetic property as safe without
    # separately reviewing its effects on this controlled storage schema.
    for sql in (
        "SELECT doc_type FROM `tabProperty Setter` WHERE doc_type IN (" + _MANAGED_MARKERS + ")",
        "SELECT dt FROM `tabCustom Field` WHERE dt IN (" + _MANAGED_MARKERS + ")",
    ):
        if _select(db, sql, _MANAGED_TYPES):
            _fail("STORAGE_PREFLIGHT_METADATA_INVALID", "preflight.overrides")


def preflight_management_structure(native, *, expected_site, expected_database_sha256):
    """Diagnose fixed storage structure without creating or trusting authority.

The caller supplies an existing native context and owns its transaction. This
function issues only SELECT statements; it does not read policies or personnel
rows. A passing snapshot cannot replace any request-time or production gate.
"""
    if (not isinstance(expected_site, str) or not expected_site or expected_site != expected_site.strip()
            or len(expected_site) > 140 or not isinstance(expected_database_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_database_sha256)):
        _fail("SOURCE_PREFLIGHT_BINDING_REQUIRED", "preflight.target")
    try:
        local = native.local
        if local.site != expected_site:
            _fail("SOURCE_PREFLIGHT_TARGET_MISMATCH", "preflight.target")
        db = local.db
        if db is None or not callable(getattr(db, "sql", None)):
            _fail("SOURCE_PREFLIGHT_CONTEXT_REQUIRED", "preflight.target")
        if native.conf.get("db_type", "mariadb") != "mariadb":
            _fail("SOURCE_PREFLIGHT_DATABASE_UNSUPPORTED", "preflight.target")
        values = _select(db, "SELECT DATABASE(), @@tx_isolation")
        if (len(values) != 1 or not isinstance(values[0], (list, tuple)) or len(values[0]) != 2
                or not isinstance(values[0][0], str)):
            _fail("SOURCE_PREFLIGHT_CONTEXT_REQUIRED", "preflight.target")
        import hashlib
        if hashlib.sha256(values[0][0].encode()).hexdigest() != expected_database_sha256:
            _fail("SOURCE_PREFLIGHT_TARGET_MISMATCH", "preflight.target")
        if values[0][1] != "REPEATABLE-READ":
            _fail("SOURCE_PREFLIGHT_DATABASE_UNSUPPORTED", "preflight.target")
        _tables(db)
        _columns(db)
        _indexes(db)
        _metadata(db)
        roots = _select(db, "SELECT name,record_key FROM `tabHBOS Organization Write Lock` ORDER BY name",
                        as_dict=True)
        if len(roots) != 1 or roots[0].get("name") != LOCK_KEY or roots[0].get("record_key") != LOCK_KEY:
            _fail("STORAGE_PREFLIGHT_ROOT_LOCK_REQUIRED", "preflight.root_lock")
    except ContractError:
        raise
    except Exception:
        raise ContractError("STORAGE_PREFLIGHT_UNAVAILABLE", "preflight") from None
    return {
        "structure_validated": True, "production_ready": False,
        "managed_tables_checked": 8, "native_tables_checked": 5, "root_lock_validated": True,
        "policy": "NOT_RUN", "runtime_hooks": "NOT_RUN", "origin": "NOT_RUN", "restore": "NOT_RUN",
        "read_only": True, "runtime_verified": False, "authorization_effect": "none",
        "position_authorization_connected": False,
    }
