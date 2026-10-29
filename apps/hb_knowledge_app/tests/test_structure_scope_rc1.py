"""Factored schema validation equals the original; fresh authority never caches."""
import copy,json
from dataclasses import replace
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator,FormatChecker
from .test_spaces import runtime
from hb_knowledge_app.hb_knowledge.execution_plan import GrantPair,validate_plan,Actor
from hb_knowledge_app.hb_knowledge.repositories import ActorState
from hb_knowledge_app.hb_knowledge.r1_contract import validation_scope,validate_structure,normalize_search,CONTRACT_VERSION
from hb_knowledge_app.hb_knowledge.internal_contract import InternalResponse
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

def fixture():
    app,actor,repo,binding=runtime()
    repo.snapshot=replace(repo.snapshot,grants=repo.snapshot.grants+(
        GrantPair('ROLE_QA','SPACE_QA','knowledge.search','GRANT_SEARCH'),),query_embedding_admitted=True)
    plan=app.provider.evaluate(actor,app.client,'knowledge.search',normalize_search({'query':'合成结构校验问题'}),'RC1_SYNTHETIC')
    return app,actor,repo,binding,plan

def oracle(value,*,response=False):
    root=Path(__file__).parents[1]/'hb_knowledge_app/hb_knowledge/schemas'
    schema=json.loads((root/('api.schema.json' if response else 'execution_plan.schema.json')).read_text())
    if response:schema={**schema,'$ref':'#/$defs/InternalDecisionResponse'};schema.pop('oneOf',None)
    return next(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(value),None) is None

def accepts(value,*,response=False):
    try:validate_structure('InternalDecisionResponse' if response else '',value,plan=not response);return True
    except KnowledgeError:return False

def test_every_binding_field_and_outer_mutation_matches_independent_original_schema():
    _,_,_,_,plan=fixture();wire=plan.to_wire();variants=[wire]
    for key in wire['bindings'][0]:
        for value in (None,True,False,7,[],{},'', ' changed '):
            trial=copy.deepcopy(wire);trial['bindings'][0][key]=value;variants.append(trial)
        trial=copy.deepcopy(wire);trial['bindings'][0].pop(key);variants.append(trial)
    for value in ([],[None],{},None):
        trial=copy.deepcopy(wire);trial['bindings']=value;variants.append(trial)
    for key in ('expires_at','subject','client','space_ids','limits','extra_property'):
        trial=copy.deepcopy(wire);trial[key]=None;variants.append(trial)
    with validation_scope():
        assert accepts(wire)
        for trial in variants:
            assert accepts(trial)==oracle(trial)
            response=InternalResponse(CONTRACT_VERSION,'ALLOWED',plan.request_id,'pre_retrieval','a'*64,plan.expires_at,plan=plan).to_wire()
            response['plan']=trial
            assert accepts(response,response=True)==oracle(response,response=True)

@pytest.mark.parametrize('transition',['withdraw','version','role','disabled','physical_pair'])
def test_positive_structure_cache_does_not_cache_authority_or_version(transition):
    app,actor,repo,binding,plan=fixture()
    with validation_scope():
        validate_plan(plan,now=app.provider.clock());app.provider.revalidate(plan)
        if transition=='withdraw':repo.snapshot=replace(repo.snapshot,bindings=(replace(binding,withdrawn=True),))
        elif transition=='version':repo.snapshot=replace(repo.snapshot,bindings=(replace(binding,version_id='NEW_VERSION'),))
        elif transition=='physical_pair':repo.snapshot=replace(repo.snapshot,bindings=(replace(binding,document_id='OTHER_PHYSICAL'),))
        elif transition=='role':repo.snapshot=replace(repo.snapshot,actor_state=ActorState(actor,(),True))
        else:repo.snapshot=replace(repo.snapshot,actor_state=ActorState(actor,('ROLE_QA',),False))
        with pytest.raises(KnowledgeError):app.provider.revalidate(plan)

def test_expiry_cross_account_and_scope_lifetime_remain_fresh():
    app,actor,_,_,plan=fixture()
    from hb_knowledge_app.hb_knowledge.execution_plan import timestamp
    from hb_knowledge_app.hb_knowledge.r1_contract import _binding_shapes
    with validation_scope():
        validate_plan(plan,now=app.provider.clock())
        with pytest.raises(KnowledgeError):validate_plan(plan,now=timestamp(plan.expires_at))
        with pytest.raises(KnowledgeError):validate_plan(plan,now=app.provider.clock(),actor=replace(actor,user_ref='OTHER_USER'))
        assert _binding_shapes.get()
    assert _binding_shapes.get() is None

def test_binding_expiry_is_rechecked_after_its_shape_was_cached():
    app,_,_,binding,plan=fixture()
    from datetime import datetime,timezone
    deadline=app.provider.clock()+3
    expiring=replace(binding,valid_until=datetime.fromtimestamp(deadline,timezone.utc).isoformat().replace('+00:00','Z'))
    plan=replace(plan,bindings=(expiring,))
    with validation_scope():
        validate_plan(plan,now=app.provider.clock())
        with pytest.raises(KnowledgeError):validate_plan(plan,now=deadline+1)
