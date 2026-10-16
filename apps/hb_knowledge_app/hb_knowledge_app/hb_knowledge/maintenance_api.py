"""Signed private controller port; no credentials or physical IDs in employee DTOs."""
import json,secrets,time
import frappe
from .errors import KnowledgeError
from .frappe_factory import _service_request,_authority_envelope,configuration
from .service_http import canonical
from . import maintenance as m

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
            rows=frappe.db.sql('SELECT name FROM `tabHBOS Knowledge Import Batch` WHERE status=%s ORDER BY modified ASC LIMIT 1 FOR UPDATE',('Queued',),as_dict=True)
            if not rows:return {'job':None}
            row,frozen,state=m._row(rows[0]['name'],True);job=m._json(row,'job_json',{})
            if job.get('status')!='Queued':raise KnowledgeError('IMPORT_BUSY')
            from .maintenance_access import permitted
            if not permitted(job.get('requested_by')):
                job['status']='Blocked'
                frappe.db.set_value(m.TABLE,row['name'],{'job_json':canonical(job),'status':'Blocked','last_error':'RECONCILIATION_REQUIRED'})
                frappe.db.commit();return {'job':None}
            job.update(status='Running',nonce=secrets.token_hex(24),lease_expires_at=time.time()+1800)
            frappe.db.set_value(m.TABLE,row['name'],{'job_json':canonical(job),'status':'Running'})
            result={'batch_id':row['name'],'job':job,'frozen':frozen,'state':state}
        elif action=='progress' and set(raw)=={'action','batch_id','job_id','nonce','state','outcome','error'}:
            row,frozen,old=m._row(raw['batch_id'],True);job=m._json(row,'job_json',{})
            if job.get('id')!=raw['job_id'] or job.get('nonce')!=raw['nonce'] or job.get('status')!='Running' or job.get('lease_expires_at',0)<time.time():raise KnowledgeError('IMPORT_BUSY')
            m.registered(frozen,raw['state'])
            if raw['outcome'] not in ('Running','Completed','Blocked','Failed'):raise KnowledgeError('INVALID_REQUEST')
            # Only the explicitly claimed group may change; previous successful
            # items and every other item must remain byte-for-byte unchanged.
            selected=set(job['document_ids'])
            for before,after in zip(old['items'],raw['state']['items']):
                if before['canonical_document_id'] not in selected and before!=after:raise KnowledgeError('INVALID_REQUEST')
            job['status']=raw['outcome']
            safe=raw['error'] if raw['error'] in ('BUDGET_BLOCKED','PARSE_FAILED','SOURCE_CHANGED','EXECUTOR_STOPPED','RECONCILIATION_REQUIRED') else None
            frappe.db.set_value(m.TABLE,row['name'],{'state_json':canonical(raw['state']),'job_json':canonical(job),'status':raw['outcome'],'last_error':safe})
            result={'updated':True}
        else:raise KnowledgeError('INVALID_REQUEST')
        frappe.db.commit();return result
    return _authority_envelope(run)
