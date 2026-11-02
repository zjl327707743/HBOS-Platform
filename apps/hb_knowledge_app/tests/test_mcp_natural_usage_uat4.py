"""Actual authorized search/source pairs, without client identity assertions."""
import json,sys,time
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import connections
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

def database(monkeypatch):
    row={'stage':'Configured','revoked':0,'verification_json':'{}'}
    db=SimpleNamespace(sql=lambda *a,**k:[row],set_value=lambda table,name,values:row.update(values),get_value=lambda *a:'OpenClaw')
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(db=db));return row

def search(name='HANDLE',request='SEARCH'):
    return {'request_id':request,'results':[{'evidence_id':name}]}

def use(handle='HANDLE',request='EVIDENCE'):
    return {'result':{'request_id':request},'arguments':{'evidence_id':handle}}

def test_natural_usage_needs_no_challenge_discovery_or_client_header(monkeypatch):
    row=database(monkeypatch)
    connections.observe('a'*32,'Search Passed',{'channel':'CLIENT'},result=search())
    assert connections.knowledge_used_at(row['verification_json']) is None
    connections.observe('a'*32,'Evidence Opened',{'channel':'CLIENT'},**use())
    assert connections.verification_state(row['verification_json'])=='KNOWLEDGE_USED'
    assert connections.knowledge_used_at(row['verification_json'])
    facts=connections.verification(row['verification_json'])
    assert facts['knowledge_usage']['search_request_id']=='SEARCH'
    assert facts['knowledge_usage']['evidence_request_id']=='EVIDENCE'
    assert facts['knowledge_usage']['assurance']=='CONNECTION_SEARCH_AND_EVIDENCE'
    assert 'HANDLE' not in row['verification_json']
    assert not facts['client_receipt']

@pytest.mark.parametrize('channel',['PORTAL_SELF_CHECK',None])
def test_self_check_cannot_acquire_usage_even_if_it_reads_a_source(monkeypatch,channel):
    row=database(monkeypatch)
    for stage in ['Authenticated','Tools Discovered','Search Passed','Evidence Opened','Answer Generated']:
        connections.observe('a'*32,stage,{'channel':channel},result=search(),arguments={'evidence_id':'HANDLE'})
    assert connections.knowledge_used_at(row['verification_json']) is None

def test_empty_search_unmatched_source_and_ask_do_not_establish_usage(monkeypatch):
    row=database(monkeypatch);o={'channel':'CLIENT'}
    connections.observe('a'*32,'Search Passed',o,result={'request_id':'EMPTY','results':[]})
    connections.observe('a'*32,'Evidence Opened',o,**use())
    connections.observe('a'*32,'Answer Generated',o)
    assert not connections.knowledge_used_at(row['verification_json'])
    connections.observe('a'*32,'Search Passed',o,result=search())
    connections.observe('a'*32,'Evidence Opened',o,**use('OTHER'))
    assert not connections.knowledge_used_at(row['verification_json'])

def test_parallel_searches_pair_the_source_with_its_own_search(monkeypatch):
    row=database(monkeypatch);o={'channel':'CLIENT','client_name':'arbitrary-advisory-header'}
    connections.observe('a'*32,'Search Passed',o,result=search('ONE','SEARCH_ONE'))
    connections.observe('a'*32,'Search Passed',o,result=search('TWO','SEARCH_TWO'))
    connections.observe('a'*32,'Evidence Opened',o,**use('ONE'))
    assert connections.verification(row['verification_json'])['knowledge_usage']['search_request_id']=='SEARCH_ONE'


def test_expired_pair_cannot_be_used_and_real_usage_is_not_cleared_by_health(monkeypatch):
    row=database(monkeypatch);o={'channel':'CLIENT'}
    connections.observe('a'*32,'Search Passed',o,result=search())
    facts=json.loads(row['verification_json']);facts['pending_searches'][0]['expires_at']=time.time()-1
    row['verification_json']=json.dumps(facts)
    connections.observe('a'*32,'Evidence Opened',o,**use())
    assert not connections.knowledge_used_at(row['verification_json'])
    connections.observe('a'*32,'Search Passed',o,result=search())
    connections.observe('a'*32,'Evidence Opened',o,**use())
    stamp=connections.knowledge_used_at(row['verification_json'])
    connections.observe('a'*32,'Tools Discovered',{'channel':'PORTAL_SELF_CHECK'})
    assert connections.knowledge_used_at(row['verification_json'])==stamp

@pytest.mark.parametrize('endpoint',['http://10.0.0.2/mcp','http://example.com/mcp','https://user:secret@example.com/mcp','https://example.com/mcp?token=x','ftp://localhost/mcp','https://example.com/mcp#token'])
def test_install_address_rejects_credentials_and_insecure_remote(monkeypatch,endpoint):
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.shared_reference',SimpleNamespace(configuration=lambda:{'mcp_public_url':endpoint}))
    with pytest.raises(KnowledgeError):connections.cfg_endpoint()


def test_company_mode_rejects_loopback(monkeypatch):
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.shared_reference',SimpleNamespace(configuration=lambda:{'mcp_public_url':'http://localhost/mcp','mcp_deployment_mode':'SERVER_HTTPS'}))
    with pytest.raises(KnowledgeError):connections.cfg_endpoint()
