"""Redis state has no process-local fallback and a mandatory recovery sentinel."""
from __future__ import annotations
import hashlib, hmac, json, secrets, time
from .errors import KnowledgeError
from .service_http import canonical
from .decision_store import DecisionTicket
from .execution_plan import plan_from_wire, iso, timestamp
from .r1_contract import normalize_search, CONTRACT_VERSION
from .internal_contract import InternalResponse, PHASES

class RedisState:
    test_only=False
    def __init__(self, client, prefix, run_id):
        self.client,self.prefix,self.run_id=client,prefix,run_id
    def key(self,key): return self.prefix+key
    def ready(self):
        try:
            if self.client.get(self.key('ready')) != self.run_id:
                raise KnowledgeError('POLICY_UNAVAILABLE')
        except KnowledgeError: raise
        except Exception: raise KnowledgeError('POLICY_UNAVAILABLE') from None
    def get(self,key):
        self.ready()
        try: return self.client.get(self.key(key))
        except Exception: raise KnowledgeError('POLICY_UNAVAILABLE') from None
    def set(self,key,value,**kwargs):
        self.ready()
        try: return self.client.set(self.key(key),value,**kwargs)
        except Exception: raise KnowledgeError('POLICY_UNAVAILABLE') from None
    def delete(self,*keys):
        self.ready()
        try: return self.client.delete(*[self.key(k) for k in keys])
        except Exception: raise KnowledgeError('POLICY_UNAVAILABLE') from None
    def eval(self,script,keys,args):
        try:
            value=self.client.eval(script,len(keys)+1,self.key('ready'),*[self.key(k) for k in keys],self.run_id,*args)
            if value == -9: raise KnowledgeError('POLICY_UNAVAILABLE')
            return value
        except KnowledgeError: raise
        except Exception: raise KnowledgeError('POLICY_UNAVAILABLE') from None

REQUEST_LUA='''
if redis.call('GET',KEYS[1])~=ARGV[1] then return -9 end
local lim=tonumber(ARGV[4]); if not lim or lim<1 or lim>12 then return -4 end
local old=redis.call('GET',KEYS[3]); if old then
 if old~=ARGV[3] then return -2 end; return 0 end
local now=redis.call('TIME'); local ms=now[1]*1000+math.floor(now[2]/1000)
redis.call('ZREMRANGEBYSCORE',KEYS[2],'-inf',ms-60000)
if redis.call('ZCARD',KEYS[2])>=lim then return -1 end
redis.call('ZADD',KEYS[2],ms,ARGV[2]); redis.call('PEXPIRE',KEYS[2],61000)
redis.call('SET',KEYS[3],ARGV[3],'EX',600); return 1
'''
OUTPUT_LUA='''
if redis.call('GET',KEYS[1])~=ARGV[1] then return -9 end
local cost=tonumber(ARGV[2]); local lim=tonumber(ARGV[3])
if not cost or cost<0 or cost~=math.floor(cost) or not lim or lim>5000 then return -4 end
local now=redis.call('TIME'); local ms=now[1]*1000+math.floor(now[2]/1000)
redis.call('ZREMRANGEBYSCORE',KEYS[2],'-inf',ms-60000)
local total=0; local values=redis.call('ZRANGE',KEYS[2],0,-1)
for _,v in ipairs(values) do total=total+tonumber(string.match(v,':(%d+)$')) end
if total+cost>lim then return -1 end
redis.call('ZADD',KEYS[2],ms,ARGV[4]..':'..cost); redis.call('PEXPIRE',KEYS[2],61000); return total+cost
'''

class RedisQuota:
    test_only=False
    def __init__(self,state,key): self.state,self.key=state,key
    def subject(self,user): return hmac.new(self.key.encode(),user.encode(),hashlib.sha256).hexdigest()
    def reserve_request(self,subject,request_id,fingerprint,*,limit=12):
        user=self.subject(subject)
        identity=hashlib.sha256(request_id.encode()).hexdigest()
        result=self.state.eval(REQUEST_LUA,['quota:req:'+user,'quota:idem:'+user+':'+identity],
                              [identity,fingerprint,limit])
        if result==-1: raise KnowledgeError('RATE_LIMITED')
        if result==-2: raise KnowledgeError('REPLAY_REJECTED')
        if result==-4: raise KnowledgeError('INVALID_REQUEST')
    def reserve_output(self,subject,codepoints,*,limit=5000):
        if type(codepoints) is not int or codepoints<0: raise KnowledgeError('INVALID_REQUEST')
        result=self.state.eval(OUTPUT_LUA,['quota:chars:'+self.subject(subject)],
                               [codepoints,limit,secrets.token_hex(16)])
        if result==-1: raise KnowledgeError('EXTRACTION_LIMITED')
        if result==-4: raise KnowledgeError('INVALID_REQUEST')

ISSUE_LUA='''
if redis.call('GET',KEYS[1])~=ARGV[1] then return -9 end
local old=redis.call('GET',KEYS[2]); if old then return old end
redis.call('SET',KEYS[2],ARGV[2],'EX',600)
redis.call('SET',KEYS[3],ARGV[3],'EX',120)
return ARGV[2]
'''
PHASE_LUA='''
if redis.call('GET',KEYS[1])~=ARGV[1] then return -9 end
if redis.call('EXISTS',KEYS[2])==0 then return -1 end
local p=ARGV[2]; local function has(x) return redis.call('SISMEMBER',KEYS[3],x)==1 end
local allowed=p=='introspect' or
 ((p=='cache_read' or p=='pre_retrieval' or p=='evidence_read') and has('introspect')) or
 (p=='post_retrieval' and has('pre_retrieval')) or
 (p=='pre_projection' and (has('post_retrieval') or has('cache_read'))) or
 (p=='pre_issue' and has('pre_projection')) or
 (p=='final_publish' and (has('pre_projection') or has('pre_issue') or has('evidence_read')))
if not allowed then return -2 end
redis.call('SADD',KEYS[3],p)
redis.call('EXPIREAT',KEYS[3],ARGV[3]); return 1
'''

class RedisDecisions:
    test_only=False
    clock=staticmethod(time.time)
    def __init__(self,provider,quota,state,key,deadline_seconds=12):
        if type(deadline_seconds) is not int or not 1<=deadline_seconds<=90:raise KnowledgeError("POLICY_UNAVAILABLE")
        self.deadline_seconds=deadline_seconds
        self.provider,self.quota,self.state,self.key=provider,quota,state,key
    def fingerprint(self,request):
        return hmac.new(self.key.encode(),canonical(request.to_wire()).encode(),hashlib.sha256).hexdigest()
    def _read(self,ref):
        value=self.state.get('decision:'+ref)
        if not value: raise KnowledgeError('DECISION_EXPIRED')
        try:
            row=json.loads(value); plan=plan_from_wire(row['plan'],now=time.time())
            ticket=DecisionTicket(ref,plan,normalize_search(row['request']),row['fingerprint'],row['digest'],row['deadline'])
            if time.time()>=timestamp(ticket.deadline_at): raise KnowledgeError('DECISION_EXPIRED')
            return ticket
        except KnowledgeError: raise
        except Exception: raise KnowledgeError('POLICY_UNAVAILABLE') from None
    def issue(self,actor,client,action,request,request_id):
        if not isinstance(request_id,str) or not 1<=len(request_id)<=128: raise KnowledgeError('INVALID_REQUEST')
        fp=self.fingerprint(request)
        identity=canonical([actor.user_ref,actor.session_ref,client.client_id,action,request_id])
        ik=hmac.new(self.key.encode(),identity.encode(),hashlib.sha256).hexdigest()
        prior=self.state.get('identity:'+ik)
        if prior:
            ticket=self._read(prior)
            if fp!=ticket.request_fingerprint: raise KnowledgeError('REPLAY_REJECTED')
            self.provider.revalidate(ticket.plan)
            return ticket
        plan=self.provider.evaluate(actor,client,action,request,request_id)
        self.quota.reserve_request(actor.user_ref,request_id,action+':'+fp+':'+actor.session_ref+':'+client.client_id)
        digest=hashlib.sha256(json.dumps(plan.to_wire(),sort_keys=True,ensure_ascii=True).encode()).hexdigest()
        ref=secrets.token_urlsafe(32)
        row=canonical({'plan':plan.to_wire(),'request':request.to_wire(),'fingerprint':fp,'digest':digest,
                       'deadline':iso(min(time.time()+self.deadline_seconds,timestamp(plan.expires_at)))})
        selected=self.state.eval(ISSUE_LUA,['identity:'+ik,'decision:'+ref],[ref,row])
        ticket=self._read(selected)
        if fp!=ticket.request_fingerprint: raise KnowledgeError('REPLAY_REJECTED')
        self.provider.revalidate(ticket.plan)
        return ticket
    def verify_request(self,ref,request):
        if self._read(ref).request_fingerprint!=self.fingerprint(request): raise KnowledgeError('REPLAY_REJECTED')
    def online(self,principal,call):
        if not principal.authenticated: raise KnowledgeError('CLIENT_AUTH_FAILED')
        if call.contract_version!=CONTRACT_VERSION or call.phase not in PHASES: raise KnowledgeError('INVALID_REQUEST')
        ticket=self._read(call.decision_ref); plan=ticket.plan
        if principal.client!=plan.client: raise KnowledgeError('CLIENT_AUTH_FAILED')
        if (call.request_id,call.action,call.request_fingerprint,call.plan_digest,call.deadline_at)!=(
             plan.request_id,plan.action,ticket.request_fingerprint,ticket.plan_digest,ticket.deadline_at):
            raise KnowledgeError('REPLAY_REJECTED')
        expected={'introspect':'introspect','cache_read':'introspect','pre_issue':'authorize-evidence',
                  'evidence_read':'authorize-evidence'} .get(call.phase,'revalidate')
        if call.operation!=expected: raise KnowledgeError('INVALID_REQUEST')
        if expected=='authorize-evidence' and not call.references: raise KnowledgeError('EMPTY_SCOPE')
        authorized={(b.binding_ref,b.version_id) for b in plan.bindings}
        if any((p.binding_ref,p.version_id) not in authorized or not p.chunk_id or len(p.chunk_id)>128 for p in call.references):
            raise KnowledgeError('SCOPE_REJECTED')
        self.provider.revalidate(plan)  # Short fresh DB read; never under a Redis lock.
        result=self.state.eval(PHASE_LUA,['decision:'+call.decision_ref,'phases:'+call.decision_ref],
                               [call.phase,int(timestamp(plan.expires_at))])
        if result==-1: raise KnowledgeError('DECISION_EXPIRED')
        if result==-2: raise KnowledgeError('INVALID_REQUEST')
        return InternalResponse(CONTRACT_VERSION,'ALLOWED',plan.request_id,call.phase,ticket.plan_digest,ticket.deadline_at,plan=plan)
    def respond(self,principal,call):
        try: return self.online(principal,call)
        except KnowledgeError as e:
            return InternalResponse(CONTRACT_VERSION,'UNAVAILABLE' if e.status==503 else 'DENIED',
                     call.request_id,call.phase,None,None,error_code=e.code)
