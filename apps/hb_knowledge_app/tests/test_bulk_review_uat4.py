"""A failed or unshared batch selection must never partially acquire approval."""
import importlib,sys
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def setup(monkeypatch):
    writes=[];commits=[]
    fake=SimpleNamespace(session=SimpleNamespace(user='SYNTHETIC_MAINTAINER'),db=SimpleNamespace(set_value=lambda *a:writes.append(a),commit=lambda:commits.append(True)))
    monkeypatch.setitem(sys.modules,'frappe',fake)
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.shared_reference',SimpleNamespace(configuration=lambda:{}))
    module=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    monkeypatch.setattr(module,'frappe',fake);monkeypatch.setattr(module,'configuration',lambda:{})
    monkeypatch.setattr(module,'require',lambda:None)
    items=[{'canonical_document_id':doc,'version_id':'VER_'+doc,'status':'parsed/indexed','sha256':'a'*64,'upload_sha256':'b'*64,'internal_sharing_confirmed':True,'owner_inclusion_confirmed':True,'disposition':'NEW','approval_ref':'OWNER_SYNTHETIC'} for doc in ('ONE','TWO')]
    monkeypatch.setattr(module,'_row',lambda *a:({'quality_json':'{}'},{},{'items':items}))
    admin=importlib.import_module('hb_knowledge_app.hb_knowledge.reference_admin')
    monkeypatch.setattr(admin,'_verify_backend',lambda *a:None)
    return module,admin,items,writes,commits


def test_bulk_review_verifies_all_items_before_writing(monkeypatch):
    module,admin,items,writes,commits=setup(monkeypatch)
    def verify(cfg,item):
        if item['canonical_document_id']=='TWO':raise RuntimeError('physical source changed')
    monkeypatch.setattr(admin,'_verify_backend',verify)
    with pytest.raises(RuntimeError):module.review_batch('BATCH',['ONE','TWO'],['text','numbers','tables','identity'],'已对照原文')
    assert not writes and not commits

@pytest.mark.parametrize('invalid',['unshared','failed','duplicate','missing'])
def test_invalid_selection_cannot_acquire_approval(monkeypatch,invalid):
    module,admin,items,writes,commits=setup(monkeypatch);ids=['ONE','TWO']
    if invalid=='unshared':items[1]['internal_sharing_confirmed']=False
    if invalid=='failed':items[1]['status']='parse_failed'
    if invalid=='duplicate':ids=['ONE','ONE']
    if invalid=='missing':ids=['ONE','ABSENT']
    with pytest.raises(KnowledgeError):module.review_batch('BATCH',ids,['text','numbers','tables','identity'],'已对照原文')
    assert not writes and not commits


def test_explicit_subset_review_preserves_unselected_exception(monkeypatch):
    module,admin,items,writes,commits=setup(monkeypatch);items[1]['status']='parse_failed'
    result=module.review_batch('BATCH',['ONE'],['text','numbers','tables','identity'],'已对照原文，第二项失败排除')
    assert result['reviewed_documents']==1 and result['status']=='Passed'
    assert len(writes)==1 and commits==[True]
    assert 'VER_TWO' not in writes[0][-1]
