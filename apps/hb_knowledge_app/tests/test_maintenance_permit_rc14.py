import copy
import pytest
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.maintenance_managed import SCHEMA, claimable
from hb_knowledge_app.hb_knowledge.maintenance_permit import controller_permit,permit_matches,require_technical_preparation

BATCH='IMP_'+'a'*32
DOC='DOC_SYNTHETIC'


def scope():
    return {'manifest_sha256':'b'*64,'expires_at':200,
        'by_batch':{BATCH:{DOC:{'version_id':'VERSION_SYNTHETIC','source_sha256':'c'*64}}}}


def frozen():
    return {'items':[{'canonical_document_id':DOC,'version_id':'VERSION_SYNTHETIC',
        'sha256':'c'*64,'owner_inclusion_confirmed':True,'internal_sharing_confirmed':True}]}


def test_permit_narrows_only_the_exact_frozen_source_and_existing_sharing():
    value=controller_permit({'maintenance_batch_permit':scope()},now=100)
    assert permit_matches(value,BATCH,{'document_ids':[DOC]},frozen())
    for field,replacement in [('version_id','NEXT'),('sha256','d'*64),
                              ('owner_inclusion_confirmed',False),('internal_sharing_confirmed',False)]:
        data=copy.deepcopy(frozen());data['items'][0][field]=replacement
        assert not permit_matches(value,BATCH,{'document_ids':[DOC]},data)
    assert not permit_matches(value,'IMP_'+'d'*32,{'document_ids':[DOC]},frozen())
    assert not permit_matches(value,BATCH,{'document_ids':['OTHER']},frozen())


def test_scope_missing_or_expired_cannot_claim_when_required():
    with pytest.raises(KnowledgeError):controller_permit({'maintenance_claim_scope_required':True},now=100)
    with pytest.raises(KnowledgeError):controller_permit({'maintenance_batch_permit':scope()},now=201)


def test_empty_explicit_scope_is_closed_and_never_becomes_legacy_unscoped():
    value=scope();value['by_batch']={}
    permit=controller_permit({'maintenance_batch_permit':value,
        'maintenance_claim_scope_required':True},now=100)
    assert permit is not None
    assert not permit_matches(permit,BATCH,{'document_ids':[DOC]},frozen())


def test_more_than_sixty_documents_or_nonlogical_batch_is_rejected():
    value=scope();value['by_batch'][BATCH]={f'DOC_{i}':{'version_id':'VERSION','source_sha256':'c'*64} for i in range(61)}
    with pytest.raises(KnowledgeError):controller_permit({'maintenance_batch_permit':value},now=100)
    value=scope();value['by_batch']['../../private']=value['by_batch'].pop(BATCH)
    with pytest.raises(KnowledgeError):controller_permit({'maintenance_batch_permit':value},now=100)


def test_technical_preparation_needs_an_exact_unexpired_preparation_permit():
    manifest = frozen()
    manifest.update(batch_sha256='b'*64,approval_status='OWNER_APPROVED')
    item, = manifest['items']
    item.update(disposition='TECHNICAL_REINDEX',parser_input='VERIFIED_ORIGINAL_NATIVE',
        expected_current_version='VERSION_SYNTHETIC',space_id='DEPT_SAFETY',
        native_source_proof={'full_source_requested':True},native_parent_binding={
            'canonical_document_id':DOC,'version_id':'VERSION_SYNTHETIC','space_id':'DEPT_SAFETY','binding_ref':'BINDING'})
    job = {'document_ids':[DOC],'operation':'parse'}
    permit = {**scope(),'prepare_only':True}
    config = {'maintenance_batch_permit':permit,'maintenance_task_checkpoint_required':True,
              'maintenance_managed_policy':{'schema':SCHEMA,'enabled':False}}
    assert claimable(config,'claim_preparation') is None
    require_technical_preparation(config,BATCH,job,manifest,[item],now=100)
    for narrowed in ({**permit,'manifest_sha256':'e'*64}, {**permit,'by_batch':{}},
                     {**permit,'expires_at':99}, scope()):
        with pytest.raises(KnowledgeError):
            require_technical_preparation({**config,'maintenance_batch_permit':narrowed},BATCH,job,manifest,[item],now=100)
    with pytest.raises(KnowledgeError):
        require_technical_preparation(config,BATCH,{**job,'operation':'retry'},manifest,[item],now=100)
