"""UAT5 failure contracts: synthetic service responses, no provider calls."""
import json

import pytest

from hb_knowledge_app.hb_knowledge.errors import ERRORS, KnowledgeError, error_payload
from hb_knowledge_app.hb_knowledge.service_http import SignedHttp


@pytest.mark.parametrize('code,status', [
    ('MODEL_TRANSPORT_FAILURE', 503), ('MODEL_REQUEST_FORMAT', 502),
    ('MODEL_REQUEST_INVALID', 502), ('MODEL_AUTH_FAILED', 502),
    ('MODEL_RATE_LIMITED', 429), ('MODEL_SERVICE_FAILED', 503),
    ('ANSWER_SCHEMA_INVALID', 502), ('CITATION_SUPPORT_FAILED', 422),
    ('RETRIEVAL_EMPTY', 404), ('RETRIEVAL_UPSTREAM_FAILED', 503),
    ('SOURCE_VERSION_STALE', 409),
])
def test_failure_keeps_stage_without_exposing_service_details(monkeypatch, code, status):
    class Response:
        status_code = status

        def __enter__(self): return self
        def __exit__(self, *args): return False
        def iter_content(self, size):
            yield json.dumps({'error': {'code': code, 'message': '/PRIVATE/provider/key'}}).encode()

    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, *args, **kwargs): return Response()

    monkeypatch.setattr('hb_knowledge_app.hb_knowledge.service_http.requests.Session', Session)
    with pytest.raises(KnowledgeError) as caught:
        SignedHttp('http://synthetic.invalid', 'synthetic-only-key', 'PORTAL').post('/ask', {}, 'PORTAL')
    error = caught.value
    assert error.code == code and error.status == status
    payload = error_payload(error, 'REQ_UAT5_SYNTHETIC')
    assert payload['error']['request_id'] == 'REQ_UAT5_SYNTHETIC'
    assert payload['error']['message'] == ERRORS[code][1]
    assert 'PRIVATE' not in json.dumps(payload)


def test_legacy_model_failure_does_not_claim_citation_validation_failed():
    assert '依据校验' not in KnowledgeError('ANSWER_MODEL_UNAVAILABLE').public_message
    assert KnowledgeError('CITATION_SUPPORT_FAILED').public_message != KnowledgeError('MODEL_TRANSPORT_FAILURE').public_message


def test_unknown_upstream_classification_fails_closed():
    assert KnowledgeError('/PRIVATE/provider/key').code == 'SERVICE_ERROR'
