from dataclasses import replace
from types import SimpleNamespace
import pytest
from .test_spaces import runtime as fixture
from hb_knowledge_app.hb_knowledge.evidence import resolve_evidence,EVIDENCE_SCHEMA
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def setup():
    app,actor,repo,binding=fixture();client=app.client;phases=[]
    reference=SimpleNamespace(actor=actor,client=client,expires_at=200,issued_at=100,binding=binding,
        policy_revision='P',corpus_revision='CORPUS_OLD',chunk_id='SYN_CHUNK',excerpt='合成可核验来源，不输出诊断正文。',page_number=None)
    ticket=SimpleNamespace(plan=SimpleNamespace(bindings=(binding,),policy_revision='P',corpus_revision='CORPUS_NEW'),
        call=lambda action,phase:SimpleNamespace(action=action,phase=phase))
    app.provider.clock=lambda:101
    app.references=SimpleNamespace(get=lambda ref:reference)
    app.decisions=SimpleNamespace(issue=lambda *a:ticket,online=lambda principal,call:phases.append(call.phase))
    app.gateway=SimpleNamespace(authorize_evidence=lambda *a,**kw:phases.append('backend'))
    cache=SimpleNamespace(get_value=lambda *a,**kw:{'schema':EVIDENCE_SCHEMA,'reference_id':'SYN_REF','expires_at':200})
    return app,actor,client,reference,ticket,cache,phases


def test_unrelated_publication_does_not_invalidate_still_current_exact_source():
    app,actor,client,reference,ticket,cache,phases=setup()
    record,issued=resolve_evidence(cache,actor,client,'SYN_HANDLE',runtime=app,request_id='uat5-source-stable')
    assert record.excerpt==reference.excerpt and issued is ticket
    assert phases==['introspect','backend','final_publish']


@pytest.mark.parametrize('fault',['version','policy','revocation'])
def test_changed_source_or_revoked_permission_stays_closed_with_private_stage(fault,caplog):
    app,actor,client,reference,ticket,cache,phases=setup()
    if fault=='version':ticket.plan.bindings=(replace(reference.binding,version_id='NEW_VERSION'),)
    if fault=='policy':ticket.plan.policy_revision='CHANGED_POLICY'
    if fault=='revocation':
        def denied(*args):raise KnowledgeError('SCOPE_REJECTED')
        app.decisions.issue=denied
    with pytest.raises(KnowledgeError) as error:
        resolve_evidence(cache,actor,client,'SYN_HANDLE',runtime=app,request_id='uat5-source-failure')
    assert error.value.code=='EVIDENCE_UNAVAILABLE' and 'backend' not in phases
    trace='\n'.join(r.message for r in caplog.records)
    assert 'SOURCE_RESOLUTION_FAILED' in trace and 'uat5-source-failure' in trace
    assert reference.excerpt not in trace and reference.binding.canonical_document_id not in trace
