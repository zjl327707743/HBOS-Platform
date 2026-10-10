"""Catalog pagination never expands the role/action/document scope."""
from dataclasses import replace
import pytest
from .test_spaces import runtime
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.execution_plan import GrantPair
from hb_knowledge_app.hb_knowledge.reference_admin import get_catalog, get_catalog_page


def catalog_runtime():
    app,actor,repo,binding=runtime()
    repo.snapshot=replace(repo.snapshot,grants=repo.snapshot.grants+(
        GrantPair('ROLE_QA','SPACE_QA','knowledge.search','GRANT_SEARCH'),),
        bindings=(replace(binding,title='合成制度长标题',document_number='SYN-001'),))
    return app,actor,repo,repo.snapshot.bindings[0]


def test_catalog_filters_paired_roles_datasets_and_denied_spaces_without_models():
    app,actor,repo,binding=catalog_runtime()
    repo.snapshot=replace(repo.snapshot,bindings=repo.snapshot.bindings+(
        replace(binding,space_id='SPACE_PROD',canonical_document_id='HIDDEN_DOC',title='未获准目录'),
        replace(binding,dataset_id='OTHER_DS',canonical_document_id='HIDDEN_DS_DOC'),))
    result=get_catalog_page(app,actor)
    assert result['total']==1 and result['documents'][0]['document_id']=='DOC_TEST'
    assert 'HIDDEN' not in str(result) and not repo.snapshot.query_embedding_admitted
    repo.snapshot=replace(repo.snapshot,denied_spaces=('SPACE_QA',))
    assert get_catalog(app,actor)=={'documents':[]}


def test_department_document_number_pagination_is_stable_and_bounded():
    app,actor,repo,binding=catalog_runtime()
    repo.snapshot=replace(repo.snapshot,bindings=tuple(
        replace(binding,canonical_document_id=f'DOC_{i:03}',version_id=f'VER_{i:03}',title=f'合成长中文标题{i:03}',document_number=f'SYN-{i:03}')
        for i in range(27)))
    first=get_catalog_page(app,actor,page='1',page_size='12')
    second=get_catalog_page(app,actor,page=2,page_size=12)
    assert first['total']==second['total']==27
    assert len(first['documents'])==len(second['documents'])==12
    assert not ({d['document_id'] for d in first['documents']}&{d['document_id'] for d in second['documents']})
    assert get_catalog_page(app,actor,query='SYN-025')['total']==1
    assert get_catalog_page(app,actor,query='合成',space_id='SPACE_PROD')['total']==0
    assert get_catalog_page(app,actor,page=100)['documents']==[]


@pytest.mark.parametrize('field,value',[('page',0),('page',True),('page','1.0'),('page','-1'),('page_size',51),('page_size',0),('query',[]),('space_id',[])])
def test_invalid_pagination_and_filters_rejected(field,value):
    app,actor,_,_=catalog_runtime()
    with pytest.raises(KnowledgeError):get_catalog_page(app,actor,**{field:value})


def test_same_revision_withdrawal_before_return_rejects_page_and_count():
    app,actor,repo,binding=catalog_runtime()
    def withdraw(phase):
        repo.snapshot=replace(repo.snapshot,bindings=(replace(binding,withdrawn=True),))
    app.checkpoint=withdraw
    with pytest.raises(KnowledgeError) as error:get_catalog_page(app,actor)
    assert error.value.code=='SCOPE_REJECTED'


def test_same_revision_role_action_revocation_rejects_old_title():
    app,actor,repo,_=catalog_runtime()
    app.checkpoint=lambda phase:setattr(repo,'snapshot',replace(repo.snapshot,grants=tuple(g for g in repo.snapshot.grants if g.action!='knowledge.search')))
    with pytest.raises(KnowledgeError):get_catalog(app,actor)
