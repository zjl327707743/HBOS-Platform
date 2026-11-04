"""RC13 batch preview: read-only, stable digest, honest classifications."""
import hashlib
import importlib
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


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
    calls = {'register': 0}

    def register(frozen, batch_state, label, creator):
        batch_id = 'IMP_' + frozen['batch_sha256'][:32]
        if batch_id not in state['rows']:
            state['rows'][batch_id] = {
                'name': batch_id, 'frozen_json': json.dumps(frozen),
                'state_json': json.dumps(batch_state), 'job_json': '{}', 'quality_json': '{}',
                'status': 'Imported', 'label': label,
                'department_key': frozen['department_key'], 'last_error': None}
            calls['register'] += 1
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
                    'department_space_map': {}}


def manifest(source, entries, **top):
    items = []
    for name, pages, extra in entries:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True) if path.parent != source else None
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


def uploaded_registry(item, *, department='production', status='uploaded',
                      document_id='DOC_' + 'c' * 24, version_id='VER_' + 'd' * 24,
                      dataset_id='a' * 32, ragflow_document_id='b' * 32):
    return {'documents': [{
        'canonical_document_id': document_id, 'version_id': version_id,
        'sha256': item['source_sha256'], 'department_key': department,
        'title': '合成流程文件', 'dataset_id': dataset_id,
        'ragflow_document_id': ragflow_document_id, 'status': status,
        'relative_path': item.get('relative_path') or '合成流程文件.md'}]}


def test_preview_is_read_only_and_the_digest_is_stable(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    body = manifest(source, [('合成一.md', ['第一页正文', '第二页正文'], {})])
    registry = uploaded_registry(body['items'][0])
    monkeypatch.setattr(maintenance, '_registry', lambda: registry)
    first = batch.plan_batch(body)
    second = batch.plan_batch(body)
    assert first['readonly'] is True
    assert first['plan_sha256'] == second['plan_sha256']
    assert first['items'][0]['disposition'] == 'NEW'
    assert first['items'][0]['pages'] == 2
    assert first['submittable'] is True
    # No DB write and no batch registration in a preview.
    assert state['writes'] == [] and state['commits'] == [] and calls['register'] == 0
    cached = tmp_path / 'upload' / 'batch' / 'plans' / first['plan_sha256']
    assert (cached / 'plan.json').is_file() and (cached / 'plan-input.json').is_file()
    # Private inputs never reach the browser projection.
    rendered = json.dumps(first, ensure_ascii=False)
    assert str(source) not in rendered and 'a' * 32 not in rendered and 'b' * 32 not in rendered


def test_same_source_processed_version_is_a_duplicate(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    pages = ['第一页正文', '第二页正文']
    body = manifest(source, [('合成重复.md', pages, {})])
    item = body['items'][0]
    text_sha = hashlib.sha256(batch._page_source_text(pages).encode()).hexdigest()
    version = batch._version_identity(item['source_sha256'], text_sha, 'production')
    registry = uploaded_registry(item, version_id=version, status='parsed/indexed')
    state['documents'][registry['documents'][0]['canonical_document_id']] = {
        'current_version': version, 'withdrawn': 0, 'ingestion_status': 'published'}
    monkeypatch.setattr(maintenance, '_registry', lambda: registry)
    plan = batch.plan_batch(body)
    entry = plan['items'][0]
    assert entry['disposition'] == 'DUPLICATE'
    assert entry['submittable'] is True
    assert entry['version_id'] == version
    assert plan['counts']['duplicate'] == 1


def test_business_update_is_classified_but_needs_the_original_parse_flow(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    body = manifest(source, [('合成换版.md', ['新版正文'], {
        'disposition_hint': 'BUSINESS_UPDATE',
        'replace': {'canonical_document_id': 'DOC_' + 'e' * 24,
                    'expected_current_version': 'VER_' + 'f' * 24}})])
    item = body['items'][0]
    document_id = 'DOC_' + 'e' * 24
    state['documents'][document_id] = {'current_version': 'VER_' + 'f' * 24,
                                       'withdrawn': 0, 'ingestion_status': 'published'}
    prior = {'canonical_document_id': document_id, 'version_id': 'VER_' + 'f' * 24,
             'sha256': 'f' * 64, 'department_key': 'production', 'status': 'parsed/indexed',
             'dataset_id': 'a' * 32, 'ragflow_document_id': 'b' * 32, 'title': '合成换版'}
    monkeypatch.setattr(maintenance, '_registry', lambda: {'documents': [prior]})
    plan = batch.plan_batch(body)
    entry = plan['items'][0]
    assert entry['disposition'] == 'BUSINESS_UPDATE'
    assert entry['submittable'] is False
    assert entry['conflict_reason'] == 'NEW_UPLOAD_REQUIRED'
    assert plan['submittable'] is False


def test_technical_repair_is_visible_but_never_enqueued(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    parent_id = 'IMP_' + '1' * 32
    body = manifest(source, [('合成修复.md', ['修复正文'], {
        'disposition_hint': 'TECHNICAL_REPAIR',
        'repair': {'parent_batch_id': parent_id, 'parent_version_id': 'VER_' + '2' * 24,
                   'reason': '解析分隔符保留修复'}})])
    item = body['items'][0]
    parent_state = {'items': [{'sha256': item['source_sha256'],
                               'version_id': 'VER_' + '2' * 24,
                               'disposition': 'NEW'}]}
    state['rows'][parent_id] = {'name': parent_id, 'frozen_json': '{}',
                                'state_json': json.dumps(parent_state), 'job_json': '{}',
                                'quality_json': '{}', 'status': 'Imported',
                                'department_key': 'production', 'label': 'parent'}
    monkeypatch.setattr(maintenance, '_registry', lambda: {'documents': []})
    plan = batch.plan_batch(body)
    entry = plan['items'][0]
    assert entry['disposition'] == 'TECHNICAL_REPAIR'
    assert entry['submittable'] is False
    assert entry['conflict_reason'] == 'REPAIR_USES_EXISTING_NATIVE_PREPARE_FLOW'
    assert plan['next_action'] == 'fix_manifest'


def test_unknown_source_is_honestly_new_upload_required(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    body = manifest(source, [('合成新文件.md', ['正文'], {})])
    monkeypatch.setattr(maintenance, '_registry', lambda: {'documents': []})
    plan = batch.plan_batch(body)
    entry = plan['items'][0]
    assert entry['disposition'] == 'NEW_UPLOAD_REQUIRED'
    assert entry['submittable'] is False
    assert entry['conflict_reason'] == 'SINGLE_FILE_UPLOAD_REQUIRED'
    assert plan['counts']['new_upload_required'] == 1


def test_page_quality_failure_blocks_submission(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    body = manifest(source, [('合成质检.md', ['正文'], {'page_checks': {'quality_pass': False}})])
    monkeypatch.setattr(maintenance, '_registry', lambda: uploaded_registry(body['items'][0]))
    plan = batch.plan_batch(body)
    assert plan['items'][0]['disposition'] == 'ANOMALY'
    assert plan['items'][0]['conflict_reason'] == 'QUALITY_CHECK_FAILED'
    assert plan['submittable'] is False


def test_duplicate_inside_one_manifest_is_an_anomaly(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    body = manifest(source, [('合成甲.md', ['同一正文'], {'file_text': 'same bytes'}),
                             ('合成乙.md', ['同一正文'], {'file_text': 'same bytes'})])
    monkeypatch.setattr(maintenance, '_registry', lambda: {
        'documents': [uploaded_registry(body['items'][0])['documents'][0]]})
    plan = batch.plan_batch(body)
    assert plan['items'][1]['disposition'] == 'ANOMALY'
    assert plan['items'][1]['conflict_reason'] == 'DUPLICATE_IN_MANIFEST'
    assert plan['submittable'] is False


@pytest.mark.parametrize('registry_status,published', [
    ('quarantined', None),
    ('parse_failed', None),
    ('parsed/indexed', None),
    ('parsed/indexed', {'current_version': 'VER_' + 'd' * 24, 'withdrawn': 1,
                        'ingestion_status': 'retired'}),
])
def test_unpublished_or_failed_version_is_reprocessed_not_duplicated(monkeypatch, tmp_path,
                                                                     registry_status, published):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    pages = ['第一页正文', '第二页正文']
    body = manifest(source, [('合成重处理.md', pages, {})])
    item = body['items'][0]
    text_sha = hashlib.sha256(batch._page_source_text(pages).encode()).hexdigest()
    version = batch._version_identity(item['source_sha256'], text_sha, 'production')
    registry = uploaded_registry(item, version_id=version, status=registry_status)
    document_id = registry['documents'][0]['canonical_document_id']
    if published:
        state['documents'][document_id] = published
    monkeypatch.setattr(maintenance, '_registry', lambda: registry)
    plan = batch.plan_batch(body)
    entry = plan['items'][0]
    assert entry['disposition'] == 'NEW'
    assert entry['submittable'] is True
    assert entry['reprocess'] is True
    assert entry['document_id'] == document_id
    assert entry['version_id'] == version
    assert plan['submittable'] is True
    # The preview never fakes an approval on a reprocess item.
    assert entry['conflict_reason'] is None


def test_quarantined_reprocess_reuses_the_same_identity_and_version(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    pages = ['失败批次正文']
    body = manifest(source, [('合成隔离重处理.md', pages, {})])
    item = body['items'][0]
    text_sha = hashlib.sha256(batch._page_source_text(pages).encode()).hexdigest()
    version = batch._version_identity(item['source_sha256'], text_sha, 'production')
    registry = uploaded_registry(item, version_id=version, status='quarantined')
    registry['documents'][0]['attempt_error'] = 'UNKNOWN_ENQUEUE_OUTCOME_REQUIRES_TASK_RECONCILIATION'
    monkeypatch.setattr(maintenance, '_registry', lambda: registry)
    plan = batch.plan_batch(body)
    entry = plan['items'][0]
    assert (entry['disposition'], entry['submittable'], entry['reprocess']) == ('NEW', True, True)
    assert entry['document_id'] == registry['documents'][0]['canonical_document_id']
    assert entry['version_id'] == version


@pytest.mark.parametrize('mutate', [
    lambda body: body.pop('sharing_confirmed'),
    lambda body: body['items'].__setitem__(0, {**body['items'][0], 'source_sha256': 'z' * 64}),
    lambda body: body['items'].__setitem__(0, {**body['items'][0], 'pages': ['正文'],
                                             'page_methods': ['native', 'native']}),
    lambda body: body['items'].__setitem__(0, {**body['items'][0], 'department': 'unknown'}),
    lambda body: body.__setitem__('schema_version', 99),
    lambda body: body['items'].__setitem__(0, {**body['items'][0],
                                             'page_checks': {'quality_pass': 'yes'}}),
    lambda body: body['items'].__setitem__(0, {**body['items'][0], 'canonical_source_path': '../escape.md'}),
])
def test_invalid_manifest_is_rejected_before_any_write(monkeypatch, tmp_path, mutate):
    source, cfg = workspace(tmp_path)
    batch, maintenance, frappe, state, calls = load_modules(monkeypatch, cfg)
    body = manifest(source, [('合成非法.md', ['正文'], {})])
    mutate(body)
    monkeypatch.setattr(maintenance, '_registry', lambda: {'documents': []})
    with pytest.raises(KnowledgeError) as error:
        batch.plan_batch(body)
    assert error.value.code == 'INVALID_REQUEST'
    assert state['writes'] == [] and state['commits'] == [] and calls['register'] == 0
