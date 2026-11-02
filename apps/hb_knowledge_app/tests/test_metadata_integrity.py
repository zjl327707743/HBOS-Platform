"""Row-input regression for R-META-01; real database tests run separately."""
from dataclasses import asdict
import json

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.execution_plan import Binding
from hb_knowledge_app.hb_knowledge.metadata_integrity import binding_from_row, physical_pair_key


def consistent_row():
    binding = Binding('SPACE_TEST', 'DOC_TEST', 'VERSION_TEST', None,
                      'DATASET_TEST', 'PHYSICAL_DOC_TEST', 'DATASET_ALIAS_TEST',
                      'BINDING_TEST', 'revision-fixed', 'SYNTHETIC_TEST',
                      'SYNTHETIC_ONLY', '2026-01-01T00:00:00Z')
    row = asdict(binding)
    row.update(name=binding.binding_ref, binding_json=json.dumps(asdict(binding)),
               pair_key=physical_pair_key(binding.backend, binding.dataset_id, binding.document_id),
               enabled=1, space_record_id=binding.space_id, space_enabled=1,
               version_record_id=binding.version_id, version_record_identity=binding.version_id,
               version_document_id=binding.canonical_document_id,
               document_record_id=binding.canonical_document_id,
               document_record_identity=binding.canonical_document_id,
               current_version=binding.version_id, withdrawn=0, ingestion_status='published')
    return row, binding


def test_consistent_control_returns_exact_binding():
    row, binding = consistent_row()
    assert binding_from_row(row) == binding


@pytest.mark.parametrize('field,value', [
    ('dataset_id', 'OTHER_DATASET'), ('version_id', 'OTHER_VERSION'),
    ('name', 'OTHER_BINDING'), ('binding_ref', 'OTHER_BINDING'),
    ('space_id', 'OTHER_SPACE'), ('canonical_document_id', 'OTHER_DOCUMENT'),
    ('backend', 'OTHER_BACKEND'), ('document_id', 'OTHER_PHYSICAL_DOCUMENT'),
    ('dataset_alias', 'OTHER_ALIAS'), ('binding_revision', 'OTHER_REVISION'),
    ('pair_key', 'wrong-pair'), ('space_record_id', None), ('space_enabled', 0),
    ('version_record_id', None), ('version_record_identity', 'OTHER_VERSION'),
    ('version_document_id', 'OTHER_DOCUMENT'), ('document_record_id', None),
    ('document_record_identity', 'OTHER_DOCUMENT'), ('current_version', 'NEW_VERSION'),
    ('withdrawn', 1), ('ingestion_status', 'pending'),
])
def test_identity_projection_or_join_drift_rejected_without_repair(field, value):
    row, _ = consistent_row()
    row[field] = value
    before = dict(row)
    with pytest.raises(KnowledgeError) as rejected:
        binding_from_row(row)
    assert rejected.value.code == 'POLICY_UNAVAILABLE'
    assert row == before


@pytest.mark.parametrize('raw', ['{}', '[]', 'null', '{', '{"dataset_id":"one","dataset_id":"two"}'])
def test_malformed_or_ambiguous_projection_rejected(raw):
    row, _ = consistent_row()
    row['binding_json'] = raw
    with pytest.raises(KnowledgeError):
        binding_from_row(row)


def test_physical_pair_is_bound_to_backend_and_both_physical_ids():
    assert len({physical_pair_key(*pair) for pair in [
        ('ragflow', 'A', 'doc'), ('other', 'A', 'doc'),
        ('ragflow', 'B', 'doc'), ('ragflow', 'A', 'other'),
    ]}) == 4
