import copy
from dataclasses import asdict, replace
import pytest
from hb_knowledge_app.hb_knowledge.execution_plan import Binding
from hb_knowledge_app.hb_knowledge.parse_revision import replacement,rollback_admission
from hb_knowledge_app.hb_knowledge.publication import PublicationConflict


def case():
    parent=Binding('SPACE','DOC','VER',None,'a'*32,'b'*32,'OLD_ALIAS','BIND_OLD','OLD_REV',
        'ORDINARY_INTERNAL_KNOWLEDGE','INTERNAL_REFERENCE_REVIEWED','2026-01-01T00:00:00Z',title='Source')
    item={'disposition':'TECHNICAL_REINDEX','status':'parsed/indexed','parser_input':'VERIFIED_ORIGINAL_NATIVE',
        'internal_sharing_confirmed':True,'owner_inclusion_confirmed':True,
        'native_source_proof':{'full_source_requested':True},'version_id':'VER','expected_current_version':'VER',
        'sha256':'1'*64,'upload_sha256':'2'*64,'business_version':None,'document_number':None,
        'source_type':parent.source_type,'authority_status':parent.authority_status,
        'canonical_document_id':'DOC','space_id':'SPACE','native_parent_binding':asdict(parent),
        'dataset_id':'c'*32,'ragflow_document_id':'d'*32,'binding_revision':'NEW_REV',
        'native_profile':{'profile_sha256':'3'*64}}
    current={'current_version':'VER','source_hash':'1'*64,'withdrawn':0,'ingestion_status':'published','dataset_id':parent.dataset_id,'parser_revision':'OLD_PARSER','embedding_revision':'ORIGINAL_EMBEDDING'}
    metadata={k:item[k] for k in ('sha256','business_version','document_number','source_type','authority_status')}
    quality={'status':'Passed','source_sha256':'1'*64,'upload_sha256':'2'*64,'evidence_sha256':'4'*64}
    approval={'batch_sha256':'5'*64,'canonical_document_id':'DOC','version_id':'VER','source_sha256':'1'*64,
        'parent_binding_ref':'BIND_OLD','parent_binding_revision':'OLD_REV','target_dataset_id':'c'*32,
        'target_document_id':'d'*32,'target_binding_revision':'NEW_REV','profile_hash':'3'*64,
        'quality_evidence_sha256':'4'*64,'review_receipt_sha256':'6'*64,'approval_ref':'MAIN_REVIEWED','parent_upload_sha256':'7'*64}
    return [item,current,metadata,parent,quality,approval,'5'*64,'2026-11-02T00:00:00Z']


def test_revision_preserves_source_business_identity_permissions_and_old_binding():
    args=case(); before=copy.deepcopy(args)
    new,receipt=replacement(*args)
    assert args==before
    for field in ('version_id','canonical_document_id','business_version','space_id','dataset_alias',
                  'source_type','authority_status','title','document_number','backend'):
        assert getattr(new,field)==getattr(args[3],field)
    assert new.document_id=='d'*32 and new.binding_ref!=args[3].binding_ref
    assert receipt['business_version_changed'] is False and receipt['old_backend_retained'] is True


@pytest.mark.parametrize('group,field,value',[
    (1,'withdrawn',1),(1,'current_version','NEW_BUSINESS_VERSION'),(1,'source_hash','9'*64),
    (1,'ingestion_status','retired'),(0,'space_id','OTHER_SCOPE'),(0,'business_version','NEW'),
    (0,'internal_sharing_confirmed',False),(0,'owner_inclusion_confirmed',False),
    (4,'status','Pending'),(4,'upload_sha256','9'*64),(5,'target_document_id','e'*32),
    (5,'review_receipt_sha256',''),(5,'profile_hash','9'*64)])
def test_no_restore_version_change_scope_change_or_unreviewed_target(group,field,value):
    args=case();args[group][field]=value
    with pytest.raises(PublicationConflict):replacement(*args)


def test_stale_parse_parent_and_bounded_experiment_cannot_be_promoted():
    args=case();args[3]=replace(args[3],binding_revision='LATER_PARSE_REV')
    with pytest.raises(PublicationConflict):replacement(*args)
    args=case();args[0]['native_source_proof']['full_source_requested']=False
    with pytest.raises(PublicationConflict):replacement(*args)

def rollback_case():
    args=case();new,evidence=replacement(*args);current={**args[1],'dataset_id':new.dataset_id}
    approval={'canonical_document_id':'DOC','version_id':'VER','source_sha256':'1'*64,
        'current_binding_ref':new.binding_ref,'return_binding_ref':args[3].binding_ref,
        'parent_upload_sha256':'7'*64,'approval_ref':'MAIN_ROLLBACK_REVIEW','review_receipt_sha256':'8'*64}
    return [evidence,current,args[2],new,args[3],approval,args[7]]

def test_rollback_changes_only_technical_binding_and_never_old_authorization_facts():
    args=rollback_case();before=copy.deepcopy(args);proof=rollback_admission(*args)
    assert args==before and proof['business_version_changed'] is False
    assert proof['old_authorization_snapshot_restored'] is False
    assert proof['both_backend_indexes_retained'] is True

@pytest.mark.parametrize('group,field,value',[(1,'withdrawn',1),(1,'current_version','LATER'),
    (1,'source_hash','9'*64),(1,'ingestion_status','retired'),(1,'dataset_id','OTHER'),
    (2,'authority_status','LATER_POLICY'),(5,'return_binding_ref','OTHER'),(5,'review_receipt_sha256','')])
def test_rollback_refuses_changed_current_facts_and_unreviewed_old_binding(group,field,value):
    args=rollback_case();args[group][field]=value
    with pytest.raises(PublicationConflict):rollback_admission(*args)
