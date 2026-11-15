"""RC13 retrieval receipts: written only from verified server evidence."""
import importlib
import json
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.service_http import canonical


def install_framework(monkeypatch, user='maintainer@example.test'):
    monkeypatch.setitem(sys.modules, 'pymysql', ModuleType('pymysql'))
    cipher = ModuleType('cryptography.fernet')
    cipher.Fernet = lambda *args: SimpleNamespace()
    crypto = ModuleType('cryptography')
    crypto.fernet = cipher
    monkeypatch.setitem(sys.modules, 'cryptography', crypto)
    monkeypatch.setitem(sys.modules, 'cryptography.fernet', cipher)
    state = {'writes': [], 'commits': [], 'rows': {}, 'documents': {}}
    def set_value(table, name, field, value=None):
        state['writes'].append((table, name, field, value))
        if table == 'HBOS Knowledge Import Batch' and name in state['rows']:
            row = state['rows'][name]
            if isinstance(field, dict):
                row.update(field)
            else:
                row[field] = value
    frappe = SimpleNamespace(
        session=SimpleNamespace(user=user),
        whitelist=lambda **kwargs: (lambda fn: fn),
        db=SimpleNamespace(get_value=lambda table, name, fields=None, as_dict=False, **kw: (
                state['documents'].get(name) if table == 'HBOS Knowledge Document' else None),
            set_value=set_value, commit=lambda: state['commits'].append(True),
            rollback=lambda: None, exists=lambda *a: False, sql=lambda *a, **k: []),
        get_all=lambda *a, **k: [], get_doc=lambda *a, **k: SimpleNamespace(insert=lambda **k2: None))
    monkeypatch.setitem(sys.modules, 'frappe', frappe)
    return frappe, state


def load_modules(monkeypatch):
    frappe, state = install_framework(monkeypatch)
    batch = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_batch')
    maintenance = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    for module in (batch, maintenance):
        monkeypatch.setattr(module, 'frappe', frappe, raising=False)

    def row(batch_id, lock=False):
        value = state['rows'][batch_id]
        return value, json.loads(value.get('frozen_json') or '{}'), json.loads(value['state_json'])

    monkeypatch.setattr(maintenance, '_row', row)
    return batch, maintenance, frappe, state


def tracked_batch(state, *, status='parsed/indexed', version='VER_' + 'd' * 24,
                  document='DOC_' + 'c' * 24, quality=None):
    batch_id = 'IMP_' + '1' * 32
    state['rows'][batch_id] = {
        'name': batch_id,
        'frozen_json': canonical({'department_key': 'production'}),
        'state_json': canonical({'items': [{
            'canonical_document_id': document, 'version_id': version,
            'status': status, 'relative_path': '合成资料.md', 'title': '合成资料',
            'department_key': 'production', 'disposition': 'NEW',
            'dataset_id': 'a' * 32, 'ragflow_document_id': 'b' * 32,
            'binding_revision': 'BR_' + 'e' * 24, 'space_id': 'DEPT_PRODUCTION'}]}),
        'quality_json': canonical(quality or {}),
        'job_json': '{}', 'status': 'Imported', 'label': '收据',
        'department_key': 'production', 'last_error': None}
    return batch_id, document, version


def actual_target(document, version, **changes):
    fields={'canonical_document_id':document,'version_id':version,
            'dataset_id':'a'*32,'document_id':'b'*32,
            'binding_revision':'BR_'+'e'*24,'space_id':'DEPT_PRODUCTION'}
    return SimpleNamespace(**(fields|changes))


@pytest.mark.parametrize('document,version', [
    ('DOC_' + 'c' * 24, 'VER_' + 'd' * 24),
    ('N1DOC-' + 'c' * 24, 'VER_' + 'd' * 24),
    ('N1DOC-' + 'c' * 24, 'N1VER-' + 'd' * 24),
    ('DOC_S3_' + 'c' * 24, 'VER_S3_' + 'd' * 24),
])
def test_server_verified_employee_evidence_is_persisted_and_replayed(monkeypatch, document, version):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id, document, version = tracked_batch(state, document=document, version=version)
    state['documents'][document] = {'current_version': version, 'withdrawn': 0,
                                    'ingestion_status': 'published'}
    verified = {'actor_user': 'employee@example.test','binding':actual_target(document,version)}
    monkeypatch.setattr(batch, '_evidence_verification',
                        lambda evidence_id, document_id, version_id: verified)
    monkeypatch.setattr(batch, '_history_verification',
                        lambda owner, query_sha, document_id, version_id: 'ACT_SYNTHETIC')
    query_sha = 'f' * 64
    evidence_id = 'opaque-evidence-id'
    first = batch.record_verification(batch_id, document, version, evidence_id, query_sha)
    assert first['replayed'] is False
    assert first['receipt']['status'] == 'VERIFIED'
    assert first['receipt']['query_sha256'] == query_sha
    assert first['receipt']['evidence_id_hash']
    assert 'opaque-evidence-id' not in json.dumps(first)
    quality = json.loads(state['rows'][batch_id]['quality_json'])
    assert quality[version]['retrieval_verified']['status'] == 'VERIFIED'
    assert quality[version]['retrieval_verified']['receipt_sha256']
    writes = len([write for write in state['writes'] if write[2] == 'quality_json'])
    assert writes == 1
    second = batch.record_verification(batch_id, document, version, evidence_id, query_sha)
    assert second['replayed'] is True
    assert second['receipt'] == first['receipt']
    assert len([write for write in state['writes'] if write[2] == 'quality_json']) == writes


@pytest.mark.parametrize('document,version', [
    ('DOC_' + 'c' * 24, 'VER_' + 'd' * 24),
    ('N1DOC-' + 'c' * 24, 'VER_' + 'd' * 24),
    ('N1DOC-' + 'c' * 24, 'N1VER-' + 'd' * 24),
    ('DOC_S3_' + 'c' * 24, 'VER_S3_' + 'd' * 24),
])
def test_a_browser_claim_without_server_evidence_is_rejected(monkeypatch, document, version):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id, document, version = tracked_batch(state, document=document, version=version)
    state['documents'][document] = {'current_version': version, 'withdrawn': 0,
                                    'ingestion_status': 'published'}
    def reject(*args, **kwargs):
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    monkeypatch.setattr(batch, '_evidence_verification', reject)
    monkeypatch.setattr(batch, '_history_verification',
                        lambda *args, **kwargs: 'ACT_SYNTHETIC')
    with pytest.raises(KnowledgeError) as error:
        batch.record_verification(batch_id, document, version, 'forged', 'f' * 64)
    assert error.value.code == 'EVIDENCE_UNAVAILABLE'
    assert state['writes'] == []


def test_search_history_must_match_the_same_query_and_reference(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id, document, version = tracked_batch(state)
    state['documents'][document] = {'current_version': version, 'withdrawn': 0,
                                    'ingestion_status': 'published'}
    monkeypatch.setattr(batch, '_evidence_verification',
                        lambda *args: {'actor_user': 'employee@example.test','binding':actual_target(document,version)})
    monkeypatch.setattr(batch, '_history_verification', lambda *args: None)
    with pytest.raises(KnowledgeError) as error:
        batch.record_verification(batch_id, document, version, 'evidence', 'f' * 64)
    assert error.value.code == 'EVIDENCE_UNAVAILABLE'
    assert state['writes'] == []


@pytest.mark.parametrize('version', ['N1VER-' + 'd' * 23, 'N1VER-' + 'd' * 25,
                                   'N1VER-' + 'D' * 24, 'N1VER-' + '../' * 8])
def test_malformed_legacy_version_never_reaches_evidence_or_writes(monkeypatch, version):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id, document, _ = tracked_batch(state, version=version)
    def forbidden(*args):
        pytest.fail('Malformed identity must be rejected before evidence lookup')
    monkeypatch.setattr(batch, '_evidence_verification', forbidden)
    with pytest.raises(KnowledgeError) as error:
        batch.record_verification(batch_id, document, version, 'evidence', 'f' * 64)
    assert error.value.code == 'INVALID_REQUEST'
    assert state['writes'] == []


@pytest.mark.parametrize('document,version', [
    ('N1DOC-' + 'c' * 24, 'VER_' + 'd' * 24),
    ('N1DOC-' + 'c' * 24, 'N1VER-' + 'd' * 24),
    ('DOC_S3_' + 'c' * 24, 'VER_S3_' + 'd' * 24),
])
@pytest.mark.parametrize('published', [None,
    {'current_version': 'VER_' + '9' * 24, 'withdrawn': 0, 'ingestion_status': 'published'},
    {'withdrawn': 1, 'ingestion_status': 'retired'},
])
def test_rebuild_identity_cannot_verify_absent_withdrawn_or_superseded_document(
        monkeypatch, document, version, published):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id, _, _ = tracked_batch(state, document=document, version=version)
    if published is not None:
        state['documents'][document] = published
    def unexpected_evidence_lookup(*args):
        pytest.fail('Stale publication must be rejected before evidence lookup')
    monkeypatch.setattr(batch, '_evidence_verification', unexpected_evidence_lookup)
    with pytest.raises(KnowledgeError) as error:
        batch.record_verification(batch_id, document, version, 'evidence', 'f' * 64)
    assert error.value.code == 'SOURCE_VERSION_STALE'
    assert state['writes'] == []


@pytest.mark.parametrize('changed',[
    {'dataset_id':'9'*32},{'document_id':'8'*32},
    {'binding_revision':'BR_old_parse'},{'space_id':'OTHER_SPACE'}])
def test_same_business_version_evidence_from_old_index_cannot_verify_new_parse(monkeypatch,changed):
    batch, maintenance, frappe, state=load_modules(monkeypatch)
    batch_id,document,version=tracked_batch(state)
    state['documents'][document]={'current_version':version,'withdrawn':0,'ingestion_status':'published'}
    monkeypatch.setattr(batch,'_evidence_verification',lambda *a:{
        'actor_user':'employee@example.test','binding':actual_target(document,version,**changed)})
    monkeypatch.setattr(batch,'_history_verification',lambda *a:'OLD_REAL_HISTORY_SAME_VERSION')
    with pytest.raises(KnowledgeError) as error:
        batch.record_verification(batch_id,document,version,'old-index-evidence','f'*64)
    assert error.value.code=='EVIDENCE_UNAVAILABLE'
    assert state['writes']==[]


def test_withdrawn_version_is_invalidated_without_losing_history(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    version = 'VER_' + 'd' * 24
    document = 'DOC_' + 'c' * 24
    receipt = {'schema': 'rc13-retrieval-verified-v1', 'status': 'VERIFIED',
               'at': time.time(), 'query_sha256': 'f' * 64,
               'evidence_id_hash': 'e' * 64, 'receipt_sha256': 'a' * 64}
    batch_id, _, _ = tracked_batch(state, quality={version: {'retrieval_verified': receipt,
                                                             'status': 'Passed'}})
    state['documents'][document] = {'current_version': version, 'withdrawn': 1,
                                    'ingestion_status': 'retired'}
    progress = batch.progress_batch(batch_id)
    entry = progress['items'][0]
    assert entry['retrieval_verified']['status'] == 'INVALIDATED'
    assert entry['retrieval_verified']['reason'] == 'WITHDRAWN'
    quality = json.loads(state['rows'][batch_id]['quality_json'])
    assert quality[version]['retrieval_verified']['receipt_sha256'] == 'a' * 64


def test_superseded_version_is_invalidated(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    version = 'VER_' + 'd' * 24
    document = 'DOC_' + 'c' * 24
    receipt = {'schema': 'rc13-retrieval-verified-v1', 'status': 'VERIFIED',
               'at': time.time(), 'receipt_sha256': 'a' * 64}
    batch_id, _, _ = tracked_batch(state, quality={version: {'retrieval_verified': receipt}})
    state['documents'][document] = {'current_version': 'VER_' + '9' * 24, 'withdrawn': 0,
                                    'ingestion_status': 'published'}
    entry = batch.progress_batch(batch_id)['items'][0]
    assert entry['retrieval_verified']['status'] == 'INVALIDATED'
    assert entry['retrieval_verified']['reason'] == 'VERSION_SUPERSEDED'


def test_publication_leaves_an_honest_pending_marker(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id, document, version = tracked_batch(state, status='parsed/indexed')
    result = {'results': [{'document_id': document, 'outcome': 'PUBLISHED',
                           'receipt_id': 'PUB_' + '2' * 64}]}
    first = batch.mark_retrieval_pending(batch_id, result)
    assert first == {'pending': 1}
    quality = json.loads(state['rows'][batch_id]['quality_json'])
    assert quality[version]['retrieval_verified']['status'] == 'PENDING'
    writes = len(state['writes'])
    second = batch.mark_retrieval_pending(batch_id, result)
    assert second == {'pending': 0} and len(state['writes']) == writes
    entry = batch.progress_batch(batch_id)['items'][0]
    assert entry['retrieval_verified']['status'] == 'PENDING'
