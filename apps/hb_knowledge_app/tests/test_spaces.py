"""Pure policy/use-case regression, not native employee/session evidence."""
from dataclasses import replace
from types import SimpleNamespace
import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.execution_plan import Actor, Client, GrantPair, Binding, ProviderStamp, timestamp
from hb_knowledge_app.hb_knowledge.repositories import ActorState, AuthoritySnapshot
from hb_knowledge_app.hb_knowledge.policy_provider import LegacyHbosPolicyProvider
from hb_knowledge_app.hb_knowledge.spaces import list_spaces


def runtime():
    actor=Actor('USER_TEST','SESSION_TEST','generation-1')
    client=Client('CLIENT_TEST')
    binding=Binding('SPACE_QA','DOC_TEST','VERSION_TEST',None,'DS_TEST','PHYSICAL_DOC_TEST','ALIAS_TEST',
                    'BINDING_TEST','fixed-1','SYNTHETIC_TEST','SYNTHETIC_ONLY','2026-01-01T00:00:00Z')
    snapshot=AuthoritySnapshot(ActorState(actor,('ROLE_QA',),True),(client,),
        (GrantPair('ROLE_QA','SPACE_QA','knowledge.spaces','GRANT_QA'),
         GrantPair('ROLE_PROD','SPACE_PROD','knowledge.spaces','GRANT_PROD'),
         GrantPair('ROLE_QA','SPACE_PROD','knowledge.evidence','GRANT_OTHER_ACTION')),
        ('SPACE_QA','SPACE_PROD'),(binding,),('DS_TEST',),(),'policy-fixed','corpus-fixed',
        ProviderStamp('HBOS_LEGACY_READONLY','bridge-fixed','2026-12-31T00:00:00Z'),
        'UNAPPROVED_MODEL',False,(('SPACE_QA','合成质检'),('SPACE_PROD','合成生产')))
    class Repository:
        test_only=True
        def read_current(self, subject): return self.snapshot
    repository=Repository();repository.snapshot=snapshot
    provider=LegacyHbosPolicyProvider(repository,environment='synthetic',clock=lambda:timestamp('2026-10-08T00:00:00Z'))
    result=SimpleNamespace(provider=provider,client=client,profile='synthetic',checkpoint=lambda phase:None)
    return result,actor,repository,binding


def test_space_titles_and_counts_use_complete_role_action_pairs_without_model():
    app,actor,repo,_=runtime()
    assert not repo.snapshot.query_embedding_admitted
    assert list_spaces(app,actor)=={'spaces':[{'space_id':'SPACE_QA','title':'合成质检','document_count':1}]}


def test_count_deduplicates_canonical_version_across_physical_bindings():
    app,actor,repo,binding=runtime()
    repo.snapshot=replace(repo.snapshot,bindings=(binding,replace(binding,binding_ref='SECOND_BINDING',document_id='SECOND_PHYSICAL')))
    assert list_spaces(app,actor)['spaces'][0]['document_count']==1


def test_no_grant_returns_empty_list_without_manufacturing_public_scope():
    app,actor,repo,_=runtime()
    repo.snapshot=replace(repo.snapshot,grants=())
    assert list_spaces(app,actor)=={'spaces':[]}


def test_withdrawn_binding_does_not_contribute_to_authorized_count():
    app,actor,repo,binding=runtime()
    repo.snapshot=replace(repo.snapshot,bindings=(replace(binding,withdrawn=True),))
    assert list_spaces(app,actor)['spaces'][0]['document_count']==0


def test_role_revocation_before_final_return_rejects_old_titles():
    app,actor,repo,_=runtime()
    def revoke(phase):
        repo.snapshot=replace(repo.snapshot,actor_state=ActorState(actor,(),True))
    app.checkpoint=revoke
    with pytest.raises(KnowledgeError) as failure:
        list_spaces(app,actor)
    assert failure.value.code=='SCOPE_REJECTED'


def test_title_cannot_expose_private_location_or_physical_id():
    app,actor,repo,_=runtime()
    repo.snapshot=replace(repo.snapshot,space_titles=(('SPACE_QA','private /source/secret.pdf'),))
    with pytest.raises(KnowledgeError):
        list_spaces(app,actor)
