"""R2 citation isolation: one unprojectable citation must not fail a REFERENCE_EXCERPTS answer."""
import importlib.util
import sys
from pathlib import Path
import pytest

APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
try:
    _service_projection = importlib.util.find_spec(
        'knowledge_service.hbos_gateway.response_projection')
except (ModuleNotFoundError, ValueError):
    _service_projection = None
if _service_projection is None:
    pytest.skip('requires hbos_knowledge_service; covered by the joint service integration run',
                allow_module_level=True)

from hb_knowledge_app.hb_knowledge.ask_projection import project_ask_results
from hb_knowledge_app.hb_knowledge.execution_plan import Binding


def binding(ref, version='VER_x'):
    return Binding('DEPT_SAFETY', 'DOC_x', version, '1.0', 'ds', 'phys', 'ds_alias', ref, 'BR_x',
                   'ORDINARY_INTERNAL_KNOWLEDGE', 'INTERNAL_REFERENCE_REVIEWED', '2026-01-01T00:00:00Z')


def item(ref, label, excerpt, version='VER_x'):
    return {'binding_ref': ref, 'version_id': version, 'chunk_id': 'chunk-' + label,
            'excerpt': excerpt, 'page_number': 1, 'score': 0.5, 'citation_label': label}


def test_reference_excerpts_isolates_unsafe_citation():
    selected = {'B1': binding('B1'), 'B2': binding('B2')}
    raw = [item('B1', 'C1', '取样管理规程要求操作人员按批准的程序执行。'),
           item('B2', 'C2', 'password: hunter2')]
    records, labels, isolated = project_ask_results(raw, ['C1', 'C2'], selected, answer_status='REFERENCE_EXCERPTS')
    assert labels == ['C1']
    assert len(records) == 1
    assert isolated and isolated[0]['citation_label'] == 'C2'


def test_all_unsafe_reference_excerpts_still_fail():
    selected = {'B2': binding('B2')}
    raw = [item('B2', 'C2', 'password: hunter2')]
    try:
        project_ask_results(raw, ['C2'], selected, answer_status='REFERENCE_EXCERPTS')
    except Exception as error:
        assert getattr(error, 'code', None) == 'UPSTREAM_INVALID_RESULT'
    else:
        raise AssertionError('an answer with no projectable citation must fail')


def test_generated_answer_keeps_strict_failure():
    selected = {'B1': binding('B1')}
    raw = [item('B1', 'C1', 'password: hunter2')]
    try:
        project_ask_results(raw, ['C1'], selected, answer_status='GENERATED_WITH_SOURCES')
    except Exception as error:
        assert getattr(error, 'code', None) == 'UPSTREAM_INVALID_RESULT'
    else:
        raise AssertionError('generated answers must still fail on an unsafe citation')
