"""Gate A: policy configuration must fail with a controlled error, not a KeyError.

The reference profile is loaded from a JSON file written by the operator. Only
some keys are validated by ``shared_reference.configuration()``; the two the
subject policy reads (``dataset_aliases``, ``approved_document_ids``) were not,
so a profile missing either raised a bare ``KeyError`` inside the Portal access
context and surfaced as a 500 instead of a policy error.
"""
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.policy import load_current_policy

REMOVE = object()


def _reference(tmp_path, monkeypatch, **overrides):
    config = {
        'profile': 'INTERNAL_SHARED_REFERENCE',
        'environment': 'production',
        'site': 'knowledge.test',
        'run_id': 'RUN_1',
        'internal_sharing_approved': True,
        'approved_space_ids': ['SPACE_A'],
        'approved_dataset_ids': ['DATASET_A'],
        'approved_document_ids': ['DOC_A'],
        'dataset_aliases': ['ALIAS_A'],
        'reader_role': 'HBOS Knowledge Reader',
        'model_policy_ref': 'MODEL_1',
        'policy_revision': 'REV_1',
        'enable_synthetic_faults': False,
    }
    for key, value in overrides.items():
        if value is REMOVE:
            config.pop(key, None)
        else:
            config[key] = value
    path = tmp_path / 'hbos-reference.json'
    path.write_text(json.dumps(config))
    monkeypatch.setenv('HBOS_KNOWLEDGE_REFERENCE_CONFIG', str(path))

    # Same dependency stubs the authority tests use: only the import surface is
    # replaced, no database or cipher behaviour is exercised here.
    monkeypatch.setitem(sys.modules, 'pymysql', ModuleType('pymysql'))
    cipher = ModuleType('cryptography.fernet')
    cipher.Fernet = lambda *args: SimpleNamespace()
    monkeypatch.setitem(sys.modules, 'cryptography', ModuleType('cryptography'))
    monkeypatch.setitem(sys.modules, 'cryptography.fernet', cipher)

    frappe = ModuleType('frappe')
    frappe.session = SimpleNamespace(user='reader@example.test')
    frappe.local = SimpleNamespace(site='knowledge.test')
    frappe.conf = {'hbos_knowledge_reference_run': 'RUN_1'}
    frappe.get_roles = lambda user: ['HBOS Knowledge Reader']
    monkeypatch.setitem(sys.modules, 'frappe', frappe)

    internal = ModuleType('hbos_portal.services.internal_users')
    internal.load_internal_user_decision = lambda user: SimpleNamespace(allowed=True)
    monkeypatch.setitem(sys.modules, 'hbos_portal', ModuleType('hbos_portal'))
    monkeypatch.setitem(sys.modules, 'hbos_portal.services', ModuleType('hbos_portal.services'))
    monkeypatch.setitem(sys.modules, 'hbos_portal.services.internal_users', internal)
    return config


def test_missing_dataset_aliases_is_a_controlled_error(tmp_path, monkeypatch):
    _reference(tmp_path, monkeypatch, dataset_aliases=REMOVE)
    with pytest.raises(KnowledgeError) as caught:
        load_current_policy()
    assert caught.value.code == 'POLICY_UNAVAILABLE'


def test_missing_approved_document_ids_is_a_controlled_error(tmp_path, monkeypatch):
    _reference(tmp_path, monkeypatch, approved_document_ids=REMOVE)
    with pytest.raises(KnowledgeError) as caught:
        load_current_policy()
    assert caught.value.code == 'POLICY_UNAVAILABLE'


def test_alias_list_is_required_not_defaulted_to_the_physical_ids(tmp_path, monkeypatch):
    _reference(tmp_path, monkeypatch, dataset_aliases=[])
    with pytest.raises(KnowledgeError) as caught:
        load_current_policy()
    assert caught.value.code == 'POLICY_UNAVAILABLE'


def test_valid_profile_keeps_the_approved_scope_verbatim(tmp_path, monkeypatch):
    _reference(tmp_path, monkeypatch)
    policy = load_current_policy()
    assert policy.dataset_ids == ('ALIAS_A',)
    assert policy.document_ids == ('DOC_A',)
    assert policy.subject == 'reader@example.test'
    assert policy.can_enter
