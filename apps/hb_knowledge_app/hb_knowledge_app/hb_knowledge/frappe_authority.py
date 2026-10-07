"""HBOS-owned native-session resolver and fresh committed authority snapshots."""
from __future__ import annotations
import hashlib, hmac, json, os, time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import pymysql
from cryptography.fernet import Fernet
from .errors import KnowledgeError
from .execution_plan import Actor, Binding, Client, GrantPair, ProviderStamp, timestamp
from .repositories import ActorState, AuthoritySnapshot
from .service_http import canonical
from .metadata_integrity import binding_from_row

def configuration():
    import frappe
    site, run = os.environ.get('HBOS_K1C2_SITE'), os.environ.get('HBOS_K1C2_RUN_ID')
    if (not site or not run or frappe.local.site != site or not frappe.conf.get('hbos_k1c2_enabled')
        or frappe.conf.get('hbos_k1c2_run_id') != run or frappe.conf.get('ignore_csrf')):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    value=json.loads(Path('/run/k1c2/hbos.json').read_text())
    if value['site']!=site or value['run_id']!=run or value['environment']!='synthetic':
        raise KnowledgeError('POLICY_UNAVAILABLE')
    return value

@contextmanager
def committed_view():
    import frappe
    conn=None
    try:
        if frappe.conf.db_host!='db': raise KnowledgeError('POLICY_UNAVAILABLE')
        conn=pymysql.connect(host='db',port=3306,user=frappe.conf.get('db_user') or frappe.conf.db_name,
             password=frappe.conf.db_password,database=frappe.conf.db_name,
             connect_timeout=2,read_timeout=3,write_timeout=3,autocommit=False,
             cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            # A NEW short consistent snapshot each time, independent of the outer POST.
            cur.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            cur.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY')
            yield cur
        conn.rollback()
    except KnowledgeError: raise
    except Exception: raise KnowledgeError('POLICY_UNAVAILABLE') from None
    finally:
        if conn: conn.close()

def rows(cur,sql,args=()):
    cur.execute(sql,args); return cur.fetchall()

class SessionProofs:
    test_only=False
    def __init__(self,state,config): self.state,self.config=state,config
    def _native(self,cur,sid,user):
        from frappe.sessions import get_expiry_in_seconds
        from hbos_portal.services.internal_users import classify_internal_user
        sessions=rows(cur,'SELECT user,sessiondata,lastupdate,status FROM `tabSessions` WHERE sid=%s AND user=%s',(sid,user))
        accounts=rows(cur,'SELECT enabled,user_type FROM `tabUser` WHERE name=%s',(user,))
        roles=tuple(sorted(x['role'] for x in rows(cur,'SELECT role FROM `tabHas Role` WHERE parent=%s AND parenttype=%s',(user,'User'))))
        if not sessions or not accounts or sessions[0]['status']!='Active':
            raise KnowledgeError('AUTHENTICATION_REQUIRED')
        data=json.loads(sessions[0]['sessiondata']); account=accounts[0]
        security=rows(cur,'SELECT security_version,blocked FROM `tabHBOS Account Security` WHERE user=%s',(user,))
        version=int(security[0]['security_version']) if security else 0
        if security and (security[0]['blocked'] or int(data.get('hbos_security_version') or 0)!=version):
            raise KnowledgeError('AUTHENTICATION_REQUIRED')
        updated=sessions[0]['lastupdate']
        # Site is explicitly UTC; native DB dates are naive UTC in this synthetic Site.
        if updated.tzinfo is None: updated=updated.replace(tzinfo=timezone.utc)
        expiry=get_expiry_in_seconds(data.get('session_expiry'))
        if time.time()-updated.timestamp()>expiry or (data.get('session_end') and timestamp(data['session_end'])<=time.time()):
            raise KnowledgeError('AUTHENTICATION_REQUIRED')
        if not classify_internal_user(user,account=account,roles=roles,config=self.config.get('internal_user_config',{})).allowed:
            raise KnowledgeError('AUTHENTICATION_REQUIRED')
        generation=hmac.new(self.config['proof_key'].encode(),canonical([sid,data.get('creation'),version]).encode(),hashlib.sha256).hexdigest()
        return roles,generation
    def from_native_request(self,client):
        import frappe
        user,sid=frappe.session.user,frappe.session.sid
        if not user or user in {'Guest','Administrator'} or sid=='Guest': raise KnowledgeError('AUTHENTICATION_REQUIRED')
        with committed_view() as cur: roles,generation=self._native(cur,sid,user)
        ref=hmac.new(self.config['proof_key'].encode(),canonical([self.config['site'],self.config['run_id'],sid,generation,client.client_id,'knowledge.read']).encode(),hashlib.sha256).hexdigest()
        value={'site':self.config['site'],'instance':self.config['run_id'],'user':user,'generation':generation,
               'client':client.client_id,'purpose':'knowledge.read','expires':time.time()+600,
               'private_session':Fernet(self.config['sid_encryption_key'].encode()).encrypt(sid.encode()).decode()}
        self.state.set('private-proof:'+ref,canonical(value),ex=600,nx=True)
        actor=Actor(user,ref,generation,True)
        self.resolve(actor,client)
        return actor
    def resolve(self,actor,client):
        raw=self.state.get('private-proof:'+actor.session_ref)
        try:
            if not raw: raise ValueError()
            proof=json.loads(raw)
            if (proof['site'],proof['instance'],proof['user'],proof['generation'],proof['client'],proof['purpose']) != (
                 self.config['site'],self.config['run_id'],actor.user_ref,actor.session_revision,client.client_id,'knowledge.read'):
                raise ValueError()
            if time.time()>=proof['expires']: raise ValueError()
            sid=Fernet(self.config['sid_encryption_key'].encode()).decrypt(proof['private_session'].encode()).decode()
            expected=hmac.new(self.config['proof_key'].encode(),canonical([
                self.config['site'],self.config['run_id'],sid,actor.session_revision,
                client.client_id,'knowledge.read']).encode(),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected,actor.session_ref): raise ValueError()
            if actor.session_ref==sid or sid in canonical(actor.__dict__): raise ValueError()
            with committed_view() as cur:
                roles,generation=self._native(cur,sid,actor.user_ref)
            if generation!=actor.session_revision or not actor.enabled: raise ValueError()
            return ActorState(actor,roles,True)
        except KnowledgeError: raise
        except Exception: raise KnowledgeError('AUTHENTICATION_REQUIRED') from None

class FrappePairedAuthority:
    test_only=False
    def __init__(self,proofs,config): self.proofs,self.config=proofs,config
    def read_current(self,actor):
        state=self.proofs.resolve(actor,self.client_for(actor))
        from .policy import policy_for_subject
        policy=policy_for_subject(self.config['legacy_policy'],actor.user_ref,internal_user=True)
        if not policy.can_search: raise KnowledgeError('SCOPE_REJECTED')
        clients=(Client('K1C2_PORTAL'),Client('K1C2_INTERNAL'))
        with committed_view() as cur:
            spaces=rows(cur,'SELECT name,required_role FROM `tabHBOS Knowledge Space` WHERE enabled=1')
            active=tuple(s['name'] for s in spaces)
            grants=tuple(GrantPair(s['required_role'],s['name'],a,'PAIR_'+s['name']+'_'+a.split('.')[-1])
                       for s in spaces for a in ('knowledge.search','knowledge.evidence','knowledge.spaces'))
            data=rows(cur,'SELECT b.*,s.name as space_record_id,s.enabled as space_enabled, '
              'v.name as version_record_id,v.version_id as version_record_identity, '
              'v.canonical_document_id as version_document_id, '
              'd.name as document_record_id,d.document_id as document_record_identity, '
              'd.current_version,d.withdrawn,d.ingestion_status '
              'FROM `tabHBOS Knowledge Backend Binding` b '
              'LEFT JOIN `tabHBOS Knowledge Space` s ON s.name=b.space_id '
              'LEFT JOIN `tabHBOS Knowledge Version` v ON v.name=b.version_id '
              'LEFT JOIN `tabHBOS Knowledge Document` d ON d.name=b.canonical_document_id '
              'WHERE b.enabled=1')
            accepted=[]
            self.rejected_binding_count=0
            for row in data:
                try:
                    accepted.append(binding_from_row(row))
                except KnowledgeError:
                    # Quarantine just this binding. Its retained handle cannot
                    # pass reauthorization; never substitute values from JSON.
                    self.rejected_binding_count+=1
            bindings=tuple(accepted)
        bindings=tuple(b for b in bindings if b.dataset_alias in policy.dataset_ids and b.canonical_document_id in policy.document_ids)
        return AuthoritySnapshot(state,clients,grants,active,bindings,tuple(b.dataset_id for b in bindings),(),
               'k1c2-policy-fixed','k1c2-corpus-fixed',ProviderStamp('HBOS_LEGACY_READONLY','k1c2-bridge-fixed',self.config['lease_until']),
               'SYNTHETIC_NO_EMBEDDING',True)
    def client_for(self,actor):
        raw=self.proofs.state.get('private-proof:'+actor.session_ref)
        if not raw: raise KnowledgeError('AUTHENTICATION_REQUIRED')
        origin=json.loads(raw)['client']
        if origin not in {'K1C2_PORTAL','K1C2_INTERNAL'}: raise KnowledgeError('CLIENT_AUTH_FAILED')
        return Client(origin)
