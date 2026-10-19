

def test_a_plan_with_more_than_five_hundred_bindings_still_validates():
    """The published set travels in the plan, so its cap is a capacity limit.

    At 515 published documents the plan exceeded the old 512-binding cap and
    every ask/search failed schema validation. Raising the bound is a capacity
    decision and must stay bounded; this test pins the new ceiling.
    """
    import json, pathlib
    from hb_knowledge_app.hb_knowledge.r1_contract import SCHEMA_ROOT
    schema = json.loads((SCHEMA_ROOT / 'execution_plan.schema.json').read_text())
    assert schema['properties']['bindings']['maxItems'] >= 1024
