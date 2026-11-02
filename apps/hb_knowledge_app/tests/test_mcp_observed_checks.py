import json,sys
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import connections
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

def test_tool_discovery_does_not_claim_search_evidence_or_agent_success(monkeypatch):
    row={'stage':'Configured','revoked':0,'verification_json':'{}'}
    db=SimpleNamespace(sql=lambda *a,**k:[row],set_value=lambda table,name,values:row.update(values))
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(db=db))
    connections.observe('synthetic','Authenticated')
    connections.observe('synthetic','Tools Discovered')
    facts=connections.verification(row['verification_json'])
    assert facts['authenticated'] and facts['tools_discovered']
    assert facts['search_passed'] is None and facts['evidence_opened'] is None
    connections.observe('synthetic','Evidence Opened')
    # A later discovery never clears or fabricates a search fact.
    connections.observe('synthetic','Tools Discovered')
    assert row['stage']=='Evidence Opened'
    assert connections.verification(row['verification_json'])['search_passed'] is None
    with pytest.raises(KnowledgeError):connections.observe('synthetic','Agent Conversation Passed')

def test_revoked_connection_cannot_acquire_success_facts(monkeypatch):
    values=[]
    db=SimpleNamespace(sql=lambda *a,**k:[{'stage':'Revoked','revoked':1,'verification_json':'{}'}],
                       set_value=lambda *a:values.append(a))
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(db=db))
    with pytest.raises(KnowledgeError):connections.observe('synthetic','Search Passed')
    assert not values
