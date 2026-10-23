"""Gate C: a directory question is answered from the plan, not through the gateway.

The fast path must be indistinguishable from the normal one except in what it
skips. These tests pin the parts that would be a security or audit change if
they drifted:

- the gateway is never called;
- the decision store is walked in the order its Lua phase table allows, with no
  fabricated phase;
- history, quota-free metadata write and audit still happen;
- the answer counts only the bindings this plan authorizes.
"""
import sys
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def _install(monkeypatch):
    frappe = ModuleType('frappe')
    frappe.defaults = SimpleNamespace(get_user_default=lambda key, user=None: None,
                                      set_user_default=lambda *a, **k: None)
    frappe.local = SimpleNamespace()
    frappe.session = SimpleNamespace(user='reader@example.test')
    frappe.db = SimpleNamespace()
    frappe.get_roles = lambda user: []
    frappe.whitelist = lambda **kwargs: (lambda fn: fn)

    inserted = []

    class Doc(dict):
        def __init__(self, values):
            super().__init__(values)
            self.name = 'ACT_1'

        def insert(self, **kwargs):
            inserted.append(dict(self))
            return self

    frappe.get_doc = lambda values: Doc(values) if isinstance(values, dict) else Doc({'name': values})
    frappe.as_json = lambda value, **kwargs: __import__('json').dumps(value)
    monkeypatch.setitem(sys.modules, 'frappe', frappe)
    return frappe, inserted


class PhaseStore:
    """The phase table from shared_state.PHASE_LUA, without Redis."""

    ALLOWED = {
        'introspect': lambda seen: True,
        'cache_read': lambda seen: 'introspect' in seen,
        'pre_retrieval': lambda seen: 'introspect' in seen,
        'post_retrieval': lambda seen: 'pre_retrieval' in seen,
        'pre_projection': lambda seen: 'post_retrieval' in seen or 'cache_read' in seen,
        'pre_issue': lambda seen: 'pre_projection' in seen,
        'evidence_read': lambda seen: 'introspect' in seen,
        'document_read': lambda seen: 'introspect' in seen,
        'pre_general_generation': lambda seen: 'introspect' in seen,
        'post_general_generation': lambda seen: 'pre_general_generation' in seen,
        'final_publish': lambda seen: bool(seen & {'pre_projection', 'pre_issue', 'evidence_read',
                                                   'document_read', 'post_general_generation'}),
    }
    OPERATION = {'introspect': 'introspect', 'cache_read': 'introspect', 'pre_issue': 'authorize-evidence',
                 'evidence_read': 'authorize-evidence', 'document_read': 'authorize-evidence'}

    def __init__(self):
        self.calls = []
        self.seen = set()

    def online(self, principal, call):
        self.calls.append((call.operation, call.phase))
        if self.OPERATION.get(call.phase, 'revalidate') != call.operation:
            raise KnowledgeError('INVALID_REQUEST')
        if not self.ALLOWED[call.phase](self.seen):
            raise KnowledgeError('INVALID_REQUEST')
        self.seen.add(call.phase)
        return SimpleNamespace(phase=call.phase)


class Ticket:
    def __init__(self, plan):
        self.plan = plan

    def call(self, operation, phase, references=()):
        return SimpleNamespace(operation=operation, phase=phase, references=references)


def _binding(space, doc, title, version='VER_1', number=None):
    return SimpleNamespace(
        space_id=space, canonical_document_id=doc, version_id=version, title=title,
        document_number=number, dataset_id='DS_' + space, dataset_alias='ALIAS_' + space,
        source_type='COMPANY_CONTROLLED', authority_status='CONTROLLED_REFERENCE_REVIEWED',
        backend='ragflow', mapping_ready=True, withdrawn=False,
        valid_from='2026-01-01T00:00:00Z', valid_until=None, publication_state='published')


def _runtime(bindings, *, ask_calls):
    decisions = PhaseStore()
    written, audited = [], []

    class Gateway:
        def ask(self, ticket=None):
            ask_calls.append(ticket)
            raise AssertionError('the gateway must not be called for a directory answer')

    snapshot = SimpleNamespace(
        bindings=tuple(bindings), allowed_datasets={b.dataset_id for b in bindings},
        active_spaces={b.space_id for b in bindings}, denied_spaces=set(),
        grants=tuple(SimpleNamespace(space_id=b.space_id, action='knowledge.search', role_ref='R')
                     for b in bindings),
        space_titles=tuple(), actor_state=SimpleNamespace(roles=('R',)))
    actor = SimpleNamespace(user_ref='reader@example.test', enabled=True)
    runtime = SimpleNamespace(
        decisions=decisions,
        gateway=Gateway(),
        client=SimpleNamespace(client_id='PORTAL'),
        profile='production',
        actor=lambda: actor,
        provider=SimpleNamespace(
            _current=lambda a, c: snapshot,
            clock=lambda: 1791424800,
            revalidate=lambda plan: None),
        audit=SimpleNamespace(record=lambda user, kind, status, count: audited.append((user, kind, status, count))),
        cache=SimpleNamespace(),
        publication=SimpleNamespace(publication_id='PUB_1', plan=None),
        quota=SimpleNamespace(reserve_output=lambda *a, **k: None),
    )
    for binding in bindings:
        binding.dataset_id = getattr(binding, 'dataset_id', 'DS')
        binding.source_type = 'COMPANY_CONTROLLED'
        binding.authority_status = 'CONTROLLED_REFERENCE_REVIEWED'
        binding.backend = 'ragflow'
        binding.mapping_ready = True
        binding.withdrawn = False
        binding.valid_from = '2026-01-01T00:00:00Z'
        binding.valid_until = None
        binding.publication_state = 'published'
    return runtime, decisions, written, audited


def _call(monkeypatch, bindings, question, *, titles=None, space_ids=None):
    frappe, inserted = _install(monkeypatch)
    from hb_knowledge_app.hb_knowledge import api
    from hb_knowledge_app.hb_knowledge.r1_contract import normalize_search

    ask_calls = []
    runtime, decisions, _, audited = _runtime(bindings, ask_calls=ask_calls)
    plan = SimpleNamespace(space_ids=tuple(space_ids) if space_ids else tuple(sorted({b.space_id for b in bindings})),
                           bindings=tuple(bindings), model_alias='deepseek-flash',
                           subject=SimpleNamespace(user_ref='reader@example.test'))
    ticket = Ticket(plan)
    request = normalize_search({'query': question, 'space_titles': titles or {},
                                'model_alias': 'deepseek-flash'})
    marks = []

    class Phase:
        def __call__(self, label):
            import contextlib
            @contextlib.contextmanager
            def cm():
                marks.append(label)
                yield
            return cm()

    out = api._catalog_direct(runtime, Phase(), ticket, titles or {}, question, request,
                              {'knowledge_only': False}, 'REQ_1')
    return out, decisions, ask_calls, inserted, audited


TITLES = {'DEPT_A': '生产部门', 'DEPT_SAFETY': '安全培训'}


def test_the_answer_comes_from_the_plan_without_the_gateway(monkeypatch):
    bindings = [_binding('DEPT_A', 'DOC_1', '操作规程 A'), _binding('DEPT_A', 'DOC_2', '操作规程 B')]
    out, decisions, ask_calls, inserted, audited = _call(
        monkeypatch, bindings, '知识库共有多少份文件', titles=TITLES)
    assert out is not None
    assert ask_calls == []
    assert out['answer_status'] == 'CATALOG_RESULTS'
    assert out['citations'] == []
    assert '2 份' in out['answer']
    import json
    payload = json.loads(inserted[0]['payload_json'])
    assert payload['answer_origin'] == 'KNOWLEDGE'
    assert payload['references'] == []
    assert payload['labels'] == []
    assert audited == [('reader@example.test', 'ask', 'SUCCESS', 0)]


def test_the_phase_order_is_the_one_the_store_allows(monkeypatch):
    bindings = [_binding('DEPT_A', 'DOC_1', '操作规程 A')]
    out, decisions, *_ = _call(monkeypatch, bindings, '知识库共有多少份文件', titles=TITLES)
    assert out is not None
    assert decisions.calls == [('introspect', 'introspect'), ('introspect', 'cache_read'),
                               ('revalidate', 'pre_projection'), ('revalidate', 'final_publish')]


def test_a_content_question_is_not_answered_from_the_plan(monkeypatch):
    bindings = [_binding('DEPT_A', 'DOC_1', '备份规程')]
    out, decisions, *_ = _call(monkeypatch, bindings, '这份规程要留多少份副本', titles=TITLES)
    assert out is None
    assert decisions.calls == []


def test_an_empty_scope_does_not_claim_zero_documents(monkeypatch):
    out, decisions, ask_calls, inserted, _ = _call(monkeypatch, [], '知识库共有多少份文件', titles=TITLES)
    assert out is None
    assert decisions.calls == []
    assert inserted == []


def test_two_versions_of_one_document_count_once(monkeypatch):
    bindings = [_binding('DEPT_A', 'DOC_1', '规程', version='VER_1'),
                _binding('DEPT_A', 'DOC_1', '规程', version='VER_2')]
    out, *_ = _call(monkeypatch, bindings, '知识库共有多少份文件', titles=TITLES)
    assert '1 份' in out['answer']


def test_titles_of_the_answer_use_the_authorized_names(monkeypatch):
    bindings = [_binding('DEPT_A', 'DOC_1', '规程')]
    out, *_ = _call(monkeypatch, bindings, '知识库共有多少份文件', titles=TITLES)
    assert '生产部门' in out['answer']
    assert 'DEPT_A' not in out['answer']


def test_a_named_subject_narrows_the_count(monkeypatch):
    bindings = [_binding('DEPT_A', 'DOC_1', '生产规程'), _binding('DEPT_SAFETY', 'DOC_2', '安全培训手册')]
    out, *_ = _call(monkeypatch, bindings, '安全培训资料一共有多少份', titles=TITLES)
    assert '1 份' in out['answer']


def test_the_plan_never_counts_a_space_it_does_not_authorize(monkeypatch):
    bindings = [_binding('DEPT_A', 'DOC_1', '规程'), _binding('DEPT_SAFETY', 'DOC_2', '手册')]
    out, *_ = _call(monkeypatch, bindings, '知识库共有多少份文件', titles=TITLES, space_ids=['DEPT_A'])
    assert '1 份' in out['answer']
    assert '手册' not in out['answer']
