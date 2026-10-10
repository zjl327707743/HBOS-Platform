from __future__ import annotations
from dataclasses import dataclass
import secrets
import time
from typing import Callable, Protocol
from .repositories import AuthorityRepository, AuthoritySnapshot
from .execution_plan import (Actor, Client, AuthorizedExecutionPlan, Limits,
                             validate_plan, validate_admission, iso, timestamp)
from .r1_contract import SearchRequest, CONTRACT_VERSION, normalize_search
from .errors import KnowledgeError

class PolicyProvider(Protocol):
    def evaluate(self, actor, client, action, request, request_id): ...
    def revalidate(self, plan): ...

class HbosReadOnlyAuthority:
    """Read-through HBOS-owned port, never accepts a request-body authority snapshot.

    Wiring must provide the current User/Session, server-owned legacy pair compiler
    and current Space/Version/Binding reader on every call. There is no memory allow
    fallback, grants editor, IAM impersonation or environment/config dump here.
    """
    test_only = False
    def __init__(self, *, current_user_session: Callable, read_legacy_policy: Callable,
                 compile_current_metadata: Callable, compatibility_lease: Callable):
        self._actor = current_user_session
        self._policy = read_legacy_policy
        self._metadata = compile_current_metadata
        self._lease = compatibility_lease

    def read_current(self, actor: Actor) -> AuthoritySnapshot:
        try:
            current = self._actor(actor)
            # Server-owned legacy source is read-only; flat ranges alone cannot authorize.
            policy = self._policy(actor.user_ref)
            snapshot = self._metadata(current, policy, self._lease())
            if not isinstance(snapshot, AuthoritySnapshot) or snapshot.actor_state != current:
                raise KnowledgeError("POLICY_UNAVAILABLE")
            return snapshot
        except KnowledgeError:
            raise
        except Exception:
            raise KnowledgeError("POLICY_UNAVAILABLE") from None

class LegacyHbosPolicyProvider:
    provider_kind="HBOS_LEGACY_READONLY"
    def __init__(self, repository: AuthorityRepository, *, environment: str, clock=time.time):
        if environment not in {"production", "synthetic"} or (environment == "production" and repository.test_only):
            raise KnowledgeError("POLICY_UNAVAILABLE")
        self.repository, self.environment, self.clock = repository, environment, clock

    @property
    def test_only(self):
        return self.repository.test_only

    def _current(self, actor: Actor, client: Client):
        if not actor.user_ref or actor.user_ref == "Guest":
            raise KnowledgeError("AUTHENTICATION_REQUIRED")
        try:
            snapshot = self.repository.read_current(actor)
        except KnowledgeError:
            raise
        except Exception:
            raise KnowledgeError("POLICY_UNAVAILABLE") from None
        current = snapshot.actor_state
        if (current.actor != actor or not current.actor.enabled or not current.session_valid):
            raise KnowledgeError("AUTHENTICATION_REQUIRED")
        if client.audience != "knowledge-gateway" or client not in snapshot.clients:
            raise KnowledgeError("CLIENT_AUTH_FAILED")
        expiry = snapshot.provider.compatibility_expires_at
        if (snapshot.provider.kind != self.provider_kind or
            (self.provider_kind=="HBOS_LEGACY_READONLY" and (not expiry or timestamp(expiry)<=self.clock())) or
            (self.provider_kind=="INTERNAL_SHARED_REFERENCE" and (self.environment!="production" or expiry is not None))):
            raise KnowledgeError("POLICY_UNAVAILABLE")
        return snapshot

    def evaluate(self, actor: Actor, client: Client, action: str,
                 request: SearchRequest, request_id: str) -> AuthorizedExecutionPlan:
        if not isinstance(request,SearchRequest) or normalize_search(request.to_wire())!=request:
            raise KnowledgeError("INVALID_REQUEST")
        now = self.clock()
        snapshot = self._current(actor, client)
        if action not in {"knowledge.search", "knowledge.evidence", "knowledge.spaces"}:
            raise KnowledgeError("MODEL_NOT_APPROVED")
        grants = tuple(g for g in snapshot.grants if g.action == action
                       and g.role_ref in snapshot.actor_state.roles
                       and g.space_id in snapshot.active_spaces
                       and g.space_id not in snapshot.denied_spaces)
        spaces = tuple(sorted({g.space_id for g in grants}))
        if request.space_ids is not None:
            if not request.space_ids:
                raise KnowledgeError("EMPTY_SCOPE")
            if set(request.space_ids) - set(spaces):
                raise KnowledgeError("SCOPE_REJECTED")
            spaces = request.space_ids
        if not spaces:
            raise KnowledgeError("EMPTY_SCOPE")
        grants = tuple(g for g in grants if g.space_id in spaces)
        selected = []
        for b in snapshot.bindings:
            if b.space_id not in spaces or b.dataset_id not in snapshot.allowed_datasets:
                continue
            if any(getattr(b, key) != value for key, value in request.context):
                continue
            try:
                validate_admission(b, self.environment, now)
            except KnowledgeError:
                continue
            selected.append(b)
        if not selected:
            raise KnowledgeError("EMPTY_SCOPE")
        if not snapshot.query_embedding_admitted:
            raise KnowledgeError("MODEL_NOT_APPROVED")
        # Wire datetimes round to microseconds. Flooring the issue second avoids a
        # rounded timestamp being fractionally later than the validation clock;
        # the authorization lifetime is shortened, never extended past 120s.
        issued = float(int(now))
        expires = min(issued + 120, timestamp(snapshot.provider.compatibility_expires_at)) if snapshot.provider.compatibility_expires_at else issued + 120
        plan = AuthorizedExecutionPlan(CONTRACT_VERSION, secrets.token_urlsafe(24), actor, client,
            action, self.environment, tuple(spaces), grants, tuple(selected),
            snapshot.policy_revision, snapshot.corpus_revision, snapshot.provider,
            request_id, iso(issued), iso(expires), Limits(), snapshot.model_policy_ref, request.search_mode)
        return validate_plan(plan, now=now)

    def revalidate(self, plan: AuthorizedExecutionPlan):
        validate_plan(plan, now=self.clock())
        current = self._current(plan.subject, plan.client)
        if not current.query_embedding_admitted or current.model_policy_ref != plan.model_policy_ref:
            raise KnowledgeError("MODEL_NOT_APPROVED")
        if (current.policy_revision != plan.policy_revision
                or current.corpus_revision != plan.corpus_revision
                or current.provider != plan.provider):
            raise KnowledgeError("SCOPE_REJECTED")
        if any(s not in current.active_spaces or s in current.denied_spaces for s in plan.space_ids):
            raise KnowledgeError("SCOPE_REJECTED")
        # Exact grant pairs plus current roles, not independent role/space sets.
        if any(g not in current.grants or g.role_ref not in current.actor_state.roles for g in plan.grant_pairs):
            raise KnowledgeError("SCOPE_REJECTED")
        for b in plan.bindings:
            if b not in current.bindings or b.dataset_id not in current.allowed_datasets:
                raise KnowledgeError("SCOPE_REJECTED")
            validate_admission(b, self.environment, self.clock())
        return plan

class FrappeLegacyReadOnlyAuthority(HbosReadOnlyAuthority):
    """Concrete READ-ONLY HBOS bridge with explicit missing persistence/session ports.

    User.enabled and role facts are read from Frappe itself. Session validity/revision
    and current paired metadata need HBOS-owned readers. No readers => no instance,
    no fake IAM and no inferred Dataset x Document relationship. NOT live-tested.
    """
    def __init__(self, frappe_api, *, session_proof_reader, internal_user_reader,
                 metadata_reader, lease_reader):
        from dataclasses import replace
        from .policy import policy_for_subject, SEARCH_CAPABILITY
        from .repositories import ActorState
        for reader in (session_proof_reader,internal_user_reader,metadata_reader,lease_reader):
            if not callable(reader):
                raise KnowledgeError("POLICY_UNAVAILABLE")
        def current_actor(actor):
            if not frappe_api.db.get_value("User",actor.user_ref,"enabled"):
                raise KnowledgeError("AUTHENTICATION_REQUIRED")
            # Reader resolves HBOS-private native session facts from an opaque Actor.
            # A service callback's native request session is deliberately irrelevant.
            current=session_proof_reader(actor)
            roles=tuple(frappe_api.get_roles(actor.user_ref))
            if not isinstance(current,ActorState) or current.actor!=actor or not current.session_valid or current.roles!=roles:
                raise KnowledgeError("AUTHENTICATION_REQUIRED")
            return current
        def legacy_policy(subject):
            return policy_for_subject(frappe_api.conf.get("hbos_knowledge_policy"),subject,
                         internal_user=bool(internal_user_reader(subject)))
        def paired_metadata(current,policy,lease):
            if not policy.can_enter or SEARCH_CAPABILITY not in policy.capabilities:
                raise KnowledgeError("SCOPE_REJECTED")
            snapshot=metadata_reader(current,lease)
            if not isinstance(snapshot,AuthoritySnapshot):
                raise KnowledgeError("POLICY_UNAVAILABLE")
            # Flat legacy values ONLY narrow current HBOS-owned paired metadata.
            # They never manufacture missing bindings or employee grant rows.
            selected=tuple(b for b in snapshot.bindings if b.dataset_alias in policy.dataset_ids
                           and b.canonical_document_id in policy.document_ids)
            return replace(snapshot,bindings=selected)
        super().__init__(current_user_session=current_actor,read_legacy_policy=legacy_policy,
                         compile_current_metadata=paired_metadata,compatibility_lease=lease_reader)
