"""Candidate transport cannot accept legacy static policy or HTTP credentials."""
import hashlib
import json
from pathlib import Path
import pytest

from hb_knowledge_app.hb_knowledge.gateway import GatewayClient
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def test_candidate_cannot_be_constructed_with_legacy_transport_credentials():
    with pytest.raises(TypeError):
        GatewayClient(endpoint='http://legacy.invalid', token='test', client_id='test')


def test_candidate_cannot_search_with_caller_supplied_static_policy():
    with pytest.raises(TypeError):
        GatewayClient(None).search(query='question', policy=object(), limit=5, request_id='test')


def test_missing_service_fails_closed_without_network_fallback():
    with pytest.raises(KnowledgeError) as error:
        GatewayClient(None).search(ticket=object())
    assert error.value.code == 'POLICY_UNAVAILABLE'


def test_legacy_transport_copy_matches_fixed_baseline_and_is_not_runtime_dependency():
    directory = Path(__file__).parent / 'legacy_p1'
    provenance = json.loads((directory / 'provenance.json').read_text())
    assert provenance['source_commit'] == '72e5b1728981b7ef102a2c9ee033ce0452c400e7'
    assert hashlib.sha256((directory / 'gateway.py').read_bytes()).hexdigest() == provenance['sha256']
    runtime = Path(__file__).parents[1] / 'hb_knowledge_app'
    for source in runtime.rglob('*.py'):
        assert 'legacy_p1' not in source.read_text()
