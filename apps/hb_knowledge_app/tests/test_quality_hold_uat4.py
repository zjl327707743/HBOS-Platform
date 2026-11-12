import importlib,json,sys
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

def setup(monkeypatch,published=False):
    writes=[];commits=[];items=[{'canonical_document_id':d,'version_id':'VER_'+d,'sha256':'a'*64,'upload_sha256':'b'*64} for d in ['ONE','TWO']]
    fake=SimpleNamespace(session=SimpleNamespace(user='SYNTHETIC_MAINTAINER'),
        db=SimpleNamespace(get_value=lambda *a,**kw:({'current_version':'VER_ONE','withdrawn':False,'ingestion_status':'published'} if published else None),
                           set_value=lambda *a:writes.append(a),commit=lambda:commits.append(True)))
    monkeypatch.setitem(sys.modules,'frappe',fake)
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.shared_reference',SimpleNamespace(configuration=lambda:{}))
    m=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance');monkeypatch.setattr(m,'frappe',fake);monkeypatch.setattr(m,'require',lambda:None)
    monkeypatch.setattr(m,'_row',lambda *a:({'quality_json':json.dumps({'VER_ONE':{'status':'Passed'},'VER_TWO':{'status':'Passed'}})},{},{'items':items}))
    return m,writes,commits

def test_exact_hold_clears_only_unpublished_selected_review(monkeypatch):
    m,writes,commits=setup(monkeypatch);r=m.hold_quality('BATCH',['ONE'],'正文覆盖待复核')
    q=json.loads(writes[0][-1]);assert r['held_documents']==1 and q['VER_ONE']['status']=='Pending' and q['VER_TWO']['status']=='Passed'
    assert commits==[True]

def test_published_version_must_be_withdrawn_before_quality_hold(monkeypatch):
    m,writes,commits=setup(monkeypatch,True)
    with pytest.raises(KnowledgeError):m.hold_quality('BATCH',['ONE','TWO'],'正文覆盖待复核')
    assert not writes and not commits

@pytest.mark.parametrize('ids',[['ONE','ONE'],['ONE','MISSING']])
def test_invalid_hold_selection_never_partially_changes_review(monkeypatch,ids):
    m,writes,commits=setup(monkeypatch)
    with pytest.raises(KnowledgeError):m.hold_quality('BATCH',ids,'正文覆盖待复核')
    assert not writes and not commits

def test_duplicate_path_never_blocks_logical_document_hold(monkeypatch):
    m,writes,commits=setup(monkeypatch);row,frozen,state=m._row('BATCH')
    state['items'].append({**state['items'][0],'disposition':'SAME_CONTENT_SKIP'})
    monkeypatch.setattr(m,'_row',lambda *a:(row,frozen,state))
    assert m.hold_quality('BATCH',['ONE'],'原文缺失待修复')['held_documents']==1
    assert len(writes)==1 and commits==[True]

def test_duplicate_path_never_blocks_withdrawal_of_current_version(monkeypatch):
    m,writes,commits=setup(monkeypatch);row,frozen,state=m._row('BATCH');state['batch_sha256']='c'*64
    state['items'].append({**state['items'][0],'disposition':'SAME_CONTENT_SKIP'})
    monkeypatch.setattr(m,'_row',lambda *a:(row,frozen,state))
    monkeypatch.setattr(m.frappe.db,'sql',lambda *a,**k:[{'current_version':'VER_ONE','withdrawn':False,'source_hash':'a'*64}],raising=False)
    monkeypatch.setattr(m.frappe,'get_doc',lambda *a:SimpleNamespace(insert=lambda **k:None),raising=False)
    assert m.withdraw('BATCH','ONE','VER_ONE','原文缺失待修复')['outcome']=='WITHDRAWN'
    assert len(writes)==1 and commits==[True]
