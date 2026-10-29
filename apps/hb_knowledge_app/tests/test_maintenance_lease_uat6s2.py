"""Optional M: a Running batch must not be stranded by its original lease.

``claim`` sets a 30-minute lease once. ``progress`` refuses any update after
``lease_expires_at``, and ``claim`` only selects ``Queued`` rows - so a parse
that legitimately runs longer than the lease, or an executor that dies, leaves
the batch permanently ``Running`` with no path back. Recording progress renews
the lease; a finished outcome does not.
"""
import json
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.service_http import canonical


def _drive(monkeypatch, job, *, action, state=None, outcome='Running'):
    # maintenance_api imports frappe_factory, which imports the authority
    # module's database driver at import time; only the import surface is
    # replaced here.
    monkeypatch.setitem(sys.modules, 'pymysql', ModuleType('pymysql'))
    cipher = ModuleType('cryptography.fernet')
    cipher.Fernet = lambda *args: SimpleNamespace()
    monkeypatch.setitem(sys.modules, 'cryptography', ModuleType('cryptography'))
    monkeypatch.setitem(sys.modules, 'cryptography.fernet', cipher)

    frappe = ModuleType('frappe')
    writes = []
    frappe.db = SimpleNamespace(commit=lambda: None,
                                set_value=lambda table, name, values: writes.append(values))
    frappe.session = SimpleNamespace(user='coordinator@example.test')
    frappe.whitelist = lambda **kwargs: (lambda fn: fn)
    monkeypatch.setitem(sys.modules, 'frappe', frappe)

    from hb_knowledge_app.hb_knowledge import maintenance_api
    monkeypatch.setattr(maintenance_api, 'frappe', frappe, raising=False)

    raw = {'action': action, 'batch_id': 'IMP_' + 'a' * 32, 'job_id': 'JOB_1', 'nonce': 'NONCE',
           'state': state if state is not None else {'items': []}, 'outcome': outcome, 'error': None}
    principal = SimpleNamespace(client=SimpleNamespace(client_id='PORTAL'))
    monkeypatch.setattr(maintenance_api, '_service_request',
                        lambda **kwargs: (raw, principal, None))
    monkeypatch.setattr(maintenance_api, 'configuration',
                        lambda: {'portal_client_id': 'PORTAL',
                                 'maintenance_coordinator_user': 'coordinator@example.test'})
    row = {'name': raw['batch_id'], 'job_json': canonical(job),
           'state_json': canonical({'items': []})}
    monkeypatch.setattr(maintenance_api.m, '_row',
                        lambda batch_id, lock=False: (row, {'department_key': 'PRODUCTION'}, {'items': []}))
    monkeypatch.setattr(maintenance_api.m, 'registered', lambda frozen, state: None)
    return maintenance_api.controller(), writes, job


def test_progress_renews_the_lease(monkeypatch):
    before = time.time() + 60
    job = {'id': 'JOB_1', 'nonce': 'NONCE', 'status': 'Running',
           'lease_expires_at': before, 'document_ids': []}
    result, writes, job = _drive(monkeypatch, job, action='progress')
    assert result.get('ok') is True, result
    renewed = json.loads(writes[0]['job_json'])
    assert renewed['lease_expires_at'] > before


def test_a_finished_job_is_not_given_a_new_lease(monkeypatch):
    before = time.time() + 60
    job = {'id': 'JOB_1', 'nonce': 'NONCE', 'status': 'Running',
           'lease_expires_at': before, 'document_ids': []}
    result, writes, _ = _drive(monkeypatch, job, action='progress', outcome='Completed')
    assert result.get('ok') is True, result
    finished = json.loads(writes[0]['job_json'])
    assert finished['status'] == 'Completed'
    assert finished['lease_expires_at'] == before


def test_a_wrong_nonce_still_cannot_renew(monkeypatch):
    job = {'id': 'JOB_1', 'nonce': 'OTHER', 'status': 'Running',
           'lease_expires_at': time.time() + 60, 'document_ids': []}
    result, writes, _ = _drive(monkeypatch, job, action='progress')
    assert result.get('ok') is not True
    assert result['error']['code'] == 'IMPORT_BUSY'
    assert writes == []
