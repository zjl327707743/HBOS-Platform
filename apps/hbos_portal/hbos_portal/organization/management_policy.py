"""Pure, explicitly injected management-policy validation and evaluation.

Nothing here verifies a Site, database lock, approval source or native session.
Even a matched result is validation_only, never a live ManagementDecision.
"""
from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
import re

from hbos_portal.authorization.errors import ContractError
from .management_contracts import (
    MANAGEMENT_OPERATIONS, ManagementApproval, ManagementAssignmentFacts,
    ManagementContext, ManagementHistoricalScope, ManagementMatch, ManagementPersonFacts,
    ManagementPersonScope, ManagementPolicy, ManagementPositionFacts,
    ManagementRule, OfflineManagementEvaluation,
)
from .source_adapter import parse_rfc3339_utc
from .storage_schema import ASSIGNMENT, POSITION, PROVIDER, digest, require_uuid, revision_key


def _fail(code, path):
    raise ContractError(code, path)


def _fields(value, names, path):
    if not isinstance(value, Mapping) or set(value) != set(names.split()):
        _fail("INVALID_FIELDS", path)
    return dict(value)


def _text(value, path):
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > 140 or "*" in value or value.upper() == "ALL"
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        _fail("INVALID_TEXT", path)
    return value


def _version(value, path, minimum=1):
    if type(value) is not int or value < minimum:
        _fail("INVALID_VERSION", path)
    return value


def _choice(value, choices, path):
    if not isinstance(value, str) or value not in choices:
        _fail("INVALID_VALUE", path)
    return value


def _boolean(value, path):
    if type(value) is not bool:
        _fail("INVALID_TYPE", path)
    return value


def _optional_text(value, path):
    return None if value is None else _text(value, path)


def _time(value):
    return parse_rfc3339_utc(value)


def _ids(value, path):
    if type(value) not in (list, tuple) or not value:
        _fail("INVALID_COLLECTION", path)
    result = tuple(_text(item, path) for item in value)
    if len(set(result)) != len(result):
        _fail("DUPLICATE_ID", path)
    return tuple(sorted(result))


def _operation(operation_id, version):
    if not isinstance(operation_id, str) or operation_id not in MANAGEMENT_OPERATIONS:
        _fail("UNKNOWN_OPERATION", "operation")
    operation = MANAGEMENT_OPERATIONS[operation_id]
    if type(version) is not int or version != operation.schema_version:
        _fail("UNSUPPORTED_VERSION", "operation.version")
    return operation


def _rule(value):
    row = _fields(value, "rule_id operation_schema_version operation_ids company_id "
                  "target_department_ids include_children assignment_until_limit_utc person_scope", "rule")
    operations = _ids(row["operation_ids"], "rule.operations")
    definitions = tuple(_operation(key, row["operation_schema_version"]) for key in operations)
    company = _text(row["company_id"], "rule.company")
    if row["include_children"] is not False:
        _fail("UNSUPPORTED_SCOPE", "rule.include_children")
    person = None
    if row["person_scope"] is not None:
        scope = _fields(row["person_scope"], "source_type company_id department_ids", "rule.person_scope")
        person = ManagementPersonScope(_choice(scope["source_type"], ("Employee",), "rule.person.source"),
            _text(scope["company_id"], "rule.person.company"), _ids(scope["department_ids"], "rule.person.departments"))
        if person.company_id != company:
            _fail("UNSUPPORTED_SCOPE", "rule.person.company")
    if any(op.family != "position" for op in definitions) and person is None:
        _fail("INCOMPLETE_SCOPE", "rule.person_scope")
    limit = None if row["assignment_until_limit_utc"] is None else _time(row["assignment_until_limit_utc"])
    if any(op.family == "assignment" and op.verb == "create" for op in definitions) and limit is None:
        _fail("INCOMPLETE_SCOPE", "rule.assignment_until_limit_utc")
    return ManagementRule(_text(row["rule_id"], "rule.id"), row["operation_schema_version"], operations,
        company, _ids(row["target_department_ids"], "rule.departments"), False, limit, person)


def parse_management_policy(payload, *, site_id, source_provider):
    """Bindings come from the injector; injected values are not runtime proof."""
    row = _fields(payload, "policy_id subject_user status revision authority_generation schema_version "
                  "valid_from_utc valid_until_utc approval rules", "policy")
    if type(row["schema_version"]) is not int or row["schema_version"] != 1:
        _fail("UNSUPPORTED_VERSION", "policy.schema_version")
    if type(row["rules"]) not in (list, tuple) or not row["rules"]:
        _fail("INVALID_COLLECTION", "policy.rules")
    rules = tuple(_rule(rule) for rule in row["rules"])
    if len({rule.rule_id for rule in rules}) != len(rules):
        _fail("DUPLICATE_ID", "policy.rules")
    start, end = _time(row["valid_from_utc"]), _time(row["valid_until_utc"])
    if start >= end:
        _fail("INVALID_INTERVAL", "policy.time")
    approval = None
    if row["approval"] is not None:
        item = _fields(row["approval"], "approval_ref approved_by approved_at_utc approved_revision "
                       "approved_authority_generation content_digest", "approval")
        if not isinstance(item["content_digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["content_digest"]):
            _fail("INVALID_DIGEST", "approval.content_digest")
        approval = ManagementApproval(_text(item["approval_ref"], "approval.ref"),
            _text(item["approved_by"], "approval.actor"), _time(item["approved_at_utc"]),
            _version(item["approved_revision"], "approval.revision"),
            _version(item["approved_authority_generation"], "approval.generation"), item["content_digest"])
    return ManagementPolicy(_text(site_id, "site"), _text(source_provider, "provider"),
        require_uuid(row["policy_id"], "policy.id"), _text(row["subject_user"], "policy.subject"),
        _choice(row["status"], ("draft", "active", "inactive", "revoked"), "policy.status"),
        _version(row["revision"], "policy.revision"), _version(row["authority_generation"], "policy.generation"),
        1, start, end, approval, tuple(sorted(rules, key=lambda rule: rule.rule_id)))


def _position(value):
    if value is None:
        return None
    row = _fields(value, "record_id company_id department_id title designation_id status revision", "position")
    return ManagementPositionFacts(require_uuid(row["record_id"], "position.id"),
        _text(row["company_id"], "position.company"), _text(row["department_id"], "position.department"),
        _text(row["title"], "position.title"), _optional_text(row["designation_id"], "position.designation"),
        _choice(row["status"], ("active", "inactive", "revoked"), "position.status"),
        _version(row["revision"], "position.revision"))


def _assignment(value):
    if value is None:
        return None
    row = _fields(value, "record_id position_id person_source_id subject_user status is_primary "
                  "valid_from_utc valid_until_utc revision", "assignment")
    start = _time(row["valid_from_utc"])
    end = None if row["valid_until_utc"] is None else _time(row["valid_until_utc"])
    if end is not None and start >= end:
        _fail("INVALID_INTERVAL", "assignment.time")
    return ManagementAssignmentFacts(require_uuid(row["record_id"], "assignment.id"),
        require_uuid(row["position_id"], "assignment.position"), _text(row["person_source_id"], "assignment.person"),
        _optional_text(row["subject_user"], "assignment.subject"),
        _choice(row["status"], ("active", "inactive", "revoked"), "assignment.status"),
        _boolean(row["is_primary"], "assignment.is_primary"), start, end,
        _version(row["revision"], "assignment.revision"))


def _person(value):
    if value is None:
        return None
    row = _fields(value, "source_type source_id company_id department_id link_status subject_user "
                  "employee_status user_enabled", "person")
    link = _choice(row["link_status"], ("linked", "unlinked", "ambiguous", "unknown"), "person.link")
    subject = _optional_text(row["subject_user"], "person.subject")
    enabled = None if row["user_enabled"] is None else _boolean(row["user_enabled"], "person.user_enabled")
    if ((link == "linked" and (subject is None or enabled is None))
            or (link != "linked" and (subject is not None or enabled is not None))):
        _fail("INCONSISTENT_PERSON", "person.link")
    return ManagementPersonFacts(_choice(row["source_type"], ("Employee",), "person.source"),
        _text(row["source_id"], "person.id"), _text(row["company_id"], "person.company"),
        _text(row["department_id"], "person.department"), link, subject,
        _text(row["employee_status"], "person.employee_status"), enabled)


def parse_management_context(payload, *, site_id, policy_provider_id, actor_user, actor_enabled):
    """Only for server-built factual contexts; not an HTTP payload parser."""
    if not isinstance(payload, Mapping):
        _fail("INVALID_FIELDS", "context")
    data = dict(payload)
    historical = _historical_scope(data.pop("historical_scope", None))
    row = _fields(data, "operation_id operation_schema_version now_utc expected_revision organization_status "
                  "position_before position_after assignment_before assignment_after person", "context")
    _operation(row["operation_id"], row["operation_schema_version"])
    return ManagementContext(_text(site_id, "site"), _text(policy_provider_id, "provider"),
        _text(actor_user, "actor"), _boolean(actor_enabled, "actor.enabled"),
        row["operation_id"], row["operation_schema_version"], _time(row["now_utc"]),
        _version(row["expected_revision"], "expected_revision", 0),
        _choice(row["organization_status"], ("active", "disabled", "unknown", "historical"), "organization.status"),
        _position(row["position_before"]), _position(row["position_after"]),
        _assignment(row["assignment_before"]), _assignment(row["assignment_after"]), _person(row["person"]), historical)


def _historical_scope(value):
    if value is None:
        return None
    row = _fields(value, "site_id source_provider record_kind record_id revision revision_ref "
        "company_id department_id person_source_id person_company_id person_department_id subject_user", "historical_scope")
    kind = _choice(row["record_kind"], (POSITION, ASSIGNMENT), "historical_scope.kind")
    key = require_uuid(row["record_id"], "historical_scope.id")
    revision = _version(row["revision"], "historical_scope.revision")
    if row["source_provider"] != PROVIDER or row["revision_ref"] != revision_key(kind, key, revision):
        _fail("HISTORICAL_SCOPE_REQUIRED", "historical_scope.ref")
    return ManagementHistoricalScope(_text(row["site_id"], "historical_scope.site"), PROVIDER, kind, key,
        revision, row["revision_ref"], _text(row["company_id"], "historical_scope.company"),
        _text(row["department_id"], "historical_scope.department"),
        *(_optional_text(row[field], "historical_scope." + field) for field in
          ("person_source_id", "person_company_id", "person_department_id", "subject_user")))


def _export(value):
    if isinstance(value, datetime):
        # Do not turn a forged naive datetime into an implicitly trusted UTC time.
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _export(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_export(item) for item in value]
    return value


def _validated_policy(policy):
    if type(policy) is not ManagementPolicy:
        _fail("INVALID_TYPE", "policy")
    row = _export(asdict(policy))
    site, provider = row.pop("site_id"), row.pop("source_provider")
    row.pop("validation_only")
    row.pop("runtime_verified")
    return parse_management_policy(row, site_id=site, source_provider=provider)


def _validated_context(context):
    if type(context) is not ManagementContext:
        _fail("INVALID_TYPE", "context")
    row = _export(asdict(context))
    bindings = {key: row.pop(key) for key in ("site_id", "policy_provider_id", "actor_user", "actor_enabled")}
    row.pop("validation_only")
    row.pop("runtime_verified")
    return parse_management_context(row, **bindings)


def _policy_digest(policy):
    row = _export(asdict(policy))
    for key in ("approval", "status", "validation_only", "runtime_verified"):
        row.pop(key)
    return digest(row)


def management_policy_digest(policy):
    """Fixed, normalized content including identity/revision/generation bindings."""
    return _policy_digest(_validated_policy(policy))


def _strict_assignment_reduction(old, new):
    if old is None or new is None:
        return False
    fixed = ("record_id", "position_id", "person_source_id", "subject_user", "is_primary", "valid_from_utc")
    if any(getattr(old, key) != getattr(new, key) for key in fixed):
        return False
    # Do not call a compound restoration + shortening a reduction.
    if new.status != old.status and not (old.status == "active" and new.status in ("inactive", "revoked")
                                         or old.status == "inactive" and new.status == "revoked"):
        return False
    if old.valid_until_utc is not None and (new.valid_until_utc is None or new.valid_until_utc > old.valid_until_utc):
        return False
    return old.status != new.status or old.valid_until_utc != new.valid_until_utc


def _strict_position_reduction(old, new):
    if old is None or new is None:
        return False
    return (all(getattr(old, field) == getattr(new, field) for field in
        ("record_id", "company_id", "department_id", "title", "designation_id"))
        and (old.status == "active" and new.status in ("inactive", "revoked")
             or old.status == "inactive" and new.status == "revoked"))


def _historical_reason(context, operation):
    history = context.historical_scope
    old = context.assignment_before if operation.family == "assignment" else context.position_before
    position = context.position_before
    if (history is None or operation.verb != "update" or old is None or position is None
            or history.site_id != context.site_id or history.record_id != old.record_id
            or history.revision != old.revision or history.company_id != position.company_id
            or history.department_id != position.department_id):
        return "HISTORICAL_SCOPE_REQUIRED"
    if operation.family == "position":
        if (history.record_kind != POSITION or not _strict_position_reduction(old, context.position_after)
                or any(getattr(history, field) is not None for field in
                    ("person_source_id", "person_company_id", "person_department_id", "subject_user"))):
            return "HISTORICAL_SCOPE_REQUIRED"
    elif operation.family == "assignment":
        person = context.person
        if (history.record_kind != ASSIGNMENT or not _strict_assignment_reduction(old, context.assignment_after)
                or person is None or history.person_source_id != old.person_source_id
                or history.person_source_id != person.source_id or history.subject_user != old.subject_user
                or history.person_company_id != person.company_id or history.person_department_id != person.department_id):
            return "HISTORICAL_SCOPE_REQUIRED"
    else:
        return "HISTORICAL_SCOPE_REQUIRED"
    return None


def _context_reason(context, operation):
    if not context.actor_enabled or context.actor_user == "Guest":
        return "ACTOR_UNAVAILABLE"
    pb, pa = context.position_before, context.position_after
    ab, aa, person = context.assignment_before, context.assignment_after, context.person
    if operation.family == "person":
        if person is None or any(item is not None for item in (pb, pa, ab, aa)) or context.expected_revision != 0:
            return "INVALID_CONTEXT"
    elif operation.family == "position":
        if any(item is not None for item in (ab, aa, person)):
            return "INVALID_CONTEXT"
        if operation.verb == "create":
            if pb is not None or pa is None or pa.revision != 1 or context.expected_revision != 0:
                return "INVALID_CONTEXT"
        elif operation.verb == "read":
            if pb is None or pa is not None or context.expected_revision != pb.revision:
                return "INVALID_CONTEXT"
        else:
            if pb is None or pa is None or context.expected_revision != pb.revision or pa.revision != pb.revision + 1:
                return "REVISION_CONFLICT"
            if any(getattr(pb, key) != getattr(pa, key) for key in ("record_id", "company_id", "department_id")):
                return "NEW_RELATION_REQUIRED"
    else:
        if person is None or pb is None or pa is not None:
            return "INVALID_CONTEXT"
        if operation.verb == "create":
            if ab is not None or aa is None or aa.revision != 1 or context.expected_revision != 0:
                return "INVALID_CONTEXT"
        elif operation.verb == "read":
            if ab is None or aa is not None or context.expected_revision != ab.revision:
                return "INVALID_CONTEXT"
        else:
            if ab is None or aa is None or context.expected_revision != ab.revision or aa.revision != ab.revision + 1:
                return "REVISION_CONFLICT"
            fixed = ("record_id", "position_id", "person_source_id", "subject_user", "valid_from_utc")
            if any(getattr(ab, key) != getattr(aa, key) for key in fixed):
                return "NEW_RELATION_REQUIRED"
        target = aa or ab
        if target.position_id != pb.record_id or target.person_source_id != person.source_id:
            return "INCONSISTENT_PERSON"
        reduction = operation.verb == "update" and _strict_assignment_reduction(ab, aa)
        if operation.verb != "read" and not reduction:
            if (person.link_status != "linked" or person.subject_user != target.subject_user
                    or person.employee_status != "Active" or not person.user_enabled):
                return "PERSON_UNAVAILABLE"
            if target.subject_user == context.actor_user:
                return "SELF_BENEFIT_DENIED"
            if target.status == "active" and pb.status != "active":
                return "INACTIVE_POSITION"
            if target.valid_until_utc is None:
                return "ASSIGNMENT_LIMIT_REQUIRED"
    if context.organization_status == "historical":
        return _historical_reason(context, operation)
    if context.historical_scope is not None:
        return "INVALID_CONTEXT"
    if context.organization_status == "unknown":
        return "SOURCE_UNAVAILABLE"
    if context.organization_status == "disabled":
        # Historical-scope cleanup remains deliberately unavailable here. These
        # facts do not prove prior ownership; the later native adapter must do so.
        return "HISTORICAL_SCOPE_REQUIRED"
    return None


def evaluate_management_policy(policies, context, *, enabled=False):
    """Match complete rules in explicit synthetic input; default closed."""
    if enabled is not True:
        return OfflineManagementEvaluation(False, ("EVALUATION_DISABLED",), None, None, None)
    context = _validated_context(context)
    if type(policies) not in (list, tuple):
        _fail("INVALID_COLLECTION", "policies")
    policies = tuple(_validated_policy(policy) for policy in policies)
    # Multiple snapshots of one mutable policy must never resurrect its old head.
    if len({policy.policy_id for policy in policies}) != len(policies):
        _fail("DUPLICATE_POLICY", "policies")
    context_digest = digest(_export(asdict(context)))
    operation = _operation(context.operation_id, context.operation_schema_version)
    reason = _context_reason(context, operation)
    if reason:
        return OfflineManagementEvaluation(False, (reason,), context_digest, context.now_utc, None)
    for policy in sorted(policies, key=lambda item: item.policy_id):
        approval = policy.approval
        content_digest = _policy_digest(policy)
        if (policy.site_id != context.site_id or policy.source_provider != context.policy_provider_id
                or policy.subject_user != context.actor_user or policy.status != "active"
                or not policy.valid_from_utc <= context.now_utc < policy.valid_until_utc
                or approval is None or approval.approved_by in ("Guest", policy.subject_user)
                or approval.approved_at_utc > context.now_utc
                or approval.approved_revision != policy.revision
                or approval.approved_authority_generation != policy.authority_generation
                or approval.content_digest != content_digest):
            continue
        for rule in policy.rules:
            if context.operation_id not in rule.operation_ids:
                continue
            position = context.position_after or context.position_before
            if position is not None and (position.company_id != rule.company_id
                                        or position.department_id not in rule.target_department_ids):
                continue
            person = context.person
            if person is not None and (rule.person_scope is None
                    or person.company_id != rule.company_id
                    or person.company_id != rule.person_scope.company_id
                    or person.department_id not in rule.person_scope.department_ids):
                continue
            if operation.family == "assignment" and operation.verb != "read":
                reduction = _strict_assignment_reduction(context.assignment_before, context.assignment_after)
                end = context.assignment_after.valid_until_utc
                if not reduction and (rule.assignment_until_limit_utc is None or end is None
                                      or end > rule.assignment_until_limit_utc):
                    continue
            match = ManagementMatch(policy.policy_id, policy.revision, policy.authority_generation,
                rule.rule_id, approval.approval_ref, content_digest)
            return OfflineManagementEvaluation(True, (), context_digest, context.now_utc, match)
    return OfflineManagementEvaluation(False, ("NO_MATCHING_POLICY",), context_digest, context.now_utc, None)
