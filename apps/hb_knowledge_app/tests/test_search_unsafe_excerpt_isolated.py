"""One unsafe source excerpt must not fail the whole authorized search.

Field defect (RC13 b07): two published documents (《石油化工厂内道路设计规范》,
《ISO 14644-10-2022（Eng)》) returned five service fragments, but the BFF
projection rejected one excerpt on display hygiene and turned the whole search
into ``UPSTREAM_INVALID_RESULT``. The correct behaviour is per-record isolation:
skip only the unsafe record, return the rest with an omission count, and answer
with an explicit content-safety error only when every record is unsafe. Scope,
version, revocation and protocol failures must still fail the whole request.
"""
import hashlib
import json
import logging
import sys
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.execution_plan import Binding, Client
from hb_knowledge_app.hb_knowledge.gateway import EvidenceRecord
from hb_knowledge_app.hb_knowledge.r1_contract import validate_structure

CLIENT = Client('CLIENT_READER')
DATASET = '54982854c48411f199f5b578948a93a2'
PHYSICAL = 'a987bc78d15711f1b7532d2662c15dae'
SAFE_EXCERPT = '厂内道路的宽度应满足消防车辆通行要求。'
UNSAFE_EXCERPT = '附件参见 javascript:alert(1) 的说明。'
UNSAFE_EXCERPT_2 = '<script>bad()</script>'


def make_binding(document='DOC_039206f254908d2db6f9931c', version='VER_6edac64b74ae7d9e55504358',
                 title='石油化工厂内道路设计规范', binding_ref='BIND_SAFE', chunk_seed='a'):
    return Binding('SPACE_SAFETY', document, version, '2018', DATASET, PHYSICAL,
                   'ALIAS_SAFETY', binding_ref, 'REV_SAFE', 'COMPANY_CONTROLLED',
                   'CONTROLLED_REFERENCE_REVIEWED', '2026-01-01T00:00:00Z',
                   title=title, document_number='GB-TEST')


def evidence_record(binding, excerpt, chunk_id='CHUNK_SAFE'):
    return EvidenceRecord(binding.canonical_document_id, binding.title,
                          binding.business_version, '内部控制参考', None, None,
                          excerpt, chunk_id, binding.dataset_alias, binding.space_id,
                          binding.version_id, binding.binding_ref, binding)


class Ticket:
    def __init__(self, plan, request):
        self.plan = plan
        self.request = request
        self.decision_ref = 'DECISION_REF'
        self.request_fingerprint = 'f' * 64
        self.plan_digest = 'a' * 64
        self.deadline_at = '2030-01-01T00:00:00Z'

    def call(self, operation, phase, references=()):
        return SimpleNamespace(operation=operation, phase=phase,
                               references=tuple(references))


class Gateway:
    def __init__(self, records=(), error=None, authorize_error=None):
        self.records = list(records)
        self.error = error
        self.authorize_error = authorize_error
        self.authorized = []

    def search(self, *, ticket):
        if self.error:
            raise KnowledgeError(self.error)
        return list(self.records)

    def authorize_evidence(self, ticket, records, *, phase):
        if self.authorize_error:
            raise KnowledgeError(self.authorize_error)
        self.authorized.append(tuple(r.chunk_id for r in records))
        return True


class Audit:
    def __init__(self):
        self.events = []

    def record(self, subject, operation, code, count=0):
        self.events.append({'subject': subject, 'operation': operation,
                            'code': code, 'count': count})


def install_frappe(monkeypatch):
    frappe = ModuleType('frappe')
    frappe.local = SimpleNamespace(response_headers={})
    frappe.whitelist = lambda **kwargs: (lambda fn: fn)
    monkeypatch.setitem(sys.modules, 'frappe', frappe)
    return frappe


def fake_runtime(*, profile='synthetic', bindings=None, records=(), gateway=None):
    bindings = tuple(bindings if bindings is not None else (make_binding(),))
    plan = SimpleNamespace(bindings=bindings, subject=SimpleNamespace(user_ref='reader@example.test'),
                           client=CLIENT, policy_revision='POLICY_FIXED',
                           corpus_revision='CORPUS_FIXED', request_id='REQ_SEARCH',
                           expires_at='2030-01-01T00:00:00Z')
    request = SimpleNamespace(to_wire=lambda: {'query': '道路设计', 'limit': 5,
                                               'search_mode': 'STANDARD'})
    ticket = Ticket(plan, request)
    references, cache_writes, quota_calls = [], [], []
    runtime = SimpleNamespace(
        profile=profile, client=CLIENT, actor=lambda: SimpleNamespace(user_ref='reader@example.test'),
        provider=SimpleNamespace(revalidate=lambda plan: None, clock=lambda: 100.0),
        decisions=SimpleNamespace(issue=lambda *args: ticket, online=lambda *args: None),
        gateway=gateway or Gateway(records),
        quota=SimpleNamespace(reserve_output=lambda *args: quota_calls.append(args)),
        audit=Audit(),
        references=SimpleNamespace(put=lambda reference: references.append(reference)),
        cache=SimpleNamespace(set_value=lambda *args, **kwargs: cache_writes.append(args)),
        publication=None, checkpoint=lambda phase: None)
    return runtime, ticket, references, cache_writes, quota_calls


def install_api(monkeypatch, runtime, gateway):
    frappe = install_frappe(monkeypatch)
    from hb_knowledge_app.hb_knowledge import api
    monkeypatch.setattr(api, 'frappe', frappe, raising=False)
    monkeypatch.setattr(api, 'load_runtime', lambda: runtime)
    monkeypatch.setattr(api, 'load_gateway_client', lambda: gateway)
    return api


def call_search(api):
    result = api.search(query='道路设计', limit=5)
    assert result.get('ok') is True, result
    return result['data']


# ---------------------------------------------------------------------------
# Partial isolation
# ---------------------------------------------------------------------------

def test_one_unsafe_record_is_skipped_and_the_rest_still_returned(monkeypatch):
    binding = make_binding()
    safe = evidence_record(binding, SAFE_EXCERPT)
    unsafe = evidence_record(binding, UNSAFE_EXCERPT, chunk_id='CHUNK_UNSAFE')
    runtime, _, references, cache_writes, quota_calls = fake_runtime(records=[unsafe, safe])
    api = install_api(monkeypatch, runtime, runtime.gateway)
    data = call_search(api)
    assert len(data['results']) == 1
    assert data['results'][0]['excerpt'] == SAFE_EXCERPT
    assert data['omitted_results'] == 1
    serialized = json.dumps(data, ensure_ascii=False)
    assert UNSAFE_EXCERPT not in serialized and 'javascript:' not in serialized
    # Only the returned source is bound; the unsafe handle/reference is never issued.
    assert [r.chunk_id for r in references] == ['CHUNK_SAFE']
    assert cache_writes and quota_calls and quota_calls[0][1] == len(SAFE_EXCERPT)
    # A partial omission is still a successful, schema-valid response.
    validate_structure('SearchData', data)


def test_multiple_unsafe_records_are_all_skipped_and_counted(monkeypatch):
    binding = make_binding()
    records = [evidence_record(binding, UNSAFE_EXCERPT, chunk_id='CHUNK_U1'),
               evidence_record(binding, SAFE_EXCERPT, chunk_id='CHUNK_SAFE'),
               evidence_record(binding, UNSAFE_EXCERPT_2, chunk_id='CHUNK_U2')]
    runtime, *_ = fake_runtime(records=records)
    api = install_api(monkeypatch, runtime, runtime.gateway)
    data = call_search(api)
    assert [row['excerpt'] for row in data['results']] == [SAFE_EXCERPT]
    assert data['omitted_results'] == 2


# ---------------------------------------------------------------------------
# All unsafe: explicit, distinguishable content-safety state
# ---------------------------------------------------------------------------

def test_all_unsafe_records_return_the_explicit_content_error(monkeypatch):
    binding = make_binding()
    records = [evidence_record(binding, UNSAFE_EXCERPT, chunk_id='CHUNK_U1'),
               evidence_record(binding, UNSAFE_EXCERPT_2, chunk_id='CHUNK_U2')]
    runtime, _, references, cache_writes, quota_calls = fake_runtime(records=records)
    api = install_api(monkeypatch, runtime, runtime.gateway)
    result = api.search(query='道路设计', limit=5)
    assert result['ok'] is False
    assert result['error']['code'] == 'SOURCE_CONTENT_UNSAFE'
    assert result['error']['retryable'] is False
    assert '安全展示检查' in result['error']['message']
    # Never presented as "no content" or "upstream failure".
    assert '没有找到' not in result['error']['message']
    assert '暂时' not in result['error']['message']
    assert UNSAFE_EXCERPT not in json.dumps(result, ensure_ascii=False)
    # Nothing was issued or charged when every record is unsafe.
    assert references == [] and cache_writes == [] and quota_calls == []
    assert runtime.audit.events == []


def test_private_diagnostic_carries_hashes_counts_and_no_body(monkeypatch, caplog):
    binding = make_binding()
    records = [evidence_record(binding, UNSAFE_EXCERPT, chunk_id='CHUNK_U1')]
    runtime, *_ = fake_runtime(records=records)
    api = install_api(monkeypatch, runtime, runtime.gateway)
    caplog.set_level(logging.WARNING, logger='hbos.knowledge.source_diagnostics')
    result = api.search(query='道路设计', limit=5)
    assert result['error']['code'] == 'SOURCE_CONTENT_UNSAFE'
    trace = '\n'.join(record.message for record in caplog.records)
    assert 'SEARCH_RESULT_OMITTED' in trace
    assert 'CONTENT_SAFETY_REJECTED' in trace
    document_hash = hashlib.sha256(binding.canonical_document_id.encode()).hexdigest()
    assert document_hash in trace
    assert binding.canonical_document_id not in trace
    assert UNSAFE_EXCERPT not in trace and 'javascript:' not in trace
    assert 'CHUNK_U1' not in trace


# ---------------------------------------------------------------------------
# Non-content failures must still fail the whole search
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('error', ['UPSTREAM_SCOPE_VIOLATION', 'UPSTREAM_UNAVAILABLE',
                                   'SOURCE_VERSION_STALE', 'SCOPE_REJECTED'])
def test_scope_version_and_protocol_failures_still_fail_whole(monkeypatch, error):
    runtime, *_ = fake_runtime(records=[evidence_record(make_binding(), SAFE_EXCERPT)],
                               gateway=Gateway(error=error))
    runtime.gateway = runtime.gateway
    api = install_api(monkeypatch, runtime, runtime.gateway)
    result = api.search(query='道路设计', limit=5)
    assert result['ok'] is False
    assert result['error']['code'] == error
    assert 'omitted_results' not in json.dumps(result)


def test_authorization_revocation_after_service_search_still_fails_whole(monkeypatch):
    binding = make_binding()
    gateway = Gateway(records=[evidence_record(binding, SAFE_EXCERPT)],
                      authorize_error='SCOPE_REJECTED')
    runtime, *_ = fake_runtime(gateway=gateway)
    api = install_api(monkeypatch, runtime, gateway)
    result = api.search(query='道路设计', limit=5)
    assert result['ok'] is False and result['error']['code'] == 'SCOPE_REJECTED'


def test_provider_revalidation_version_failure_still_fails_whole(monkeypatch):
    binding = make_binding()
    runtime, *_ = fake_runtime(records=[evidence_record(binding, SAFE_EXCERPT)])

    def stale(plan):
        raise KnowledgeError('SOURCE_VERSION_STALE')

    runtime.provider.revalidate = stale
    api = install_api(monkeypatch, runtime, runtime.gateway)
    result = api.search(query='道路设计', limit=5)
    assert result['ok'] is False and result['error']['code'] == 'SOURCE_VERSION_STALE'


def test_non_content_projection_failure_is_not_isolated(monkeypatch):
    # page_number=0 violates EvidenceCard structure; that is a protocol defect,
    # not display hygiene, so it must not be silently reduced to "omitted".
    binding = make_binding()
    record = evidence_record(binding, SAFE_EXCERPT)
    record = EvidenceRecord(record.document_id, record.title, record.version,
                            record.status_note, record.section, 0, record.excerpt,
                            record.chunk_id, record.dataset_id, record.space_id,
                            record.version_id, record.binding_ref, record.binding)
    runtime, *_ = fake_runtime(records=[record])
    api = install_api(monkeypatch, runtime, runtime.gateway)
    result = api.search(query='道路设计', limit=5)
    assert result['ok'] is False and result['error']['code'] == 'INVALID_REQUEST'
    assert 'omitted_results' not in json.dumps(result)


def test_environment_or_source_scope_error_is_not_isolated_as_content(monkeypatch):
    # A SYNTHETIC_TEST binding in production is a scope error, not content
    # hygiene: it must fail the whole search, never be counted as omitted.
    binding = make_binding()
    binding = Binding(binding.space_id, binding.canonical_document_id,
                      binding.version_id, binding.business_version, binding.dataset_id,
                      binding.document_id, binding.dataset_alias, binding.binding_ref,
                      binding.binding_revision, 'SYNTHETIC_TEST', 'SYNTHETIC_ONLY',
                      binding.valid_from, title=binding.title)
    runtime, *_ = fake_runtime(profile='production', bindings=(binding,),
                               records=[evidence_record(binding, SAFE_EXCERPT)])
    api = install_api(monkeypatch, runtime, runtime.gateway)
    result = api.search(query='道路设计', limit=5)
    assert result['ok'] is False and result['error']['code'] == 'SCOPE_REJECTED'


# ---------------------------------------------------------------------------
# Schema / production gateway boundary
# ---------------------------------------------------------------------------

def test_search_data_omitted_results_is_optional_and_bounded():
    base = {'request_id': 'REQ', 'mode': 'retrieval', 'results': []}
    validate_structure('SearchData', dict(base))
    for value in (0, 1, 5):
        validate_structure('SearchData', {**base, 'omitted_results': value})
    for value in (-1, 6, True, 1.5, '1'):
        with pytest.raises(KnowledgeError) as failure:
            validate_structure('SearchData', {**base, 'omitted_results': value})
        assert failure.value.code == 'INVALID_REQUEST'


def test_gateway_search_keeps_scope_checks_but_does_not_reject_one_unsafe_excerpt(monkeypatch):
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

    binding = make_binding()
    fragments = [
        {'binding_ref': binding.binding_ref, 'version_id': binding.version_id,
         'chunk_id': 'CHUNK_SAFE', 'excerpt': SAFE_EXCERPT, 'page_number': None, 'score': .9},
        {'binding_ref': binding.binding_ref, 'version_id': binding.version_id,
         'chunk_id': 'CHUNK_UNSAFE', 'excerpt': UNSAFE_EXCERPT, 'page_number': None,
         'score': .8},
    ]
    ticket = Ticket(SimpleNamespace(bindings=(binding,), client=CLIENT,
                                    subject=SimpleNamespace(user_ref='reader@example.test'),
                                    policy_revision='POLICY_FIXED', request_id='REQ_SEARCH'),
                    SimpleNamespace(to_wire=lambda: {'query': '道路设计', 'limit': 5,
                                                     'search_mode': 'STANDARD'}))

    class Http:
        def __init__(self, value):
            self.value = value

        def post(self, path, payload, origin):
            return self.value

    gateway = HttpGateway.__new__(HttpGateway)
    gateway.profile = 'production'
    gateway.http = Http({'status': 'SUCCESS', 'results': fragments})
    records = gateway.search(ticket=ticket)
    # Both records leave the gateway intact: per-record content isolation is the
    # use case's job, so one unsafe excerpt can no longer fail the whole search.
    assert [record.chunk_id for record in records] == ['CHUNK_SAFE', 'CHUNK_UNSAFE']
    assert records[1].excerpt == UNSAFE_EXCERPT

    # The identity/scope boundary stays in the gateway and still fails closed.
    gateway.http = Http({'status': 'SUCCESS', 'results': [
        {'binding_ref': 'BIND_OTHER', 'version_id': binding.version_id,
         'chunk_id': 'CHUNK_OTHER', 'excerpt': SAFE_EXCERPT, 'page_number': None,
         'score': .9}]})
    with pytest.raises(KnowledgeError) as failure:
        gateway.search(ticket=ticket)
    assert failure.value.code == 'UPSTREAM_SCOPE_VIOLATION'
