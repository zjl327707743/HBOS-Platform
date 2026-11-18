import json,logging
import pytest,requests
from hb_knowledge_app.hb_knowledge import service_http as mod
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

PATH='/api/method/hb_knowledge_app.hb_knowledge.frappe_factory.authority_revalidate'
PAYLOAD={'request_id':'safe-test-123','phase':'pre_issue','query':'SECRET_QUERY'}

class Response:
    def __init__(self,body=b'{}',status=200,parts=None,error=None):
        self.body,self.status_code,self.parts,self.error=body,status,parts,error
        self.closed=False
    def __enter__(self):return self
    def __exit__(self,*args):self.closed=True
    def iter_content(self,size):
        assert size==8192
        if self.error:raise self.error
        yield from self.parts if self.parts is not None else [self.body]

def install(monkeypatch,response=None,error=None):
    state={'sends':0,'closed':False}
    class Session:
        def __enter__(self):return self
        def __exit__(self,*args):state['closed']=True
        def post(self,url,**kw):
            state['sends']+=1;state['timeout']=kw['timeout']
            assert self.trust_env is False and kw['stream'] is True and kw['allow_redirects'] is False
            if error:raise error
            return response
    monkeypatch.setattr(mod.requests,'Session',Session)
    return state

def receipt(caplog):
    rows=[json.loads(r.message)for r in caplog.records if r.name==mod.LOGGER.name]
    assert len(rows)==1
    return rows[0]

@pytest.mark.parametrize('error,category',[
    (requests.ConnectTimeout('SECRET_EXCEPTION'),'CONNECT_TIMEOUT'),
    (requests.ReadTimeout('SECRET_EXCEPTION'),'READ_TIMEOUT'),
    (requests.ConnectionError('SECRET_EXCEPTION'),'CONNECTION_ERROR'),
    (requests.exceptions.ChunkedEncodingError('SECRET_EXCEPTION'),'CONNECTION_ERROR')])
def test_transport_failures_correlate_actual_authority_phase_without_retry(monkeypatch,caplog,error,category):
    state=install(monkeypatch,error=error);http=mod.SignedHttp('http://internal/SECRET_HOST','SECRET_KEY','caller')
    with pytest.raises(KnowledgeError)as e:http.post(PATH,PAYLOAD,'SECRET_ORIGIN')
    assert e.value.code=='UPSTREAM_UNAVAILABLE' and state['sends']==1 and state['closed'] and state['timeout']==(2,6)
    v=receipt(caplog);assert v['request_id']=='safe-test-123' and v['operation']=='authority_revalidate' and v['phase']=='pre_issue' and v['failure_category']==category
    assert 'SECRET'not in caplog.text

@pytest.mark.parametrize('body',[b'{SECRET_MALFORMED',b'\xff'])
def test_invalid_json_and_encoding_are_safe_and_response_is_closed(monkeypatch,caplog,body):
    response=Response(body);state=install(monkeypatch,response)
    with pytest.raises(KnowledgeError):mod.SignedHttp('http://internal','key','caller').post('/v1/knowledge/ask',PAYLOAD,'client')
    assert receipt(caplog)['failure_category']=='INVALID_JSON' and response.closed and state['sends']==1
    assert 'SECRET'not in caplog.text

def test_stream_body_bound_is_not_raised_and_no_replay_occurs(monkeypatch,caplog):
    response=Response(parts=[b'x'*200]);state=install(monkeypatch,response);http=mod.SignedHttp('http://internal','key','caller');http.max_body=128
    with pytest.raises(KnowledgeError)as e:http.post('/v1/knowledge/search',PAYLOAD,'client')
    v=receipt(caplog);assert e.value.code=='UPSTREAM_UNAVAILABLE' and v['failure_category']=='BODY_LIMIT' and v['response_bytes']==200 and state['sends']==1 and response.closed

def test_upstream_safe_error_code_and_read_state_are_preserved(monkeypatch,caplog):
    response=Response(json.dumps({'error':{'code':'SCOPE_REJECTED','message':'SECRET_RESPONSE'}}).encode(),403);install(monkeypatch,response)
    with pytest.raises(KnowledgeError)as e:mod.SignedHttp('http://internal','key','caller').post('/v1/knowledge/authorize-evidence',PAYLOAD,'client')
    assert e.value.code=='SCOPE_REJECTED';v=receipt(caplog);assert v['error_code']=='SCOPE_REJECTED' and v['http_status']==403 and v['operation']=='authorize_evidence';assert 'SECRET'not in caplog.text

def test_unknown_status_response_has_no_raw_message(monkeypatch,caplog):
    install(monkeypatch,Response(b'{"SECRET_RESPONSE":1}',502))
    with pytest.raises(KnowledgeError):mod.SignedHttp('http://internal','key','caller').post('/SECRET_PATH',PAYLOAD,'client')
    v=receipt(caplog);assert v['operation']=='OTHER' and v['failure_category']=='UNEXPECTED_HTTP' and 'SECRET'not in caplog.text

def test_custom_exception_name_invalid_id_phase_and_timeout_cannot_leak(monkeypatch,caplog):
    secret_class=type('SECRET_CUSTOM_CLASS',(Exception,),{});install(monkeypatch,error=secret_class('SECRET_EXCEPTION'))
    http=mod.SignedHttp('http://internal/SECRET_URL','SECRET_KEY','caller');http.read_timeout='SECRET_TIMEOUT'
    with pytest.raises(KnowledgeError):http.post('/SECRET_PATH',{'request_id':'SECRET\nTOKEN','phase':'SECRET_PHASE'},'SECRET_ORIGIN')
    v=receipt(caplog);assert v['request_id']is None and v['phase']is None and v['read_timeout']is None and v['exception_class']=='Exception' and 'SECRET'not in caplog.text

def test_logger_failure_does_not_mask_original_error_or_send_again(monkeypatch):
    state=install(monkeypatch,error=requests.ReadTimeout('SECRET_EXCEPTION'))
    def broken(*args,**kw):raise RuntimeError('logger unavailable')
    monkeypatch.setattr(mod.LOGGER,'warning',broken)
    with pytest.raises(KnowledgeError)as e:mod.SignedHttp('http://internal','key','caller').post(PATH,PAYLOAD,'client')
    assert e.value.code=='UPSTREAM_UNAVAILABLE' and state['sends']==1 and state['closed']

def test_success_has_no_failure_receipt_and_one_send(monkeypatch,caplog):
    response=Response(b'{"allowed":true}');state=install(monkeypatch,response)
    http=mod.SignedHttp('http://internal','key','caller');http.read_timeout=80
    assert http.post(PATH,PAYLOAD,'client')=={'allowed':True}
    assert state['sends']==1 and state['timeout']==(2,80) and response.closed and state['closed'] and not caplog.records
