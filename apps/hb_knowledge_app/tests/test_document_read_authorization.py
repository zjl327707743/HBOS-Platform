"""Controlled document-body reader: authorization, per-page revalidation, DTO safety.

The reader is a separate controlled use case from ``get_evidence`` (500 cp
excerpt). It must reuse the exact same server-side space/role/current-version
snapshot, never accept identity from the request body, never expose physical
dataset/document ids or the upstream address, and re-check authorization on
every page. A withdrawn/bumped/role-revoked source must fail on the next page.
"""
import json
import sys
from dataclasses import replace
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge import document_reader
from hb_knowledge_app.hb_knowledge.audit import SafeAudit
from hb_knowledge_app.hb_knowledge.decision_store import DecisionStore
from hb_knowledge_app.hb_knowledge.document_reader_contract import (
    BODY_READ_SENTINEL, DISCLOSURE, MAX_SEARCH_BLOCKS, PAGE_NUMBERING, PAGE_SIZE,
    TOC_SCAN_PAGES, TOC_SOURCE, normalize_document_read, normalize_page,
)
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.execution_plan import (
    Actor, Binding, Client, GrantPair, ProviderStamp, timestamp,
)
from hb_knowledge_app.hb_knowledge.internal_contract import (
    PHASES, InternalRequest, ReferenceProof,
)
from hb_knowledge_app.hb_knowledge.policy_provider import LegacyHbosPolicyProvider
from hb_knowledge_app.hb_knowledge.r1_contract import CONTRACT_VERSION, normalize_search
from hb_knowledge_app.hb_knowledge.repositories import ActorState, AuthoritySnapshot

NOW = timestamp('2026-10-08T00:00:00Z')
ACTOR = Actor('USER_READER', 'SESSION_READER', 'generation-1')
CLIENT = Client('CLIENT_READER')
DATASET = 'a' * 32
PHYSICAL = 'b' * 32
DOCUMENT = 'DOC_SYNTHETIC_001'
VERSION = 'VER_SYNTHETIC_001'


def make_binding(*, space='SPACE_QA', document=DOCUMENT, version=VERSION,
                 title='合成受控制度', dataset=DATASET, physical=PHYSICAL,
                 withdrawn=False, publication_state='published',
                 source_type='SYNTHETIC_TEST', authority_status='SYNTHETIC_ONLY',
                 binding_ref='BIND_SYNTHETIC_DOCUMENT'):
    return Binding(space, document, version, '4.0', dataset, physical, 'SYNTHETIC',
                   binding_ref, 'REV_SYNTHETIC', source_type, authority_status,
                   '2026-01-01T00:00:00Z', withdrawn=withdrawn,
                   publication_state=publication_state, title=title,
                   document_number='SYN-001')


def snapshot(*, actions=('document.read',), role='ROLE_READER', bindings=None,
             spaces=('SPACE_QA',), titles=(('SPACE_QA', '合成质检'),),
             admitted=False, base=None):
    if base is not None:
        return base
    grants = tuple(GrantPair(role, space, action, f'GRANT_{space}_{action}')
                   for space in spaces for action in actions)
    return AuthoritySnapshot(
        ActorState(ACTOR, (role,), True), (CLIENT,), grants, spaces,
        tuple(bindings if bindings is not None else (make_binding(),)),
        (DATASET,), (), 'policy-fixed', 'corpus-fixed',
        ProviderStamp('HBOS_LEGACY_READONLY', 'bridge-fixed', '2026-12-31T00:00:00Z'),
        'UNAPPROVED_MODEL', admitted, titles)


class Repository:
    test_only = True

    def __init__(self, value):
        self.snapshot = value

    def read_current(self, actor):
        return self.snapshot


class Quota:
    def reserve_request(self, *args, **kwargs):
        return None

    def reserve_output(self, *args, **kwargs):
        return None


class RecordingDecisions(DecisionStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phases = []

    def online(self, principal, call):
        self.phases.append(call.phase)
        return super().online(principal, call)


def page_payload(page=1, *, page_count=12, block_total=96, blocks=None,
                 toc=None, toc_source=TOC_SOURCE, derived=True, extra=None):
    if blocks is None:
        first = (page - 1) * PAGE_SIZE + 1
        blocks = []
        for index in range(PAGE_SIZE):
            ordinal = first + index
            if ordinal > block_total:
                break
            blocks.append({'ordinal': ordinal, 'section': None,
                           'text': f'合成受控正文第{ordinal}段。'})
    if toc is None:
        toc = [{'title': '1. 目的', 'ordinal': 1}]
    payload = {'status': 'SUCCESS', 'page': page, 'page_size': PAGE_SIZE,
               'page_count': page_count, 'block_total': block_total,
               'blocks': blocks, 'toc': toc, 'toc_source': toc_source,
               'derived': derived}
    if extra:
        payload.update(extra)
    return payload


def search_payload(*, matches=None, searched_blocks=96, capped=False):
    if matches is None:
        matches = [{'ordinal': 1, 'page': 1, 'block_id': 'b1', 'snippet': '合成受控正文'}]
    return {'status': 'SUCCESS', 'matches': matches,
            'searched_blocks': searched_blocks, 'capped': capped}


class Gateway:
    test_only = False

    def __init__(self, *, page_pages=None, search=None):
        self.page_pages = page_pages or {}
        self.search = search
        self.page_calls = []
        self.search_calls = []
        self.before_page_return = None
        self.error = None
        self.ticket = None

    def document_page(self, ticket, *, page):
        self.page_calls.append(page)
        self.ticket = ticket
        if self.error:
            raise self.error if isinstance(self.error, KnowledgeError) else KnowledgeError(self.error)
        if self.before_page_return:
            self.before_page_return()
        if page in self.page_pages:
            return self.page_pages[page]
        return page_payload(page)

    def document_search(self, ticket, *, query, limit):
        self.search_calls.append((query, limit))
        self.ticket = ticket
        if self.error:
            raise self.error if isinstance(self.error, KnowledgeError) else KnowledgeError(self.error)
        return self.search or search_payload()


def reader_runtime(*, value=None, gateway=None, clock=None):
    repository = Repository(value if value is not None else snapshot())
    provider = LegacyHbosPolicyProvider(repository, environment='synthetic',
                                        clock=clock or (lambda: NOW))
    quota = Quota()
    decisions = RecordingDecisions(provider, quota, clock=clock or (lambda: NOW),
                                   deadline_seconds=12)
    runtime = SimpleNamespace(profile='synthetic', provider=provider, decisions=decisions,
                              gateway=gateway or Gateway(), quota=quota, audit=SafeAudit(),
                              client=CLIENT, actor=lambda: ACTOR,
                              checkpoint=lambda phase: None, repository=repository)
    return runtime, repository


def candidate_binding(runtime):
    return runtime.repository.snapshot.bindings[0]


def assert_unavailable(call, code='DOCUMENT_READ_UNAVAILABLE', state=None):
    with pytest.raises(KnowledgeError) as failure:
        call()
    assert failure.value.code == code
    if state is not None:
        assert failure.value.state == state
    return failure.value


# ---------------------------------------------------------------------------
# Happy path / contract shape
# ---------------------------------------------------------------------------

def test_current_authorized_document_opens_with_the_frozen_contract():
    runtime, _ = reader_runtime()
    data = document_reader.open_document(runtime, DOCUMENT, None, 'REQ_DOC_OPEN')
    assert set(data) == {'document', 'body', 'navigation', 'disclosure'}
    document, body, navigation = data['document'], data['body'], data['navigation']
    assert document == {
        'document_id': DOCUMENT, 'version_id': VERSION, 'title': '合成受控制度',
        'document_number': 'SYN-001', 'space_id': 'SPACE_QA', 'space_title': '合成质检',
        'business_version': '4.0', 'status_note': 'SYNTHETIC_ONLY',
        'reference_state': 'CURRENT', 'authorization': 'AUTHORIZED',
        'source_type': 'SYNTHETIC_TEST'}
    assert body['origin'] == 'INDEXED_CHUNKS'
    assert body['page_numbering'] == PAGE_NUMBERING == 'UNAVAILABLE'
    assert body['derived'] is True
    assert body['page'] == 1 and body['page_count'] == 12 and body['block_total'] == 96
    assert len(body['blocks']) == PAGE_SIZE
    for index, block in enumerate(body['blocks']):
        assert set(block) == {'block_id', 'ordinal', 'page_number', 'section', 'text'}
        assert block['block_id'] == f'b{block["ordinal"]}'
        assert block['ordinal'] == index + 1
        assert block['page_number'] is None and block['section'] is None
        assert len(block['text']) <= 4000
    assert navigation['toc'] == [{'title': '1. 目的', 'ordinal': 1, 'page_number': None}]
    assert navigation['toc_source'] == TOC_SOURCE == 'ORIGINAL_HEADING_LINES'
    assert data['disclosure'] == DISCLOSURE and '不是原件下载' in data['disclosure']
    # The plan that authorized the read is exactly this one document.
    plan = runtime.gateway.ticket.plan
    assert plan.action == 'document.read'
    assert plan.bindings == (candidate_binding(runtime),)
    # No physical dataset/document id, path, upstream URL or native chunk id.
    text = json.dumps(data, ensure_ascii=False)
    for secret in (DATASET, PHYSICAL, '/api/', 'ragflow', 'http://', 'https://'):
        assert secret not in text
    assert 'b' + '1' in text  # opaque block id is the only ordinal-shaped id


def test_version_is_resolved_when_omitted_and_must_match_the_current_version():
    runtime, _ = reader_runtime()
    opened = document_reader.open_document(runtime, DOCUMENT, VERSION, 'REQ_CURRENT')
    assert opened['document']['version_id'] == VERSION
    # Same logical document without a version resolves the one current binding.
    resolved = document_reader.open_document(runtime, DOCUMENT, None, 'REQ_RESOLVE')
    assert resolved['document']['version_id'] == VERSION
    failure = assert_unavailable(
        lambda: document_reader.open_document(runtime, DOCUMENT, 'VER_OLD_0001', 'REQ_OLD'),
        state='VERSION_STALE')
    assert 'ver_old_0001' not in json.dumps(failure.public_message).lower()


def test_page_read_returns_the_same_shape_and_advances_ordinals():
    runtime, _ = reader_runtime()
    data = document_reader.read_document_page(runtime, DOCUMENT, VERSION, 2, 'REQ_PAGE_2')
    assert set(data) == {'document', 'body', 'navigation', 'disclosure'}
    assert data['body']['page'] == 2
    ordinals = [block['ordinal'] for block in data['body']['blocks']]
    assert ordinals == list(range(PAGE_SIZE + 1, PAGE_SIZE * 2 + 1))
    assert all(block['block_id'] == f'b{block["ordinal"]}' for block in data['body']['blocks'])
    assert data['document']['version_id'] == VERSION


# ---------------------------------------------------------------------------
# Authorization rejection matrix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('actions', [('knowledge.search',), ('knowledge.evidence',)])
def test_missing_document_read_grant_is_unavailable(actions):
    runtime, _ = reader_runtime(value=snapshot(actions=actions))
    failure = assert_unavailable(
        lambda: document_reader.open_document(runtime, DOCUMENT, None, 'REQ_NO_GRANT'),
        state='NOT_AUTHORIZED')
    assert json.loads(json.dumps(failure.public_message))  # fixed safe message only


def test_a_grant_for_another_role_cannot_be_used():
    value = snapshot(actions=('document.read',))
    foreign = replace(value, grants=tuple(
        GrantPair('ROLE_OTHER', g.space_id, g.action, g.grant_ref) for g in value.grants))
    runtime, _ = reader_runtime(value=foreign)
    assert_unavailable(lambda: document_reader.open_document(runtime, DOCUMENT, None, 'REQ_ROLE'),
                       state='NOT_AUTHORIZED')


def test_guest_or_disabled_actor_is_rejected_before_any_plan():
    runtime, _ = reader_runtime()

    def guest():
        raise KnowledgeError('AUTHENTICATION_REQUIRED')

    runtime.actor = guest
    runtime.gateway = Gateway()
    with pytest.raises(KnowledgeError) as failure:
        document_reader.open_document(runtime, DOCUMENT, None, 'REQ_GUEST')
    assert failure.value.code == 'AUTHENTICATION_REQUIRED'
    assert runtime.gateway.page_calls == []


def test_document_bound_to_another_space_is_not_readable():
    foreign = make_binding(space='SPACE_PROD', title='跨空间资料')
    runtime, _ = reader_runtime(value=snapshot(
        actions=('document.read',), spaces=('SPACE_QA',), bindings=(foreign,)))
    assert_unavailable(lambda: document_reader.open_document(runtime, DOCUMENT, None, 'REQ_CROSS'),
                       state='NOT_AUTHORIZED')


def test_unknown_or_another_users_document_is_unavailable():
    runtime, _ = reader_runtime()
    assert_unavailable(
        lambda: document_reader.open_document(runtime, 'DOC_OTHER_USER_001', None, 'REQ_OTHER'),
        state='NOT_AUTHORIZED')


def test_withdrawn_current_version_is_unavailable_with_a_state():
    withdrawn = make_binding(withdrawn=True)
    runtime, _ = reader_runtime(value=snapshot(bindings=(withdrawn,)))
    assert_unavailable(lambda: document_reader.open_document(runtime, DOCUMENT, VERSION, 'REQ_WITHDRAWN'),
                       state='WITHDRAWN')


def test_unpublished_binding_is_unavailable_with_a_state():
    draft = make_binding(publication_state='draft')
    runtime, _ = reader_runtime(value=snapshot(bindings=(draft,)))
    assert_unavailable(lambda: document_reader.open_document(runtime, DOCUMENT, None, 'REQ_DRAFT'),
                       state='NOT_PUBLISHED')


def test_multiple_current_versions_are_ambiguous_and_refused():
    runtime, _ = reader_runtime(value=snapshot(bindings=(
        make_binding(version='VER_SYNTHETIC_001', binding_ref='BIND_A'),
        make_binding(version='VER_SYNTHETIC_002', binding_ref='BIND_B'))))
    assert_unavailable(lambda: document_reader.open_document(runtime, DOCUMENT, None, 'REQ_AMBIG'),
                       state='VERSION_AMBIGUOUS')


@pytest.mark.parametrize('document,version', [
    ('', None), ('DOC/../secret', None), ('https://example.invalid/doc', None),
    ('DOC_SYNTHETIC_001 ', None), ('DOC\x00SYNTHETIC', None), (None, None),
    (123, None), ('DOC_SYNTHETIC_001', ''), ('DOC_SYNTHETIC_001', 'VER/OLD'),
    ('DOC_SYNTHETIC_001', 'VER 2'), ('DOC_SYNTHETIC_001', 42),
    ('D' * 121, None), (DOCUMENT, 'V' * 129)])
def test_malformed_document_or_version_identifiers_are_invalid_requests(document, version):
    runtime, _ = reader_runtime()
    with pytest.raises(KnowledgeError) as failure:
        document_reader.open_document(runtime, document, version, 'REQ_INVALID_ID')
    assert failure.value.code == 'INVALID_REQUEST'
    assert runtime.gateway.page_calls == []


def test_extra_identity_keys_are_rejected_by_the_contract():
    with pytest.raises(KnowledgeError) as failure:
        normalize_document_read({'document_id': DOCUMENT, 'dataset_id': DATASET})
    assert failure.value.code == 'INVALID_REQUEST'
    with pytest.raises(KnowledgeError) as failure:
        normalize_document_read({'document_id': DOCUMENT, 'version_id': None})
    assert failure.value.code == 'INVALID_REQUEST'


@pytest.mark.parametrize('page', [0, 1025, -1, True, 1.0, '1.0', '0', None, [1]])
def test_invalid_page_is_an_invalid_request(page):
    runtime, _ = reader_runtime()
    with pytest.raises(KnowledgeError) as failure:
        document_reader.read_document_page(runtime, DOCUMENT, VERSION, page, 'REQ_BAD_PAGE')
    assert failure.value.code == 'INVALID_REQUEST'
    assert runtime.gateway.page_calls == []


def test_page_beyond_page_count_is_its_own_error():
    runtime, _ = reader_runtime(gateway=Gateway(page_pages={}))
    runtime.gateway.error = 'DOCUMENT_READ_PAGE_OUT_OF_RANGE'
    with pytest.raises(KnowledgeError) as failure:
        document_reader.read_document_page(runtime, DOCUMENT, VERSION, 99, 'REQ_RANGE')
    assert failure.value.code == 'DOCUMENT_READ_PAGE_OUT_OF_RANGE'
    assert normalize_page(3) == 3


# ---------------------------------------------------------------------------
# Per-page reauthorization
# ---------------------------------------------------------------------------

def test_every_page_issues_a_fresh_plan_and_walks_the_authority_phases():
    runtime, _ = reader_runtime()
    document_reader.open_document(runtime, DOCUMENT, VERSION, 'REQ_FIRST')
    first_phases = list(runtime.decisions.phases)
    first_plan = runtime.gateway.ticket.plan.plan_id
    document_reader.read_document_page(runtime, DOCUMENT, VERSION, 2, 'REQ_SECOND')
    second_phases = runtime.decisions.phases[len(first_phases):]
    assert first_phases == ['introspect', 'document_body_read', 'final_publish']
    assert second_phases == ['introspect', 'document_body_read', 'final_publish']
    assert runtime.gateway.ticket.plan.plan_id != first_plan
    assert runtime.gateway.page_calls == [1, 2]


def test_withdrawal_between_page_read_and_return_rejects_the_page():
    runtime, repository = reader_runtime()
    binding = candidate_binding(runtime)

    def withdraw():
        repository.snapshot = replace(repository.snapshot,
                                      bindings=(replace(binding, withdrawn=True),))

    runtime.gateway.before_page_return = withdraw
    assert_unavailable(lambda: document_reader.read_document_page(
        runtime, DOCUMENT, VERSION, 2, 'REQ_WITHDRAWN_MID'))


def test_role_removal_between_page_read_and_return_rejects_the_page():
    runtime, repository = reader_runtime()
    binding = candidate_binding(runtime)

    def revoke():
        repository.snapshot = replace(
            repository.snapshot,
            actor_state=ActorState(ACTOR, (), True))

    runtime.gateway.before_page_return = revoke
    assert_unavailable(lambda: document_reader.read_document_page(
        runtime, DOCUMENT, VERSION, 2, 'REQ_ROLE_MID'))


def test_version_bump_between_pages_rejects_the_old_page():
    runtime, repository = reader_runtime()
    binding = candidate_binding(runtime)

    def bump():
        repository.snapshot = replace(repository.snapshot, bindings=(
            replace(binding, version_id='VER_SYNTHETIC_002'),))

    runtime.gateway.before_page_return = bump
    assert_unavailable(lambda: document_reader.read_document_page(
        runtime, DOCUMENT, VERSION, 2, 'REQ_BUMP_MID'), state='VERSION_STALE')


def test_plan_action_cannot_be_reused_for_search_or_evidence():
    runtime, _ = reader_runtime(value=snapshot(actions=('document.read', 'knowledge.search'),
                                               admitted=True))
    document_reader.open_document(runtime, DOCUMENT, None, 'REQ_ACTION')
    ticket = runtime.gateway.ticket
    assert ticket.plan.action == 'document.read'
    runtime.repository.snapshot = replace(runtime.repository.snapshot, query_embedding_admitted=True)
    with pytest.raises(KnowledgeError) as failure:
        runtime.decisions.verify_request(ticket.decision_ref,
                                         normalize_search({'query': '任意问题'}))
    assert failure.value.code == 'REPLAY_REJECTED'
    search_call = InternalRequest(CONTRACT_VERSION, 'introspect', ticket.decision_ref,
                                  ticket.plan.request_id, 'knowledge.search', 'introspect',
                                  ticket.request_fingerprint, ticket.plan_digest,
                                  ticket.deadline_at, ())
    with pytest.raises(KnowledgeError) as failure:
        runtime.decisions.online(SimpleNamespace(client=CLIENT, authenticated=True), search_call)
    assert failure.value.code == 'REPLAY_REJECTED'
    assert runtime.gateway.search_calls == []


def test_search_plan_cannot_be_reused_to_read_body():
    runtime, _ = reader_runtime(value=snapshot(actions=('knowledge.search',), admitted=True))
    ticket = runtime.decisions.issue(ACTOR, CLIENT, 'knowledge.search',
                                     normalize_search({'query': '任意问题'}), 'REQ_SEARCH')
    principal = SimpleNamespace(client=CLIENT, authenticated=True)
    runtime.decisions.online(principal, ticket.call('introspect', 'introspect'))
    proof = ReferenceProof(candidate_binding(runtime).binding_ref, VERSION, BODY_READ_SENTINEL)
    with pytest.raises(KnowledgeError) as failure:
        runtime.decisions.online(
            principal, ticket.call('authorize-evidence', 'document_body_read', (proof,)))
    assert failure.value.code == 'SCOPE_REJECTED'
    from hb_knowledge_app.hb_knowledge.gateway import document_call
    with pytest.raises(KnowledgeError) as failure:
        document_call(ticket)
    assert failure.value.code == 'SCOPE_REJECTED'


def test_production_redis_decision_store_walks_the_body_read_phase():
    """The durable (Redis) decision store, not only the in-memory test one."""
    import time
    from hb_knowledge_app.hb_knowledge.execution_plan import iso
    from hb_knowledge_app.hb_knowledge.shared_state import PHASE_LUA, RedisDecisions

    runtime, _ = reader_runtime(clock=time.time)
    request = normalize_document_read({'document_id': DOCUMENT})
    plan = runtime.provider.evaluate(ACTOR, CLIENT, 'document.read', request, 'REQ_REDIS')
    fingerprint, digest = 'b' * 64, 'a' * 64
    deadline = iso(time.time() + 60)
    row = {'plan': plan.to_wire(), 'request': request.to_wire(),
           'fingerprint': fingerprint, 'digest': digest, 'deadline': deadline}

    class State:
        def get(self, key):
            return json.dumps(row) if key.startswith('decision:') else None

        def eval(self, script, keys, args):
            return 1  # phase-order Lua is reviewed by the phase table tests

    assert 'document_body_read' in PHASE_LUA
    decisions = RedisDecisions(runtime.provider, Quota(), State(), 'key',
                               deadline_seconds=60)
    principal = SimpleNamespace(client=CLIENT, authenticated=True)
    binding = plan.bindings[0]
    proof = (ReferenceProof(binding.binding_ref, binding.version_id, BODY_READ_SENTINEL),)
    call = InternalRequest(CONTRACT_VERSION, 'authorize-evidence', 'REF',
                           plan.request_id, 'document.read', 'document_body_read',
                           fingerprint, digest, deadline, proof)
    response = decisions.online(principal, call)
    assert response.phase == 'document_body_read' and response.plan.action == 'document.read'
    # The signed wire envelope (plan action + phase) must pass the shared schema.
    from hb_knowledge_app.hb_knowledge.r1_contract import validate_structure
    validate_structure('InternalDecisionResponse', response.to_wire())
    # The same durable store refuses to reuse the body plan for evidence read.
    with pytest.raises(KnowledgeError) as failure:
        decisions.online(principal, InternalRequest(
            CONTRACT_VERSION, 'authorize-evidence', 'REF', plan.request_id,
            'document.read', 'evidence_read', fingerprint, digest, deadline, proof))
    assert failure.value.code == 'SCOPE_REJECTED'


def test_evidence_and_document_phases_stay_separate():
    assert 'document_read' in PHASES and 'document_body_read' in PHASES
    runtime, _ = reader_runtime()
    document_reader.open_document(runtime, DOCUMENT, None, 'REQ_PHASE_SPLIT')
    # The reader never emits the metadata-only bookmark phase.
    assert 'document_read' not in runtime.decisions.phases


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def test_search_returns_bounded_matches():
    runtime, _ = reader_runtime()
    matches = [{'ordinal': 3, 'page': 1, 'block_id': 'b3', 'snippet': '温度要求'},
               {'ordinal': 9, 'page': 2, 'block_id': 'b9', 'snippet': '压力要求'}]
    runtime.gateway = Gateway(search=search_payload(matches=matches, searched_blocks=96))
    data = document_reader.search_document(runtime, DOCUMENT, VERSION, '要求', 5, 'REQ_SEARCH')
    assert data == {'matches': matches, 'searched_blocks': 96, 'capped': False}
    assert runtime.gateway.search_calls == [('要求', 5)]
    assert all(len(match['snippet']) <= 240 for match in data['matches'])
    plan = runtime.gateway.ticket.plan
    assert plan.action == 'document.read' and len(plan.bindings) == 1


@pytest.mark.parametrize('query,limit', [
    ('', 5), ('x' * 121, 5), (None, 5), (123, 5), ('温度\n压力', 5),
    ('<b>温度</b>', 5), ('https://example.invalid/x', 5),
    ('温度', 0), ('温度', 21), ('温度', True), ('温度', '5'), ('温度', None), ('温度', 1.5)])
def test_invalid_search_query_or_limit_is_rejected(query, limit):
    runtime, _ = reader_runtime()
    with pytest.raises(KnowledgeError) as failure:
        document_reader.search_document(runtime, DOCUMENT, VERSION, query, limit, 'REQ_BAD_SEARCH')
    assert failure.value.code == 'INVALID_REQUEST'
    assert runtime.gateway.search_calls == []


def test_malformed_search_projection_is_an_upstream_invalid_result():
    cases = [
        {'matches': [{'ordinal': 2, 'page': 1, 'block_id': 'b2', 'snippet': 'x'}],
         'searched_blocks': 96, 'capped': False, 'dataset_id': DATASET},
        {'matches': [{'ordinal': 2, 'page': 9, 'block_id': 'b2', 'snippet': 'x'}],
         'searched_blocks': 96, 'capped': False},
        {'matches': [{'ordinal': 2, 'page': 1, 'block_id': 'CHUNK_NATIVE', 'snippet': 'x'}],
         'searched_blocks': 96, 'capped': False},
        {'matches': [{'ordinal': 2, 'page': 1, 'block_id': 'b2', 'snippet': 'x' * 241}],
         'searched_blocks': 96, 'capped': False},
        {'matches': [], 'searched_blocks': MAX_SEARCH_BLOCKS + 1, 'capped': False},
        {'matches': [], 'searched_blocks': 1, 'capped': 'no'},
    ]
    for payload in cases:
        runtime, _ = reader_runtime()
        runtime.gateway = Gateway(search={'status': 'SUCCESS', **payload})
        with pytest.raises(KnowledgeError) as failure:
            document_reader.search_document(runtime, DOCUMENT, VERSION, 'x', 5, 'REQ_BAD_UPSTREAM')
        assert failure.value.code == 'UPSTREAM_INVALID_RESULT'


# ---------------------------------------------------------------------------
# Upstream failure semantics and DTO hygiene
# ---------------------------------------------------------------------------

def test_service_side_stale_state_survives_the_controlled_error():
    runtime, _ = reader_runtime()
    runtime.gateway.error = KnowledgeError('DOCUMENT_READ_UNAVAILABLE', state='VERSION_STALE')
    with pytest.raises(KnowledgeError) as failure:
        document_reader.read_document_page(runtime, DOCUMENT, VERSION, 2, 'REQ_STALE_UPSTREAM')
    assert failure.value.code == 'DOCUMENT_READ_UNAVAILABLE'
    assert failure.value.state == 'VERSION_STALE'
    assert '/' not in failure.value.public_message


@pytest.mark.parametrize('code', ['UPSTREAM_UNAVAILABLE', 'POLICY_UNAVAILABLE',
                                  'UPSTREAM_INVALID_RESULT', 'UPSTREAM_SCOPE_VIOLATION',
                                  'RATE_LIMITED', 'DECISION_EXPIRED'])
def test_service_failures_keep_their_own_meaning(code):
    runtime, _ = reader_runtime()
    runtime.gateway.error = code
    with pytest.raises(KnowledgeError) as failure:
        document_reader.open_document(runtime, DOCUMENT, None, 'REQ_UPSTREAM')
    assert failure.value.code == code


@pytest.mark.parametrize('payload', [
    page_payload(page=2),
    page_payload(page=1, extra={'dataset_id': DATASET}),
    page_payload(page=1, extra={'page_count': 0}),
    page_payload(page=1, extra={'derived': False}),
    page_payload(page=1, extra={'toc_source': 'GUESSED'}),
    page_payload(page=1, blocks=[{'ordinal': 1, 'section': None, 'text': ''}]),
    page_payload(page=1, blocks=[{'ordinal': 9, 'section': None, 'text': 'x'}]),
    page_payload(page=1, blocks=[{'ordinal': 1, 'section': None, 'text': 'x' * 4001}]),
    page_payload(page=1, blocks=[{'ordinal': 1, 'section': None, 'text': f'物理 {DATASET}'}]),
    page_payload(page=1, blocks=[{'ordinal': 1, 'section': None, 'text': '<script>x</script>'}]),
    page_payload(page=1, blocks=[{'ordinal': 1, 'section': None, 'text': 'x', 'chunk_id': 'C1'}]),
    page_payload(page=1, toc=[{'title': 'x' * 121, 'ordinal': 1}]),
    page_payload(page=1, toc=[{'title': '1. 目的', 'ordinal': 1, 'page_number': 3}]),
    page_payload(page=1, toc=[{'title': '1. 目的', 'ordinal': 0}]),
])
def test_malformed_or_leaky_page_projection_is_refused(payload):
    runtime, _ = reader_runtime(gateway=Gateway(page_pages={1: payload}))
    with pytest.raises(KnowledgeError) as failure:
        document_reader.open_document(runtime, DOCUMENT, None, 'REQ_BAD_PAGE_DTO')
    assert failure.value.code == 'UPSTREAM_INVALID_RESULT'
    assert DATASET not in json.dumps(failure.value.public_message)


def test_binding_title_cannot_expose_physical_identifiers():
    leaky = make_binding(title=f'合成受控制度 {DATASET}')
    runtime, _ = reader_runtime(value=snapshot(bindings=(leaky,)))
    with pytest.raises(KnowledgeError) as failure:
        document_reader.open_document(runtime, DOCUMENT, None, 'REQ_TITLE_LEAK')
    assert failure.value.code == 'UPSTREAM_INVALID_RESULT'
    assert DATASET not in json.dumps(failure.value.public_message)


def test_toc_truncation_is_only_forwarded_when_true():
    runtime, _ = reader_runtime(gateway=Gateway(page_pages={
        1: page_payload(page=1, page_count=TOC_SCAN_PAGES + 4,
                        block_total=(TOC_SCAN_PAGES + 4) * PAGE_SIZE,
                        extra={'toc_truncated': True})}))
    data = document_reader.open_document(runtime, DOCUMENT, None, 'REQ_TOC')
    assert data['navigation']['toc_truncated'] is True
    runtime, _ = reader_runtime()
    data = document_reader.open_document(runtime, DOCUMENT, None, 'REQ_TOC_2')
    assert 'toc_truncated' not in data['navigation']


# ---------------------------------------------------------------------------
# Audit: hashed actor, action, bytes only; never body/token
# ---------------------------------------------------------------------------

def test_audit_records_only_hashed_actor_action_and_bytes():
    runtime, _ = reader_runtime()
    data = document_reader.open_document(runtime, DOCUMENT, None, 'REQ_AUDIT')
    assert len(runtime.audit.events) == 1
    event = runtime.audit.events[0]
    assert set(event) == {'actor_key', 'operation', 'code', 'count'}
    assert event['operation'] == 'document_read' and event['code'] == 'SUCCESS'
    assert event['actor_key'] != ACTOR.user_ref and len(event['actor_key']) == 16
    body_bytes = sum(len(block['text'].encode()) for block in data['body']['blocks'])
    assert event['count'] == body_bytes
    serialized = json.dumps(runtime.audit.events, ensure_ascii=False)
    for text in (block['text'] for block in data['body']['blocks']):
        assert text not in serialized
    assert 'SESSION_READER' not in serialized and DOCUMENT not in serialized


def test_search_audit_counts_returned_snippet_bytes():
    runtime, _ = reader_runtime()
    data = document_reader.search_document(runtime, DOCUMENT, None, '要求', 5, 'REQ_SEARCH_AUDIT')
    event = runtime.audit.events[0]
    assert event['operation'] == 'document_read' and event['code'] == 'SUCCESS'
    assert event['count'] == sum(len(match['snippet'].encode()) for match in data['matches'])


# ---------------------------------------------------------------------------
# Frappe endpoint wiring: _run envelope, no-store, forged params refused
# ---------------------------------------------------------------------------

def _install_frappe(monkeypatch):
    frappe = ModuleType('frappe')
    frappe.local = SimpleNamespace(response_headers={})
    frappe.whitelist = lambda **kwargs: (lambda fn: fn)
    monkeypatch.setitem(sys.modules, 'frappe', frappe)
    return frappe


def _api(monkeypatch, runtime):
    frappe = _install_frappe(monkeypatch)
    from hb_knowledge_app.hb_knowledge import api
    monkeypatch.setattr(api, 'frappe', frappe, raising=False)
    monkeypatch.setattr(api, 'load_runtime', lambda: runtime)
    return api, frappe


def test_endpoints_use_the_run_envelope_and_no_store(monkeypatch):
    runtime, _ = reader_runtime()
    api, frappe = _api(monkeypatch, runtime)
    result = api.open_document(document_id=DOCUMENT, version_id=None)
    assert result['ok'] is True
    assert set(result['data']) == {'document', 'body', 'navigation', 'disclosure'}
    assert frappe.local.response_headers['Cache-Control'] == 'private, no-store, max-age=0'
    assert frappe.local.response_headers['Pragma'] == 'no-cache'
    page = api.read_document_page(document_id=DOCUMENT, version_id=VERSION, page=2)
    assert page['ok'] is True and page['data']['body']['page'] == 2
    search = api.search_document(document_id=DOCUMENT, version_id=VERSION, query='要求', limit=5)
    assert search['ok'] is True and 'matches' in search['data']


def test_endpoints_refuse_forged_identity_and_transport_fields(monkeypatch):
    runtime, _ = reader_runtime()
    api, _ = _api(monkeypatch, runtime)
    for fields in ({'dataset_id': DATASET}, {'document_id_physical': PHYSICAL},
                   {'space_id': 'SPACE_PROD'}, {'path': '/tmp/x'},
                   {'call': {'decision_ref': 'X'}}):
        kwargs = {'document_id': DOCUMENT, 'version_id': None, **fields}
        result = api.open_document(**kwargs)
        assert result['ok'] is False
        assert result['error']['code'] == 'INVALID_REQUEST'
    for kwargs in ({'document_id': DOCUMENT, 'version_id': None, 'page': 0},
                   {'document_id': DOCUMENT, 'version_id': None, 'page': '2.5'},
                   {'document_id': 'DOC/../x', 'version_id': None, 'page': 1},
                   {'document_id': DOCUMENT, 'version_id': 'VER OLD', 'page': 1}):
        result = api.read_document_page(**kwargs)
        assert result['ok'] is False and result['error']['code'] == 'INVALID_REQUEST'
    for kwargs in ({'document_id': DOCUMENT, 'version_id': None, 'query': 'x' * 121, 'limit': 5},
                   {'document_id': DOCUMENT, 'version_id': None, 'query': '温度', 'limit': 21},
                   {'document_id': DOCUMENT, 'version_id': None, 'query': '', 'limit': 5}):
        result = api.search_document(**kwargs)
        assert result['ok'] is False and result['error']['code'] == 'INVALID_REQUEST'


def test_error_envelope_carries_an_enumerable_safe_state(monkeypatch):
    runtime, _ = reader_runtime()
    api, _ = _api(monkeypatch, runtime)
    result = api.open_document(document_id=DOCUMENT, version_id='VER_OLD_0001')
    assert result['ok'] is False
    assert result['error']['code'] == 'DOCUMENT_READ_UNAVAILABLE'
    assert result['error']['state'] == 'VERSION_STALE'
    serialized = json.dumps(result, ensure_ascii=False)
    assert DATASET not in serialized and PHYSICAL not in serialized
    assert '/api/' not in serialized and 'ragflow' not in serialized.lower()


def test_signed_gateway_sends_only_the_proof_and_page(monkeypatch):
    """BFF -> service wire: route, page and a single body-read proof only."""
    from types import ModuleType
    monkeypatch.setitem(sys.modules, 'pymysql', ModuleType('pymysql'))
    cipher = ModuleType('cryptography.fernet')
    cipher.Fernet = lambda *args, **kwargs: SimpleNamespace()
    monkeypatch.setitem(sys.modules, 'cryptography', ModuleType('cryptography'))
    monkeypatch.setitem(sys.modules, 'cryptography.fernet', cipher)
    frappe = ModuleType('frappe')
    frappe.whitelist = lambda **kwargs: (lambda fn: fn)
    frappe.local = SimpleNamespace()
    monkeypatch.setitem(sys.modules, 'frappe', frappe)

    from hb_knowledge_app.hb_knowledge.frappe_factory import HttpGateway
    runtime, _ = reader_runtime()
    document_reader.open_document(runtime, DOCUMENT, VERSION, 'REQ_GATEWAY')
    ticket = runtime.gateway.ticket

    class Recorder:
        def __init__(self):
            self.calls = []

        def post(self, path, payload, origin):
            self.calls.append((path, payload, origin))
            return {'status': 'SUCCESS'}

    gateway = HttpGateway.__new__(HttpGateway)
    gateway.http = Recorder()
    gateway.profile = 'production'
    assert gateway.document_page(ticket=ticket, page=2) == {'status': 'SUCCESS'}
    assert gateway.document_search(ticket=ticket, query='要求', limit=5) == {'status': 'SUCCESS'}
    page_path, page_payload, page_origin = gateway.http.calls[0]
    assert page_path == '/v1/knowledge/document-page'
    assert page_origin == CLIENT.client_id
    assert set(page_payload) == {'call', 'page'} and page_payload['page'] == 2
    call = InternalRequest.from_wire(page_payload['call'])
    assert (call.operation, call.phase, call.action) == (
        'authorize-evidence', 'document_body_read', 'document.read')
    assert len(call.references) == 1
    assert call.references[0].chunk_id == BODY_READ_SENTINEL
    search_path, search_payload, _ = gateway.http.calls[1]
    assert search_path == '/v1/knowledge/document-search'
    assert set(search_payload) == {'call', 'query', 'limit'}
    serialized = json.dumps([page_payload, search_payload])
    # The signed internal call names an opaque binding/version (never physical
    # dataset/document ids); the browser projection is asserted separately.
    for hidden in (DATASET, PHYSICAL, '/api/', 'ragflow', 'http://', 'https://'):
        assert hidden not in serialized


def test_signed_transport_carries_only_an_enumerated_reader_state(monkeypatch):
    from hb_knowledge_app.hb_knowledge import service_http

    class Response:
        status_code = 404

        def __init__(self, state):
            self.state = state

        def iter_content(self, size):
            payload = {"ok": False, "error": {"code": "DOCUMENT_READ_UNAVAILABLE",
                       "message": "该资料暂不可阅读或授权已变化，请重新检索。",
                       "retryable": False, "request_id": "R"}}
            if self.state is not None:
                payload["error"]["state"] = self.state
            yield json.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Session:
        trust_env = True

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            return Response(current_state[0])

    current_state = [None]

    def factory(*args, **kwargs):
        return Session()

    monkeypatch.setattr(service_http.requests, 'Session', factory)
    transport = service_http.SignedHttp('http://127.0.0.1:1', 'key', 'hbos-bff')
    current_state[0] = 'VERSION_STALE'
    with pytest.raises(KnowledgeError) as failure:
        transport.post('/v1/knowledge/document-page', {'call': {}, 'page': 1},
                       CLIENT.client_id)
    assert failure.value.code == 'DOCUMENT_READ_UNAVAILABLE'
    assert failure.value.state == 'VERSION_STALE'
    # Anything not in the fixed enumeration is dropped, never echoed.
    current_state[0] = '<script>LEAKY_UPSTREAM_PLACE</script>'
    with pytest.raises(KnowledgeError) as failure:
        transport.post('/v1/knowledge/document-page', {'call': {}, 'page': 1},
                       CLIENT.client_id)
    assert failure.value.code == 'DOCUMENT_READ_UNAVAILABLE'
    assert failure.value.state is None
    assert 'LEAKY' not in json.dumps(failure.value.public_message)
    assert 'LEAKY' not in json.dumps(failure.value.state)


# ---------------------------------------------------------------------------
# Frozen boundaries: get_evidence excerpt, downloads, MCP, schema enums
# ---------------------------------------------------------------------------

def test_existing_evidence_excerpt_and_original_delivery_are_unchanged():
    from hb_knowledge_app.hb_knowledge.download_policy import document_download_decision
    # No combination of flags can enable the original download action.
    assert document_download_decision(subject_enabled=True, version_current=True,
                                      iam_allowed=True, department_allowed=True,
                                      public_download_allowed=True).allowed is False
    # The reader adds no download/export endpoint to the public API module.
    from hb_knowledge_app.hb_knowledge import api
    names = {name for name in dir(api) if not name.startswith('_')}
    assert not {name for name in names
                if any(token in name for token in ('download', 'export', 'zip', 'original'))}
    # The public excerpt projection is untouched by this workpackage.
    from hb_knowledge_app.hb_knowledge.evidence import EVIDENCE_TTL_SECONDS
    assert EVIDENCE_TTL_SECONDS == 300


def test_schemas_and_phase_table_admit_the_new_controlled_action():
    from hb_knowledge_app.hb_knowledge.r1_contract import SCHEMA_ROOT
    plan = json.loads((SCHEMA_ROOT / 'execution_plan.schema.json').read_text())
    assert 'document.read' in plan['properties']['action']['enum']
    assert 'document.read' in plan['properties']['grant_pairs']['items']['properties']['action']['enum']
    api_schema = json.loads((SCHEMA_ROOT / 'api.schema.json').read_text())
    internal = api_schema['$defs']['InternalDecisionRequest']
    assert 'document.read' in internal['properties']['action']['enum']
    assert 'document_body_read' in internal['properties']['phase']['enum']
    response = api_schema['$defs']['InternalDecisionResponse']
    assert 'document_body_read' in response['properties']['phase']['enum']
    assert 'document_read' in response['properties']['phase']['enum']
    assert PHASES.index('document_read') != PHASES.index('document_body_read')
