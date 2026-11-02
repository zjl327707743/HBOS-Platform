import copy
import pytest
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.maintenance_permit import controller_permit,permit_matches

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


def test_more_than_sixty_documents_or_nonlogical_batch_is_rejected():
    value=scope();value['by_batch'][BATCH]={f'DOC_{i}':{'version_id':'VERSION','source_sha256':'c'*64} for i in range(61)}
    with pytest.raises(KnowledgeError):controller_permit({'maintenance_batch_permit':value},now=100)
    value=scope();value['by_batch']['../../private']=value['by_batch'].pop(BATCH)
    with pytest.raises(KnowledgeError):controller_permit({'maintenance_batch_permit':value},now=100)
