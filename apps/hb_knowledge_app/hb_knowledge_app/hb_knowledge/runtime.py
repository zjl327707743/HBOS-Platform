from __future__ import annotations
from dataclasses import dataclass
from .execution_plan import Actor, Client
from .errors import KnowledgeError

@dataclass
class CandidateRuntime:
    profile: str
    provider: object
    decisions: object
    references: object
    cache: object
    gateway: object
    quota: object
    audit: object
    actor_resolver: object
    client: Client
    checkpoint: object = lambda phase: None

    def __post_init__(self):
        if self.profile not in {"synthetic", "production"}:
            raise KnowledgeError("POLICY_UNAVAILABLE")
        if self.profile == "production" and any(getattr(p,"test_only",False) for p in
             (self.provider,self.decisions,self.references,self.cache,self.gateway,self.quota,self.audit)):
            raise KnowledgeError("POLICY_UNAVAILABLE")

    def actor(self) -> Actor:
        actor = self.actor_resolver()
        if not isinstance(actor, Actor) or not actor.enabled or actor.user_ref == "Guest":
            raise KnowledgeError("AUTHENTICATION_REQUIRED")
        return actor

def load_runtime():
    import frappe
    # Deliberate explicit composition port. Missing real wiring cannot load a fixture.
    runtime = getattr(frappe.local, "hbos_knowledge_runtime", None)
    if not isinstance(runtime, CandidateRuntime):
        import os
        if not (os.environ.get("HBOS_K1C2_SITE") or os.environ.get("HBOS_KNOWLEDGE_REFERENCE_CONFIG")):
            raise KnowledgeError("POLICY_UNAVAILABLE")
        from .frappe_factory import build_runtime
        runtime = build_runtime()
        frappe.local.hbos_knowledge_runtime = runtime
    return runtime
