from __future__ import annotations
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass
from .execution_plan import Actor, Client, ServicePrincipal, AuthorizedExecutionPlan, iso, timestamp
from .r1_contract import SearchRequest, CONTRACT_VERSION
from .internal_contract import InternalRequest, InternalResponse, PHASES
from .errors import KnowledgeError

@dataclass(frozen=True)
class DecisionTicket:
    decision_ref: str
    plan: AuthorizedExecutionPlan
    request: SearchRequest
    request_fingerprint: str
    plan_digest: str
    deadline_at: str

    def call(self, operation, phase, references=()):
        return InternalRequest(CONTRACT_VERSION, operation, self.decision_ref,
            self.plan.request_id, self.plan.action, phase, self.request_fingerprint,
            self.plan_digest, self.deadline_at, tuple(references))

class DecisionStore:
    # Real durable store / Redis multi-process transaction NOT IMPLEMENTED.
    test_only = True
    def __init__(self, provider, quota, *, clock=time.time, deadline_seconds=12):
        if not 0 < deadline_seconds <= 60:
            raise ValueError("deadline bound")
        self.provider, self.quota, self.clock, self.deadline_seconds = provider, quota, clock, deadline_seconds
        self._fingerprint_key = secrets.token_bytes(32)
        self._entries, self._identities, self._phases = {}, {}, {}
        self._lock = threading.RLock()

    def fingerprint(self, request: SearchRequest):
        # Internal keyed binding, NEVER returned to employees or logged.
        value = json.dumps(request.to_wire(), sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return hmac.new(self._fingerprint_key, value.encode(), hashlib.sha256).hexdigest()

    def issue(self, actor: Actor, client: Client, action: str, request: SearchRequest, request_id: str):
        if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
            raise KnowledgeError("INVALID_REQUEST")
        fingerprint = self.fingerprint(request)
        key = (actor.user_ref, actor.session_ref, client, action, request_id)
        with self._lock:
            prior = self._identities.get(key)
            if prior:
                ticket = self._entries[prior]
                if ticket.request_fingerprint != fingerprint:
                    raise KnowledgeError("REPLAY_REJECTED")
                # Idempotent retry is NOT a cached allow.
                self._validate_ticket(ticket)
                self.provider.revalidate(ticket.plan)
                self.quota.reserve_request(actor.user_ref, request_id, action + ":" + fingerprint)
                return ticket
            plan = self.provider.evaluate(actor, client, action, request, request_id)
            self.quota.reserve_request(actor.user_ref, request_id, action + ":" + fingerprint,
                                       limit=plan.limits.requests_per_minute)
            digest = hashlib.sha256(json.dumps(plan.to_wire(), sort_keys=True, ensure_ascii=True).encode()).hexdigest()
            ticket = DecisionTicket(secrets.token_urlsafe(32), plan, request, fingerprint, digest,
                                    iso(min(self.clock() + self.deadline_seconds, timestamp(plan.expires_at))))
            self._entries[ticket.decision_ref] = ticket
            self._identities[key] = ticket.decision_ref
            self._phases[ticket.decision_ref] = set()
            return ticket

    def _validate_ticket(self, ticket):
        if self.clock() >= timestamp(ticket.deadline_at) or self.clock() >= timestamp(ticket.plan.expires_at):
            raise KnowledgeError("DECISION_EXPIRED")

    def verify_request(self, decision_ref, request: SearchRequest):
        with self._lock:
            ticket = self._entries.get(decision_ref)
            if ticket is None:
                raise KnowledgeError("SCOPE_REJECTED")
            if ticket.request_fingerprint != self.fingerprint(request):
                raise KnowledgeError("REPLAY_REJECTED")

    def online(self, principal: ServicePrincipal, call: InternalRequest):
        with self._lock:
            if not principal.authenticated:
                raise KnowledgeError("CLIENT_AUTH_FAILED")
            if not isinstance(call.references, tuple) or call.contract_version != CONTRACT_VERSION or call.phase not in PHASES:
                raise KnowledgeError("INVALID_REQUEST")
            ticket = self._entries.get(call.decision_ref)
            if not ticket:
                raise KnowledgeError("SCOPE_REJECTED")
            plan = ticket.plan
            if principal.client != plan.client:
                raise KnowledgeError("CLIENT_AUTH_FAILED")
            expected = (plan.request_id, plan.action, ticket.request_fingerprint, ticket.plan_digest, ticket.deadline_at)
            actual = (call.request_id, call.action, call.request_fingerprint, call.plan_digest, call.deadline_at)
            if actual != expected:
                raise KnowledgeError("REPLAY_REJECTED")
            self._validate_ticket(ticket)
            phases = self._phases[call.decision_ref]
            valid = {
                "introspect": call.operation == "introspect",
                "cache_read": call.operation == "introspect" and "introspect" in phases,
                "pre_retrieval": call.operation == "revalidate" and "introspect" in phases,
                "post_retrieval": call.operation == "revalidate" and "pre_retrieval" in phases,
                "pre_projection": call.operation == "revalidate" and bool({"post_retrieval","cache_read"} & phases),
                "pre_issue": call.operation == "authorize-evidence" and "pre_projection" in phases,
                "evidence_read": call.operation == "authorize-evidence" and "introspect" in phases,
                "document_read": call.operation == "authorize-evidence" and "introspect" in phases,
                "final_publish": call.operation == "revalidate" and bool({"pre_projection","pre_issue","evidence_read","document_read"} & phases),
            }
            if not valid[call.phase]:
                raise KnowledgeError("INVALID_REQUEST")
            if call.operation == "authorize-evidence" and not call.references:
                raise KnowledgeError("EMPTY_SCOPE")
            if call.phase=='document_read' and (len(call.references)!=1 or call.references[0].chunk_id!='CATALOG_METADATA_ONLY'):
                raise KnowledgeError('SCOPE_REJECTED')
            authorized = {(b.binding_ref,b.version_id) for b in plan.bindings}
            for proof in call.references:
                if (proof.binding_ref,proof.version_id) not in authorized or not proof.chunk_id or len(proof.chunk_id)>128:
                    raise KnowledgeError("SCOPE_REJECTED")
            # ALWAYS reads current authority; a repeated phase is not "already consumed".
            self.provider.revalidate(plan)
            phases.add(call.phase)
            return InternalResponse(CONTRACT_VERSION,"ALLOWED",plan.request_id,call.phase,
                                    ticket.plan_digest,ticket.deadline_at,plan=plan)

    def respond(self, principal, call):
        try:
            return self.online(principal,call)
        except KnowledgeError as error:
            outcome = "UNAVAILABLE" if error.status == 503 else "DENIED"
            return InternalResponse(CONTRACT_VERSION,outcome,call.request_id,call.phase,
                                    None,None,error_code=error.code)
