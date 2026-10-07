from __future__ import annotations
import secrets
import math
from .errors import KnowledgeError
from .repositories import KnowledgeReference
from .gateway import EvidenceRecord
from .r1_contract import normalize_search
from .execution_plan import timestamp

EVIDENCE_TTL_SECONDS = 300
EVIDENCE_SCHEMA = "k1c2-evidence-1"
EVIDENCE_NAMESPACE = "hbos:k1c2:knowledge:evidence:"

def _evidence_key(evidence_id):
    return EVIDENCE_NAMESPACE + evidence_id

def issue_evidence(cache, ticket, record: EvidenceRecord, *, runtime):
    runtime.provider.revalidate(ticket.plan)
    if record.binding not in ticket.plan.bindings or record.binding_ref != record.binding.binding_ref:
        raise KnowledgeError("UPSTREAM_SCOPE_VIOLATION")
    b=record.binding
    if (record.document_id,record.dataset_id,record.version,record.space_id,record.version_id)!=(b.canonical_document_id,b.dataset_alias,b.business_version,b.space_id,b.version_id):
        raise KnowledgeError("UPSTREAM_SCOPE_VIOLATION")
    from knowledge_service.hbos_gateway.response_projection import public_evidence
    public_evidence(record,"ISSUE_PROJECTION_DEMO",environment=runtime.profile)
    now=runtime.provider.clock()
    reference=KnowledgeReference(secrets.token_urlsafe(24), ticket.plan.subject,ticket.plan.client,
        record.binding,record.chunk_id,record.excerpt,record.page_number,now,now+300,
        ticket.plan.policy_revision,ticket.plan.corpus_revision)
    runtime.references.put(reference)
    evidence_id=secrets.token_urlsafe(32)
    # No excerpt or guessed binding is read from old P1 payloads.
    cache.set_value(_evidence_key(evidence_id),
        {"schema":EVIDENCE_SCHEMA,"reference_id":reference.reference_id,"expires_at":reference.expires_at},
        expires_in_sec=EVIDENCE_TTL_SECONDS)
    return evidence_id

def resolve_evidence(cache, actor, client, evidence_id, *, runtime, request_id):
    if not isinstance(evidence_id,str) or not 1 <= len(evidence_id) <= 128:
        raise KnowledgeError("EVIDENCE_UNAVAILABLE")
    payload=cache.get_value(_evidence_key(evidence_id), expires=True)
    if not isinstance(payload,dict) or set(payload)!={"schema","reference_id","expires_at"} or payload["schema"]!=EVIDENCE_SCHEMA:
        raise KnowledgeError("EVIDENCE_UNAVAILABLE")
    if not isinstance(payload["reference_id"],str) or not payload["reference_id"]:
        raise KnowledgeError("EVIDENCE_UNAVAILABLE")
    reference=runtime.references.get(payload["reference_id"])
    now=runtime.provider.clock()
    if (reference is None or reference.actor!=actor or reference.client!=client
        or type(payload["expires_at"]) not in (int,float) or not math.isfinite(payload["expires_at"]) or payload["expires_at"]!=reference.expires_at
        or now>=reference.expires_at or reference.expires_at-reference.issued_at>300):
        raise KnowledgeError("EVIDENCE_UNAVAILABLE")
    request=normalize_search({"query":"EVIDENCE_LOOKUP","space_ids":[reference.binding.space_id]})
    try:
        ticket=runtime.decisions.issue(actor,client,"knowledge.evidence",request,request_id)
        runtime.decisions.online(__principal(client),ticket.call("introspect","introspect"))
        if (reference.binding not in ticket.plan.bindings or reference.policy_revision!=ticket.plan.policy_revision
                or reference.corpus_revision!=ticket.plan.corpus_revision):
            raise KnowledgeError("EVIDENCE_UNAVAILABLE")
        b=reference.binding
        record=EvidenceRecord(b.canonical_document_id,b.title,b.business_version,
             "SYNTHETIC_ONLY" if b.source_type=="SYNTHETIC_TEST" else b.authority_status,
             b.section,reference.page_number,reference.excerpt,reference.chunk_id,
             b.dataset_alias,b.space_id,b.version_id,b.binding_ref,b)
        runtime.checkpoint("before_evidence_backend")
        runtime.gateway.authorize_evidence(ticket,[record],phase="evidence_read")
        runtime.checkpoint("before_evidence_publication")
        runtime.decisions.online(__principal(client),ticket.call("revalidate","final_publish"))
        return record,ticket
    except KnowledgeError as error:
        if error.code in {"POLICY_UNAVAILABLE","UPSTREAM_UNAVAILABLE","MODEL_NOT_APPROVED",
                          "RATE_LIMITED","EXTRACTION_LIMITED","DECISION_EXPIRED"}:
            raise
        raise KnowledgeError("EVIDENCE_UNAVAILABLE") from None

def __principal(client):
    from .execution_plan import ServicePrincipal
    return ServicePrincipal(client,True)
