"""Smaller transport results retain every current authority and phase check."""
import json
from dataclasses import replace
from types import SimpleNamespace
import pytest
from .test_structure_scope_rc1 import fixture
from hb_knowledge_app.hb_knowledge.decision_store import DecisionStore
from hb_knowledge_app.hb_knowledge.execution_plan import ServicePrincipal
from hb_knowledge_app.hb_knowledge.repositories import ActorState
from hb_knowledge_app.hb_knowledge.r1_contract import normalize_search,validate_structure
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def setup():
    app,actor,repo,binding,_=fixture();clock=[app.provider.clock()]
    store=DecisionStore(app.provider,SimpleNamespace(reserve_request=lambda *a,**k:None),clock=lambda:clock[0])
    ticket=store.issue(actor,app.client,'knowledge.search',normalize_search({'query':'synthetic'}),'SYNTHETIC_ACK')
    principal=ServicePrincipal(app.client,True)
    store.online(principal,ticket.call('introspect','introspect'))
    return app,actor,repo,binding,store,ticket,principal,clock


def receipt(store,ticket,principal,phase='pre_retrieval'):
    call=ticket.call('revalidate',phase)
    out=store.respond(principal,call).to_revalidation_receipt(call,principal)
    validate_structure('InternalRevalidationReceipt',out)
    return out


def test_fresh_ack_does_not_serialize_or_issue_a_plan(monkeypatch):
    _,_,_,_,store,ticket,principal,_=setup()
    call=ticket.call('revalidate','pre_retrieval')
    # Fresh authority validation legitimately inspects the existing plan. Only
    # its transport projection avoids serializing that plan a second time.
    response=store.respond(principal,call)
    monkeypatch.setattr(type(ticket.plan),'to_wire',lambda self:pytest.fail('plan copied'))
    out=response.to_revalidation_receipt(call,principal)
    validate_structure('InternalRevalidationReceipt',out)
    assert out['outcome']=='ALLOWED' and 'plan' not in out
    assert out['decision_ref']==ticket.decision_ref and out['plan_digest']==ticket.plan_digest
    assert len(json.dumps(out))<1024


@pytest.mark.parametrize('transition',['withdraw','version','physical_pair','role','disabled','client','expiry','request_id','digest','out_of_order'])
def test_warm_ack_never_reuses_an_allow_or_skips_phase(transition):
    app,actor,repo,binding,store,ticket,principal,clock=setup()
    assert receipt(store,ticket,principal)['outcome']=='ALLOWED'
    call=ticket.call('revalidate','pre_retrieval')
    if transition=='withdraw':repo.snapshot=replace(repo.snapshot,bindings=(replace(binding,withdrawn=True),))
    elif transition=='version':repo.snapshot=replace(repo.snapshot,bindings=(replace(binding,version_id='CHANGED'),))
    elif transition=='physical_pair':repo.snapshot=replace(repo.snapshot,bindings=(replace(binding,document_id='CHANGED'),))
    elif transition=='role':repo.snapshot=replace(repo.snapshot,actor_state=ActorState(actor,(),True))
    elif transition=='disabled':repo.snapshot=replace(repo.snapshot,actor_state=ActorState(actor,('ROLE_QA',),False))
    elif transition=='client':principal=replace(principal,client=replace(principal.client,client_id='OTHER'))
    elif transition=='expiry':clock[0]+=13
    elif transition=='request_id':call=replace(call,request_id='OTHER')
    elif transition=='digest':call=replace(call,plan_digest='b'*64)
    else:call=ticket.call('revalidate','final_publish')
    out=store.respond(principal,call).to_revalidation_receipt(call,principal)
    validate_structure('InternalRevalidationReceipt',out)
    assert out['outcome']!='ALLOWED' and out['error_code'] and out['plan_digest'] is None


def test_ack_cannot_replace_introspection_or_authorize_evidence():
    _,_,_,_,store,ticket,principal,_=setup()
    call=ticket.call('introspect','introspect')
    with pytest.raises(KnowledgeError):store.respond(principal,call).to_revalidation_receipt(call,principal)
    good=receipt(store,ticket,principal)
    for edited in [dict(good,plan={}),dict(good,phase='document_body_read'),dict(good,operation='authorize-evidence'),dict(good,deadline_at=None)]:
        with pytest.raises(KnowledgeError):validate_structure('InternalRevalidationReceipt',edited)


def test_signed_search_matches_the_business_request_on_the_revalidated_ticket(monkeypatch):
    from hb_knowledge_app.hb_knowledge.shared_state import RedisDecisions

    _,_,_,_,_,ticket,principal,_=setup()
    events=[]
    provider=SimpleNamespace(revalidate=lambda plan:events.append(('revalidate',plan)))
    state=SimpleNamespace(eval=lambda *args:events.append(('phase',args)) or 1)
    decisions=RedisDecisions(provider,None,state,'fixture-key')
    ticket=replace(ticket,request_fingerprint=decisions.fingerprint(ticket.request))
    def read(ref):
        events.append(('read',ref))
        return ticket
    monkeypatch.setattr(decisions,'_read',read)
    call=ticket.call('introspect','introspect')
    with pytest.raises(KnowledgeError) as rejected:
        decisions.online(principal,call,request=normalize_search({'query':'edited request'}))
    assert rejected.value.code=='REPLAY_REJECTED'
    assert events==[('read',ticket.decision_ref)]
    events.clear()
    assert decisions.online(principal,call,request=ticket.request).require_plan()==ticket.plan
    assert [event[0] for event in events]==['read','revalidate','phase']
