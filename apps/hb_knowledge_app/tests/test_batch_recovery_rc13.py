"""RC13 recovery: quarantined technical failures retry without replaying successes."""
import hashlib
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
        get_all=lambda *a, **k: [],
        get_doc=lambda *a, **k: SimpleNamespace(insert=lambda **k2: None))
    monkeypatch.setitem(sys.modules, 'frappe', frappe)
    return frappe, state


def load_modules(monkeypatch, cfg=None):
    frappe, state = install_framework(monkeypatch)
    batch = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_batch')
    maintenance = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    for module in (batch, maintenance):
        monkeypatch.setattr(module, 'frappe', frappe, raising=False)
    if cfg is not None:
        monkeypatch.setattr(batch, '_config', lambda: cfg)

    def row(batch_id, lock=False):
        value = state['rows'][batch_id]
        return value, json.loads(value['frozen_json']), json.loads(value['state_json'])

    monkeypatch.setattr(maintenance, '_row', row)
    return batch, maintenance, frappe, state


BATCH = 'IMP_' + '7' * 32
DOC_FAILED = 'DOC_' + '1' * 24
DOC_DONE = 'DOC_' + '2' * 24
VER_FAILED = 'VER_' + '3' * 24
VER_DONE = 'VER_' + '4' * 24


def failed_batch(state, *, job_status='Blocked', job_extra=None, item_status='quarantined'):
    items = [
        {'canonical_document_id': DOC_FAILED, 'version_id': VER_FAILED,
         'relative_path': '失败资料.md', 'title': '失败资料', 'department_key': 'production',
         'status': item_status, 'dataset_id': 'a' * 32,
         'ragflow_document_id': 'b' * 32, 'upload_sha256': 'c' * 64,
         'upload_name': VER_FAILED + '.txt', 'actual_run': 'DONE', 'chunk_count': 0,
         'progress': 0, 'attempt_error': 'UNKNOWN_ENQUEUE_OUTCOME_REQUIRES_TASK_RECONCILIATION',
         'private_parse_message': 'Stored original checksum mismatch'},
        {'canonical_document_id': DOC_DONE, 'version_id': VER_DONE,
         'relative_path': '成功资料.md', 'title': '成功资料', 'department_key': 'production',
         'status': 'parsed/indexed', 'dataset_id': 'a' * 32,
         'ragflow_document_id': 'd' * 32, 'upload_sha256': 'e' * 64,
         'upload_name': VER_DONE + '.txt', 'actual_run': 'DONE', 'chunk_count': 8,
         'progress': 1},
    ]
    job = {'id': 'JOB_1', 'status': job_status, 'operation': 'parse',
           'document_ids': [DOC_FAILED, DOC_DONE], 'requested_by': 'maintainer@example.test',
           'requested_at': time.time() - 300, 'lease_generation': 2, 'nonce': None,
           'lease_expires_at': None, 'pause_requested': False, 'reclaims': []}
    if job_extra:
        job.update(job_extra)
    state['rows'][BATCH] = {
        'name': BATCH, 'frozen_json': canonical({'department_key': 'production',
                                                 'batch_sha256': 'a' * 64}),
        'state_json': canonical({'items': items, 'batch_sha256': 'a' * 64}),
        'job_json': canonical(job), 'quality_json': '{}', 'status': job_status,
        'department_key': 'production', 'label': '隔离重试', 'last_error': None}
    return BATCH


def test_quarantined_retry_resets_only_the_failed_item_and_audits_the_request(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id = failed_batch(state)
    before = json.loads(state['rows'][batch_id]['state_json'])
    result = batch.retry_batch(batch_id, [DOC_FAILED], '核对派生文本后重试，修复原件校验错误')
    assert result['status'] == 'Queued' and result['replayed'] is False
    assert result['retried_documents'] == 1 and result['job_id']
    after = json.loads(state['rows'][batch_id]['state_json'])
    failed = next(item for item in after['items'] if item['canonical_document_id'] == DOC_FAILED)
    done = next(item for item in after['items'] if item['canonical_document_id'] == DOC_DONE)
    # The failed item is re-driven from the start and must upload the generated
    # derivative text, so the stale physical id is cleared.
    assert failed['status'] == 'planned'
    assert failed['ragflow_document_id'] is None
    assert failed['upload_sha256'] is None and failed['upload_name'] is None
    # Historical failure facts are retained, not overwritten.
    assert failed['attempt_error'] == 'UNKNOWN_ENQUEUE_OUTCOME_REQUIRES_TASK_RECONCILIATION'
    assert failed['private_parse_message'] == 'Stored original checksum mismatch'
    assert failed['actual_run'] == 'DONE'
    # Already successful items are never touched by the retry.
    assert done == before['items'][1]
    row = state['rows'][batch_id]
    assert row['status'] == 'Queued'
    job = json.loads(row['job_json'])
    assert job['status'] == 'Queued' and job['operation'] == 'parse'
    assert job['document_ids'] == [DOC_FAILED]
    assert job['lease_generation'] == 2
    assert job['retry_id'] and len(job['retry_id']) == 28
    assert len(job['recoveries']) == 1
    audit = job['recoveries'][0]
    assert audit['kind'] == 'QUARANTINE_RETRY'
    assert audit['reason'] == '核对派生文本后重试，修复原件校验错误'
    assert len(audit['actor_hash']) == 16
    assert audit['document_ids'] == [DOC_FAILED]
    assert audit['prior_statuses'] == {DOC_FAILED: 'quarantined'}
    assert audit['prior_attempt_errors'][DOC_FAILED] == \
        'UNKNOWN_ENQUEUE_OUTCOME_REQUIRES_TASK_RECONCILIATION'
    assert state['commits']


def test_repeating_the_same_retry_while_queued_is_idempotent(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id = failed_batch(state)
    first = batch.retry_batch(batch_id, [DOC_FAILED], '隔离重试原因')
    writes = len(state['writes'])
    second = batch.retry_batch(batch_id, [DOC_FAILED], '隔离重试原因')
    assert second['replayed'] is True
    assert second['job_id'] == first['job_id']
    assert second['retry_id'] == first['retry_id']
    # No extra mutation or duplicate recovery record.
    assert len(state['writes']) == writes
    job = json.loads(state['rows'][batch_id]['job_json'])
    assert len(job['recoveries']) == 1


def test_a_different_active_job_still_blocks_a_retry(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id = failed_batch(state)
    batch.retry_batch(batch_id, [DOC_FAILED], '隔离重试原因')
    job = json.loads(state['rows'][batch_id]['job_json'])
    job['retry_id'] = 'RCV_' + 'f' * 24
    state['rows'][batch_id]['job_json'] = canonical(job)
    with pytest.raises(KnowledgeError) as error:
        batch.retry_batch(batch_id, [DOC_FAILED], '另一个重试')
    assert error.value.code == 'IMPORT_BUSY'


def test_only_quarantined_items_can_be_retried(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id = failed_batch(state)
    with pytest.raises(KnowledgeError) as error:
        batch.retry_batch(batch_id, [DOC_DONE], '已成功项不应重试')
    assert error.value.code == 'INVALID_REQUEST'
    assert state['writes'] == []


def test_retry_after_success_is_a_noop_not_a_replay(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id = failed_batch(state)
    batch.retry_batch(batch_id, [DOC_FAILED], '隔离重试原因')
    state_row = json.loads(state['rows'][batch_id]['state_json'])
    for item in state_row['items']:
        if item['canonical_document_id'] == DOC_FAILED:
            item['status'] = 'parsed/indexed'
    state['rows'][batch_id]['state_json'] = canonical(state_row)
    job = json.loads(state['rows'][batch_id]['job_json'])
    job['status'] = 'Completed'
    state['rows'][batch_id]['job_json'] = canonical(job)
    with pytest.raises(KnowledgeError) as error:
        batch.retry_batch(batch_id, [DOC_FAILED], '隔离重试原因')
    assert error.value.code == 'INVALID_REQUEST'


def test_retry_rejects_active_running_or_paused_batches(monkeypatch):
    for job_status in ('Running', 'Queued', 'Paused'):
        batch, maintenance, frappe, state = load_modules(monkeypatch)
        batch_id = failed_batch(state, job_status=job_status)
        with pytest.raises(KnowledgeError) as error:
            batch.retry_batch(batch_id, [DOC_FAILED], '活动批次不允许重试')
        assert error.value.code == 'IMPORT_BUSY'
        assert state['writes'] == []


def test_progress_does_not_report_a_stale_error_after_recovery_succeeds(monkeypatch):
    batch, maintenance, frappe, state = load_modules(monkeypatch)
    batch_id = failed_batch(state)
    state_row = json.loads(state['rows'][batch_id]['state_json'])
    state_row['items'][0].update(status='parsed/indexed', chunk_count=6, progress=1)
    state['rows'][batch_id]['state_json'] = canonical(state_row)
    progress = batch.progress_batch(batch_id)
    assert progress['items'][0]['status'] == 'parsed/indexed'
    assert progress['items'][0]['error_code'] is None
