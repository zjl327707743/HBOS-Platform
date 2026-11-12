import copy,json
import pytest
import importlib,sys
from types import SimpleNamespace
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


def fixture(monkeypatch):
    m,admin,items,writes,commits=setup(monkeypatch)
    for item in items:item.update(internal_sharing_confirmed=False,owner_inclusion_confirmed=False,technical_admission='ADMIT_INTERNAL_REFERENCE',ragflow_document_id='b'*32,dataset_id='a'*32)
    f={'approval_status':'OWNER_PROCESSING_ONLY','batch_sha256':'c'*64,'items':copy.deepcopy(items)}
    state={**copy.deepcopy(f),'mode':'apply','dataset_id':'a'*32}
    quality={i['version_id']:{'status':'Passed','source_sha256':i['sha256'],'upload_sha256':i['upload_sha256']} for i in items}
    monkeypatch.setattr(m,'_row',lambda *a:({'quality_json':json.dumps(quality)},f,state))
    monkeypatch.setattr(m.frappe.db,'exists',lambda *a:False,raising=False)
    registrations=[];monkeypatch.setattr(m,'register_batch',lambda *a:registrations.append(a))
    return m,admin,f,state,quality,writes,commits,registrations


def test_explicit_sharing_confirmation_preserves_original_processing_freeze_and_physical_identity(monkeypatch):
    m,admin,f,state,q,writes,commits,registrations=fixture(monkeypatch);before=copy.deepcopy((f,state))
    result=m.approve_sharing('ORIGINAL',['ONE','TWO'],'已获准内部共享，不含私人或保密内容')
    assert (f,state)==before and len(registrations)==1 and result['approved_documents']==2
    new_frozen,new_state,_,_=registrations[0]
    assert new_frozen['parent_processing_batch']=='ORIGINAL' and new_frozen['approval_status']=='OWNER_APPROVED'
    for old,new in zip(state['items'],new_state['items']):
        assert new['internal_sharing_confirmed'] and new['owner_inclusion_confirmed']
        assert (old['canonical_document_id'],old['version_id'],old['ragflow_document_id'])==(new['canonical_document_id'],new['version_id'],new['ragflow_document_id'])


@pytest.mark.parametrize('invalid',['failed','quarantined','missing_quality','wrong_hash','missing_identity'])
def test_sharing_cannot_bypass_quality_or_exact_selection(monkeypatch,invalid):
    m,admin,f,state,q,writes,commits,registrations=fixture(monkeypatch)
    if invalid in ('failed','quarantined'):state['items'][1]['status']='parse_failed' if invalid=='failed' else 'quarantined'
    if invalid=='missing_quality':q.pop('VER_TWO')
    if invalid=='wrong_hash':q['VER_TWO']['upload_sha256']='wrong'
    if invalid in ('missing_quality','wrong_hash'):monkeypatch.setattr(m,'_row',lambda *a:({'quality_json':json.dumps(q)},f,state))
    ids=['ONE','ABSENT'] if invalid=='missing_identity' else ['ONE','TWO']
    with pytest.raises(KnowledgeError):m.approve_sharing('ORIGINAL',ids,'已确认共享')
    assert not writes and not commits and not registrations
