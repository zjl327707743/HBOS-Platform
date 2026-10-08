"""Real request composition; this module never imports fixtures or a Harness."""
from __future__ import annotations
import os, time, json
import redis
from .frappe_authority import configuration, SessionProofs, FrappePairedAuthority
from .shared_state import RedisState, RedisQuota, RedisDecisions
from .persistent_publication import Publication, HandleCache, DatabaseReferences, DatabaseAudit
from .policy_provider import LegacyHbosPolicyProvider
from .runtime import CandidateRuntime
from .execution_plan import Client, ServicePrincipal
from .gateway import search_body, EvidenceRecord
from .service_http import SignedHttp, authenticate, MAX_BODY
from .errors import KnowledgeError
from .internal_contract import InternalRequest
from .r1_contract import normalize_search, validate_structure

def setup_request():
    import frappe
    path=getattr(getattr(frappe.local,'request',None),'path','')
    if '/hb_knowledge_app.hb_knowledge.' in path:
        frappe.flags.disable_traceback=True
        frappe.local.response_headers['Cache-Control']='private, no-store, max-age=0'

def components():
    cfg=configuration()
    state=RedisState(redis.Redis.from_url(cfg['redis_url'],decode_responses=True,
                      socket_connect_timeout=2,socket_timeout=2),cfg['prefix'],cfg['run_id'])
    state.ready()
    proofs=SessionProofs(state,cfg)
    if cfg.get('profile')=='INTERNAL_SHARED_REFERENCE':
        from .shared_reference import InternalSharedAuthority, InternalSharedReferenceProvider
        provider=InternalSharedReferenceProvider(InternalSharedAuthority(proofs,cfg),environment='production')
    else:
        provider=LegacyHbosPolicyProvider(FrappePairedAuthority(proofs,cfg),environment='synthetic')
    quota=RedisQuota(state,cfg['fingerprint_key'])
    decisions=RedisDecisions(provider,quota,state,cfg['fingerprint_key'],deadline_seconds=cfg.get('decision_deadline_seconds',12))
    return cfg,state,proofs,provider,quota,decisions

class HttpGateway:
    test_only=True  # Synthetic transport stays explicitly marked.
    configured=True
    def __init__(self,cfg):
        self.profile=cfg['environment']
        self.http=SignedHttp(cfg['gateway_url'],cfg['bff_key'],'hbos-bff')
    def search(self,*,ticket):
        raw=self.http.post('/v1/knowledge/search',search_body(ticket),ticket.plan.client.client_id)
        if not isinstance(raw,dict) or set(raw)!={'status','results'} or raw['status']!='SUCCESS' or not isinstance(raw['results'],list) or len(raw['results'])>5:
            raise KnowledgeError('UPSTREAM_INVALID_RESULT')
        selected={b.binding_ref:b for b in ticket.plan.bindings}; result=[]
        from knowledge_service.hbos_gateway.response_projection import public_evidence
        for fragment in raw['results']:
            if not isinstance(fragment,dict) or set(fragment)!={'binding_ref','version_id','chunk_id','excerpt','page_number','score'}:
                raise KnowledgeError('UPSTREAM_INVALID_RESULT')
            b=selected.get(fragment['binding_ref'])
            if not b or b.version_id!=fragment['version_id'] or not isinstance(fragment['chunk_id'],str):
                raise KnowledgeError('UPSTREAM_SCOPE_VIOLATION')
            record=EvidenceRecord(b.canonical_document_id,b.title,b.business_version,
                 'SYNTHETIC_ONLY' if b.source_type=='SYNTHETIC_TEST' else '内部参考／有效性待核' if b.authority_status=='CONTROLLED_REFERENCE_REVIEWED' else b.authority_status,
                 b.section,fragment['page_number'],fragment['excerpt'],fragment['chunk_id'],b.dataset_alias,
                 b.space_id,b.version_id,b.binding_ref,b)
            public_evidence(record,'CHECK_PROJECTION',environment=cfg_environment(self))
            result.append(record)
        return result
    def authorize_evidence(self,ticket,records,*,phase):
        from .internal_contract import ReferenceProof
        call=ticket.call('authorize-evidence',phase,tuple(ReferenceProof(r.binding_ref,r.version_id,r.chunk_id) for r in records))
        raw=self.http.post('/v1/knowledge/authorize-evidence',call.to_wire(),ticket.plan.client.client_id)
        if raw!={'allowed':True,'budget_owner':'HBOS'}: raise KnowledgeError('UPSTREAM_INVALID_RESULT')
        return True

    def ask(self,*,ticket):
        if getattr(self,'profile',None)!='production':raise KnowledgeError('MODEL_NOT_APPROVED')
        raw=self.http.post('/v1/knowledge/ask',search_body(ticket),ticket.plan.client.client_id)
        if not isinstance(raw,dict) or set(raw)!={'status','answer','labels','results'} or raw['status']!='SUCCESS':raise KnowledgeError('UPSTREAM_INVALID_RESULT')
        from .public_strings import safe_string
        answer=safe_string(raw['answer'],1500)
        if not isinstance(raw['labels'],list) or len(set(raw['labels']))!=len(raw['labels']) or not isinstance(raw['results'],list) or len(raw['results'])>5:raise KnowledgeError('UPSTREAM_INVALID_RESULT')
        from knowledge_service.hbos_gateway.response_projection import public_evidence
        records=[];labels=[];selected={b.binding_ref:b for b in ticket.plan.bindings}
        for item in raw['results']:
            if not isinstance(item,dict) or set(item)!={'binding_ref','version_id','chunk_id','excerpt','page_number','score','citation_label'}:raise KnowledgeError('UPSTREAM_INVALID_RESULT')
            b=selected.get(item['binding_ref']);label=item['citation_label']
            if not b or b.version_id!=item['version_id'] or label not in {'C1','C2','C3','C4','C5'} or label in labels:raise KnowledgeError('UPSTREAM_SCOPE_VIOLATION')
            r=EvidenceRecord(b.canonical_document_id,b.title,b.business_version,'内部参考／有效性待核',b.section,item['page_number'],item['excerpt'],item['chunk_id'],b.dataset_alias,b.space_id,b.version_id,b.binding_ref,b)
            public_evidence(r,'ASK_PROJECTION_CHECK',environment='production');records.append(r);labels.append(label)
        if set(labels)!=set(raw['labels']):raise KnowledgeError('UPSTREAM_INVALID_RESULT')
        return answer,labels,records

def cfg_environment(gateway):
    return gateway.profile

class ReferenceHttpGateway(HttpGateway):
    test_only=False
    def __init__(self,cfg):
        if cfg.get('profile')!='INTERNAL_SHARED_REFERENCE' or cfg.get('environment')!='production' or not cfg.get('internal_sharing_approved'):
            raise KnowledgeError('POLICY_UNAVAILABLE')
        super().__init__(cfg)
        self.http.read_timeout=80

def build_runtime(client=None):
    import frappe
    cfg,state,proofs,provider,quota,decisions=components()
    real=cfg.get('profile')=='INTERNAL_SHARED_REFERENCE'
    client=client or Client(cfg['portal_client_id'] if real else 'K1C2_PORTAL')
    clients={Client(cfg['portal_client_id'])} if real else {Client('K1C2_PORTAL'),Client('K1C2_INTERNAL')}
    if client not in clients:
        raise KnowledgeError('CLIENT_AUTH_FAILED')
    def checkpoint(phase):
        # Test faults are owner-controlled Redis entries in the new namespace only.
        if cfg.get('enable_synthetic_faults'):
            if state.get('fault:'+phase)=='fail': raise KnowledgeError('SERVICE_ERROR')
            if state.get('barrier:'+phase)=='armed':
                state.set('barrier:'+phase+':reached','1',ex=20)
                until=time.monotonic()+5
                while state.get('barrier:'+phase)=='armed' and time.monotonic()<until:
                    time.sleep(.02)
                if state.get('barrier:'+phase)=='armed': raise KnowledgeError('SERVICE_ERROR')
    publication=Publication(state,provider,checkpoint)
    runtime=CandidateRuntime('production' if real else 'synthetic',provider,decisions,DatabaseReferences(publication),
         HandleCache(state,publication),ReferenceHttpGateway(cfg) if real else HttpGateway(cfg),quota,DatabaseAudit(publication,cfg['audit_key']),
         lambda:proofs.from_native_request(client),client,checkpoint)
    runtime.publication=publication
    return runtime

def _service_request():
    import frappe
    cfg,state,proofs,provider,quota,decisions=components()
    body=frappe.request.get_data()
    principal=authenticate(frappe.request.headers,body,frappe.request.path,cfg['authority_auth'],state)
    if frappe.request.headers.get('Cookie'):
        raise KnowledgeError('CLIENT_AUTH_FAILED')
    try: payload=json.loads(body)
    except Exception: raise KnowledgeError('INVALID_REQUEST') from None
    return payload,principal,decisions

def _authority_envelope(fn):
    from .errors import error_payload
    try: return {'ok':True,'data':fn()}
    except KnowledgeError as e: return error_payload(e)
    except Exception: return error_payload(KnowledgeError('POLICY_UNAVAILABLE'))

import frappe

@frappe.whitelist(allow_guest=True,methods=['POST'])
def authority_call(**ignored):
    def run():
        raw,principal,decisions=_service_request()
        call=InternalRequest.from_wire(raw)
        response=decisions.respond(principal,call).to_wire()
        validate_structure('InternalDecisionResponse',response)
        return response
    return _authority_envelope(run)

@frappe.whitelist(allow_guest=True,methods=['POST'])
def authority_search(**ignored):
    def run():
        raw,principal,decisions=_service_request()
        validate_structure('InternalSearchCompat',raw)
        if raw['client_id']!=principal.client.client_id: raise KnowledgeError('CLIENT_AUTH_FAILED')
        business={k:v for k,v in raw.items() if k in {'query','limit','space_ids','context'}}
        decisions.verify_request(raw['decision_ref'],normalize_search(business))
        from knowledge_service.hbos_gateway.policy_client import InProcessPolicyClient
        call=InProcessPolicyClient.make_call(raw,'introspect','introspect')
        response=decisions.online(principal,call)
        plan=response.require_plan()
        if (raw['subject']!=plan.subject.user_ref or raw['policy_revision']!=plan.policy_revision
            or set(raw['dataset_ids'])!={b.dataset_alias for b in plan.bindings}
            or set(raw['document_ids'])!={b.canonical_document_id for b in plan.bindings}):
            raise KnowledgeError('SCOPE_REJECTED')
        return response.to_wire()
    return _authority_envelope(run)

@frappe.whitelist(methods=['POST'])
def synthetic_internal_search(query=None,limit=5,**kwargs):
    # Explicit second controlled client for this isolated synthetic Site only.
    # The server chooses the client; body/header declarations cannot select it.
    configuration()
    cmd=kwargs.pop('cmd',None)
    if cmd is not None and cmd!='hb_knowledge_app.hb_knowledge.frappe_factory.synthetic_internal_search':
        raise KnowledgeError('INVALID_REQUEST')
    frappe.local.hbos_knowledge_runtime=build_runtime(Client('K1C2_INTERNAL'))
    from .api import search
    return search(query=query,limit=limit,**kwargs)
