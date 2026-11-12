"""RC13 lease fencing: reclaim only expired leases; stale workers cannot write."""
import importlib
import json
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError, error_payload
from hb_knowledge_app.hb_knowledge.service_http import canonical


def fake_run(api_module, monkeypatch):
    """Drive the signed port without Frappe's request/envelope plumbing."""
    def envelope(inner):
        try:
            return {'ok': True, 'data': inner()}
        except KnowledgeError as error:
            return error_payload(error, 'synthetic-request-id')
    monkeypatch.setattr(api_module, '_authority_envelope', envelope)


def install_framework(monkeypatch, user='maintainer@example.test'):
    monkeypatch.setitem(sys.modules, 'pymysql', ModuleType('pymysql'))
    cipher = ModuleType('cryptography.fernet')
    cipher.Fernet = lambda *args: SimpleNamespace()
    crypto = ModuleType('cryptography')
    crypto.fernet = cipher
    monkeypatch.setitem(sys.modules, 'cryptography', crypto)
    monkeypatch.setitem(sys.modules, 'cryptography.fernet', cipher)
    state = {'writes': [], 'commits': [], 'rows': {}, 'documents': {}, 'sql': []}
    def set_value(table, name, values):
        state['writes'].append((table, name, values))
        if table == 'HBOS Knowledge Import Batch' and name in state['rows'] and isinstance(values, dict):
            state['rows'][name].update(values)
    def sql(query, *args, **kwargs):
        state['sql'].append((query, args))
        return []
    frappe = SimpleNamespace(
        session=SimpleNamespace(user=user),
        whitelist=lambda **kwargs: (lambda fn: fn),
        db=SimpleNamespace(get_value=lambda table, name, fields=None, as_dict=False, **kw: (
                state['documents'].get(name) if table == 'HBOS Knowledge Document' else None),
            set_value=set_value, commit=lambda: state['commits'].append(True),
            rollback=lambda: None, exists=lambda *a: False, sql=sql),
        get_all=lambda *a, **k: [], get_doc=lambda *a, **k: SimpleNamespace(insert=lambda **k2: None))
    monkeypatch.setitem(sys.modules, 'frappe', frappe)
    return frappe, state


def load_modules(monkeypatch):
    frappe, state = install_framework(monkeypatch)
    batch = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_batch')
    maintenance = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    api_module = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_api')
    for module in (batch, maintenance, api_module):
        monkeypatch.setattr(module, 'frappe', frappe, raising=False)

    def row(batch_id, lock=False):
        value = state['rows'][batch_id]
        return value, json.loads(value['frozen_json']), json.loads(value['state_json'])

    monkeypatch.setattr(maintenance, '_row', row)
    return batch, maintenance, api_module, frappe, state


def running_batch(batch_id, *, generation=2, lease_delta=-60, items=None):
    job = {'id': 'JOB_1', 'status': 'Running', 'operation': 'parse', 'document_ids': ['DOC_1'],
           'requested_by': 'maintainer@example.test', 'requested_at': time.time() - 100,
           'lease_generation': generation, 'nonce': 'NONCE_OLD',
           'lease_expires_at': time.time() + lease_delta, 'pause_requested': False,
           'reclaims': []}
    state = {'items': items or [{'canonical_document_id': 'DOC_1', 'version_id': 'VER_1',
                                 'status': 'parse_queued', 'relative_path': 'a.md'}],
             'batch_sha256': 'a' * 64}
    return {'name': batch_id, 'frozen_json': '{}', 'state_json': json.dumps(state),
            'job_json': canonical(job), 'quality_json': '{}', 'status': 'Running',
            'department_key': 'production', 'label': 'lease', 'last_error': None}


def test_reclaim_only_touches_expired_leases_and_audits_the_fence(monkeypatch, tmp_path):
    batch, maintenance, api_module, frappe, state = load_modules(monkeypatch)
    expired_id = 'IMP_' + '1' * 32
    live_id = 'IMP_' + '2' * 32
    state['rows'][expired_id] = running_batch(expired_id, generation=2, lease_delta=-60)
    state['rows'][live_id] = running_batch(live_id, generation=4, lease_delta=600)
    monkeypatch.setattr(batch, '_expired_batches', lambda batch_id=None: [expired_id, live_id])
    reclaimed = batch.reclaim_expired(actor='coordinator@example.test', reason='LEASE_EXPIRED')
    assert [entry['batch_id'] for entry in reclaimed] == [expired_id]
    expired = state['rows'][expired_id]
    assert expired['status'] == 'Queued'
    job = json.loads(expired['job_json'])
    assert job['status'] == 'Queued' and job['lease_generation'] == 3
    assert job['nonce'] is None and job['lease_expires_at'] is None
    assert len(job['reclaims']) == 1
    audit = job['reclaims'][0]
    assert audit['previous_generation'] == 2 and audit['new_generation'] == 3
    assert audit['reason'] == 'LEASE_EXPIRED' and len(audit['actor_hash']) == 16
    assert audit['previous_nonce_sha256']
    # Item states are never bulk-reset by a reclaim.
    assert json.loads(expired['state_json']) == json.loads(state['rows'][expired_id]['state_json'])
    assert json.loads(expired['state_json'])['items'][0]['status'] == 'parse_queued'
    live = state['rows'][live_id]
    assert live['status'] == 'Running'
    assert json.loads(live['job_json'])['lease_generation'] == 4
    assert len([write for write in state['writes'] if write[1] == live_id]) == 0


def test_explicit_reclaim_of_a_live_lease_is_a_noop(monkeypatch):
    batch, maintenance, api_module, frappe, state = load_modules(monkeypatch)
    live_id = 'IMP_' + '3' * 32
    state['rows'][live_id] = running_batch(live_id, lease_delta=600)
    monkeypatch.setattr(batch, '_expired_batches', lambda batch_id=None: [live_id])
    result = batch.reclaim_batch(live_id, '维护员尝试回收一个仍有效的租约')
    assert result == {'reclaimed': [], 'total': 0}
    assert json.loads(state['rows'][live_id]['job_json'])['lease_generation'] == 2
    assert state['writes'] == []


def test_claim_advances_the_generation_and_counts_the_bounded_sweep(monkeypatch):
    batch, maintenance, api_module, frappe, state = load_modules(monkeypatch)
    batch_id = 'IMP_' + '4' * 32
    state['rows'][batch_id] = running_batch(batch_id, generation=5, lease_delta=600)
    state['rows'][batch_id]['status'] = 'Queued'
    job = json.loads(state['rows'][batch_id]['job_json'])
    job.update(status='Queued', nonce=None, lease_expires_at=None, generation=5)
    job['lease_generation'] = 5
    state['rows'][batch_id]['job_json'] = canonical(job)
    sweep = []
    monkeypatch.setattr(batch, 'reclaim_expired', lambda **kwargs: sweep.append(kwargs) or [])
    raw = {'action': 'claim'}
    principal = SimpleNamespace(client=SimpleNamespace(client_id='PORTAL'))
    monkeypatch.setattr(api_module, '_service_request', lambda **kw: (raw, principal, None))
    monkeypatch.setattr(api_module, 'configuration', lambda: {
        'portal_client_id': 'PORTAL', 'maintenance_coordinator_user': 'coordinator@example.test'})
    fake_run(api_module, monkeypatch)
    monkeypatch.setattr(api_module.m, '_row',
                        lambda name, lock=False: (state['rows'][name], {}, json.loads(
                            state['rows'][name]['state_json'])))
    monkeypatch.setattr(frappe.db, 'sql', lambda *a, **k: [{'name': batch_id}])
    from hb_knowledge_app.hb_knowledge import maintenance_access
    monkeypatch.setattr(maintenance_access, 'permitted', lambda user=None: True)
    result = api_module.controller()
    assert result['ok'] is True, result
    claimed = result['data']
    assert claimed['job']['lease_generation'] == 6
    assert claimed['job']['status'] == 'Running' and claimed['job']['nonce']
    assert claimed['job']['lease_expires_at'] > time.time()
    assert claimed['reclaimed'] == 0
    assert len(sweep) == 1


def drive_progress(monkeypatch, job, *, generation, outcome='Running', state=None):
    frappe, fake_state = install_framework(monkeypatch)
    api_module = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_api')
    monkeypatch.setattr(api_module, 'frappe', frappe, raising=False)
    raw = {'action': 'progress', 'batch_id': 'IMP_' + 'a' * 32, 'job_id': 'JOB_1',
           'nonce': 'NONCE_OLD', 'state': state if state is not None else {'items': []},
           'outcome': outcome, 'error': None, 'lease_generation': generation}
    principal = SimpleNamespace(client=SimpleNamespace(client_id='PORTAL'))
    monkeypatch.setattr(api_module, '_service_request', lambda **kw: (raw, principal, None))
    monkeypatch.setattr(api_module, 'configuration', lambda: {
        'portal_client_id': 'PORTAL', 'maintenance_coordinator_user': 'coordinator@example.test'})
    fake_run(api_module, monkeypatch)
    row = {'name': raw['batch_id'], 'job_json': canonical(job),
           'state_json': canonical({'items': []})}
    maintenance = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    monkeypatch.setattr(maintenance, '_row', lambda batch_id, lock=False: (
        row, {'department_key': 'production'}, {'items': []}))
    monkeypatch.setattr(maintenance, 'registered', lambda frozen, value: None)
    return api_module.controller(), fake_state, row


def test_progress_requires_the_current_generation(monkeypatch):
    job = {'id': 'JOB_1', 'nonce': 'NONCE_OLD', 'status': 'Running',
           'lease_expires_at': time.time() + 60, 'document_ids': [],
           'lease_generation': 7}
    result, writes, _ = drive_progress(monkeypatch, job, generation=6)
    assert result.get('ok') is not True
    assert result['error']['code'] == 'IMPORT_BUSY'
    assert writes['writes'] == []


def test_progress_without_generation_is_rejected_once_fenced(monkeypatch):
    job = {'id': 'JOB_1', 'nonce': 'NONCE_OLD', 'status': 'Running',
           'lease_expires_at': time.time() + 60, 'document_ids': [],
           'lease_generation': 7}
    result, writes, _ = drive_progress(monkeypatch, job, generation=None)
    assert result.get('ok') is not True
    assert result['error']['code'] == 'IMPORT_BUSY'
    assert writes['writes'] == []


def test_current_generation_renews_the_lease(monkeypatch):
    before = time.time() + 60
    job = {'id': 'JOB_1', 'nonce': 'NONCE_OLD', 'status': 'Running',
           'lease_expires_at': before, 'document_ids': [],
           'lease_generation': 7}
    result, writes, _ = drive_progress(monkeypatch, job, generation=7)
    assert result['ok'] is True, result
    renewed = json.loads(writes['writes'][0][2]['job_json'])
    assert renewed['lease_expires_at'] > before and renewed['lease_generation'] == 7


def test_terminal_report_closes_the_fence_for_late_writes(monkeypatch):
    before = time.time() + 60
    job = {'id': 'JOB_1', 'nonce': 'NONCE_OLD', 'status': 'Running',
           'lease_expires_at': before, 'document_ids': [],
           'lease_generation': 7}
    result, writes, _ = drive_progress(monkeypatch, job, generation=7, outcome='Completed')
    assert result['ok'] is True, result
    finished = json.loads(writes['writes'][0][2]['job_json'])
    assert finished['status'] == 'Completed' and finished['nonce'] is None
    assert finished['lease_expires_at'] == before
    # A late Running report from the same worker is rejected: status != Running.
    late = {'id': 'JOB_1', 'nonce': 'NONCE_OLD', 'status': 'Completed',
            'lease_expires_at': before, 'document_ids': [], 'lease_generation': 7}
    result, writes, _ = drive_progress(monkeypatch, late, generation=7)
    assert result.get('ok') is not True and result['error']['code'] == 'IMPORT_BUSY'
    assert writes['writes'] == []
