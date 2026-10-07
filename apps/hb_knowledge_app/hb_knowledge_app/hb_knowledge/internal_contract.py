"""Shared R1.1 internal contract. Not an employee-facing identity/proxy API."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .execution_plan import AuthorizedExecutionPlan
from .errors import KnowledgeError
from .r1_contract import CONTRACT_VERSION

PHASES = ("introspect", "pre_retrieval", "post_retrieval", "pre_projection",
          "cache_read", "pre_issue", "evidence_read", "final_publish")

@dataclass(frozen=True)
class ReferenceProof:
    binding_ref: str
    version_id: str
    chunk_id: str

@dataclass(frozen=True)
class InternalRequest:
    contract_version: str
    operation: str
    decision_ref: str
    request_id: str
    action: str
    phase: str
    request_fingerprint: str
    plan_digest: str
    deadline_at: str
    references: tuple[ReferenceProof, ...] = ()

    def to_wire(self):
        value = asdict(self)
        value["references"] = list(value["references"])
        return value

    @classmethod
    def from_wire(cls, value):
        from .r1_contract import validate_structure
        validate_structure("InternalDecisionRequest", value)
        raw = dict(value)
        raw["references"] = tuple(ReferenceProof(**x) for x in raw["references"])
        return cls(**raw)

@dataclass(frozen=True)
class InternalResponse:
    contract_version: str
    outcome: str
    request_id: str
    phase: str
    plan_digest: str | None
    deadline_at: str | None
    budget_owner: str = "HBOS"
    plan: AuthorizedExecutionPlan | None = None
    error_code: str | None = None

    def require_plan(self):
        if self.outcome != "ALLOWED" or self.plan is None:
            raise KnowledgeError(self.error_code or "POLICY_UNAVAILABLE")
        return self.plan

    def to_wire(self):
        value = asdict(self)
        value["plan"] = self.plan.to_wire() if self.plan else None
        return value
