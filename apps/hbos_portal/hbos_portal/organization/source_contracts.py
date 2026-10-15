"""Immutable offline source evidence, never an authorization decision."""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Mapping

from hbos_portal.authorization.contracts import (
    AssignmentProjection, OfflineResult, PositionProjection, SourceRef,
)


@dataclass(frozen=True, slots=True)
class SourceContext:
    site_id: str
    provider_id: str
    captured_at: datetime


@dataclass(frozen=True, slots=True)
class SourceFingerprint:
    reference: SourceRef
    modified: str


@dataclass(frozen=True, slots=True)
class SourceSnapshot(OfflineResult):
    context: SourceContext
    rows: Mapping[str, Mapping[str, Mapping[str, object]]] = field(repr=False)
    # A declaration by the injector, not proof of a trusted runtime query.
    employee_links_complete: bool
    coverage: str = field(default="provided_set_only", init=False)


@dataclass(frozen=True, slots=True)
class PersonSourceEvidence(OfflineResult):
    context: SourceContext
    requested_ref: SourceRef
    canonical_person_ref: SourceRef | None
    subject_user: str | None
    link_status: str
    qualification_status: str
    reason_codes: tuple[str, ...]
    employee_refs: tuple[SourceRef, ...]
    user_enabled: bool | None
    employee_status: str | None
    company_ref: SourceRef | None
    department_ref: SourceRef | None
    designation_ref: SourceRef | None
    joining_date: date | None
    relieving_date: date | None
    fingerprints: tuple[SourceFingerprint, ...]


@dataclass(frozen=True, slots=True)
class PositionSourceEvidence(OfflineResult):
    projection: PositionProjection
    company_ref: SourceRef
    designation_ref: SourceRef | None
    authorization_generation: int
    fingerprints: tuple[SourceFingerprint, ...]
    snapshot: SourceSnapshot = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class AssignmentSourceEvidence(OfflineResult):
    projection: AssignmentProjection
    person: PersonSourceEvidence
    position: PositionSourceEvidence
    fingerprint: SourceFingerprint
