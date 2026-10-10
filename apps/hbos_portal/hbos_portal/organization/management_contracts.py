"""Immutable management-policy inputs/results. No runtime authority or I/O."""
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType

from hbos_portal.authorization.contracts import OfflineResult


@dataclass(frozen=True, slots=True)
class ManagementOperation:
    family: str
    verb: str
    schema_version: int = 1


# Only the seven currently specified operations in this management domain.
# Future semantics require an explicit implementation/version, never a wildcard.
MANAGEMENT_OPERATIONS = MappingProxyType({
    f"hbos.organization.{family}.{verb}": ManagementOperation(family, verb)
    for family, verbs in (("position", ("read", "create", "update")),
                          ("assignment", ("read", "create", "update")),
                          ("person", ("lookup",)))
    for verb in verbs
})


@dataclass(frozen=True, slots=True)
class ManagementPersonScope:
    source_type: str
    company_id: str
    department_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ManagementRule:
    rule_id: str
    operation_schema_version: int
    operation_ids: tuple[str, ...]
    company_id: str
    target_department_ids: tuple[str, ...]
    include_children: bool
    assignment_until_limit_utc: datetime | None
    person_scope: ManagementPersonScope | None


@dataclass(frozen=True, slots=True)
class ManagementApproval:
    approval_ref: str
    approved_by: str
    approved_at_utc: datetime
    approved_revision: int
    approved_authority_generation: int
    content_digest: str


@dataclass(frozen=True, slots=True)
class ManagementPolicy(OfflineResult):
    site_id: str
    source_provider: str
    policy_id: str
    subject_user: str
    status: str
    revision: int
    authority_generation: int
    schema_version: int
    valid_from_utc: datetime
    valid_until_utc: datetime
    approval: ManagementApproval | None
    rules: tuple[ManagementRule, ...]


@dataclass(frozen=True, slots=True)
class ManagementPositionFacts:
    record_id: str
    company_id: str
    department_id: str
    title: str
    designation_id: str | None
    status: str
    revision: int


@dataclass(frozen=True, slots=True)
class ManagementAssignmentFacts:
    record_id: str
    position_id: str
    person_source_id: str
    subject_user: str | None
    status: str
    is_primary: bool
    valid_from_utc: datetime
    valid_until_utc: datetime | None
    revision: int


@dataclass(frozen=True, slots=True)
class ManagementPersonFacts:
    source_type: str
    source_id: str
    company_id: str
    department_id: str
    link_status: str
    subject_user: str | None
    employee_status: str
    user_enabled: bool | None


@dataclass(frozen=True, slots=True)
class ManagementHistoricalScope:
    site_id: str
    source_provider: str
    record_kind: str
    record_id: str
    revision: int
    revision_ref: str
    company_id: str
    department_id: str
    person_source_id: str | None
    person_company_id: str | None
    person_department_id: str | None
    subject_user: str | None


@dataclass(frozen=True, slots=True)
class ManagementContext(OfflineResult):
    site_id: str
    policy_provider_id: str
    actor_user: str
    actor_enabled: bool
    operation_id: str
    operation_schema_version: int
    now_utc: datetime
    expected_revision: int
    organization_status: str
    position_before: ManagementPositionFacts | None
    position_after: ManagementPositionFacts | None
    assignment_before: ManagementAssignmentFacts | None
    assignment_after: ManagementAssignmentFacts | None
    person: ManagementPersonFacts | None
    historical_scope: ManagementHistoricalScope | None = None


@dataclass(frozen=True, slots=True)
class ManagementMatch:
    policy_id: str
    policy_revision: int
    authority_generation: int
    rule_id: str
    approval_ref: str
    policy_digest: str


@dataclass(frozen=True, slots=True)
class OfflineManagementEvaluation(OfflineResult):
    matched: bool
    reason_codes: tuple[str, ...]
    context_digest: str | None
    evaluated_at_utc: datetime | None
    match: ManagementMatch | None
    authorization_effect: str = field(default="none", init=False)
