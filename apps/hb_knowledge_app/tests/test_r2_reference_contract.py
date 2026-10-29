

def test_a_plan_with_more_than_five_hundred_bindings_still_validates():
    """The published set travels in the plan, so its cap is a capacity limit.

    At 515 published documents the plan exceeded the old 512-binding cap and
    every ask/search failed schema validation. Raising the bound is a capacity
    decision and must stay bounded; this test pins the new ceiling.
    """
    import json, pathlib
    from hb_knowledge_app.hb_knowledge.r1_contract import SCHEMA_ROOT
    for name, path in (('execution_plan', ('schema_version',)),
                       ('api', None)):
        if name == 'execution_plan':
            schema = json.loads((SCHEMA_ROOT / 'execution_plan.schema.json').read_text())
            assert schema['properties']['bindings']['maxItems'] >= 1024
        else:
            # The service re-validates the decision response, which embeds the
            # same plan under its own cap. Both must move together.
            api = json.loads((SCHEMA_ROOT / 'api.schema.json').read_text())
            plan = api['$defs']['AuthorizedExecutionPlan']
            assert plan['properties']['bindings']['maxItems'] >= 1024
