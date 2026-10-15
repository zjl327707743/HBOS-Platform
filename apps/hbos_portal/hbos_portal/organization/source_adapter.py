"""Pure, explicitly injected source adaptation; no Frappe or runtime discovery.

Selected native fields and proposed relationship fields are validated separately.
Even a complete-link declaration cannot verify employee date policy, source trust
or business approval. Every result remains validation_only / runtime_verified=False.
"""
from collections.abc import Mapping
from datetime import date, datetime, timezone
import re
from types import MappingProxyType

from hbos_portal.authorization.contracts import SourceRef
from hbos_portal.authorization.errors import ContractError
from hbos_portal.authorization.validation import (
    validate_assignment_projection, validate_position_projection,
)
from .source_contracts import (
    AssignmentSourceEvidence, PersonSourceEvidence, PositionSourceEvidence,
    SourceContext, SourceFingerprint, SourceSnapshot,
)


_UTC = timezone.utc
_RFC3339 = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)")
_DB_TIME = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,6})?")
_SCHEMAS = {
    "User": ("name", "enabled", "user_type", "modified"),
    "Employee": ("name", "user_id", "company", "department", "designation", "status",
                 "date_of_joining", "relieving_date", "modified"),
    "Company": ("name", "modified"),
    "Department": ("name", "company", "parent_department", "is_group", "disabled", "modified"),
    "Designation": ("name", "modified"),
}


def _fail(code, path):
    raise ContractError(code, path)


def _fields(value, required, path):
    if not isinstance(value, Mapping):
        _fail("INVALID_TYPE", path)
    if set(value) - set(required):
        _fail("UNKNOWN_FIELD", path)
    for key in required:
        if key not in value:
            _fail("MISSING_FIELD", f"{path}.{key}")
    return dict(value)


def _text(value, path):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        _fail("INVALID_TEXT", path)
    return value


def _link(value, path):
    return None if value is None or value == "" else _text(value, path)


def _check(value, path):
    if type(value) not in (bool, int) or value not in (0, 1):
        _fail("INVALID_CHECK", path)
    return bool(value)


def _positive_integer(value, path):
    if type(value) is not int or value < 1:
        _fail("INVALID_VERSION", path)
    return value


def _utc(value, path):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("TIMEZONE_REQUIRED", path)
    try:
        return value.astimezone(_UTC)
    except (ValueError, OverflowError):
        raise ContractError("INVALID_TIME", path) from None


def parse_rfc3339_utc(value):
    """Parse an explicit offset without silently truncating sub-microsecond time."""
    if not isinstance(value, str) or not _RFC3339.fullmatch(value) or value.endswith("-00:00"):
        _fail("INVALID_TIME", "time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _utc(parsed, "time")
    except (ValueError, OverflowError):
        raise ContractError("INVALID_TIME", "time") from None


def encode_utc_datetime(value):
    """Encode ONLY a new explicitly UTC database field; not native Site datetimes."""
    return _utc(value, "time").replace(tzinfo=None)


def decode_utc_datetime(value):
    """Decode ONLY a field whose storage contract explicitly promises naive UTC."""
    if isinstance(value, str):
        if not _DB_TIME.fullmatch(value):
            _fail("INVALID_STORAGE_TIME", "time")
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, OverflowError):
            raise ContractError("INVALID_STORAGE_TIME", "time") from None
    if not isinstance(value, datetime) or value.tzinfo is not None:
        _fail("INVALID_STORAGE_TIME", "time")
    return value.replace(tzinfo=_UTC)


def interval_contains(instant, start, end):
    """Half-open time arithmetic, not a qualification or permission check."""
    instant, start = _utc(instant, "instant"), _utc(start, "start")
    end = None if end is None else _utc(end, "end")
    if end is not None and start >= end:
        _fail("INVALID_INTERVAL", "end")
    return start <= instant and (end is None or instant < end)


def _native_date(value, path, optional=False):
    if optional and (value is None or value == ""):
        return None
    if type(value) is date:
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    _fail("INVALID_DATE", path)


def build_source_snapshot(*, site_id, provider_id, captured_at, rows_by_type,
                          employee_links_complete=False):
    """Copy selected source fields; completeness is an unverified declaration.

    A future trusted loader must establish Site, provenance, coverage and freshness
    itself. Passing True here never proves database completeness or permission.
    """
    context = SourceContext(_text(site_id, "context.site_id"),
                            _text(provider_id, "context.provider_id"), parse_rfc3339_utc(captured_at))
    if type(employee_links_complete) is not bool:
        _fail("INVALID_TYPE", "employee_links_complete")
    tables = _fields(rows_by_type, _SCHEMAS, "source.rows")
    copied = {}
    for kind, fields in _SCHEMAS.items():
        values = tables[kind]
        if not isinstance(values, (list, tuple)):
            _fail("INVALID_COLLECTION", f"source.{kind}")
        indexed = {}
        for i, value in enumerate(values):
            path = f"source.{kind}[{i}]"
            row = _fields(value, fields, path)
            name = _text(row["name"], path + ".name")
            _text(row["modified"], path + ".modified")
            if name in indexed:
                _fail("DUPLICATE_ID", f"source.{kind}")
            if kind == "User":
                row["enabled"] = _check(row["enabled"], path + ".enabled")
                _text(row["user_type"], path + ".user_type")
            elif kind == "Employee":
                _text(row["company"], path + ".company")
                for key in ("user_id", "department", "designation"):
                    row[key] = _link(row[key], path + "." + key)
                if _text(row["status"], path + ".status") not in ("Active", "Inactive", "Suspended", "Left"):
                    _fail("INVALID_STATUS", path + ".status")
                row["date_of_joining"] = _native_date(row["date_of_joining"], path + ".date_of_joining")
                row["relieving_date"] = _native_date(row["relieving_date"], path + ".relieving_date", True)
            elif kind == "Department":
                for key in ("company", "parent_department"):
                    row[key] = _link(row[key], path + "." + key)
                for key in ("is_group", "disabled"):
                    row[key] = _check(row[key], path + "." + key)
            indexed[name] = MappingProxyType(row)
        copied[kind] = MappingProxyType(dict(sorted(indexed.items())))
    return SourceSnapshot(context, MappingProxyType(copied), employee_links_complete)


def _get(snapshot, kind, key, path):
    row = snapshot.rows[kind].get(key)
    if row is None:
        _fail("UNKNOWN_REFERENCE", path)
    return row


def _fingerprint(kind, row):
    return SourceFingerprint(SourceRef(kind, row["name"]), row["modified"])


def _department_chain(snapshot, department_id, company_id):
    chain, seen = [], set()
    while department_id is not None:
        if department_id in seen:
            _fail("CYCLIC_ORGANIZATION", "department.parent_department")
        seen.add(department_id)
        row = _get(snapshot, "Department", department_id, "department")
        if row["disabled"]:
            _fail("DISABLED_ORGANIZATION", "department")
        if row["company"] != company_id:
            # Only an unowned group ROOT may connect otherwise owned departments.
            if row["company"] is not None or not row["is_group"] or row["parent_department"] is not None:
                _fail("COMPANY_MISMATCH", "department.company")
        chain.append(row)
        department_id = row["parent_department"]
    return tuple(chain)


def resolve_person(snapshot, source_type, source_id):
    """Resolve exact source keys; never match contact details or assert qualification."""
    if source_type not in ("User", "Employee"):
        _fail("UNSUPPORTED_SOURCE", "person.source_type")
    source_id = _text(source_id, "person.source_id")
    requested = SourceRef(source_type, source_id)
    original = _get(snapshot, source_type, source_id, "person.source_id")
    employee = original if source_type == "Employee" else None
    user_id = original["user_id"] if employee is not None else source_id
    user = snapshot.rows["User"].get(user_id) if user_id is not None else None
    candidates = tuple(row for row in snapshot.rows["Employee"].values()
                       if user_id is not None and row["user_id"] == user_id)
    if employee is None and len(candidates) == 1:
        employee = candidates[0]
    reasons, subject, canonical = [], None, None
    organization_fingerprints = []
    status = "unknown"
    if user_id is None:
        status, canonical = "unlinked", requested
        reasons.append("ACCOUNT_UNLINKED")
    elif len(candidates) > 1:
        status = "ambiguous"
        reasons.append("MULTIPLE_EMPLOYEE_LINKS")
    elif user is None:
        reasons.append("USER_MISSING")
    elif user_id in ("Guest", "Administrator"):
        reasons.append("RESERVED_ACCOUNT")
    elif not snapshot.employee_links_complete:
        reasons.append("INCOMPLETE_LINK_SET")
    elif not candidates:
        status = "unlinked"
        reasons.append("EMPLOYEE_MISSING")
    else:
        status, subject = "linked", user_id
        canonical = SourceRef("Employee", candidates[0]["name"])
    if user is not None and not user["enabled"]:
        reasons.append("ACCOUNT_DISABLED")
    if user is not None and user["user_type"] not in ("System User", "Website User"):
        reasons.append("UNSUPPORTED_USER_TYPE")
    if user_id in ("Guest", "Administrator") and "RESERVED_ACCOUNT" not in reasons:
        reasons.append("RESERVED_ACCOUNT")
    if user_id is not None and user is None and "USER_MISSING" not in reasons:
        reasons.append("USER_MISSING")
    if employee is not None:
        if employee["status"] != "Active":
            reasons.append("EMPLOYEE_NOT_ACTIVE")
        reasons.append("EMPLOYEE_DATE_POLICY_UNRESOLVED")
        if employee["relieving_date"] is not None and employee["relieving_date"] < employee["date_of_joining"]:
            reasons.append("EMPLOYEE_DATES_INCONSISTENT")
        try:
            company = _get(snapshot, "Company", employee["company"], "employee.company")
            organization_fingerprints.append(_fingerprint("Company", company))
            if employee["department"] is not None:
                chain = _department_chain(snapshot, employee["department"], employee["company"])
                if chain[0]["company"] != employee["company"]:
                    _fail("COMPANY_MISMATCH", "employee.department")
                organization_fingerprints.extend(_fingerprint("Department", row) for row in chain)
            if employee["designation"] is not None:
                designation = _get(snapshot, "Designation", employee["designation"], "employee.designation")
                organization_fingerprints.append(_fingerprint("Designation", designation))
        except ContractError:
            reasons.append("EMPLOYEE_ORGANIZATION_UNRESOLVED")
    fingerprints = [_fingerprint(source_type, original)]
    if user is not None:
        fingerprints.append(_fingerprint("User", user))
    fingerprints.extend(_fingerprint("Employee", row) for row in candidates)
    fingerprints.extend(organization_fingerprints)
    fingerprints = tuple(sorted(set(fingerprints), key=lambda f: (f.reference.source_type, f.reference.source_id)))
    def employee_ref(field, kind):
        value = employee[field] if employee is not None else None
        return None if value is None else SourceRef(kind, value)
    qualification = status if status in ("unlinked", "ambiguous") else "unknown"
    return PersonSourceEvidence(
        snapshot.context, requested, canonical, subject, status, qualification,
        tuple(sorted(set(reasons))), tuple(SourceRef("Employee", row["name"]) for row in candidates),
        user["enabled"] if user is not None else None, employee["status"] if employee is not None else None,
        employee_ref("company", "Company"), employee_ref("department", "Department"),
        employee_ref("designation", "Designation"),
        employee["date_of_joining"] if employee is not None else None,
        employee["relieving_date"] if employee is not None else None, fingerprints,
    )


def adapt_position(payload, snapshot):
    """Map proposed relationship fields and retain facts absent from the A DTO."""
    data = _fields(payload, ("name", "title", "company", "department", "designation", "status",
                             "revision", "authorization_generation", "modified"), "position")
    company_id = _text(data["company"], "position.company")
    department_id = _text(data["department"], "position.department")
    company = _get(snapshot, "Company", company_id, "position.company")
    chain = _department_chain(snapshot, department_id, company_id)
    if chain[0]["company"] != company_id:
        _fail("COMPANY_MISMATCH", "position.department")
    designation_id = _link(data["designation"], "position.designation")
    designation = None if designation_id is None else _get(snapshot, "Designation", designation_id, "position.designation")
    projection = validate_position_projection({
        "position_id": data["name"], "department_ref": {"source_type": "Department", "source_id": department_id},
        "label": data["title"], "status": data["status"], "revision": data["revision"],
    })
    generation = _positive_integer(data["authorization_generation"], "position.authorization_generation")
    _text(data["modified"], "position.modified")
    fingerprints = [_fingerprint("HBOS Position", data), _fingerprint("Company", company)]
    fingerprints.extend(_fingerprint("Department", row) for row in chain)
    if designation is not None:
        fingerprints.append(_fingerprint("Designation", designation))
    return PositionSourceEvidence(projection, SourceRef("Company", company_id),
                                  None if designation_id is None else SourceRef("Designation", designation_id),
                                  generation, tuple(fingerprints), snapshot)


def adapt_assignment(payload, snapshot, positions):
    """Map a proposed assignment; a stored subject claim cannot override sources."""
    data = _fields(payload, ("name", "person_source_type", "person_source_id", "subject_user", "position",
                             "is_primary", "valid_from_utc", "valid_until_utc", "status", "revision",
                             "authorization_generation", "modified"), "assignment")
    position_id = _text(data["position"], "assignment.position")
    positions = tuple(positions)
    if any(not isinstance(p, PositionSourceEvidence) or p.snapshot is not snapshot for p in positions):
        _fail("SOURCE_SNAPSHOT_MISMATCH", "assignment.positions")
    if len({p.projection.position_id for p in positions}) != len(positions):
        _fail("DUPLICATE_ID", "assignment.positions")
    position = next((p for p in positions if p.projection.position_id == position_id), None)
    if position is None:
        _fail("UNKNOWN_REFERENCE", "assignment.position")
    person = resolve_person(snapshot, data["person_source_type"], data["person_source_id"])
    if _link(data["subject_user"], "assignment.subject_user") != person.subject_user:
        _fail("SUBJECT_MISMATCH", "assignment.subject_user")
    if person.company_ref is not None and person.company_ref != position.company_ref:
        _fail("COMPANY_MISMATCH", "assignment.person")
    if "EMPLOYEE_ORGANIZATION_UNRESOLVED" in person.reason_codes:
        _fail("UNKNOWN_REFERENCE", "assignment.person.organization")
    start = decode_utc_datetime(data["valid_from_utc"])
    end = None if data["valid_until_utc"] is None else decode_utc_datetime(data["valid_until_utc"])
    projection = validate_assignment_projection({
        "assignment_id": data["name"],
        "person_ref": {"source_type": person.requested_ref.source_type, "source_id": person.requested_ref.source_id},
        "subject_user": person.subject_user, "position_id": position_id,
        "is_primary": _check(data["is_primary"], "assignment.is_primary"),
        "valid_from": start.isoformat(), "valid_until": None if end is None else end.isoformat(),
        "status": data["status"], "revision": data["revision"],
        "authorization_generation": data["authorization_generation"], "qualification_status": person.qualification_status,
    }, (p.projection for p in positions))
    _text(data["modified"], "assignment.modified")
    return AssignmentSourceEvidence(projection, person, position, _fingerprint("HBOS Personnel Assignment", data))
