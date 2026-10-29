from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import activity
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def reopen(monkeypatch,data):
    requests=[];ticket=SimpleNamespace(plan=object())
    def issue(actor,client,action,request,request_id):requests.append(request);return ticket
    actor=SimpleNamespace(user_ref='synthetic-owner')
    monkeypatch.setattr(activity,'current',lambda runtime:(actor,{}))
    monkeypatch.setattr(activity,'owned',lambda name,actor:(None,data))
    runtime=SimpleNamespace(client=object(),decisions=SimpleNamespace(issue=issue),provider=SimpleNamespace(revalidate=lambda plan:None))
    return activity.reopen(runtime,'synthetic-history','synthetic-request'),requests


def test_saved_context_participates_in_new_authorization_and_replay(monkeypatch):
    context={'equipment_id':'SYNTHETIC-EQUIPMENT','asset_id':'SYNTHETIC-ASSET'}
    result,requests=reopen(monkeypatch,{'query':'synthetic query','space_ids':['SYNTHETIC-SPACE'],'references':[],'context':context})
    assert result['context']==dict(requests[0].context)==context
    assert result['space_ids']==list(requests[0].space_ids)


def test_legacy_saved_record_stays_compatible_without_inventing_context(monkeypatch):
    result,requests=reopen(monkeypatch,{'query':'synthetic query','space_ids':[],'references':[]})
    assert result=={'query':'synthetic query','space_ids':[]} and not requests[0].context


def test_invalid_persisted_context_cannot_be_replayed(monkeypatch):
    with pytest.raises(KnowledgeError):reopen(monkeypatch,{'query':'synthetic query','space_ids':[],'references':[],'context':{'forged_scope':'synthetic'}})
