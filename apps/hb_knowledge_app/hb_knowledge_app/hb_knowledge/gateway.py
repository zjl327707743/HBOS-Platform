from __future__ import annotations
from dataclasses import dataclass
from .execution_plan import Binding, ServicePrincipal
from .errors import KnowledgeError
from .internal_contract import ReferenceProof
from .r1_contract import CONTRACT_VERSION

@dataclass(frozen=True)
class EvidenceRecord:
    document_id: str
    title: str | None
    version: str | None
    status_note: str | None
    section: str | None
    page_number: int | None
    excerpt: str
    chunk_id: str
    dataset_id: str
    space_id: str
    version_id: str
    binding_ref: str
    binding: Binding

    @classmethod
    def from_fragment(cls, fragment):
        b=fragment.binding
        return cls(b.canonical_document_id,b.title,b.business_version,
                   "SYNTHETIC_ONLY" if b.source_type=="SYNTHETIC_TEST" else "内部参考／有效性待核" if b.authority_status in {"CONTROLLED_REFERENCE_REVIEWED","INTERNAL_REFERENCE_REVIEWED"} else b.authority_status,
                   b.section,fragment.page_number,fragment.excerpt,fragment.chunk_id,
                   b.dataset_alias,b.space_id,b.version_id,b.binding_ref,b)

def search_body(ticket):
    plan = ticket.plan
    return {**ticket.request.to_wire(), "contract_version": CONTRACT_VERSION,
        "client_id":plan.client.client_id, "subject":plan.subject.user_ref,
        "policy_revision":plan.policy_revision,
        "dataset_ids":sorted({b.dataset_alias for b in plan.bindings}),
        "document_ids":sorted({b.canonical_document_id for b in plan.bindings}),
        "request_id":plan.request_id, "decision_ref":ticket.decision_ref,
        "request_fingerprint":ticket.request_fingerprint, "plan_digest":ticket.plan_digest,
        "deadline_at":ticket.deadline_at}


def document_call(ticket):
    """The one signed internal call shape for a document-body read.

    The proof names the single binding this plan authorizes plus a fixed
    sentinel instead of a native chunk id. Page numbers are read parameters of
    the service route, not authorization material, and the request body never
    carries a dataset/document id or a filesystem path.
    """
    from .document_reader_contract import BODY_READ_SENTINEL
    plan = ticket.plan
    if getattr(plan, "action", None) != "document.read" or len(plan.bindings) != 1:
        raise KnowledgeError("SCOPE_REJECTED")
    binding = plan.bindings[0]
    return ticket.call("authorize-evidence", "document_body_read",
                       (ReferenceProof(binding.binding_ref, binding.version_id,
                                       BODY_READ_SENTINEL),))

class GatewayClient:
    """Trusted BFF boundary to the ONE service core. No legacy/static fallback."""
    def __init__(self, service):
        self.service = service
        self.test_only = getattr(service, "test_only", False)

    @property
    def configured(self):
        return self.service is not None

    def search(self, *, ticket):
        if self.service is None:
            raise KnowledgeError("POLICY_UNAVAILABLE")
        principal = ServicePrincipal(ticket.plan.client, True)
        fragments = self.service.search(search_body(ticket), principal)
        result=[]
        for fragment in fragments:
            if fragment.binding not in ticket.plan.bindings:
                raise KnowledgeError("UPSTREAM_SCOPE_VIOLATION")
            result.append(EvidenceRecord.from_fragment(fragment))
        return result

    def authorize_evidence(self, ticket, records, *, phase):
        if self.service is None:
            raise KnowledgeError("POLICY_UNAVAILABLE")
        proofs=tuple(ReferenceProof(r.binding_ref,r.version_id,r.chunk_id) for r in records)
        return self.service.verify_evidence(ticket.call("authorize-evidence",phase,proofs),
                                           ServicePrincipal(ticket.plan.client, True))

def load_gateway_client():
    from .runtime import load_runtime
    return load_runtime().gateway
