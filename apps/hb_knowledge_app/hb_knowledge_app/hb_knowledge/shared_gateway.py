"""Short HBOS actor context for a trusted shared-gateway relay.

This supplements the caller's own OAuth connection. It is never an OAuth token,
never grants roles, and cannot substitute a different connection owner.
"""
import base64,hashlib,hmac,json,re,time
from pathlib import Path
from urllib.parse import urlsplit
from .errors import KnowledgeError
from .service_http import canonical

HEADER='x-hbos-actor-proof'
FIELDS={'v','site','resource','actor_binding','iat','exp','nonce'}

def actor_binding(user_ref,cfg):
    return hmac.new(cfg['proof_key'].encode(),canonical(['HBOS_MCP_ACTOR_V1',cfg['site'],user_ref]).encode(),hashlib.sha256).hexdigest()

def bridge_config(cfg):
    value=cfg.get('shared_gateway_bridge')
    if not isinstance(value,dict) or value.get('enabled') is not True:raise KnowledgeError('POLICY_UNAVAILABLE')
    if set(value)!={'enabled','key_file','resource'}:raise KnowledgeError('POLICY_UNAVAILABLE')
    if not isinstance(value['key_file'],str) or not isinstance(value['resource'],str):raise KnowledgeError('POLICY_UNAVAILABLE')
    url=urlsplit(value['resource'])
    if (not url.hostname or url.path!='/mcp' or url.username or url.password or url.query or url.fragment
            or url.scheme not in ('http','https') or url.scheme=='http' and url.hostname not in ('localhost','127.0.0.1','::1','knowledge-rebuild.localhost','knowledge-r2.localhost')):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    p=Path(value['key_file'])
    if not p.is_absolute() or not p.is_file() or p.is_symlink() or p.stat().st_mode&0o077:raise KnowledgeError('POLICY_UNAVAILABLE')
    key=p.read_bytes().strip()
    if not 32<=len(key)<=128:raise KnowledgeError('POLICY_UNAVAILABLE')
    if value['resource']!=cfg.get('mcp_public_url',cfg.get('oauth',{}).get('resource')):raise KnowledgeError('POLICY_UNAVAILABLE')
    return value,key

def issue_actor_context(user_ref,cfg,nonce,now=None):
    value,key=bridge_config(cfg)
    if not isinstance(nonce,str) or not re.fullmatch('[0-9a-f]{32}',nonce):raise KnowledgeError('INVALID_REQUEST')
    now=int(time.time() if now is None else now)
    claims={'v':1,'site':cfg['site'],'resource':value['resource'],'actor_binding':actor_binding(user_ref,cfg),'iat':now,'exp':now+30,'nonce':nonce}
    payload=base64.urlsafe_b64encode(canonical(claims).encode()).rstrip(b'=')
    signature=base64.urlsafe_b64encode(hmac.new(key,payload,hashlib.sha256).digest()).rstrip(b'=')
    return {'proof':payload.decode()+'.'+signature.decode(),'expires_at':claims['exp'],'purpose':'SHARED_GATEWAY_ACTOR_CONTEXT_NOT_A_CREDENTIAL'}

def verify_actor_context(proof,cfg,expected_binding,now=None):
    value,key=bridge_config(cfg)
    try:
        if not isinstance(proof,str) or len(proof)>1024:raise ValueError()
        payload,signature=proof.split('.')
        if not re.fullmatch('[A-Za-z0-9_-]+',payload) or not re.fullmatch('[A-Za-z0-9_-]{43}',signature):raise ValueError()
        calculated=base64.urlsafe_b64encode(hmac.new(key,payload.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
        if not hmac.compare_digest(calculated,signature):raise ValueError()
        j=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
        now=time.time() if now is None else now
        if set(j)!=FIELDS or type(j['v']) is not int or j['v']!=1:raise ValueError()
        if j['site']!=cfg['site'] or j['resource']!=value['resource']:raise ValueError()
        if not isinstance(j['actor_binding'],str) or not re.fullmatch('[0-9a-f]{64}',j['actor_binding']):raise ValueError()
        if not isinstance(expected_binding,str) or not hmac.compare_digest(j['actor_binding'],expected_binding):raise ValueError()
        if any(type(j[x]) is not int for x in ('iat','exp')) or not 0<j['exp']-j['iat']<=30 or not j['iat']<=now+3<j['exp']+3:raise ValueError()
        if j['exp']<=now or not re.fullmatch('[0-9a-f]{32}',j['nonce']):raise ValueError()
        return j
    except (ValueError,TypeError,KeyError,UnicodeError):raise KnowledgeError('AUTHENTICATION_REQUIRED') from None
