import json,sys,time
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import connections

def database(monkeypatch):
    row={'stage':'Configured','revoked':0,'verification_json':json.dumps({'challenge':{'id':'a'*32,'expires_at':time.time()+60}})}
    db=SimpleNamespace(sql=lambda *a,**k:[row],set_value=lambda table,name,values:row.update(values),get_value=lambda *a:'OpenClaw')
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(db=db));return row

def test_browser_even_with_old_evidence_facts_never_proves_client(monkeypatch):
    row=database(monkeypatch)
    for stage in ('Authenticated','Tools Discovered','Search Passed','Evidence Opened'):
        connections.observe('b'*32,stage,{'channel':'PORTAL_SELF_CHECK'})
    assert connections.verification_state(row['verification_json'])=='SERVER_READY'
    assert not connections.verification(row['verification_json'])['client_receipt']

def test_challenge_pairs_actual_client_search_and_evidence(monkeypatch):
    row=database(monkeypatch);name='b'*32
    observation={'channel':'CLIENT','client_name':'OpenClaw','challenge_id':'a'*32}
    connections.observe(name,'Authenticated',observation);connections.observe(name,'Tools Discovered',observation)
    assert connections.verification_state(row['verification_json'])=='CLIENT_CONNECTED'
    connections.observe(name,'Search Passed',observation,result={'request_id':'SEARCH','results':[{'evidence_id':'HANDLE'}]})
    connections.observe(name,'Evidence Opened',observation,result={'request_id':'WRONG'},arguments={'evidence_id':'OTHER_HANDLE'})
    assert connections.verification_state(row['verification_json'])=='CLIENT_CONNECTED'
    connections.observe(name,'Evidence Opened',observation,result={'request_id':'EVIDENCE'},arguments={'evidence_id':'HANDLE'})
    assert connections.verification_state(row['verification_json'])=='KNOWLEDGE_USED'
    receipt=connections.verification(row['verification_json'])['client_receipt']
    assert receipt['search_request_id']=='SEARCH' and receipt['evidence_request_id']=='EVIDENCE'
    assert 'HANDLE' not in row['verification_json']

@pytest.mark.parametrize('overrides',[{'challenge_id':'c'*32},{'client_name':'Hermes'},{'channel':'PORTAL_SELF_CHECK'}])
def test_wrong_or_browser_challenge_cannot_prove_client(monkeypatch,overrides):
    row=database(monkeypatch)
    observation={'channel':'CLIENT','client_name':'OpenClaw','challenge_id':'a'*32,**overrides}
    connections.observe('b'*32,'Authenticated',observation);connections.observe('b'*32,'Tools Discovered',observation)
    assert connections.verification_state(row['verification_json']) in ('CLIENT_NOT_VERIFIED','SERVER_READY')
