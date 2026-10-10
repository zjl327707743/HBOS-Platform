"""DB/Redis compensation protocol. A DB row alone never makes a handle readable."""
from __future__ import annotations
import json, hashlib, hmac, time, secrets
from dataclasses import asdict
from .errors import KnowledgeError
from .execution_plan import Actor, Client, Binding
from .repositories import KnowledgeReference
from .service_http import canonical

ACTIVATE='''
if redis.call('GET',KEYS[1])~=ARGV[1] then return -9 end
for i=2,#KEYS do local v=redis.call('GET',KEYS[i]); if v~=ARGV[2*i-2] then return -1 end end
for i=2,#KEYS do local ttl=redis.call('PTTL',KEYS[i]); if ttl<=0 then return -1 end end
for i=2,#KEYS do local ttl=redis.call('PTTL',KEYS[i]); redis.call('SET',KEYS[i],ARGV[2*i-1],'PX',ttl) end
return 1
'''

class Publication:
    def __init__(self,state,provider,checkpoint):
        self.state,self.provider,self.checkpoint=state,provider,checkpoint
        self.handles=[]; self.references=[]; self.audits=[]; self.plan=None; self.finished=False
        self.publication_id=secrets.token_hex(24)
    def finish(self):
        import frappe
        if not self.references and not self.audits: return
        if self.plan: self.provider.revalidate(self.plan)
        self.checkpoint('db_commit')
        frappe.db.commit()  # Pending DB rows become visible to independent callbacks.
        self.checkpoint('redis_publish')
        for key,payload in self.handles:
            if not self.state.set('handle:'+key,canonical({**payload,'state':'Pending'}),ex=max(1,int(payload['expires_at']-time.time())),nx=True):
                raise KnowledgeError('SERVICE_ERROR')
        for name in self.references: frappe.db.set_value('HBOS Knowledge Reference',name,'publication_state','Active',update_modified=False)
        # Audits remain Prepared; a failure is never pre-counted as SUCCESS.
        frappe.db.commit()
        if self.plan: self.provider.revalidate(self.plan)
        if self.handles:
            keys=[]; args=[]
            for key,payload in self.handles:
                keys.append('handle:'+key)
                args += [canonical({**payload,'state':'Pending'}),canonical({**payload,'state':'Active'})]
            if self.state.eval(ACTIVATE,keys,args)!=1: raise KnowledgeError('SERVICE_ERROR')
        if self.plan: self.provider.revalidate(self.plan)
        for name in self.audits: frappe.db.set_value('HBOS Knowledge Audit',name,'publication_state','Complete',update_modified=False)
        frappe.db.commit()
        self.finished=True
    def abort(self):
        import frappe
        # Delete Redis gates first; even an unknown DB commit outcome cannot consume.
        for key,_ in self.handles:
            try: self.state.delete('handle:'+key)
            except Exception: pass  # Redis outage itself fails reads closed.
        try:
            frappe.db.rollback()
            for name in self.references:
                frappe.db.sql('UPDATE `tabHBOS Knowledge Reference` SET publication_state=%s WHERE name=%s',('Aborted',name))
            for name in self.audits:
                frappe.db.sql('UPDATE `tabHBOS Knowledge Audit` SET publication_state=%s WHERE name=%s',('Aborted',name))
            frappe.db.commit()
        except Exception:
            try: frappe.db.rollback()
            except Exception: pass

class HandleCache:
    test_only=False
    def __init__(self,state,publication): self.state,self.publication=state,publication
    def _id(self,key):
        if not key.startswith('hbos:k1c2:knowledge:evidence:'): raise KnowledgeError('EVIDENCE_UNAVAILABLE')
        return key.rsplit(':',1)[1]
    def set_value(self,key,value,**kwargs):
        self.publication.handles.append((self._id(key),value))
    def get_value(self,key,**kwargs):
        raw=self.state.get('handle:'+self._id(key))
        if not raw: return None
        try:
            value=json.loads(raw)
            if value.pop('state',None)!='Active': return None
            return value
        except Exception: return None

class DatabaseReferences:
    test_only=False
    def __init__(self,publication): self.publication=publication
    def put(self,reference):
        import frappe
        if 'private_session' in canonical(asdict(reference)): raise KnowledgeError('SERVICE_ERROR')
        frappe.get_doc({'doctype':'HBOS Knowledge Reference','reference_id':reference.reference_id,
             'actor_key':hashlib.sha256(reference.actor.user_ref.encode()).hexdigest(),
             'reference_json':canonical(asdict(reference)),'publication_state':'Pending',
             'publication_id':self.publication.publication_id,
             'consume_until':reference.expires_at}).insert(ignore_permissions=True)
        self.publication.references.append(reference.reference_id)
    def get(self,ref):
        from .frappe_authority import committed_view,rows
        with committed_view() as cur:
            found=rows(cur,'SELECT r.reference_json,r.publication_state FROM `tabHBOS Knowledge Reference` r '
                  'WHERE r.name=%s AND EXISTS (SELECT 1 FROM `tabHBOS Knowledge Audit` a '
                  'WHERE a.publication_id=r.publication_id AND a.publication_state=%s)',(ref,'Complete'))
        if not found or found[0]['publication_state']!='Active': return None
        try:
            raw=json.loads(found[0]['reference_json'])
            raw['actor']=Actor(**raw['actor']); raw['client']=Client(**raw['client']); raw['binding']=Binding(**raw['binding'])
            return KnowledgeReference(**raw)
        except Exception: raise KnowledgeError('EVIDENCE_UNAVAILABLE') from None

class DatabaseAudit:
    test_only=False
    def __init__(self,publication,key): self.publication,self.key=publication,key
    def record(self,subject,operation,code,count=0):
        import frappe
        if operation not in {'search','evidence','ask','restore','contract'} or type(count) is not int: raise KnowledgeError('SERVICE_ERROR')
        self.publication.checkpoint('audit_write')
        row=frappe.get_doc({'doctype':'HBOS Knowledge Audit',
           'actor_key':hmac.new(self.key.encode(),subject.encode(),hashlib.sha256).hexdigest()[:24],
           'operation':operation,'code':'AUTHORIZED_PUBLICATION' if code=='SUCCESS' else code,
           'publication_id':self.publication.publication_id,
           'result_count':count,'publication_state':'Prepared'}).insert(ignore_permissions=True)
        self.publication.audits.append(row.name)
