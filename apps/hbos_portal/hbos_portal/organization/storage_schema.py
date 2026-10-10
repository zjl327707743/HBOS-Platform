"""Storage identities and canonical snapshots; no framework dependencies."""
import hashlib
import json
from uuid import UUID

from hbos_portal.authorization.errors import ContractError

POSITION = "HBOS Position"
ASSIGNMENT = "HBOS Personnel Assignment"
POSITION_REVISION = "HBOS Position Revision"
ASSIGNMENT_REVISION = "HBOS Personnel Assignment Revision"
RECEIPT = "HBOS Organization Command Receipt"
WRITE_LOCK = "HBOS Organization Write Lock"
LOCK_KEY = "relations-v1"
PROVIDER = "hbos_portal.organization.v1"
IMMUTABLE = frozenset((POSITION_REVISION, ASSIGNMENT_REVISION, RECEIPT, WRITE_LOCK))
MASTER_FIELDS = {
    POSITION: ("title", "company", "department", "designation", "status"),
    ASSIGNMENT: ("person_source_type", "person_source_id", "subject_user", "position",
                 "is_primary", "valid_from_utc", "valid_until_utc", "status"),
}
VERSION_FIELDS = ("revision", "authorization_generation", "source_provider", "source_key")


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def revision_key(doctype, record_id, revision):
    return digest([doctype, record_id, revision])


def receipt_key(site_id, actor, command_type, request_key):
    return digest([site_id, actor, command_type, request_key])


def require_uuid(value, path):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ContractError("INVALID_ID", path) from None
    return value


def validate_storage_record(doctype, name, get):
    """Defense in depth even when Document.flags.ignore_validate is supplied."""
    if doctype not in {*MASTER_FIELDS, *IMMUTABLE} or not name or get("record_key") != name:
        raise ContractError("INVALID_STORAGE_KEY", "record")
    if doctype in MASTER_FIELDS:
        require_uuid(name, "record")
        for key in ("revision", "authorization_generation"):
            if type(get(key)) is not int or get(key) < 1:
                raise ContractError("INVALID_VERSION", key)
        if get("source_provider") != PROVIDER or get("source_key") != name:
            raise ContractError("SOURCE_MISMATCH", "record")
    elif doctype in (POSITION_REVISION, ASSIGNMENT_REVISION):
        master = POSITION if doctype == POSITION_REVISION else ASSIGNMENT
        parent = get("position" if master == POSITION else "assignment")
        revision = get("revision")
        if type(revision) is not int or revision < 1 or type(get("previous_revision")) is not int or get("previous_revision") != revision - 1:
            raise ContractError("INVALID_VERSION", "revision")
        require_uuid(parent, "parent")
        if name != revision_key(master, parent, revision):
            raise ContractError("INVALID_STORAGE_KEY", "revision")
        try:
            facts = json.loads(get("snapshot_json"))
        except (TypeError, ValueError):
            raise ContractError("INVALID_SNAPSHOT", "snapshot") from None
        if not isinstance(facts, dict) or facts.get("record_key") != parent or type(facts.get("revision")) is not int or facts.get("revision") != revision:
            raise ContractError("INVALID_SNAPSHOT", "snapshot")
        if get("content_digest") != digest(facts):
            raise ContractError("SNAPSHOT_MISMATCH", "snapshot")
    elif doctype == RECEIPT:
        if name != receipt_key(get("site_id"), get("actor"), get("command_type"), get("request_key")):
            raise ContractError("INVALID_STORAGE_KEY", "receipt")
    elif name != LOCK_KEY:
        raise ContractError("INVALID_STORAGE_KEY", "lock")
