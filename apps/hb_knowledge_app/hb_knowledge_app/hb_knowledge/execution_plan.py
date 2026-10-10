from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import math
from .errors import KnowledgeError
from .r1_contract import validate_structure, CONTRACT_VERSION

ACTIONS = ("knowledge.search", "knowledge.evidence", "knowledge.spaces")
ADMISSION = {
    "COMPANY_CONTROLLED": "CONTROLLED_APPROVED",
    "EXTERNAL_REFERENCE": "EXTERNAL_REFERENCE_REVIEWED",
    "ORDINARY_INTERNAL_KNOWLEDGE": "INTERNAL_REFERENCE_REVIEWED",
    "SYNTHETIC_TEST": "SYNTHETIC_ONLY",
}

def timestamp(value: str) -> float:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.timestamp()
    except (TypeError, ValueError, AttributeError, OverflowError):
        raise KnowledgeError("INVALID_REQUEST") from None

def iso(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")

@dataclass(frozen=True)
class Actor:
    user_ref: str
    session_ref: str
    session_revision: str
    enabled: bool = True

@dataclass(frozen=True)
class Client:
    client_id: str
    audience: str = "knowledge-gateway"
    channel: str = "PORTAL"

@dataclass(frozen=True)
class ServicePrincipal:
    # Constructed by the transport authenticator, never deserialized from request data.
    client: Client
    authenticated: bool = False

@dataclass(frozen=True)
class GrantPair:
    role_ref: str
    space_id: str
    action: str
    grant_ref: str

@dataclass(frozen=True)
class Binding:
    space_id: str
    canonical_document_id: str
    version_id: str
    business_version: str | None
    dataset_id: str
    document_id: str
    dataset_alias: str
    binding_ref: str
    binding_revision: str
    source_type: str
    authority_status: str
    valid_from: str
    valid_until: str | None = None
    backend: str = "ragflow"
    publication_state: str = "published"
    withdrawn: bool = False
    mapping_ready: bool = True
    title: str | None = None
    section: str | None = None
    equipment_id: str | None = None
    asset_id: str | None = None
    component_id: str | None = None
    document_number: str | None = None

@dataclass(frozen=True)
class ProviderStamp:
    kind: str
    authority_revision: str
    compatibility_expires_at: str | None

@dataclass(frozen=True)
class Limits:
    max_results: int = 5
    max_excerpt_codepoints: int = 500
    max_answer_codepoints: int = 2000
    requests_per_minute: int = 12
    external_codepoints_per_minute: int = 5000

@dataclass(frozen=True)
class AuthorizedExecutionPlan:
    schema_version: str
    plan_id: str
    subject: Actor
    client: Client
    action: str
    environment: str
    space_ids: tuple[str, ...]
    grant_pairs: tuple[GrantPair, ...]
    bindings: tuple[Binding, ...]
    policy_revision: str
    corpus_revision: str
    provider: ProviderStamp
    request_id: str
    issued_at: str
    expires_at: str
    limits: Limits
    model_policy_ref: str
    search_mode: str = "STANDARD"

    def to_wire(self):
        value = asdict(self)
        for key in ("space_ids", "grant_pairs", "bindings"):
            value[key] = list(value[key])
        return value

def validate_admission(binding: Binding, environment: str, now: float):
    if (binding.backend != "ragflow" or not binding.mapping_ready or binding.withdrawn
            or binding.publication_state != "published"):
        raise KnowledgeError("SCOPE_REJECTED")
    if (ADMISSION.get(binding.source_type) != binding.authority_status and
        not (binding.source_type=="COMPANY_CONTROLLED" and binding.authority_status=="CONTROLLED_REFERENCE_REVIEWED")):
        raise KnowledgeError("SCOPE_REJECTED")
    if environment == "production" and binding.source_type == "SYNTHETIC_TEST":
        raise KnowledgeError("SCOPE_REJECTED")
    if binding.authority_status == "CONTROLLED_APPROVED" and not binding.business_version:
        raise KnowledgeError("SCOPE_REJECTED")
    start = timestamp(binding.valid_from)
    end = timestamp(binding.valid_until) if binding.valid_until else None
    if start > now or (end is not None and (end <= start or end <= now)):
        raise KnowledgeError("SCOPE_REJECTED")

def validate_plan(plan: AuthorizedExecutionPlan, *, now: float,
                  client: Client | None = None, actor: Actor | None = None,
                  action: str | None = None, request_id: str | None = None):
    if not isinstance(plan, AuthorizedExecutionPlan) or not math.isfinite(now):
        raise KnowledgeError("INVALID_REQUEST")
    for field in ("space_ids", "grant_pairs", "bindings"):
        if not isinstance(getattr(plan, field), tuple):
            raise KnowledgeError("INVALID_REQUEST")
    validate_structure("", plan.to_wire(), plan=True)
    def identifiers(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in {"title","section"} or item is None: continue
                identifiers(item)
        elif isinstance(value,(list,tuple)):
            for item in value: identifiers(item)
        elif isinstance(value,str) and (not value.strip() or value!=value.strip()):
            raise KnowledgeError("INVALID_REQUEST")
    identifiers(plan.to_wire())
    issued, expires = timestamp(plan.issued_at), timestamp(plan.expires_at)
    if expires <= issued or expires - issued > 120 or issued > now:
        raise KnowledgeError("INVALID_REQUEST")
    if expires <= now:
        raise KnowledgeError("DECISION_EXPIRED")
    if plan.action not in ACTIONS:
        raise KnowledgeError("MODEL_NOT_APPROVED")
    if not plan.subject.enabled or plan.subject.user_ref == "Guest":
        raise KnowledgeError("AUTHENTICATION_REQUIRED")
    for supplied, expected in ((client, plan.client), (actor, plan.subject),
                               (action, plan.action), (request_id, plan.request_id)):
        if supplied is not None and supplied != expected:
            raise KnowledgeError("SCOPE_REJECTED")
    if plan.provider.kind == "HBOS_LEGACY_READONLY":
        expiry = plan.provider.compatibility_expires_at
        if not expiry or timestamp(expiry) <= now or timestamp(expiry) < expires:
            raise KnowledgeError("POLICY_UNAVAILABLE")
    scopes = set(plan.space_ids)
    grants = {(g.space_id, g.action) for g in plan.grant_pairs}
    if any(g.space_id not in scopes or g.action != plan.action for g in plan.grant_pairs):
        raise KnowledgeError("SCOPE_REJECTED")
    if any((space, plan.action) not in grants for space in scopes):
        raise KnowledgeError("SCOPE_REJECTED")
    if len({b.binding_ref for b in plan.bindings}) != len(plan.bindings):
        raise KnowledgeError("SCOPE_REJECTED")
    # A physical pair cannot ambiguously identify two canonical versions in one plan.
    if len({(b.dataset_id, b.document_id) for b in plan.bindings}) != len(plan.bindings):
        raise KnowledgeError("SCOPE_REJECTED")
    for binding in plan.bindings:
        if binding.space_id not in scopes:
            raise KnowledgeError("SCOPE_REJECTED")
        validate_admission(binding, plan.environment, now)
    return plan

def plan_from_wire(value: dict, *, now: float):
    validate_structure("", value, plan=True)
    raw = dict(value)
    raw["subject"] = Actor(**raw["subject"])
    raw["client"] = Client(**raw["client"])
    raw["provider"] = ProviderStamp(**raw["provider"])
    raw["limits"] = Limits(**raw["limits"])
    raw["space_ids"] = tuple(raw["space_ids"])
    raw["grant_pairs"] = tuple(GrantPair(**g) for g in raw["grant_pairs"])
    raw["bindings"] = tuple(Binding(**b) for b in raw["bindings"])
    return validate_plan(AuthorizedExecutionPlan(**raw), now=now)
