"""RC13 A-class size limits: configurable 64MiB normal path, explicit codes.

The normal maintenance import limit is a private configuration value, not a
reverse-proxy or API-body limit: ``maintenance_max_source_bytes`` defaults to
64 MiB and may be lowered (within the 20..64 MiB normal range) per deployment.
Manifest body size and per-item source size stay separate decisions with
separate error codes.
"""
import importlib
import io
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.maintenance_contract import (
    DEFAULT_MAX_SOURCE_BYTES,
    MAX_FILE,
    admit_file,
    configured_max_source_bytes,
    require_source_size,
    source_size_budget,
)

MIB = 1024 * 1024


def test_normal_limit_defaults_to_64_mib_and_is_configurable_down_to_20_mib():
    assert DEFAULT_MAX_SOURCE_BYTES == 64 * MIB
    assert configured_max_source_bytes({}) == 64 * MIB
    assert configured_max_source_bytes({'maintenance_max_source_bytes': 20 * MIB}) == 20 * MIB
    assert configured_max_source_bytes({'maintenance_max_source_bytes': 64 * MIB}) == 64 * MIB


@pytest.mark.parametrize('value', [19 * MIB, 64 * MIB + 1, True, False, 0, -1,
                                   20 * MIB + 0.5, '20MiB', [20 * MIB]])
def test_configured_limit_outside_the_normal_range_fails_closed(value):
    with pytest.raises(KnowledgeError) as error:
        configured_max_source_bytes({'maintenance_max_source_bytes': value})
    assert error.value.code == 'POLICY_UNAVAILABLE'


def test_legacy_constant_stays_a_legacy_alias_not_the_new_default():
    # Existing importers/tests that only know the old 20MiB constant keep the
    # old admission semantics; production callers pass the configured limit.
    assert MAX_FILE == 20 * MIB


@pytest.mark.parametrize('size,accepted', [(64 * MIB - 1, True), (64 * MIB, True),
                                           (64 * MIB + 1, False)])
def test_per_item_boundary_is_inclusive_at_the_configured_limit(size, accepted):
    if accepted:
        assert require_source_size(size, 64 * MIB) == size
    else:
        with pytest.raises(KnowledgeError) as error:
            require_source_size(size, 64 * MIB)
        assert error.value.code == 'SOURCE_SIZE_LIMIT_EXCEEDED'


def test_batch_and_manifest_budgets_are_separate_derived_bounds():
    budget = source_size_budget({})
    assert budget == {'per_file': 64 * MIB, 'per_batch': 256 * MIB,
                      'per_manifest': 1024 * MIB}
    configured = source_size_budget({'maintenance_max_source_bytes': 20 * MIB})
    assert configured == {'per_file': 20 * MIB, 'per_batch': 80 * MIB,
                          'per_manifest': 320 * MIB}


def test_admit_file_enforces_the_explicit_limit_with_a_size_specific_code():
    data = b'a' * (20 * MIB)
    assert admit_file('synthetic.txt', data, max_bytes=20 * MIB)[0] == '.txt'
    with pytest.raises(KnowledgeError) as error:
        admit_file('synthetic.txt', data + b'a', max_bytes=20 * MIB)
    assert error.value.code == 'SOURCE_SIZE_LIMIT_EXCEEDED'
    # Legacy default admission still rejects the old 20MiB boundary.
    with pytest.raises(KnowledgeError) as legacy:
        admit_file('synthetic.txt', b'a' * (MAX_FILE + 1))
    assert legacy.value.code == 'SOURCE_SIZE_LIMIT_EXCEEDED'


def test_file_type_failures_are_still_invalid_request_not_size_codes():
    with pytest.raises(KnowledgeError) as error:
        admit_file('synthetic.exe', b'MZ' + b'x' * 64)
    assert error.value.code == 'INVALID_REQUEST'
    with pytest.raises(KnowledgeError) as error:
        admit_file('synthetic.pdf', b'not a pdf')
    assert error.value.code == 'INVALID_REQUEST'
    with pytest.raises(KnowledgeError) as error:
        admit_file('synthetic.txt', b'', max_bytes=20 * MIB)
    assert error.value.code == 'INVALID_REQUEST'


def install_framework(monkeypatch):
    monkeypatch.setitem(sys.modules, 'pymysql', ModuleType('pymysql'))
    cipher = ModuleType('cryptography.fernet')
    cipher.Fernet = lambda *args: SimpleNamespace()
    crypto = ModuleType('cryptography')
    crypto.fernet = cipher
    monkeypatch.setitem(sys.modules, 'cryptography', crypto)
    monkeypatch.setitem(sys.modules, 'cryptography.fernet', cipher)
    state = {'writes': [], 'commits': []}
    frappe = SimpleNamespace(session=SimpleNamespace(user='maintainer@example.test'),
                             whitelist=lambda **kwargs: (lambda fn: fn),
                             db=SimpleNamespace(commit=lambda: state['commits'].append(True),
                                                rollback=lambda: None, set_value=lambda *a: None),
                             get_all=lambda *a, **k: [], get_doc=lambda *a, **k: None)
    monkeypatch.setitem(sys.modules, 'frappe', frappe)
    return frappe, state


def load_batch(monkeypatch, cfg):
    frappe, state = install_framework(monkeypatch)
    batch = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_batch')
    maintenance = importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    monkeypatch.setattr(batch, 'frappe', frappe, raising=False)
    monkeypatch.setattr(maintenance, 'frappe', frappe, raising=False)
    monkeypatch.setattr(batch, '_config', lambda: cfg)
    monkeypatch.setattr(maintenance, '_registry', lambda: {'documents': []})
    return batch, maintenance, state


def workspace(tmp_path, limit=None):
    source = tmp_path / 'sources'
    source.mkdir()
    upload = tmp_path / 'upload'
    upload.mkdir()
    derivative = tmp_path / 'derivative'
    derivative.mkdir()
    cfg = {'maintenance_upload_root': str(upload),
           'maintenance_batch_source_roots': [str(source)],
           'maintenance_derivative_root': str(derivative),
           'maintenance_embedding_model': 'approved-embedding',
           'department_space_map': {}}
    if limit is not None:
        cfg['maintenance_max_source_bytes'] = limit
    return source, cfg


def sparse_source(source, name, size):
    path = source / name
    with path.open('wb') as handle:
        handle.truncate(size)
    import hashlib
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_for(path, sha, pages=('正文',), **extra):
    item = {'source_sha256': sha, 'canonical_source_path': path.name,
            'pages': list(pages), 'page_methods': ['native'] * len(pages),
            'page_checks': {'quality_pass': True}}
    item.update(extra)
    return {'schema_version': 2, 'department': 'production',
            'sharing_confirmed': True, 'items': [item]}


@pytest.mark.parametrize('offset,accepted', [(-1, True), (0, True), (1, False)])
def test_batch_manifest_per_item_source_boundary(monkeypatch, tmp_path, offset, accepted):
    limit = 20 * MIB
    source, cfg = workspace(tmp_path, limit)
    batch, maintenance, state = load_batch(monkeypatch, cfg)
    path, sha = sparse_source(source, '大文件.md', limit + offset)
    body = manifest_for(path, sha)
    if accepted:
        plan = batch.plan_batch(body)
        assert plan['items'][0]['submittable'] is False  # no registry candidate yet
    else:
        with pytest.raises(KnowledgeError) as error:
            batch.plan_batch(body)
        assert error.value.code == 'SOURCE_SIZE_LIMIT_EXCEEDED'


def test_manifest_body_limit_is_its_own_code_and_never_a_source_size_code(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path)
    batch, maintenance, state = load_batch(monkeypatch, cfg)
    oversized = ' ' * (batch.MAX_PLAN_MANIFEST_BYTES + 1)
    with pytest.raises(KnowledgeError) as error:
        batch.plan_batch(oversized)
    assert error.value.code == 'MANIFEST_SIZE_LIMIT_EXCEEDED'


def test_plan_source_budget_exceeding_its_own_bound_is_explicit(monkeypatch, tmp_path):
    limit = 20 * MIB
    source, cfg = workspace(tmp_path, limit)
    batch, maintenance, state = load_batch(monkeypatch, cfg)
    assert batch.source_size_budget(cfg)['per_manifest'] == 16 * limit
    with pytest.raises(KnowledgeError) as error:
        batch.require_manifest_source_budget(16 * limit + 1, cfg)
    assert error.value.code == 'BATCH_SOURCE_SIZE_LIMIT_EXCEEDED'
    assert batch.require_manifest_source_budget(16 * limit, cfg) == 16 * limit


def test_upload_reads_configured_limit_and_reports_size_specific_error(monkeypatch, tmp_path):
    source, cfg = workspace(tmp_path, 20 * MIB)
    batch, maintenance, state = load_batch(monkeypatch, cfg)
    payload = b'x' * (20 * MIB + 1)
    request = SimpleNamespace(files={'file': SimpleNamespace(
        filename='synthetic.md', stream=io.BytesIO(payload))})
    frappe = maintenance.frappe
    frappe.local = SimpleNamespace(request=request)
    monkeypatch.setattr(maintenance, 'configuration', lambda: cfg)
    monkeypatch.setattr(maintenance, 'require', lambda: None)
    with pytest.raises(KnowledgeError) as error:
        maintenance.upload('production', 'synthetic', True)
    assert error.value.code == 'SOURCE_SIZE_LIMIT_EXCEEDED'


def test_submission_group_total_bytes_guard_uses_the_batch_budget(monkeypatch, tmp_path):
    """Defence in depth: the group freeze refuses a >4-document or oversized
    group before any staging/registration, with the batch-specific code."""
    limit = 20 * MIB
    source, cfg = workspace(tmp_path, limit)
    batch, maintenance, state = load_batch(monkeypatch, cfg)
    group = {'kind': 'derivative', 'department': 'production', 'dataset_id': 'a' * 32,
             'items': [({'index': index, 'source_sha256': '%064x' % index,
                         'source_size': limit, 'source_path': str(tmp_path / 'absent'),
                         'relative_path': 'p%d.md' % index, 'department': 'production'},
                        {'candidate': {'embedding_model': 'approved-embedding'}})
                       for index in range(5)]}
    context = {'derivative_root': tmp_path / 'derivative', 'registry': {'documents': []},
               'label': 'synthetic', 'cfg': cfg}
    with pytest.raises(KnowledgeError) as error:
        batch._freeze_group(tmp_path / 'plan', 'a' * 64, {}, group, 'OWNER_SYNTHETIC', context)
    assert error.value.code == 'BATCH_SOURCE_SIZE_LIMIT_EXCEEDED'
