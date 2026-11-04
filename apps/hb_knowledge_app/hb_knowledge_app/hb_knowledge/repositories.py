"""Authority and reference ports; no editable employee database in this candidate."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .execution_plan import Actor, Client, GrantPair, Binding, ProviderStamp

@dataclass(frozen=True)
class ActorState:
    actor: Actor
    roles: tuple[str, ...]
    session_valid: bool

@dataclass(frozen=True)
class AuthoritySnapshot:
    actor_state: ActorState
    clients: tuple[Client, ...]
    grants: tuple[GrantPair, ...]
    active_spaces: tuple[str, ...]
    bindings: tuple[Binding, ...]
    allowed_datasets: tuple[str, ...]
    denied_spaces: tuple[str, ...]
    policy_revision: str
    corpus_revision: str
    provider: ProviderStamp
    model_policy_ref: str
    query_embedding_admitted: bool
    space_titles: tuple[tuple[str, str], ...] = ()

class AuthorityRepository(Protocol):
    test_only: bool
    def read_current(self, actor: Actor) -> AuthoritySnapshot: ...

@dataclass(frozen=True)
class KnowledgeReference:
    reference_id: str
    actor: Actor
    client: Client
    binding: Binding
    chunk_id: str
    excerpt: str
    page_number: int | None
    issued_at: float
    expires_at: float
    policy_revision: str
    corpus_revision: str

class ReferenceRepository(Protocol):
    test_only: bool
    def put(self, reference: KnowledgeReference) -> None: ...
    def get(self, reference_id: str) -> KnowledgeReference | None: ...
