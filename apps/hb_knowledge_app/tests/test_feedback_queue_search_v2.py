"""P09 v2: feedback queue search must match decoded (non-ASCII) payload values.

The served candidate stores ``payload_json`` through
``service_http.canonical`` (``ensure_ascii=True``), so the previous raw
``payload_json LIKE`` could never match a Chinese query. v2 scans the
maintenance-scoped queue in bounded pages, decodes each stored payload and
substring-matches the decoded JSON text (which keeps the old ASCII semantics
for keys/values known to the LIKE path).

These tests replace the served candidate's ``test_feedback_queue_search_r2.py``
(which asserted the superseded raw-LIKE query) and cover the same contract the
isolated P09 fix suite covered, in this repository's in-process style.
"""
import importlib
import json
import sys
import types

import pytest

from hb_knowledge_app.hb_knowledge import activity
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def _payload(**values):
    # Exactly how service_http.canonical serialises feedback payloads.
    return json.dumps(values, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


ROWS = [
    {'name': 'A', 'status': 'Pending', 'creation': '2026-10-08 10:48:57',
     'payload_json': _payload(category='内容疑问', note='页面真实验收：请维护人核对资料版本标注。')},
    {'name': 'B', 'status': 'Pending', 'creation': '2026-10-08 10:38:13',
     'payload_json': _payload(category='版本疑问', note='R2 实际验收：请维护人核对版本标注。')},
    {'name': 'C', 'status': 'In Review', 'creation': '2026-10-08 10:34:35',
     'payload_json': _payload(category='版本疑问', note='R2 实际验收：请维护人核对版本标注。',
                              reviewer='knowledge-maintainer@hbos.local')},
    {'name': 'D', 'status': 'Pending', 'creation': '2026-10-08 10:32:48',
     'payload_json': _payload(category='内容疑问', note='R2 候选验收反馈')},
]


class FakeFrappe:
    """Only the frappe surface the queue uses; db.sql must never be reached."""

    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def get_all(self, doctype, filters=None, fields=None, order_by=None,
                limit_start=0, limit_page_length=None):
        self.calls.append({'doctype': doctype, 'filters': filters, 'fields': fields,
                           'order_by': order_by, 'limit_start': limit_start,
                           'limit_page_length': limit_page_length})
        rows = [row for row in self.rows
                if not (filters or {}).get('status') or row['status'] == filters['status']]
        return rows[limit_start:limit_start + (limit_page_length or len(rows))]

    @property
    def db(self):
        def sql(*args, **kwargs):
            raise AssertionError('feedback search must not use the raw payload_json LIKE query')
        return types.SimpleNamespace(sql=sql)


def queue(monkeypatch, rows, **kwargs):
    fake = FakeFrappe(rows)
    monkeypatch.setitem(sys.modules, 'frappe', fake)
    monkeypatch.setitem(sys.modules, 'hb_knowledge_app.hb_knowledge.maintenance_access',
                        types.SimpleNamespace(require=lambda *a, **k: None))
    return activity.feedback_queue(None, **kwargs), fake


def test_plain_queue_is_unchanged(monkeypatch):
    output, fake = queue(monkeypatch, ROWS, page=1, page_size=12, status='Pending')
    assert [item['id'] for item in output['items']] == ['A', 'B', 'D']
    assert output['has_more'] is False and 'scan_truncated' not in output
    assert fake.calls[0]['filters'] == {'kind': 'Feedback', 'status': 'Pending'}
    assert fake.calls[0]['limit_start'] == 0 and fake.calls[0]['limit_page_length'] == 13


def test_chinese_query_matches_decoded_values(monkeypatch):
    output, _ = queue(monkeypatch, ROWS, page=1, page_size=12, status='Pending', query='维护')
    assert [item['id'] for item in output['items']] == ['A', 'B']
    assert output['scan_truncated'] is False
    everything, _ = queue(monkeypatch, ROWS, page=1, page_size=12, query='维护')
    assert [item['id'] for item in everything['items']] == ['A', 'B', 'C']
    missing, _ = queue(monkeypatch, ROWS, page=1, page_size=12, query='不存在')
    assert missing['items'] == [] and missing['has_more'] is False


def test_mixed_and_ascii_values_keep_prior_semantics(monkeypatch):
    output, _ = queue(monkeypatch, ROWS, page=1, page_size=12, query='R2 实际验收')
    assert [item['id'] for item in output['items']] == ['B', 'C']
    output, _ = queue(monkeypatch, ROWS, page=1, page_size=12, query='knowledge-maintainer@hbos.local')
    assert [item['id'] for item in output['items']] == ['C']
    # Decoded matching keeps the old inserted-text semantics: stored keys stay
    # reachable (ASCII key "note" appears in every payload)...
    output, _ = queue(monkeypatch, ROWS, page=1, page_size=12, query='NOTE')
    assert [item['id'] for item in output['items']] == ['A', 'B', 'C', 'D']
    # ...but a term that is neither a key nor a value never matches.
    output, _ = queue(monkeypatch, ROWS, page=1, page_size=12, query='version')
    assert output['items'] == []


def test_wildcards_are_literal(monkeypatch):
    assert queue(monkeypatch, ROWS, page=1, page_size=12, query='%')[0]['items'] == []
    assert queue(monkeypatch, ROWS, page=1, page_size=12, query='_')[0]['items'] == []
    assert queue(monkeypatch, ROWS, page=1, page_size=12, query=r'\\')[0]['items'] == []


def _many(count, match_all=True):
    return [{'name': f'N{index}', 'status': 'Pending',
             'creation': f'2026-10-08 10:{index:02d}:00',
             'payload_json': _payload(note='匹配词 内容' if match_all else '其他 内容')}
            for index in range(count)]


def test_pagination_contract(monkeypatch):
    rows = _many(30)
    page1, _ = queue(monkeypatch, rows, page=1, page_size=12, query='匹配词')
    page2, _ = queue(monkeypatch, rows, page=2, page_size=12, query='匹配词')
    page3, _ = queue(monkeypatch, rows, page=3, page_size=12, query='匹配词')
    page4, _ = queue(monkeypatch, rows, page=4, page_size=12, query='匹配词')
    assert len(page1['items']) == 12 and page1['has_more'] is True
    assert len(page2['items']) == 12 and page2['has_more'] is True
    assert len(page3['items']) == 6 and page3['has_more'] is False
    assert page4['items'] == [] and page4['has_more'] is False


def test_scan_cap_is_explicit(monkeypatch):
    output, _ = queue(monkeypatch, _many(5100, match_all=False), page=1, page_size=12, query='匹配词')
    assert output['items'] == [] and output['scan_truncated'] is True
    output, _ = queue(monkeypatch, _many(5100, match_all=True), page=1, page_size=12, query='匹配词')
    assert len(output['items']) == 12 and output['scan_truncated'] is False


def test_validation_and_empty_query(monkeypatch):
    for bad in ('   ', 'x' * 121, 5):
        with pytest.raises(KnowledgeError) as failure:
            queue(monkeypatch, ROWS, page=1, page_size=12, query=bad)
        assert failure.value.code == 'INVALID_REQUEST'
    assert (queue(monkeypatch, ROWS, page=1, page_size=12, query='')[0]
            == queue(monkeypatch, ROWS, page=1, page_size=12)[0])


def test_api_forwards_query_to_the_activity_queue(monkeypatch):
    stubbed_frappe = types.SimpleNamespace(
        whitelist=lambda *args, **kwargs: (lambda function: function),
        local=types.SimpleNamespace(response_headers={}))
    monkeypatch.setitem(sys.modules, 'frappe', stubbed_frappe)
    imported_here = 'hb_knowledge_app.hb_knowledge.api' not in sys.modules
    api = importlib.import_module('hb_knowledge_app.hb_knowledge.api')
    monkeypatch.setattr(api, 'frappe', stubbed_frappe, raising=False)
    monkeypatch.setattr(api, 'load_runtime', lambda: 'runtime-sentinel')
    captured = {}

    def feedback_queue(runtime, page, page_size, status, query):
        captured.update(runtime=runtime, page=page, page_size=page_size,
                        status=status, query=query)
        return {'items': [], 'page': page, 'page_size': page_size, 'has_more': False}

    monkeypatch.setattr(activity, 'feedback_queue', feedback_queue)
    try:
        result = api.get_feedback_queue(page=2, page_size=5, status='Pending', query='维护')
    finally:
        if imported_here:
            sys.modules.pop('hb_knowledge_app.hb_knowledge.api', None)
            package = sys.modules.get('hb_knowledge_app.hb_knowledge')
            if package is not None:
                package.__dict__.pop('api', None)
    assert result == {'ok': True, 'data': {'items': [], 'page': 2, 'page_size': 5, 'has_more': False}}
    assert captured == {'runtime': 'runtime-sentinel', 'page': 2, 'page_size': 5,
                        'status': 'Pending', 'query': '维护'}
