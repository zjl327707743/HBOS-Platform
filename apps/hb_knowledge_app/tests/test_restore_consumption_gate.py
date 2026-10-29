from types import SimpleNamespace
import sys
import pytest
from hb_knowledge_app.hb_knowledge import activity, evidence
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.execution_plan import Binding


def fixture(monkeypatch, *, revoked=False):
    b=Binding('SPACE','DOC','VERSION',None,'dataset','physical-doc','alias','binding','revision',
              'COMPANY_CONTROLLED','CONTROLLED_REFERENCE_REVIEWED','2026-01-01T00:00:00Z',title='资料')
    actor=SimpleNamespace(user_ref='synthetic-owner');mapping={('DOC','VERSION'):b}
    data={'query':'已存问题','space_ids':['SPACE'],'references':[['DOC','VERSION','binding','chunk']],
          'previews':[{'reference':['DOC','VERSION','binding','chunk'],'page_number':None,'excerpt':'有限依据'}],
          'answer':'已存答案[C1]','labels':['C1']}
    # The domain unit tests exercise publication, not the separately shipped
    # service projector. Its real implementation is covered by service and HTTP tests.
    monkeypatch.setitem(sys.modules,'knowledge_service.hbos_gateway.response_projection',
        SimpleNamespace(public_evidence=lambda record,handle,**kwargs:{'evidence_id':handle,'document_id':record.document_id,'excerpt':record.excerpt}))
    audits=[];ticket=SimpleNamespace(plan=object(),call=lambda *args:object())
    runtime=SimpleNamespace(client=object(),profile='production',cache=object(),publication=SimpleNamespace(plan=None),
        decisions=SimpleNamespace(issue=lambda *args:ticket,online=lambda *args:None),
        provider=SimpleNamespace(revalidate=lambda *args:None),gateway=SimpleNamespace(authorize_evidence=lambda *args,**kwargs:None),
        quota=SimpleNamespace(reserve_output=lambda *args:None),audit=SimpleNamespace(record=lambda *args:audits.append(args)))
    monkeypatch.setattr(evidence,'issue_evidence',lambda *args,**kwargs:'fresh-handle')
    monkeypatch.setattr(activity,'current',lambda runtime:(actor,{} if revoked else mapping))
    return runtime,SimpleNamespace(name='saved'),data,actor,mapping,audits


def test_saved_answer_publishes_a_consumption_audit_after_source_revalidation(monkeypatch):
    runtime,row,data,actor,mapping,audits=fixture(monkeypatch)
    result=activity.restore(runtime,row,data,actor,mapping,'restore-request')
    assert result['restored']['turns'][0]['citations'][0]['evidence_id']=='fresh-handle'
    assert audits==[('synthetic-owner','restore','SUCCESS',1)]


def test_revoked_source_cannot_publish_restored_handles_or_success_audit(monkeypatch):
    runtime,row,data,actor,mapping,audits=fixture(monkeypatch,revoked=True)
    with pytest.raises(KnowledgeError):activity.restore(runtime,row,data,actor,mapping,'restore-request')
    assert audits==[]

def test_insufficient_evidence_turn_still_completes_the_authorization_phase_chain(monkeypatch):
    runtime,row,data,actor,mapping,audits=fixture(monkeypatch)
    data.update(references=[],previews=[],answer='资料不足',labels=[])
    phases=[];ticket=SimpleNamespace(plan=object(),call=lambda operation,phase:phase)
    runtime.decisions.issue=lambda *args:ticket
    runtime.decisions.online=lambda principal,phase:phases.append(phase)
    result=activity.restore(runtime,row,data,actor,mapping,'restore-request')
    assert result['restored']['turns'][0]['citations']==[]
    assert phases==['introspect','cache_read','pre_projection','final_publish']
