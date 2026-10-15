"""Inactive-by-default Frappe storage adapter. No endpoint, migration, or commit."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
import json
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from .source_adapter import decode_utc_datetime
from .storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, LOCK_KEY, MASTER_FIELDS, POSITION, POSITION_REVISION,
    RECEIPT, VERSION_FIELDS, WRITE_LOCK, canonical_json, revision_key, validate_storage_record,
)
from .write_guard import _controlled_write


@dataclass(frozen=True)
class _SourceReadScope:
    database: object
    site: str
    generation: int
    writer_locked: bool = False


class FrappeRelationRepository:
    def __init__(self, *, enabled=False, native=None):
        self.enabled = enabled is True
        self._module = native
        self._source_scope = ContextVar("hbos_relation_source_scope", default=None)
        self._source_generation = ContextVar("hbos_relation_source_generation", default=0)

    def _native(self):
        if not self.enabled:
            raise ContractError("WRITES_DISABLED", "repository")
        if self._module is None:
            import frappe
            self._module = frappe
        return self._module

    @property
    def site_id(self):
        return self._native().local.site

    @contextmanager
    def transaction(self):
        native = self._native()
        point = "hbos_rel_" + uuid4().hex
        native.db.savepoint(point)
        generation = self._source_generation.get()
        token = self._source_scope.set(_SourceReadScope(native.db, native.local.site, generation))
        try:
            yield
            if generation != self._source_generation.get():
                raise ContractError("RELATION_TRANSACTION_RETRY_REQUIRED", "transaction")
        except BaseException as error:
            deadlock_type = getattr(native, "QueryDeadlockError", None)
            if isinstance(deadlock_type, type) and isinstance(error, deadlock_type):
                # InnoDB snapshot conflicts/deadlocks can discard the entire
                # transaction, including this savepoint and outer callers' work.
                # Reset Frappe bookkeeping and invalidate nested source scopes.
                # The caller must restart the whole request; never retry here.
                self._source_generation.set(self._source_generation.get() + 1)
                native.db.rollback()
                raise ContractError("RELATION_TRANSACTION_RETRY_REQUIRED", "transaction") from error
            if generation == self._source_generation.get():
                native.db.rollback(save_point=point)
            raise
        finally:
            self._source_scope.reset(token)

    def initialize_write_lock(self):
        """Explicit deployment bootstrap only, after schema validation; never auto-run."""
        native = self._native()
        if not native.db.exists(WRITE_LOCK, LOCK_KEY):
            self._insert(WRITE_LOCK, {"record_key": LOCK_KEY})

    def lock_writer(self):
        native = self._native()
        rows = native.db.sql(
            "SELECT name FROM `tabHBOS Organization Write Lock` WHERE name=%s FOR UPDATE", (LOCK_KEY,))
        if not rows:
            raise ContractError("STORAGE_NOT_READY", "write_lock")
        scope = self._source_scope.get()
        if (scope is not None and scope.database is native.db and scope.site == native.local.site
                and scope.generation == self._source_generation.get()):
            self._source_scope.set(replace(scope, writer_locked=True))

    def require_locked_source_context(self):
        """Internal loader capability; not Document.flags or a request parameter."""
        native = self._native()
        scope = self._source_scope.get()
        if (scope is None or not scope.writer_locked or scope.database is not native.db
                or scope.site != native.local.site or scope.generation != self._source_generation.get()):
            raise ContractError("SOURCE_TRANSACTION_REQUIRED", "source.context")
        return native

    def lock_sources(self, references):
        # Table names are constants; request-provided identifiers never become SQL.
        tables = {"User": "tabUser", "Employee": "tabEmployee", "Company": "tabCompany",
                  "Department": "tabDepartment", "Designation": "tabDesignation"}
        native = self._native()
        references = tuple(references)
        if any(kind not in tables for kind, key in references):
            raise ContractError("UNSUPPORTED_SOURCE", "locks")
        for kind in tables:
            for key in sorted({key for source_type, key in references if source_type == kind}):
                if not native.db.sql(f"SELECT name FROM `{tables[kind]}` WHERE name=%s FOR UPDATE", (key,)):
                    raise ContractError("SOURCE_CHANGED_RETRY", "locks")

    def get_master(self, kind, record_id):
        native = self._native()
        if kind not in MASTER_FIELDS:
            raise ContractError("UNSUPPORTED_SOURCE", "record")
        fields = ("record_key",) + MASTER_FIELDS[kind] + VERSION_FIELDS + ("modified",)
        # Current reads also matter for relationship facts and receipts: an outer
        # Frappe request may already have established a REPEATABLE READ snapshot.
        rows = native.db.sql("SELECT " + ",".join("`" + field + "`" for field in fields)
                             + f" FROM `tab{kind}` WHERE name=%s FOR UPDATE", (record_id,), as_dict=True)
        if not rows:
            return None
        result = dict(rows[0])
        result["_source_modified"] = str(result.pop("modified"))
        return self._normalize(result)

    @staticmethod
    def _normalize(row):
        for key in ("designation", "subject_user", "valid_until_utc"):
            if key in row and row[key] == "":
                row[key] = None
        for key in ("valid_from_utc", "valid_until_utc"):
            if key in row and row[key] is not None:
                row[key] = decode_utc_datetime(row[key]).strftime("%Y-%m-%d %H:%M:%S.%f")
        if "is_primary" in row:
            row["is_primary"] = bool(row["is_primary"])
        return row

    def list_positions(self):
        """Fixed current fact query, available only inside the root capability."""
        native = self.require_locked_source_context()
        fields = ("record_key",) + MASTER_FIELDS[POSITION] + VERSION_FIELDS
        rows = native.db.sql("SELECT " + ",".join("`" + field + "`" for field in fields)
                             + " FROM `tabHBOS Position` ORDER BY name FOR UPDATE", as_dict=True)
        return tuple(self._normalize(dict(row)) for row in rows)

    def get_person_label(self, employee_id):
        """Read only the label of an already authorized stable Employee key."""
        native = self.require_locked_source_context()
        rows = native.db.sql("SELECT name,employee_name FROM `tabEmployee` "
                             "WHERE name=%s FOR UPDATE", (employee_id,), as_dict=True)
        if not rows:
            return None
        if len(rows) != 1 or rows[0]["name"] != employee_id:
            raise ContractError("SOURCE_CHANGED_RETRY", "person.label")
        label = rows[0]["employee_name"]
        return "" if label is None else label

    def list_assignments(self):
        fields = ("record_key",) + MASTER_FIELDS[ASSIGNMENT] + VERSION_FIELDS
        rows = self._native().db.sql("SELECT " + ",".join("`" + field + "`" for field in fields)
                                    + " FROM `tabHBOS Personnel Assignment` ORDER BY name FOR UPDATE", as_dict=True)
        return tuple(self._normalize(dict(row)) for row in rows)

    def get_receipt(self, key):
        rows = self._native().db.sql(
            "SELECT request_digest,result_json FROM `tabHBOS Organization Command Receipt` WHERE name=%s FOR UPDATE",
            (key,), as_dict=True)
        return None if not rows else {"request_digest": rows[0]["request_digest"], "result": json.loads(rows[0]["result_json"])}

    def get_revision(self, kind, record_id, revision):
        """Current immutable revision read; callers also verify master equality."""
        self.require_locked_source_context()
        if kind not in (POSITION, ASSIGNMENT):
            raise ContractError("UNSUPPORTED_SOURCE", "revision")
        history = POSITION_REVISION if kind == POSITION else ASSIGNMENT_REVISION
        parent = "position" if kind == POSITION else "assignment"
        fields = ("record_key", parent, "revision", "previous_revision", "snapshot_json", "content_digest",
                  "actor", "policy_ref", "reason", "source_evidence_json", "recorded_at_utc")
        key = revision_key(kind, record_id, revision)
        rows = self._native().db.sql("SELECT " + ",".join("`" + field + "`" for field in fields)
            + f" FROM `tab{history}` WHERE name=%s FOR UPDATE", (key,), as_dict=True)
        if not rows:
            raise ContractError("HISTORICAL_SCOPE_REQUIRED", "revision")
        row = dict(rows[0])
        validate_storage_record(history, key, row.get)
        return row

    def save_master(self, kind, record, *, expected_revision):
        native = self._native()
        if expected_revision == 0:
            self._insert(kind, record)
            return
        doc = native.get_doc(kind, record["record_key"], for_update=True)
        if doc.revision != expected_revision:
            raise ContractError("REVISION_CONFLICT", "expected_revision")
        doc.update(record)
        with _controlled_write(kind, doc.name):
            doc.save(ignore_permissions=True)

    def append_revision(self, kind, record):
        self._insert(kind, record)

    def insert_receipt(self, key, record):
        data = dict(record)
        data["result_json"] = canonical_json(data.pop("result"))
        self._insert(RECEIPT, {**data, "record_key": key})

    def _insert(self, kind, record):
        validate_storage_record(kind, record["record_key"], record.get)
        doc = self._native().get_doc({"doctype": kind, **record})
        with _controlled_write(kind, record["record_key"]):
            doc.insert(ignore_permissions=True)
