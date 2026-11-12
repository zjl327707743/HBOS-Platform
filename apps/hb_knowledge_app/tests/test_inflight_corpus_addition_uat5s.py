"""Synthetic policy logic; live no-fault reproduction is kept in Owner evidence."""
from dataclasses import replace
import pytest
from .test_spaces import runtime
from hb_knowledge_app.hb_knowledge.execution_plan import ProviderStamp
from hb_knowledge_app.hb_knowledge.r1_contract import normalize_search
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

def fixture(monkeypatch,shared=True):
    app,actor,repo,binding=runtime()
    repo.snapshot=replace(repo.snapshot,query_embedding_admitted=True,model_policy_ref='SYNTHETIC_APPROVED')
    plan=app.provider.evaluate(actor,app.client,'knowledge.spaces',normalize_search({'query':'合成资料'}),'SYN_REQUEST')
    if shared:
        stamp=ProviderStamp('INTERNAL_SHARED_REFERENCE','SYN_SHARED_AUTHORITY',None)
        plan=replace(plan,provider=stamp);repo.snapshot=replace(repo.snapshot,provider=stamp)
        # Exercise only revalidation's corpus rule with synthetic bindings.
        # Native session/client/production port checks are not stubbed in the
        # live reproduction and remain covered by their own boundary suites.
        monkeypatch.setattr(app.provider,'_current',lambda *a:repo.snapshot)
    return app.provider,repo,binding,plan

def test_shared_addition_keeps_the_original_signed_scope_and_checks_all_old_bindings(monkeypatch):
    provider,repo,binding,plan=fixture(monkeypatch)
    new=replace(binding,canonical_document_id='NEW_DOC',version_id='NEW_VER',document_id='NEW_PHYSICAL',binding_ref='NEW_BINDING')
    repo.snapshot=replace(repo.snapshot,bindings=(binding,new),corpus_revision='NEW_CORPUS')
    assert provider.revalidate(plan) is plan and plan.bindings==(binding,)
    assert new not in plan.bindings and plan.corpus_revision=='corpus-fixed'

@pytest.mark.parametrize('fault',['binding_removed','version_replaced','dataset_removed','grant_removed','role_removed','space_denied','policy_changed','provider_changed','model_changed'])
def test_corpus_addition_does_not_hide_any_revocation_or_replacement(monkeypatch,fault):
    provider,repo,binding,plan=fixture(monkeypatch);repo.snapshot=replace(repo.snapshot,corpus_revision='NEW_CORPUS')
    overrides={
        'binding_removed':{'bindings':()},
        'version_replaced':{'bindings':(replace(binding,version_id='REPLACED'),)},
        'dataset_removed':{'allowed_datasets':()},
        'grant_removed':{'grants':()},
        'role_removed':{'actor_state':replace(repo.snapshot.actor_state,roles=())},
        'space_denied':{'denied_spaces':plan.space_ids},
        'policy_changed':{'policy_revision':'NEW_POLICY'},
        'provider_changed':{'provider':replace(repo.snapshot.provider,authority_revision='CHANGED')},
        'model_changed':{'model_policy_ref':'CHANGED'},
    }
    repo.snapshot=replace(repo.snapshot,**overrides[fault])
    with pytest.raises(KnowledgeError):provider.revalidate(plan)

def test_legacy_provider_keeps_exact_corpus_revision_requirement(monkeypatch):
    provider,repo,binding,plan=fixture(monkeypatch,shared=False)
    repo.snapshot=replace(repo.snapshot,corpus_revision='NEW_CORPUS')
    with pytest.raises(KnowledgeError) as e:provider.revalidate(plan)
    assert e.value.code=='SCOPE_REJECTED'
