"""MC-3: the maintenance page can show a document's version lineage.

The lineage is derived from the existing backend bindings and import batches;
nothing is inferred from title similarity and no corpus scan happens.
"""
import sys
from types import ModuleType

if 'frappe' not in sys.modules:  # the pure helper does not touch frappe
    sys.modules['frappe'] = ModuleType('frappe')
sys.modules.setdefault('pymysql', ModuleType('pymysql'))
_cipher = ModuleType('cryptography.fernet'); _cipher.Fernet = lambda *a, **k: None
sys.modules.setdefault('cryptography', ModuleType('cryptography'))
sys.modules.setdefault('cryptography.fernet', _cipher)

import pytest  # noqa: E402

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError  # noqa: E402
from hb_knowledge_app.hb_knowledge.maintenance import _lineage_rows  # noqa: E402

DOC = 'DOC_0123456789abcdef01234567'


def batch(modified, versions, doc=DOC):
    return {'name': 'IMP_' + modified, 'modified': modified,
            'state_json': '{"items":[' + ','.join(
                '{"canonical_document_id":"%s","version_id":"%s","sha256":"%s"}' % (doc, v, 'a' * 64)
                for v in versions) + ']}'}


def test_lineage_orders_by_batch_time_and_links_the_chain():
    binding_rows = [{'version_id': 'VER_old', 'enabled': True},
                    {'version_id': 'VER_new', 'enabled': True}]
    batch_rows = [batch('2026-11-01 00:00:00', ['VER_old']),
                  batch('2026-11-02 00:00:00', ['VER_new'])]
    result = _lineage_rows(DOC, 'VER_new', binding_rows, batch_rows, 1, 12)
    assert result['total'] == 2 and [v['version_id'] for v in result['versions']] == ['VER_old', 'VER_new']
    old, new = result['versions']
    assert old['publication_state'] == 'HISTORICAL' and old['superseded_by'] == 'VER_new'
    assert old['rollback_eligible'] is True
    assert new['publication_state'] == 'PUBLISHED' and new['supersedes'] == 'VER_old'
    assert new['rollback_eligible'] is False


def test_lineage_records_source_hash_and_quality_state():
    batch_rows = [{'name': 'IMP_x', 'modified': '2026-11-02 00:00:00',
                   'state': {'items': [{'canonical_document_id': DOC, 'version_id': 'VER_one',
                                        'sha256': 'b' * 64}]}}]
    result = _lineage_rows(DOC, 'VER_one', [], batch_rows, 1, 12)
    only = result['versions'][0]
    assert only['source_hash'] == 'b' * 64 and only['quality_state'] == 'VERIFIED'


def test_lineage_skips_duplicate_skip_items_and_other_documents():
    batch_rows = [{'name': 'IMP_y', 'modified': '2026-11-03 00:00:00',
                   'state': {'items': [
                       {'canonical_document_id': DOC, 'version_id': 'VER_keep'},
                       {'canonical_document_id': DOC, 'version_id': 'VER_skipped',
                        'disposition': 'SAME_CONTENT_SKIP'},
                       {'canonical_document_id': 'DOC_other', 'version_id': 'VER_other'}]}}]
    result = _lineage_rows(DOC, 'VER_keep', [], batch_rows, 1, 12)
    assert [v['version_id'] for v in result['versions']] == ['VER_keep']


def test_lineage_paginates_without_losing_the_total():
    batch_rows = [batch(f'2026-11-{index:02d} 00:00:00', [f'VER_{index:02d}']) for index in range(1, 26)]
    result = _lineage_rows(DOC, 'VER_25', [], batch_rows, 3, 10)
    assert result['total'] == 25 and len(result['versions']) == 5
    assert result['has_more'] is False and result['page'] == 3
    assert result['versions'][0]['version_id'] == 'VER_21'


def test_lineage_is_empty_when_nothing_records_the_document():
    result = _lineage_rows(DOC, None, [], [], 1, 12)
    assert result['total'] == 0 and result['versions'] == [] and result['has_more'] is False


def test_lineage_only_marks_bindings_the_backend_actually_has():
    binding_rows = [{'version_id': 'VER_a', 'enabled': False}]
    batch_rows = [batch('2026-11-01 00:00:00', ['VER_a', 'VER_b'])]
    result = _lineage_rows(DOC, 'VER_b', binding_rows, batch_rows, 1, 12)
    states = {v['version_id']: v['publication_state'] for v in result['versions']}
    assert states == {'VER_a': 'UNPUBLISHED', 'VER_b': 'PUBLISHED'}
    assert result['versions'][1]['rollback_eligible'] is False


def test_the_frappe_entry_point_rejects_malformed_document_ids(monkeypatch):
    import frappe  # the module stub installed above
    from hb_knowledge_app.hb_knowledge import maintenance as module

    called = {}
    monkeypatch.setattr(module, 'require', lambda: called.setdefault('require', True))
    for bad in (None, '', 'DOC_', 'evil', 'doc_0123456789abcdef01234567', 'DOC_short'):
        with pytest.raises(KnowledgeError):
            module.version_lineage(bad, 1, 12)
    assert called.get('require') is True
