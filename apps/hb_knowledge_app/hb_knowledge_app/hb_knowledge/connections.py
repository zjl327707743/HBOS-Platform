"""User-owned, expiring app connections; no Frappe sid or upstream key export."""
import hashlib, hmac, json, re, secrets, time
from datetime import datetime, timezone
from .errors import KnowledgeError
from .execution_plan import Actor, Client
from .repositories import ActorState
from .service_http import canonical
from .public_strings import safe_string

DOCTYPE = 'HBOS Knowledge Connection'
TOOLS = ('list_knowledge_spaces', 'search_knowledge', 'get_evidence', 'ask_knowledge')
AUDIENCE = 'hbos-knowledge-mcp'

def _user(cur, user, cfg):
    from .frappe_authority import rows
    from hbos_portal.services.internal_users import classify_internal_user
    accounts=rows(cur,'SELECT enabled,user_type FROM `tabUser` WHERE name=%s',(user,))
    roles=tuple(sorted(r['role'] for r in rows(cur,'SELECT role FROM `tabHas Role` WHERE parent=%s AND parenttype=%s',(user,'User'))))
    security=rows(cur,'SELECT security_version,blocked FROM `tabHBOS Account Security` WHERE user=%s',(user,))
    version=int(security[0]['security_version']) if security else 0
    if (not accounts or not classify_internal_user(user,account=accounts[0],roles=roles,config=cfg).allowed
            or cfg['reader_role'] not in roles or (security and security[0]['blocked'])):
        raise KnowledgeError('AUTHENTICATION_REQUIRED')
    return roles,version

def _connection(cur, name, cfg):
    from .frappe_authority import rows
    records=rows(cur,'SELECT name,owner_user,token_hash,security_version,audience,expires_at,revoked FROM `tabHBOS Knowledge Connection` WHERE name=%s',(name,))
    if len(records)!=1:raise KnowledgeError('AUTHENTICATION_REQUIRED')
    r=records[0]
    expires=r['expires_at'].replace(tzinfo=timezone.utc).timestamp()
    roles,version=_user(cur,r['owner_user'],cfg)
    if r['revoked'] or r['audience']!=AUDIENCE or expires<=time.time() or version!=r['security_version']:
        raise KnowledgeError('AUTHENTICATION_REQUIRED')
    return r,roles,expires

def authenticate(token, cfg):
    from .frappe_authority import committed_view
    if not isinstance(token,str) or not re.fullmatch(r'hbos_mcp_[0-9a-f]{32}\.[A-Za-z0-9_-]{43}',token):
        raise KnowledgeError('AUTHENTICATION_REQUIRED')
    name,secret=token.removeprefix('hbos_mcp_').split('.')
    with committed_view() as cur:r,roles,expires=_connection(cur,name,cfg)
    if not hmac.compare_digest(hashlib.sha256(secret.encode()).hexdigest(),r['token_hash']):
        raise KnowledgeError('AUTHENTICATION_REQUIRED')
    return r,roles,expires

def issue_actor(token, cfg, state):
    r,_,expires=authenticate(token,cfg)
    generation=hmac.new(cfg['proof_key'].encode(),canonical([r['name'],r['token_hash'],r['security_version']]).encode(),hashlib.sha256).hexdigest()
    ref=hmac.new(cfg['proof_key'].encode(),canonical([cfg['site'],cfg['run_id'],r['name'],generation,AUDIENCE]).encode(),hashlib.sha256).hexdigest()
    proof={'site':cfg['site'],'instance':cfg['run_id'],'user':r['owner_user'],'generation':generation,
           'client':cfg['portal_client_id'],'purpose':'knowledge.read','expires':min(expires,time.time()+600),
           'connection_ref':r['name']}
    state.set('private-proof:'+ref,canonical(proof),ex=600)
    return Actor(r['owner_user'],ref,generation,True)

def resolve_actor(actor, client, proof, cfg):
    from .frappe_authority import committed_view
    if (proof.get('site'),proof.get('instance'),proof.get('user'),proof.get('client'),proof.get('purpose')) != (
            cfg['site'],cfg['run_id'],actor.user_ref,client.client_id,'knowledge.read') or proof.get('expires',0)<=time.time():
        raise KnowledgeError('AUTHENTICATION_REQUIRED')
    with committed_view() as cur:r,roles,_=_connection(cur,proof['connection_ref'],cfg)
    generation=hmac.new(cfg['proof_key'].encode(),canonical([r['name'],r['token_hash'],r['security_version']]).encode(),hashlib.sha256).hexdigest()
    ref=hmac.new(cfg['proof_key'].encode(),canonical([cfg['site'],cfg['run_id'],r['name'],generation,AUDIENCE]).encode(),hashlib.sha256).hexdigest()
    if (r['owner_user']!=actor.user_ref or not actor.enabled or not hmac.compare_digest(ref,actor.session_ref)
            or not hmac.compare_digest(generation,actor.session_revision) or generation!=proof['generation']):
        raise KnowledgeError('AUTHENTICATION_REQUIRED')
    return ActorState(actor,roles,True)

def create(runtime,label,client_name):
    import frappe
    from .shared_reference import configuration
    cfg=configuration();actor=runtime.actor();runtime.provider._current(actor,runtime.client)
    if client_name not in {'OpenClaw','Hermes'}:raise KnowledgeError('INVALID_REQUEST')
    label=safe_string(label or client_name,80).strip()
    if not label:raise KnowledgeError('INVALID_REQUEST')
    # Serialize the per-owner active-connection cap across native requests.
    frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE',(actor.user_ref,))
    active=frappe.db.count(DOCTYPE,{'owner_user':actor.user_ref,'revoked':0,'expires_at':['>',datetime.now(timezone.utc).replace(tzinfo=None)]})
    if active>=8:raise KnowledgeError('RATE_LIMITED')
    name=secrets.token_hex(16);secret=secrets.token_urlsafe(32)
    expires=datetime.fromtimestamp(time.time()+7*86400,timezone.utc).replace(tzinfo=None)
    from .frappe_authority import committed_view
    with committed_view() as cur:_,version=_user(cur,actor.user_ref,cfg)
    frappe.get_doc({'doctype':DOCTYPE,'connection_id':name,'owner_user':actor.user_ref,'label':label,
        'client_name':client_name,'token_hash':hashlib.sha256(secret.encode()).hexdigest(),'security_version':version,
        'audience':AUDIENCE,'expires_at':expires,'revoked':0,'stage':'Configured'}).insert(ignore_permissions=True)
    runtime.provider._current(actor,runtime.client)
    return {'id':name,'token':'hbos_mcp_'+name+'.'+secret,'expires_at':expires.isoformat()+'Z',
            'auth_type':'PERSONAL_BEARER_TOKEN','tools':list(TOOLS)}

def list_owned(runtime):
    import frappe
    actor=runtime.actor();runtime.provider._current(actor,runtime.client)
    rows=frappe.get_all(DOCTYPE,filters={'owner_user':actor.user_ref},fields=['name','label','client_name','expires_at','revoked','last_used_at','stage'],order_by='creation desc',limit_page_length=50)
    return {'items':[{'id':r.name,'label':safe_string(r.label,80),'client':r.client_name,
        'expires_at':r.expires_at.isoformat()+'Z','revoked':bool(r.revoked),'expired':r.expires_at<=datetime.now(timezone.utc).replace(tzinfo=None),
        'last_used_at':r.last_used_at.isoformat()+'Z' if r.last_used_at else None,'stage':r.stage} for r in rows],
        'tools':list(TOOLS),'auth_type':'PERSONAL_BEARER_TOKEN','ttl_days':7,
        'portal_logout_revokes_connection':False,'deployment':'LOCAL_UAT',
        'query_blocked':__import__(__package__+'.api',fromlist=['_availability'])._availability(runtime).get('blocked',True),
        'endpoint':cfg_endpoint(),'client_versions':configuration_metadata('versions'),
        'client_verification':configuration_metadata('verification')}

def configuration_metadata(field):
    from .shared_reference import configuration
    value=configuration().get('mcp_client_validation',{}).get(field,{})
    allowed={'VERIFIED_TOOLS_ONLY_QUERY_BLOCKED','VERIFIED_QUERY_AND_SOURCE_BEFORE_BUDGET_STOP','PENDING_REAL_CLIENT_TEST'}
    return {client:safe_string(value.get(client,'PENDING_REAL_CLIENT_TEST' if field=='verification' else '未验证'),80)
            if field!='verification' or value.get(client) in allowed else 'PENDING_REAL_CLIENT_TEST'
            for client in ('OpenClaw','Hermes')}

def cfg_endpoint():
    from .shared_reference import configuration
    value=configuration().get('mcp_public_url')
    if not value:raise KnowledgeError('POLICY_UNAVAILABLE')
    return value

def revoke(runtime,name):
    import frappe
    actor=runtime.actor();runtime.provider._current(actor,runtime.client)
    if not isinstance(name,str) or not re.fullmatch(r'[0-9a-f]{32}',name):raise KnowledgeError('INVALID_REQUEST')
    records=frappe.db.sql('SELECT name FROM `tabHBOS Knowledge Connection` WHERE name=%s AND owner_user=%s FOR UPDATE',(name,actor.user_ref))
    if len(records)!=1:raise KnowledgeError('AUTHENTICATION_REQUIRED')
    frappe.db.set_value(DOCTYPE,name,{'revoked':1,'stage':'Revoked'})
    return {'revoked':True}

def observe(name,stage):
    import frappe
    stages={'Authenticated':1,'Tools Discovered':2,'Knowledge Used':3}
    if stage not in stages:raise KnowledgeError('INVALID_REQUEST')
    rows=frappe.db.sql('SELECT stage,revoked FROM `tabHBOS Knowledge Connection` WHERE name=%s FOR UPDATE',(name,),as_dict=True)
    if len(rows)!=1 or rows[0]['revoked']:raise KnowledgeError('AUTHENTICATION_REQUIRED')
    current=rows[0]['stage'];new=stage if stages.get(current,0)<stages[stage] else current
    frappe.db.set_value(DOCTYPE,name,{'stage':new,'last_used_at':datetime.now(timezone.utc).replace(tzinfo=None)})
