import json
import sys
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import activity
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def test_personal_feedback_filters_principal_and_drops_internal_references(monkeypatch):
    queries=[];actor=SimpleNamespace(user_ref='SYNTHETIC_OWNER')
    def get_all(doctype,**kwargs):
        queries.append(kwargs)
        return [SimpleNamespace(name='SYNTHETIC_FEEDBACK',status='In Review',creation='2026-10-10',modified='2026-10-11',
            payload_json=json.dumps({'query':'PRIVATE_QUERY','category':'内容疑问','note':'合成员工反馈',
                                     'references':[['PRIVATE_DOCUMENT','PRIVATE_VERSION','PRIVATE_BINDING','PRIVATE_CHUNK']]}))]
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(get_all=get_all))
    calls=[]
    monkeypatch.setattr(activity,'current',lambda runtime:(calls.append(True) or actor,{}))
    output=activity.list_feedback(object())
    assert queries[0]['filters']=={'owner_user':'SYNTHETIC_OWNER','kind':'Feedback'} and len(calls)==2
    assert output['items'][0]['status']=='In Review' and 'PRIVATE_' not in str(output)
    assert set(output['items'][0])=={'id','category','note','status','created_at','updated_at'}


def test_revoked_session_at_final_check_cannot_return_feedback(monkeypatch):
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(get_all=lambda *a,**k:[]))
    count=0
    def current(runtime):
        nonlocal count
        count+=1
        if count==2:raise KnowledgeError('AUTHENTICATION_REQUIRED')
        return SimpleNamespace(user_ref='SYNTHETIC_OWNER'),{}
    monkeypatch.setattr(activity,'current',current)
    with pytest.raises(KnowledgeError):activity.list_feedback(object())
