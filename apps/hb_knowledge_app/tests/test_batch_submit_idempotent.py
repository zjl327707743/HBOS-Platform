"""RC13 submit: one frozen batch set per plan digest, at most four per job."""
import hashlib
import importlib
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

import importlib.util


def _requires_service():
    if importlib.util.find_spec('knowledge_service') is None:
        pytest.skip('requires hbos_knowledge_service package; covered by the joint service integration run')


def install_framework(monkeypatch, user='maintainer@example.test'):
    monkeypatch.setitem(sys.modules, 'pymysql', ModuleType('pymysql'))
    cipher = ModuleType('cryptography.fernet')
    cipher.Fernet = lambda *args: SimpleNamespace()
    crypto = ModuleType('cryptography')
    crypto.fernet = cipher
    monkeypatch.setitem(sys.modules, 'cryptography', crypto)
    monkeypatch.setitem(sys.modules, 'cryptography.fernet', cipher)
    state = {'writes': [], 'commits': [], 'rows': {}, 'documents': {}}
    def set_value(table, name, values):
        state['writes'].append((table, name, values))
        if table == 'HBOS Knowledge Import Batch' and name in state['rows'] and isinstance(values, dict):
            state['rows'][name].update(values)
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


def load_modules(monkeypatch, cfg):
    frappe, state = install_framework(monkeypatch)
    batch = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_batch')
    maintenance = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    monkeypatch.setattr(batch, 'frappe', frappe, raising=False)
    monkeypatch.setattr(maintenance, 'frappe', frappe, raising=False)
    monkeypatch.setattr(batch, '_config', lambda: cfg)
    calls = {'register': 0, 'batches': []}
    def register(frozen, batch_state, label, creator):
        batch_id = 'IMP_' + frozen['batch_sha256'][:32]
        if batch_id not in state['rows']:
            state['rows'][batch_id] = {
                'name': batch_id, 'frozen_json': json.dumps(frozen),
                'state_json': json.dumps(batch_state), 'job_json': '{}', 'quality_json': '{}',
                'status': 'Imported', 'label': label,
                'department_key': frozen['department_key'], 'last_error': None}
            calls['register'] += 1
            calls['batches'].append(batch_id)
        return batch_id
    def row(batch_id, lock=False):
        value = state['rows'][batch_id]
        return value, json.loads(value['frozen_json']), json.loads(value['state_json'])
    monkeypatch.setattr(maintenance, 'register_batch', register)
    monkeypatch.setattr(maintenance, '_row', row)
    return batch, maintenance, frappe, state, calls


def workspace(tmp_path):
    source = tmp_path / 'sources'
    source.mkdir()
    upload = tmp_path / 'upload'
    upload.mkdir()
    derivative = tmp_path / 'derivative'
    derivative.mkdir()
    return source, {'maintenance_upload_root': str(upload),
                    'maintenance_batch_source_roots': [str(source)],
                    'maintenance_derivative_root': str(derivative),
                    'maintenance_embedding_model': 'approved-composite-embedding',
                    'department_space_map': {}}


def manifest(source, entries, **top):
    items = []
    for name, pages, extra in entries:
        path = source / name
        path.write_text(extra.pop('file_text', 'synthetic original bytes for ' + name), encoding='utf-8')
        extra = dict(extra)
        item = {'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'canonical_source_path': name, 'pages': pages,
                'page_methods': extra.pop('page_methods', ['native'] * len(pages)),
                'page_checks': extra.pop('page_checks', {'quality_pass': True})}
        item.update(extra)
        items.append(item)
    value = {'schema_version': 2, 'department': 'production',
             'sharing_confirmed': True, 'items': items}
    value.update(top)
    return value


def registry_for(items, *, department='production', status='uploaded'):
    documents = []
    for offset, item in enumerate(items):
        documents.append({'canonical_document_id': 'DOC_' + format(offset + 1, '024x'),
                          'version_id': 'VER_' + format(offset + 1, '024x'),
                          'sha256': item['source_sha256'], 'department_key': department,
                          'title': '合成流程文件' + str(offset), 'dataset_id': 'a' * 32,
                          'ragflow_document_id': format(offset + 1, '032x'),
                          'embedding_model': 'approved-composite-embedding',
                          'status': status,
                          'relative_path': item.get('relative_path') or 'file' + str(offset) + '.md'})
    return {'documents': documents}


def test_replaying_one_digest_never_registers_or_enqueues_twice(monkeypatch, tmp_path):
    _requires_service()
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    entries = [('批量%02d.md' % index, ['第%d页正文' % index], {}) for index in range(5)]
    body = manifest(source, entries)
    monkeypatch.setattr(maintenance, '_registry', lambda: registry_for(body['items']))
    plan = batch.plan_batch(body)
    assert plan['submittable'] is True
    first = batch.submit_batch(plan['plan_sha256'], 'OWNER_RC13_BATCH_A', 'RC13 批量入库')
    assert first['replayed'] is False
    assert len(first['batches']) == 2
    sizes = sorted(batch_entry['documents'] for batch_entry in first['batches'])
    assert sizes == [1, 4]
    assert all(batch_entry['documents'] <= 4 for batch_entry in first['batches'])
    assert calls['register'] == 2
    registered = list(state['rows'])
    # Every queued job names at most four frozen documents.
    for batch_entry in first['batches']:
        row = state['rows'][batch_entry['batch_id']]
        job = json.loads(row['job_json'])
        assert job['lease_generation'] == 0 and job['operation'] == 'parse'
        assert 1 <= len(job['document_ids']) <= 4
    second = batch.submit_batch(plan['plan_sha256'], 'OWNER_RC13_BATCH_A', 'RC13 批量入库')
    assert second['replayed'] is True
    assert [entry['batch_id'] for entry in second['batches']] == \
           [entry['batch_id'] for entry in first['batches']]
    # No second registration and no second derivative write.
    assert calls['register'] == 2
    assert list(state['rows']) == registered
    for batch_id in registered:
        frozen = json.loads(state['rows'][batch_id]['frozen_json'])
        item = frozen['items'][0]
        version = item['version_id']
        derivative = tmp_path / 'derivative' / batch_id / 'derivatives' / (version + '.txt')
        assert derivative.is_file()
        assert derivative.stat().st_mode & 0o777 == 0o600
        # The generated derivative text must be uploaded by the native stage:
        # keeping the original asset's physical id here makes apply() skip the
        # upload and fail with "Stored original checksum mismatch".
        assert item['ragflow_document_id'] is None
        assert item['dataset_id'] and item['dataset_id'] != '0' * 32
        asset = item['native_text_preflight']['original_asset']
        assert asset['dataset_id'] == item['dataset_id']
        assert asset['document_id'] and asset['document_id'] != '0' * 32
        # apply()/controller needs this exact per-batch map next to derivatives.
        dataset_map = tmp_path / 'derivative' / batch_id / 'dataset-map.json'
        assert json.loads(dataset_map.read_text()) == {
            'dataset_id': item['dataset_id'], 'department_key': 'production',
            'embedding_model': 'approved-composite-embedding',
            'batch_sha256': frozen['batch_sha256']}
    # Several queued batches never share one workspace: every batch has its own
    # map, and the maps do not overwrite each other.
    maps = sorted((tmp_path / 'derivative').glob('IMP_*/dataset-map.json'))
    assert len(maps) == 2
    payloads = [json.loads(path.read_text()) for path in maps]
    assert len({payload['batch_sha256'] for payload in payloads}) == 2


def test_duplicate_items_register_an_audit_batch_without_a_job(monkeypatch, tmp_path):
    _requires_service()
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    pages = ['重复正文']
    body = manifest(source, [('重复资料.md', pages, {})])
    item = body['items'][0]
    text_sha = hashlib.sha256(batch._page_source_text(pages).encode()).hexdigest()
    version = batch._version_identity(item['source_sha256'], text_sha, 'production')
    registry = registry_for(body['items'])
    registry['documents'][0]['version_id'] = version
    registry['documents'][0]['status'] = 'parsed/indexed'
    document_id = registry['documents'][0]['canonical_document_id']
    state['documents'][document_id] = {'current_version': version, 'withdrawn': 0,
                                       'ingestion_status': 'published'}
    monkeypatch.setattr(maintenance, '_registry', lambda: registry)
    plan = batch.plan_batch(body)
    assert plan['items'][0]['disposition'] == 'DUPLICATE'
    receipt = batch.submit_batch(plan['plan_sha256'], 'OWNER_RC13_BATCH_B', '重复审计')
    assert len(receipt['batches']) == 1
    entry = receipt['batches'][0]
    assert entry['kind'] == 'duplicate' and entry['queued_documents'] == 0
    assert json.loads(state['rows'][entry['batch_id']]['job_json']) == {}
    assert json.loads(state['rows'][entry['batch_id']]['state_json'])['items'][0]['status'] == 'skipped_duplicate'


def test_blocked_plan_never_freezes_a_batch(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    body = manifest(source, [('未知来源.md', ['正文'], {})])
    monkeypatch.setattr(maintenance, '_registry', lambda: {'documents': []})
    plan = batch.plan_batch(body)
    with pytest.raises(KnowledgeError) as error:
        batch.submit_batch(plan['plan_sha256'], 'OWNER_RC13_BATCH_C', '阻断')
    assert error.value.code == 'BATCH_PLAN_BLOCKED'
    assert calls['register'] == 0 and not state['rows']


def test_missing_shared_derivative_root_fails_before_any_registration(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    body = manifest(source, [('共享目录.md', ['正文'], {})])
    monkeypatch.setattr(maintenance, '_registry', lambda: registry_for(body['items']))
    plan = batch.plan_batch(body)
    cfg.pop('maintenance_derivative_root')
    with pytest.raises(KnowledgeError) as error:
        batch.submit_batch(plan['plan_sha256'], 'OWNER_RC13_BATCH_D', '未配置共享目录')
    assert error.value.code == 'BATCH_DERIVATIVE_ROOT_UNCONFIGURED'
    assert calls['register'] == 0 and state['writes'] == []


def test_registry_drift_between_preview_and_submit_is_rejected(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    body = manifest(source, [('漂移资料.md', ['正文'], {})])
    registry = registry_for(body['items'])
    monkeypatch.setattr(maintenance, '_registry', lambda: registry)
    plan = batch.plan_batch(body)
    registry['documents'][0]['status'] = 'parse_queued'
    with pytest.raises(KnowledgeError) as error:
        batch.submit_batch(plan['plan_sha256'], 'OWNER_RC13_BATCH_E', '漂移')
    assert error.value.code in ('BATCH_PLAN_STALE', 'BATCH_PLAN_BLOCKED')
    assert calls['register'] == 0


def test_unknown_digest_is_rejected(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    with pytest.raises(KnowledgeError) as error:
        batch.submit_batch('a' * 64, 'OWNER_RC13_BATCH_F', '不存在')
    assert error.value.code == 'BATCH_PLAN_STALE'
    assert calls['register'] == 0
