"""Signed private controller port; no credentials or physical IDs in employee DTOs."""
import hashlib,json,secrets,time
import frappe
from .errors import KnowledgeError
from .frappe_factory import _service_request,_authority_envelope,configuration
from .service_http import canonical
from . import maintenance as m

DEFAULT_LEASE_SECONDS = 1800
MIN_LEASE_SECONDS = 5
MAX_LEASE_SECONDS = 86400


def lease_seconds(cfg):
    """Controller lease length, configurable for drills and slow parsers.

    The default stays the historical 30 minutes. A deployment may set
    ``maintenance_lease_seconds`` (5..86400) in the private reference config;
    the claim and the Running-progress renewal read the same bound. Invalid
    values fall back to the default instead of shortening the lease silently.
    """
    value = (cfg or {}).get('maintenance_lease_seconds', DEFAULT_LEASE_SECONDS)
    if type(value) is not int or not MIN_LEASE_SECONDS <= value <= MAX_LEASE_SECONDS:
        return DEFAULT_LEASE_SECONDS
    return value


@frappe.whitelist(allow_guest=True,methods=['POST'])
def controller(**ignored):
    def run():
        raw,principal,_=_service_request(max_body=4*1048576);cfg=configuration()
        if principal.client.client_id!=cfg['portal_client_id']:raise KnowledgeError('CLIENT_AUTH_FAILED')
        action=raw.get('action')
        if action=='register' and set(raw)=={'action','frozen','state','label','approval_ref'}:
            if not raw['approval_ref'] or raw['approval_ref']!=raw['frozen'].get('approval_ref'):raise KnowledgeError('INVALID_REQUEST')
            result={'batch_id':m.register_batch(raw['frozen'],raw['state'],raw['label'],cfg['maintenance_coordinator_user'])}
        elif action=='update' and set(raw)=={'action','batch_id','state'}:
            row,frozen,old=m._row(raw['batch_id'],True)
            if m._json(row,'job_json',{}).get('status')=='Running':raise KnowledgeError('IMPORT_BUSY')
            m.registered(frozen,raw['state']);frappe.db.set_value(m.TABLE,row['name'],'state_json',canonical(raw['state']));result={'updated':True}
        elif action=='claim' and set(raw)=={'action'}:
            # Bounded sweep first: only a Running batch whose own lease has
            # already expired is requeued, and only that row is touched. A live
            # Running batch is never reset here.
            from .maintenance_batch import reclaim_expired
            reclaimed=reclaim_expired(actor=cfg['maintenance_coordinator_user'],reason='LEASE_EXPIRED')
            rows=frappe.db.sql('SELECT name FROM `tabHBOS Knowledge Import Batch` WHERE status=%s ORDER BY modified ASC LIMIT 1 FOR UPDATE',('Queued',),as_dict=True)
            if not rows:return {'job':None,'reclaimed':len(reclaimed)}
            row,frozen,state=m._row(rows[0]['name'],True);job=m._json(row,'job_json',{})
            if job.get('status')!='Queued':raise KnowledgeError('IMPORT_BUSY')
            from .maintenance_access import permitted
            if not permitted(job.get('requested_by')):
                job['status']='Blocked'
                frappe.db.set_value(m.TABLE,row['name'],{'job_json':canonical(job),'status':'Blocked','last_error':'RECONCILIATION_REQUIRED'})
                frappe.db.commit();return {'job':None,'reclaimed':len(reclaimed)}
            generation=int(job.get('lease_generation') or 0)+1;now=time.time()
            job.update(status='Running',nonce=secrets.token_hex(24),lease_expires_at=now+lease_seconds(cfg),
                lease_generation=generation,claimed_at=now,pause_requested=False,
                holder_hash=hashlib.sha256(canonical([cfg['maintenance_coordinator_user'],
                    row['name'],generation]).encode('utf-8')).hexdigest()[:16])
            frappe.db.set_value(m.TABLE,row['name'],{'job_json':canonical(job),'status':'Running'})
            result={'batch_id':row['name'],'job':job,'frozen':frozen,'state':state,
                'reclaimed':len(reclaimed)}
        elif action=='progress' and ({'action','batch_id','job_id','nonce','state','outcome','error'}<=set(raw)
                and set(raw)<={'action','batch_id','job_id','nonce','state','outcome','error','lease_generation'}):
            row,frozen,old=m._row(raw['batch_id'],True);job=m._json(row,'job_json',{})
            if job.get('id')!=raw['job_id'] or job.get('nonce')!=raw['nonce'] or job.get('status')!='Running' or job.get('lease_expires_at',0)<time.time():raise KnowledgeError('IMPORT_BUSY')
            # Fence: a worker that lost its lease (reclaim bumped the
            # generation) must never write into the reclaimed batch. Rows claimed
            # before the fence existed have no generation and keep the legacy
            # nonce+lease check only.
            if 'lease_generation' in job:
                supplied=raw.get('lease_generation')
                if type(supplied) is not int or supplied!=job['lease_generation']:raise KnowledgeError('IMPORT_BUSY')
            m.registered(frozen,raw['state'])
            if raw['outcome'] not in ('Running','Completed','Blocked','Failed'):raise KnowledgeError('INVALID_REQUEST')
            # Only the explicitly claimed group may change; previous successful
            # items and every other item must remain byte-for-byte unchanged.
            selected=set(job['document_ids'])
            for before,after in zip(old['items'],raw['state']['items']):
                if before['canonical_document_id'] not in selected and before!=after:raise KnowledgeError('INVALID_REQUEST')
            job['status']=raw['outcome']
            # The lease was set once at claim, so a parse that outlived it could
            # never report again and the batch stayed Running forever. Progress
            # while still Running renews it by the same 30 minutes; a terminal
            # outcome keeps the original lease so nothing looks live afterwards.
            if raw['outcome']=='Running':job['lease_expires_at']=time.time()+lease_seconds(cfg)
            else:job['nonce']=None
            safe=raw['error'] if raw['error'] in ('BUDGET_BLOCKED','PARSE_FAILED','SOURCE_CHANGED','EXECUTOR_STOPPED','RECONCILIATION_REQUIRED','PAUSED_BY_MAINTAINER') else None
            frappe.db.set_value(m.TABLE,row['name'],{'state_json':canonical(raw['state']),'job_json':canonical(job),'status':raw['outcome'],'last_error':safe})
            result={'updated':True}
            if job.get('pause_requested'):result['pause_requested']=True
        else:raise KnowledgeError('INVALID_REQUEST')
        frappe.db.commit();return result
    return _authority_envelope(run)
