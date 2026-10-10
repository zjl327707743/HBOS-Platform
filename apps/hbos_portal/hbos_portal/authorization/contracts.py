"""Immutable output DTOs; callers submit plain data to the validators."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

from .errors import RegistryFailure


@dataclass(frozen=True, slots=True)
class OfflineResult:
    validation_only: bool = field(default=True, init=False)
    runtime_verified: bool = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class RegistrationInput:
    source_id: str
    expected_app_id: str
    definition: Mapping


@dataclass(frozen=True, slots=True)
class ResourceDefinition:
    resource_id: str
    label: str


@dataclass(frozen=True, slots=True)
class ScopeDefinition:
    scope_type: str
    schema_version: int
    dimension: str
    reference_type: str
    allow_descendants: bool


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    action_id: str
    label: str
    resource_id: str
    scope_types: tuple[str, ...]
    enabled: bool
    implemented: bool
    status: str

    @property
    def declared_available(self) -> bool:
        # This is a manifest claim, never runtime verification.
        return self.enabled and self.implemented and self.status == "active"


@dataclass(frozen=True, slots=True)
class EntryBinding:
    binding_key: str
    action_id: str
    resource_id: str
    scope_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AppDefinition(OfflineResult):
    source_id: str
    contract_version: int
    app_id: str
    definition_revision: str
    resources: tuple[ResourceDefinition, ...]
    scopes: tuple[ScopeDefinition, ...]
    actions: tuple[ActionDefinition, ...]
    bindings: tuple[EntryBinding, ...]


@dataclass(frozen=True, slots=True)
class RegistrySnapshot(OfflineResult):
    apps: Mapping[str, AppDefinition]
    failures: tuple[RegistryFailure, ...]


@dataclass(frozen=True, slots=True)
class TemplateVersion(OfflineResult):
    app_id: str
    template_id: str
    version: int
    action_ids: tuple[str, ...]
    unavailable_action_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoleComponent:
    component_id: str
    template: TemplateVersion


@dataclass(frozen=True, slots=True)
class RoleBundleVersion(OfflineResult):
    role_id: str
    version: int
    components: tuple[RoleComponent, ...]


@dataclass(frozen=True, slots=True)
class ScopeSelection:
    component_id: str
    scope_type: str
    schema_version: int
    dimension: str
    reference_type: str
    reference_ids: tuple[str, ...]
    include_descendants: bool


@dataclass(frozen=True, slots=True)
class PositionBinding(OfflineResult):
    binding_id: str
    version: int
    position_id: str
    role_id: str
    role_version: int
    component_scopes: tuple[ScopeSelection, ...]


@dataclass(frozen=True, slots=True)
class SourceRef:
    source_type: str
    source_id: str


@dataclass(frozen=True, slots=True)
class PositionProjection(OfflineResult):
    position_id: str
    department_ref: SourceRef
    label: str
    status: str
    revision: int


@dataclass(frozen=True, slots=True)
class AssignmentProjection(OfflineResult):
    assignment_id: str
    person_ref: SourceRef
    subject_user: str | None
    position_id: str
    is_primary: bool
    valid_from: datetime
    valid_until: datetime | None
    status: str
    revision: int
    authorization_generation: int
    qualification_status: str


@dataclass(frozen=True, slots=True)
class AssignmentSet(OfflineResult):
    assignments: tuple[AssignmentProjection, ...]
    coverage: str = field(default="provided_set_only", init=False)
