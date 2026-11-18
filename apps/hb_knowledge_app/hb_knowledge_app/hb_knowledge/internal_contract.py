"""Shared R1.1 internal contract. Not an employee-facing identity/proxy API."""
from __future__ import annotations
from dataclasses import dataclass, asdict, fields
from .execution_plan import AuthorizedExecutionPlan
from .errors import KnowledgeError
from .r1_contract import CONTRACT_VERSION

PHASES = ("introspect", "pre_retrieval", "post_retrieval", "pre_projection",
          "cache_read", "pre_issue", "evidence_read", "document_read",
          "document_body_read", "final_publish",
          "pre_general_generation", "post_general_generation")

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
        value = {field.name:getattr(self,field.name) for field in fields(self) if field.name!='plan'}
        value["plan"] = self.plan.to_wire() if self.plan else None
        return value

    def to_revalidation_receipt(self, call, principal):
        """A fresh phase result; never serialize or reissue an authority plan.

        The caller must still obtain this response from DecisionStore.respond,
        which performs the same ticket, phase and current-authority checks.
        Only revalidation consumers that already hold the signed plan use it.
        """
        if call.operation != 'revalidate' or call.references:
            raise KnowledgeError('INVALID_REQUEST')
        if self.outcome == 'ALLOWED' and self.plan is None:
            raise KnowledgeError('POLICY_UNAVAILABLE')
        return {name: getattr(self, name) for name in (
            'contract_version', 'outcome', 'request_id', 'phase', 'plan_digest',
            'deadline_at', 'budget_owner', 'error_code')} | {
            'operation': 'revalidate', 'decision_ref': call.decision_ref,
            'request_fingerprint': call.request_fingerprint,
            'client_id': principal.client.client_id}
