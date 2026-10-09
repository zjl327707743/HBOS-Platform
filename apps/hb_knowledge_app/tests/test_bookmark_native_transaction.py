import sys
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import activity
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def run(monkeypatch,rows,*,user='synthetic-owner'):
    calls=[]
    def sql(query,args,as_dict):
        calls.append((query,args))
        return rows.pop(0)
    def unexpected_insert(*args,**kwargs):
        raise AssertionError('A saved bookmark must not be inserted again')
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(db=SimpleNamespace(sql=sql),get_doc=unexpected_insert))
    monkeypatch.setattr(activity,'current',lambda runtime:(SimpleNamespace(user_ref=user),{}))
    return calls,lambda:activity.write('Bookmark','synthetic query',[],[],object())


def test_current_locked_bookmark_survives_earlier_request_snapshot(monkeypatch):
    payload=activity.canonical({'query':'synthetic query','space_ids':[],'references':[]})
    calls,save=run(monkeypatch,[[{'name':'synthetic-owner','enabled':1}],[{'name':'deterministic-existing','payload_json':payload}]])
    assert save()=='deterministic-existing'
    assert all('FOR UPDATE' in query for query,_ in calls)
    assert '`tabUser`' in calls[0][0] and calls[0][1]==('synthetic-owner',)
    assert calls[1][1][1:]==('synthetic-owner','Bookmark')


def test_original_random_bookmark_id_is_preserved(monkeypatch):
    calls,save=run(monkeypatch,[[{'name':'synthetic-owner','enabled':1}],[],[{'name':'legacy-random-id'}]])
    assert save()=='legacy-random-id'
    assert len(calls)==3 and 'payload_json=%s' in calls[-1][0]


def test_disabled_native_user_cannot_save_with_an_earlier_actor(monkeypatch):
    calls,save=run(monkeypatch,[[{'name':'synthetic-owner','enabled':0}]])
    with pytest.raises(KnowledgeError) as failure:save()
    assert failure.value.code=='AUTHENTICATION_REQUIRED'
    assert len(calls)==1


def test_existing_identifier_with_different_payload_fails_closed(monkeypatch):
    _,save=run(monkeypatch,[[{'name':'synthetic-owner','enabled':1}],[{'name':'deterministic-existing','payload_json':'different'}]])
    with pytest.raises(KnowledgeError) as failure:save()
    assert failure.value.code=='SERVICE_ERROR'
