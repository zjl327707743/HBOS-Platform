"""WP6: published documents beyond the first-1000 projection stay reachable.

The maintenance page is a bounded projection by design. What must stay possible
server-side is finding a published document that sorts past the projection (by
title/document number substring, by exact logical document id, or by page) and
finding its import batch (so detail/withdraw/revision flows can be entered).
Every lookup is bounded and returns an explicit FOUND/NOT_FOUND state.
"""
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

# Import surface only: the dashboard is exercised with explicit fakes below.
_frappe = ModuleType('frappe')
_frappe.whitelist = lambda **kwargs: (lambda fn: fn)
_frappe.local = SimpleNamespace(response_headers={})
sys.modules['frappe'] = _frappe
sys.modules.setdefault('pymysql', ModuleType('pymysql'))
_cipher = ModuleType('cryptography.fernet'); _cipher.Fernet = lambda *a, **k: None
sys.modules.setdefault('cryptography', ModuleType('cryptography'))
sys.modules.setdefault('cryptography.fernet', _cipher)

from hb_knowledge_app.hb_knowledge import (activity, api, maintenance,  # noqa: E402
                                           maintenance_access, maintenance_batch, runtime as runtime_module)
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError  # noqa: E402

TARGET_ID = 'DOC_ffffffffffffffffffffffff'
TARGET_TITLE = 'ZZZ 目标资料：道路交叉口设计'
TARGET_NUMBER = 'GB-WP6-001'
TARGET_VERSION = 'VER_ffffffffffffffffffffffff'


def published_fixture(count=1031, target=TARGET_ID):
    values = {}
    for index in range(count - 1):
        doc = f'DOC_{index:024d}'
        values[doc] = {'document_id': doc, 'version_id': f'VER_{index:024d}',
                       'current_version': f'VER_{index:024d}',
                       'title': f'A 资料{index:04d}', 'document_number': f'NO-{index:04d}',
                       'department': 'safety'}
    values[target] = {'document_id': target, 'version_id': TARGET_VERSION,
                      'current_version': TARGET_VERSION, 'title': TARGET_TITLE,
                      'document_number': TARGET_NUMBER, 'department': 'safety'}
    return values


def batch_fixture(count=538, document_id=TARGET_ID, document_index=400):
    batches = []
    for index in range(count):
        items = []
        if index == document_index:
            items = [{'canonical_document_id': document_id, 'version_id': TARGET_VERSION,
                      'disposition': 'REPLACE_CURRENT'}]
            items += [{'canonical_document_id': f'DOC_OTHER_{n:04d}', 'version_id': f'VER_OTHER_{n:04d}',
                       'disposition': 'REPLACE_CURRENT'} for n in range(5)]
        else:
            items = [{'canonical_document_id': f'DOC_{index:04d}{n:04d}', 'version_id': f'VER_{index:04d}{n:04d}',
                      'disposition': 'REPLACE_CURRENT'} for n in range(2)]
        batches.append({'name': f'IMP_{index:032x}', 'label': f'批次{index:04d}',
                        'department_key': 'safety' if index % 2 else 'public_law',
                        'status': 'Published', 'modified': f'2026-10-{(index % 27) + 1:02d}',
                        'state_json': json.dumps({'items': items})})
    return batches


class FakeDB:
    def __init__(self, batches):
        self._batches = batches

    def count(self, table):
        return len(self._batches)


class FakeFrappe:
    def __init__(self, batches):
        self.db = FakeDB(batches)
        self._batches = batches
        self.calls = []

    def get_all(self, table, **kwargs):
        self.calls.append(kwargs)
        fields = kwargs.get('fields') or ['name']
        limit = kwargs.get('limit_page_length')
        start = kwargs.get('limit_start') or 0
        rows = self._batches
        if limit is None:
            selected = rows[start:]
        elif limit == 0:
            selected = rows[start:]
        else:
            selected = rows[start:start + limit]
        return [{field: row.get(field) for field in fields} for row in selected]


def fake_runtime(published, batches):
    bindings = tuple(SimpleNamespace(canonical_document_id=value['document_id'],
                                     version_id=value['version_id'],
                                     title=value['title'],
                                     document_number=value['document_number'],
                                     space_id='DEPT_' + value['department'].upper(),
                                     dataset_id='DS_MAINTENANCE')
                    for value in published.values())
    snapshot = SimpleNamespace(bindings=bindings, allowed_datasets=('DS_MAINTENANCE',))
    provider = SimpleNamespace(_current=lambda actor, client: snapshot)
    return SimpleNamespace(provider=provider, actor=lambda: SimpleNamespace(user_ref='m@example.test'),
                           client=SimpleNamespace(client_id='CLIENT_MAINTENANCE'))


def install(monkeypatch, *, published=None, batches=None, require=None):
    published = published if published is not None else published_fixture()
    batches = batches if batches is not None else batch_fixture()
    frappe = FakeFrappe(batches)
    monkeypatch.setattr(maintenance, 'frappe', frappe, raising=False)
    monkeypatch.setattr(maintenance, 'require', require or (lambda: None))
    monkeypatch.setattr(maintenance, 'department_funnel', lambda published: [])
    monkeypatch.setattr(activity, 'feedback_queue', lambda runtime: {'items': []})
    monkeypatch.setattr(runtime_module, 'load_runtime', lambda: fake_runtime(published, batches))
    monkeypatch.setattr(api, '_availability', lambda runtime: {'configured': True, 'blocked': False})
    monkeypatch.setattr(maintenance_batch, 'batch_available', lambda: True)
    return frappe


def call_dashboard(**kwargs):
    return maintenance.dashboard(**kwargs)


# ---------------------------------------------------------------------------
# Published projection: default stays bounded
# ---------------------------------------------------------------------------

def test_default_projection_stays_bounded_and_backward_compatible(monkeypatch):
    install(monkeypatch)
    result = call_dashboard()
    assert len(result['published_documents']) == 1000
    assert result['published_total'] == 1031
    assert result['published_truncated'] is True
    assert result['published_matched'] == 1031
    assert result['published_page'] == 1 and result['published_page_size'] == 1000
    assert result['published_has_more'] is True
    assert result['published_query'] is None and result['published_document_id'] is None
    assert result['published_lookup_state'] is None
    # Legacy response keys used by the existing maintenance view stay present.
    for key in ('departments', 'batches', 'selected', 'feedback',
                'import_availability', 'department_funnel', 'published_total'):
        assert key in result
    assert len(result['batches']) == 100 and result['batches_total'] == 538
    assert result['batches_has_more'] is True and result['batch_scan_truncated'] is False


# ---------------------------------------------------------------------------
# Free-text/document-number search reaches a document past the projection
# ---------------------------------------------------------------------------

def test_query_finds_a_document_outside_the_first_thousand(monkeypatch):
    install(monkeypatch)
    projected = {d['document_id'] for d in call_dashboard()['published_documents']}
    assert TARGET_ID not in projected
    result = call_dashboard(published_query='目标资料')
    assert [d['document_id'] for d in result['published_documents']] == [TARGET_ID]
    assert result['published_matched'] == 1
    assert result['published_truncated'] is False
    assert result['published_has_more'] is False
    assert result['published_query'] == '目标资料'
    assert result['published_page_size'] == 50
    assert result['published_lookup_state'] is None


def test_title_prefix_and_case_insensitive_query_reach_the_document(monkeypatch):
    install(monkeypatch)
    prefix = call_dashboard(published_query=TARGET_TITLE[:6])
    assert [d['document_id'] for d in prefix['published_documents']] == [TARGET_ID]
    lowered = call_dashboard(published_query='zzz 目标资料')
    assert [d['document_id'] for d in lowered['published_documents']] == [TARGET_ID]
    # The query is an in-memory substring match over title/document number/id/
    # department, so a prefix cannot silently widen the authorization scope: it
    # only filters the already-authorized published snapshot.
    assert lowered['published_matched'] == 1


def test_query_by_document_number_finds_the_same_document(monkeypatch):
    install(monkeypatch)
    result = call_dashboard(published_query=TARGET_NUMBER)
    assert [d['document_id'] for d in result['published_documents']] == [TARGET_ID]
    assert result['published_matched'] == 1


def test_exact_document_id_lookup_and_not_found_state(monkeypatch):
    install(monkeypatch)
    found = call_dashboard(published_document_id=TARGET_ID)
    assert [d['document_id'] for d in found['published_documents']] == [TARGET_ID]
    assert found['published_matched'] == 1
    assert found['published_lookup_state'] == 'FOUND'
    assert found['published_truncated'] is False
    missing = call_dashboard(published_document_id='DOC_' + '9' * 24)
    assert missing['published_documents'] == []
    assert missing['published_matched'] == 0
    assert missing['published_lookup_state'] == 'NOT_FOUND'
    assert missing['published_total'] == 1031


def test_published_pagination_reaches_late_pages(monkeypatch):
    install(monkeypatch)
    second = call_dashboard(published_page=2, published_page_size=50)
    assert len(second['published_documents']) == 50
    assert second['published_page'] == 2 and second['published_page_size'] == 50
    assert second['published_matched'] == 1031
    assert second['published_has_more'] is True
    last = call_dashboard(published_page=21, published_page_size=50)
    assert len(last['published_documents']) == 31
    assert last['published_has_more'] is False
    assert last['published_truncated'] is False
    beyond_last = call_dashboard(published_page=22, published_page_size=50)
    assert beyond_last['published_documents'] == []
    assert beyond_last['published_has_more'] is False
    assert beyond_last['published_truncated'] is False


@pytest.mark.parametrize('kwargs', [
    {'published_query': 'x' * 121}, {'published_page': 0}, {'published_page': 'x'},
    {'published_page_size': 51}, {'published_page_size': 0},
    {'published_document_id': 'DOC_../escape'}, {'published_document_id': ''},
    {'published_query': '目标', 'published_document_id': TARGET_ID},
])
def test_invalid_published_lookup_parameters_are_rejected(monkeypatch, kwargs):
    install(monkeypatch)
    with pytest.raises(KnowledgeError) as failure:
        call_dashboard(**kwargs)
    assert failure.value.code == 'INVALID_REQUEST'


# ---------------------------------------------------------------------------
# Batch lookup: old batches outside the 100-row projection
# ---------------------------------------------------------------------------

def test_batch_projection_is_bounded_but_reports_the_real_total(monkeypatch):
    install(monkeypatch)
    result = call_dashboard()
    assert len(result['batches']) == 100
    assert result['batches_total'] == 538 and result['batches_has_more'] is True
    second = call_dashboard(batch_page=2, batch_page_size=100)
    assert len(second['batches']) == 100
    assert second['batches'][0]['name'] == 'IMP_' + f'{100:032x}'
    assert second['batches_has_more'] is True
    last = call_dashboard(batch_page=6, batch_page_size=100)
    assert len(last['batches']) == 38 and last['batches_has_more'] is False
    beyond_last = call_dashboard(batch_page=7, batch_page_size=100)
    assert beyond_last['batches'] == [] and beyond_last['batches_has_more'] is False


def test_document_id_locates_its_old_batch_outside_the_projection(monkeypatch):
    install(monkeypatch)
    listed = {b['name'] for b in call_dashboard()['batches']}
    assert 'IMP_' + f'{400:032x}' not in listed
    result = call_dashboard(batch_document_id=TARGET_ID)
    assert result['batch_lookup_state'] == 'FOUND'
    assert result['batches_matched'] == 1
    assert [b['name'] for b in result['batches']] == ['IMP_' + f'{400:032x}']
    assert result['batches'][0]['document_page'] == 1
    missing = call_dashboard(batch_document_id='DOC_' + '9' * 24)
    assert missing['batches'] == [] and missing['batches_matched'] == 0
    assert missing['batch_lookup_state'] == 'NOT_FOUND'


def test_batch_query_finds_an_old_batch_by_label(monkeypatch):
    install(monkeypatch)
    result = call_dashboard(batch_query='批次0400')
    assert [b['name'] for b in result['batches']] == ['IMP_' + f'{400:032x}']
    assert result['batches_matched'] == 1
    assert result['batch_query'] == '批次0400'
    assert result['batch_lookup_state'] is None


def test_batch_scan_stays_bounded_on_a_corpus_above_the_cap(monkeypatch):
    install(monkeypatch, batches=batch_fixture(count=1001))
    result = call_dashboard(batch_document_id=TARGET_ID)
    assert result['batches_total'] == 1001
    assert result['batch_scan_truncated'] is True
    frappe = maintenance.frappe
    scan_calls = [call for call in frappe.calls if call.get('limit_page_length') == 1000]
    assert scan_calls, 'document locate must scan at most the bounded batch window'
    assert all((call.get('limit_start') or 0) == 0 for call in scan_calls)


@pytest.mark.parametrize('kwargs', [
    {'batch_page': 0}, {'batch_page_size': 101}, {'batch_document_id': 'not-a-document'},
    {'batch_query': 'x' * 121},
    {'batch_query': '批次', 'batch_document_id': TARGET_ID},
])
def test_invalid_batch_lookup_parameters_are_rejected(monkeypatch, kwargs):
    install(monkeypatch)
    with pytest.raises(KnowledgeError) as failure:
        call_dashboard(**kwargs)
    assert failure.value.code == 'INVALID_REQUEST'


# ---------------------------------------------------------------------------
# Permission boundary and endpoint wiring
# ---------------------------------------------------------------------------

def test_non_maintainer_still_gets_scope_rejected(monkeypatch):
    def denied():
        raise KnowledgeError('SCOPE_REJECTED')
    install(monkeypatch, require=denied)
    with pytest.raises(KnowledgeError) as failure:
        call_dashboard(published_query='目标资料')
    assert failure.value.code == 'SCOPE_REJECTED'


def _install_api(monkeypatch, captured):
    frappe = ModuleType('frappe')
    frappe.local = SimpleNamespace(response_headers={})
    frappe.whitelist = lambda **kwargs: (lambda fn: fn)
    monkeypatch.setitem(sys.modules, 'frappe', frappe)
    monkeypatch.setattr(api, 'frappe', frappe, raising=False)
    monkeypatch.setattr(maintenance_access, 'require', lambda: None)
    monkeypatch.setattr(maintenance, 'dashboard', lambda *args, **kwargs: captured.update(kwargs) or {'ok': True})
    return api


def test_get_maintenance_endpoint_passes_the_lookup_parameters(monkeypatch):
    captured = {}
    api = _install_api(monkeypatch, captured)
    result = api.get_maintenance(published_query='目标', published_document_id=None,
                                 published_page=2, published_page_size=50,
                                 batch_query='批次', batch_page=3, batch_page_size=25,
                                 batch_document_id=None)
    assert result['ok'] is True
    assert captured == {'published_query': '目标', 'published_document_id': None,
                        'published_page': 2, 'published_page_size': 50,
                        'batch_query': '批次', 'batch_page': 3, 'batch_page_size': 25,
                        'batch_document_id': None}
    rejected = api.get_maintenance(published_query='目标', forged='1')
    assert rejected['ok'] is False and rejected['error']['code'] == 'INVALID_REQUEST'
