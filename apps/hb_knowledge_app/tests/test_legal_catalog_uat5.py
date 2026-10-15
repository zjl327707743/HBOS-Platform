from dataclasses import replace
import pytest
from .test_catalog_page import catalog_runtime
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.execution_plan import GrantPair
from hb_knowledge_app.hb_knowledge.reference_admin import get_catalog_page
from hb_knowledge_app.hb_knowledge.legal_metadata import legal_metadata,LAW_SPACE
from hb_knowledge_app.hb_knowledge.download_policy import document_download_decision


def test_law_filter_stays_inside_current_role_and_version_scope(monkeypatch):
    app,actor,repo,binding=catalog_runtime()
    law=replace(binding,space_id=LAW_SPACE,canonical_document_id='LAW_SYN',version_id='LAW_VER',title='合成法规')
    repo.snapshot=replace(repo.snapshot,active_spaces=repo.snapshot.active_spaces+(LAW_SPACE,),
        grants=repo.snapshot.grants+tuple(GrantPair('ROLE_QA',LAW_SPACE,a,'LAW_'+a) for a in ('knowledge.search','knowledge.spaces')),
        bindings=repo.snapshot.bindings+(law,),space_titles=repo.snapshot.space_titles+((LAW_SPACE,'公司公共法律法规知识'),))
    import hb_knowledge_app.hb_knowledge.legal_metadata as module
    monkeypatch.setattr(module,'for_version',lambda version:legal_metadata({'category':'安全环保','effective_status':'待核'}))
    page=get_catalog_page(app,actor,law_category='安全环保')
    assert page['total']==1 and page['documents'][0]['document_id']=='LAW_SYN'
    assert page['documents'][0]['legal_metadata']['effective_status']=='待核'
    assert get_catalog_page(app,actor,space_id='SPACE_QA',law_category='安全环保')['total']==0
    repo.snapshot=replace(repo.snapshot,denied_spaces=(LAW_SPACE,))
    assert get_catalog_page(app,actor,law_category='安全环保')['total']==0


@pytest.mark.parametrize('value',[
 {'category':'安全环保','effective_status':'根据文件夹推断有效'},
 {'category':'私有隐藏分类','effective_status':'待核'},
 {'category':'待分类','effective_status':'待核','published_date':'2026-13-01'},
 {'category':'待分类','effective_status':'待核','download_url':'https://example.invalid'},
])
def test_unverified_legal_status_and_unsafe_extra_fields_rejected(value):
    with pytest.raises(KnowledgeError):legal_metadata(value)


def test_download_permission_cannot_be_inferred_from_search_or_public_law_scope():
    assert not document_download_decision(subject_enabled=True,version_current=True).allowed
    decision=document_download_decision(subject_enabled=True,version_current=True,iam_allowed=True,public_download_allowed=True)
    assert not decision.allowed and decision.action=='document.download' and decision.reason=='ORIGINAL_DELIVERY_DISABLED'
    stale=document_download_decision(subject_enabled=True,version_current=False,iam_allowed=True,department_allowed=True)
    assert not stale.allowed and stale.reason=='SOURCE_VERSION_STALE'
