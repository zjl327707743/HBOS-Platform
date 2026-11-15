"""A rolled-back positive index can be requalified without rewriting history."""
import copy, hashlib
from dataclasses import replace
import pytest
from .test_parse_revision import case, rollback_case
from hb_knowledge_app.hb_knowledge import parse_revision as revision
from hb_knowledge_app.hb_knowledge.service_http import canonical
from hb_knowledge_app.hb_knowledge.publication import PublicationConflict


def setup_case():
    args=case();new,forward=revision.replacement(*args)
    rollback=revision.rollback_admission(*rollback_case())
    fref='PUB_TECH_'+revision.revision_key('BATCH',args[0])[:32]
    rref='PUB_ROLLBACK_'+'a'*32
    raw={fref:canonical(forward),rref:canonical(rollback)}
    proof={'forward_revision_ref':fref,'rollback_revision_ref':rref,
           'forward_sha256':hashlib.sha256(raw[fref].encode()).hexdigest(),
           'rollback_sha256':hashlib.sha256(raw[rref].encode()).hexdigest()}
    approval={**args[5],'approval_ref':'MAIN_FRESH_REVIEW_AFTER_ROLLBACK',
              'review_receipt_sha256':'9'*64,'resume_from_rollback':proof}
    return args,new,raw,approval


def test_reviewed_recovery_has_new_audit_key_and_preserves_original_key():
    args,new,raw,approval=setup_case();before=copy.deepcopy(raw)
    old=revision.revision_key('BATCH',args[0])
    assert revision.effective_revision_key('BATCH',args[0],args[5],raw.get)==old
    resumed=revision.effective_revision_key('BATCH',args[0],approval,raw.get)
    assert resumed!=old and resumed==revision.effective_revision_key('BATCH',args[0],approval,raw.get)
    assert raw==before


@pytest.mark.parametrize('field,value',[
    ('canonical_document_id','OTHER'),('version_id','LATER'),('source_sha256','0'*64),
    ('target_document_id','e'*32),('target_binding_revision','OTHER'),
    ('profile_hash','8'*64),('quality_evidence_sha256','8'*64),
    ('parent_binding_ref','OTHER'),('parent_binding_revision','OTHER')])
def test_recovery_cannot_select_another_source_index_or_parent(field,value):
    args,new,raw,approval=setup_case();approval[field]=value
    with pytest.raises(PublicationConflict):
        revision.effective_revision_key('BATCH',args[0],approval,raw.get)


@pytest.mark.parametrize('change',['missing_forward','missing_rollback','tampered','old_review','old_approval','not_rollback'])
def test_no_missing_tampered_or_unreviewed_recovery(change):
    args,new,raw,approval=setup_case();proof=approval['resume_from_rollback']
    if change=='missing_forward':raw.pop(proof['forward_revision_ref'])
    if change=='missing_rollback':raw.pop(proof['rollback_revision_ref'])
    if change=='tampered':raw[proof['rollback_revision_ref']]+=' '
    if change=='old_review':approval['review_receipt_sha256']=args[5]['review_receipt_sha256']
    if change=='old_approval':approval['approval_ref']=args[5]['approval_ref']
    if change=='not_rollback':
        raw[proof['rollback_revision_ref']]=raw[proof['forward_revision_ref']]
        proof['rollback_sha256']=hashlib.sha256(raw[proof['rollback_revision_ref']].encode()).hexdigest()
    with pytest.raises(PublicationConflict):revision.effective_revision_key('BATCH',args[0],approval,raw.get)


def test_same_physical_pair_reuses_disabled_binding_and_original_timestamp():
    args,retained,raw,approval=setup_case()
    expected=replace(retained,valid_from='2026-11-03T00:00:00Z')
    actual=revision.reusable_rolled_back_binding(expected,retained,False,'2026-11-03T01:00:00Z')
    assert actual is retained and actual.valid_from==retained.valid_from


@pytest.mark.parametrize('field,value',[
    ('document_id','e'*32),('binding_revision','OTHER'),('space_id','OTHER'),
    ('authority_status','OTHER'),('valid_until','2026-01-01T00:00:00Z')])
def test_reuse_cannot_restore_different_or_expired_binding(field,value):
    args,expected,raw,approval=setup_case();retained=replace(expected,**{field:value})
    with pytest.raises(PublicationConflict):
        revision.reusable_rolled_back_binding(expected,retained,False,'2026-11-03T01:00:00Z')


def test_already_enabled_target_is_not_a_recovery_parent():
    args,expected,raw,approval=setup_case()
    with pytest.raises(PublicationConflict):
        revision.reusable_rolled_back_binding(expected,expected,True,'2026-11-03T01:00:00Z')
