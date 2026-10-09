import sys
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import activity
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


class Conflict(Exception):pass


def setup(monkeypatch,*,staged=False):
    rolled=[]
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(QueryDeadlockError=Conflict,db=SimpleNamespace(rollback=lambda:rolled.append(True))))
    runtime=SimpleNamespace(publication=SimpleNamespace(references=['prepared'] if staged else [],audits=[],handles=[]))
    return runtime,rolled


def test_snapshot_conflict_restarts_only_once_and_reauthorizes_source(monkeypatch):
    runtime,rolled=setup(monkeypatch);resolved=[];writes=[]
    def resolve():resolved.append(True);return SimpleNamespace(space_id='synthetic-space')
    def write(*args):
        writes.append(args)
        if len(writes)==1:raise Conflict()
        return 'same-native-bookmark'
    monkeypatch.setattr(activity,'write',write)
    assert activity.save_bookmark(runtime,'synthetic query',resolve)=='same-native-bookmark'
    assert len(resolved)==len(writes)==2 and rolled==[True]


def test_second_conflict_does_not_retry_forever(monkeypatch):
    runtime,rolled=setup(monkeypatch);calls=[]
    def write(*args):calls.append(True);raise Conflict()
    monkeypatch.setattr(activity,'write',write)
    with pytest.raises(KnowledgeError) as failure:activity.save_bookmark(runtime,'synthetic query',lambda:SimpleNamespace(space_id='synthetic-space'))
    assert failure.value.code=='SERVICE_ERROR' and len(calls)==2 and rolled==[True]


def test_staged_publication_must_not_be_rolled_back_by_bookmark_retry(monkeypatch):
    runtime,rolled=setup(monkeypatch,staged=True)
    monkeypatch.setattr(activity,'write',lambda *args:(_ for _ in ()).throw(Conflict()))
    with pytest.raises(KnowledgeError):activity.save_bookmark(runtime,'synthetic query',lambda:SimpleNamespace(space_id='synthetic-space'))
    assert rolled==[]


def test_lost_source_after_retry_cannot_persist_old_reference(monkeypatch):
    runtime,rolled=setup(monkeypatch);resolved=[];writes=[]
    def resolve():
        resolved.append(True)
        if len(resolved)==2:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
        return SimpleNamespace(space_id='synthetic-space')
    def write(*args):writes.append(True);raise Conflict()
    monkeypatch.setattr(activity,'write',write)
    with pytest.raises(KnowledgeError) as failure:activity.save_bookmark(runtime,'synthetic query',resolve)
    assert failure.value.code=='EVIDENCE_UNAVAILABLE' and len(writes)==1 and rolled==[True]
