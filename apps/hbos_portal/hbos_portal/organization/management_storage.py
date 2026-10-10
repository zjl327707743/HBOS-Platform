"""Canonical protected policy storage and pinned server-side approval evidence.

Approval pins are supplied by trusted deployment code after human verification.
This module does not authenticate a human or turn submitted strings into approval.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
import json

from hbos_portal.authorization.errors import ContractError
from .management_policy import management_policy_digest, parse_management_policy
from .source_adapter import decode_utc_datetime, encode_utc_datetime
from .storage_schema import canonical_json, digest, revision_key

POLICY = "HBOS Organization Management Policy"
POLICY_REVISION = "HBOS Organization Management Policy Revision"
POLICY_PROVIDER = "hbos_portal.management-policy.v1"
POLICY_FIELDS = ("record_key", "site_id", "source_provider", "subject_user", "status", "revision",
                 "authority_generation", "schema_version", "valid_from_utc", "valid_until_utc",
                 "content_digest", "policy_json")
REVISION_FIELDS = ("record_key", "policy", "revision", "previous_revision", "snapshot_json",
                   "snapshot_digest", "actor", "reason", "approval_source_ref", "recorded_at_utc")


def _export(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _export(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_export(item) for item in value]
    return value


def policy_data(policy):
    # Reparse even directly constructed dataclasses; do not trust type hints.
    from .management_contracts import ManagementPolicy
    if type(policy) is not ManagementPolicy:
        raise ContractError("INVALID_TYPE", "policy")
    data = _export(asdict(policy))
    data.pop("validation_only")
    data.pop("runtime_verified")
    site, provider = data.pop("site_id"), data.pop("source_provider")
    checked = parse_management_policy(data, site_id=site, source_provider=provider)
    if provider != POLICY_PROVIDER:
        raise ContractError("POLICY_PROVIDER_MISMATCH", "policy")
    data = _export(asdict(checked))
    data.pop("validation_only")
    data.pop("runtime_verified")
    return data


def stored_time(value):
    return encode_utc_datetime(value).strftime("%Y-%m-%d %H:%M:%S.%f")


def policy_record(policy):
    data = policy_data(policy)
    return dict(record_key=policy.policy_id, site_id=policy.site_id, source_provider=POLICY_PROVIDER,
        subject_user=policy.subject_user, status=policy.status, revision=policy.revision,
        authority_generation=policy.authority_generation, schema_version=policy.schema_version,
        valid_from_utc=stored_time(policy.valid_from_utc), valid_until_utc=stored_time(policy.valid_until_utc),
        content_digest=management_policy_digest(policy), policy_json=canonical_json(data))


def policy_from_record(name, get):
    try:
        raw = get("policy_json")
        data = json.loads(raw)
        if not isinstance(data, dict) or canonical_json(data) != raw:
            raise ValueError
        site, provider = data.pop("site_id"), data.pop("source_provider")
        policy = parse_management_policy(data, site_id=site, source_provider=provider)
        expected = policy_record(policy)
        if name != policy.policy_id:
            raise ValueError
        for key, value in expected.items():
            actual = get(key)
            if key.endswith("_utc"):
                actual = stored_time(decode_utc_datetime(actual))
            if actual != value or (type(value) is int and type(actual) is not int):
                raise ValueError
        return policy
    except (TypeError, ValueError, KeyError):
        raise ContractError("POLICY_STORAGE_MISMATCH", "policy") from None


def validate_policy_record(doctype, name, get):
    if doctype == POLICY:
        return policy_from_record(name, get)
    if doctype != POLICY_REVISION:
        raise ContractError("UNSUPPORTED_SOURCE", "policy")
    try:
        snapshot = json.loads(get("snapshot_json"))
        policy = policy_from_record(get("policy"), snapshot.get)
        if (get("record_key") != name or name != revision_key(POLICY, policy.policy_id, policy.revision)
                or type(get("revision")) is not int or get("revision") != policy.revision
                or type(get("previous_revision")) is not int or get("previous_revision") != policy.revision - 1
                or get("snapshot_json") != canonical_json(snapshot)
                or get("snapshot_digest") != digest(snapshot)):
            raise ValueError
        for key, maximum in (("actor", 140), ("reason", 500)):
            text = get(key)
            if not isinstance(text, str) or not text.strip() or text != text.strip() or len(text) > maximum:
                raise ValueError
        if get("actor") == "Guest":
            raise ValueError
        reference = get("approval_source_ref")
        if reference not in (None, "") and (not isinstance(reference, str) or not reference.strip() or len(reference) > 140):
            raise ValueError
        if policy.status == "active" and not reference:
            raise ValueError
        decode_utc_datetime(get("recorded_at_utc"))
        return policy
    except (TypeError, ValueError, KeyError, AttributeError):
        raise ContractError("POLICY_STORAGE_MISMATCH", "policy.revision") from None


@dataclass(frozen=True, slots=True)
class PolicyApprovalPin:
    site_id: str
    database_sha256: str
    policy_id: str
    revision: int
    authority_generation: int
    subject_user: str
    content_digest: str
    approval_json: str
    source_ref: str


class PinnedPolicyApprovalVerifier:
    """Exact preverified server pins, not request data or an approval workflow.

    Production has no configured pins. A privileged Python caller can supply
    dependencies; this does not defend against an attacker controlling that code.
    """
    def __init__(self, pins=()):
        if type(pins) not in (tuple, list) or any(type(pin) is not PolicyApprovalPin for pin in pins):
            raise ContractError("INVALID_APPROVAL_SOURCE", "pins")
        self._pins = tuple(pins)

    def verify(self, policy, *, database_sha256, now_utc):
        data = policy_data(policy)
        approval = policy.approval
        if (approval is None or approval.approved_by in ("Guest", policy.subject_user)
                or approval.approved_at_utc > now_utc or approval.approved_revision != policy.revision
                or approval.approved_authority_generation != policy.authority_generation
                or approval.content_digest != management_policy_digest(policy)):
            raise ContractError("POLICY_APPROVAL_REQUIRED", "policy")
        expected = (policy.site_id, database_sha256, policy.policy_id, policy.revision,
            policy.authority_generation, policy.subject_user, management_policy_digest(policy), canonical_json(data["approval"]))
        matches = tuple(pin for pin in self._pins if (
            pin.site_id, pin.database_sha256, pin.policy_id, pin.revision, pin.authority_generation,
            pin.subject_user, pin.content_digest, pin.approval_json) == expected
            and type(pin.revision) is int and type(pin.authority_generation) is int
            and isinstance(pin.source_ref, str) and 0 < len(pin.source_ref) <= 140
            and pin.source_ref == pin.source_ref.strip())
        if len(matches) != 1:
            raise ContractError("POLICY_APPROVAL_REQUIRED", "policy")
        return matches[0].source_ref
