"""Columns own binding identity; JSON is a checked, immutable projection.

Neither reader nor controller repairs disagreement. A corrupt binding is
excluded from authority snapshots, so an unrelated valid binding can survive.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from .errors import KnowledgeError
from .execution_plan import Binding
from .service_http import canonical

IDENTITY_FIELDS = (
    'binding_ref', 'space_id', 'canonical_document_id', 'version_id',
    'backend', 'dataset_id', 'document_id', 'dataset_alias', 'binding_revision',
)


def physical_pair_key(backend: str, dataset: str, document: str) -> str:
    return hashlib.sha256(canonical([backend, dataset, document]).encode()).hexdigest()


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate metadata key')
        value[key] = item
    return value


def binding_from_row(row: Mapping) -> Binding:
    """Validate both representations and joined identities from one snapshot."""
    try:
        raw = json.loads(row['binding_json'], object_pairs_hook=_unique_object)
        binding = Binding(**raw)
        for field in IDENTITY_FIELDS:
            value = row[field]
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError('Invalid metadata identity')
            if value != getattr(binding, field):
                raise ValueError('Metadata projection drift')
        if row['name'] != row['binding_ref']:
            raise ValueError('Binding primary key drift')
        if row['pair_key'] != physical_pair_key(binding.backend, binding.dataset_id, binding.document_id):
            raise ValueError('Physical pair drift')
        if (row['space_record_id'] != binding.space_id
                or row['version_record_id'] != binding.version_id
                or row['version_record_identity'] != binding.version_id
                or row['version_document_id'] != binding.canonical_document_id
                or row['document_record_id'] != binding.canonical_document_id
                or row['document_record_identity'] != binding.canonical_document_id):
            raise ValueError('Joined metadata identity drift')
        if row.get('enabled'):
            if (not row['space_enabled'] or row['current_version'] != binding.version_id
                    or row['withdrawn'] or row['ingestion_status'] != 'published'):
                raise ValueError('Binding is not currently published')
        return binding
    except (TypeError, ValueError, KeyError):
        raise KnowledgeError('POLICY_UNAVAILABLE') from None
