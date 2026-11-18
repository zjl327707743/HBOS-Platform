"""Browser maintenance projections and batch preflight; no model calls."""
import hashlib
import json
from pathlib import Path
import re
import secrets
import time

import frappe

from .errors import KnowledgeError
from .maintenance_access import require
from .maintenance_contract import DEPARTMENTS, configured_max_source_bytes
from .shared_reference import configuration


def with_workflow(workflow_id,action):
    if workflow_id is not None and (not isinstance(workflow_id,str) or not re.fullmatch('[a-f0-9]{32}',workflow_id)):
        raise KnowledgeError('INVALID_REQUEST')
    frappe.local.hbos_maintenance_workflow_id=workflow_id
    try:return action()
    finally:frappe.local.hbos_maintenance_workflow_id=None


def record_manual_action(batch_id,kind):
    """Count one explicit UI operation across its deterministic file loop."""
    from . import maintenance as m
    row,_,_=m._row(batch_id,True);job=m._json(row,'job_json',{})
    if not job.get('managed_admission'):return
    workflow=getattr(frappe.local,'hbos_maintenance_workflow_id',None)
    request_id=getattr(frappe.local,'hbos_knowledge_request_id',None)
    if not workflow and not request_id:raise KnowledgeError('INVALID_REQUEST')
    operation='ADOPT' if workflow and kind in ('REVIEW','PUBLISH') else kind
    identity=hashlib.sha256(json.dumps([frappe.session.user,workflow or request_id,operation]).encode()).hexdigest()
    events=job.setdefault('manual_events',[])
    if not any(event['id']==identity for event in events):
        events.append({'id':identity,'operation':operation,'at':time.time(),
                       'actor_hash':hashlib.sha256(frappe.session.user.encode()).hexdigest()[:16]})
        frappe.db.set_value(m.TABLE,batch_id,'job_json',m.canonical(job))


def precheck(items, department):
    require()
    if isinstance(items,str):
        try:items=json.loads(items)
        except ValueError:raise KnowledgeError('INVALID_REQUEST') from None
    if department not in DEPARTMENTS or not isinstance(items,list) or not 1<=len(items)<=50:
        raise KnowledgeError('INVALID_REQUEST')
    from .maintenance import _registry
    from .maintenance_batch import _safe_relative_path
    registry=_registry()['documents']
    limit=configured_max_source_bytes(configuration())
    rows=[]
    for index,item in enumerate(items):
        if (not isinstance(item,dict) or set(item)!={'filename','relative_path','source_sha256','bytes'}
                or not isinstance(item['source_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',item['source_sha256'])
                or type(item['bytes']) is not int or not 0<item['bytes']<=limit):
            raise KnowledgeError('INVALID_REQUEST')
        try:relative=_safe_relative_path(item['relative_path'])
        except KnowledgeError:
            rows.append({'index':index,'filename':str(item['filename'])[:240],'relative_path':None,
                         'state':'SOURCE_EXCEPTION','existing_documents':0})
            continue
        if Path(relative).name!=item['filename']:raise KnowledgeError('INVALID_REQUEST')
        matches=[row for row in registry if row.get('sha256')==item['source_sha256'] and row.get('department_key')==department]
        identities={(row['canonical_document_id'],row['version_id']) for row in matches}
        state='DUPLICATE' if len(identities)==1 else 'IDENTITY_REVIEW' if identities else 'NEW'
        rows.append({'index':index,'filename':item['filename'],'relative_path':relative,'state':state,
                     'existing_documents':len(identities)})
    return {'items':rows,'new':sum(row['state']=='NEW' for row in rows),
            'duplicates':sum(row['state']=='DUPLICATE' for row in rows),
            'blocked':sum(row['state'] in ('IDENTITY_REVIEW','SOURCE_EXCEPTION') for row in rows),
            'provider_calls':0,'classification_preserved':True}


def template_catalog():
    require()
    cfg=configuration()
    from .maintenance_native_upload import _profiles
    from .maintenance_managed import public_template
    profiles=_profiles(cfg)
    if profiles is None:raise KnowledgeError('POLICY_UNAVAILABLE')
    policy=cfg.get('maintenance_managed_policy') or {}
    versions=policy.get('implementation_commits',{})
    return {'template_lock_sha256':policy.get('template_lock_sha256'),
            'templates':[{'key':key,'title':title,'implementation_commit':versions.get(profile),
                          **public_template({'native_profile':profiles[profile]})}
                         for key,title,profile in [('text_pdf','文字 PDF / 普通文本','plain'),
                           ('scan_pdf','扫描或混合 PDF','deepdoc'),('office','原生 DOCX','plain')]
                           +([('workbook','原生工作簿','workbook')] if 'workbook' in profiles else [])],
            'actual_implementation_commits':versions,
            'document_defaults_are_not_effective_settings':True}


def pipeline():
    require()
    from . import maintenance as m
    from .maintenance_managed import can_validate_existing_result, queue_kind, safe_resume, should_revalidate
    rows=frappe.db.sql('SELECT name,label,status,last_error,state_json,quality_json,job_json FROM `tabHBOS Knowledge Import Batch` '
        'WHERE LOCATE(%s,job_json)>0 OR LOCATE(%s,job_json)>0 ORDER BY modified DESC LIMIT 1000',
        ('"managed_admission"','"managed_intake"'),as_dict=True)
    records=[];seen=set();available=0;cohorts={};manual={}
    for row in rows:
        state=m._json(row,'state_json',{});quality=m._json(row,'quality_json',{});job=m._json(row,'job_json',{})
        can_revalidate=(job.get('status') in ('Completed','Blocked','Paused') and not job.get('nonce')
                        and can_validate_existing_result(state,job))
        for event in job.get('manual_events') or []:manual[event['id']]=event
        submitted = next((event for event in job.get('manual_events', []) if event['operation']=='SUBMIT'), None)
        cohort = None
        if submitted:
            cohort = cohorts.setdefault(submitted['id'], {'batch_id': submitted['id'],
                'started_at': submitted['at'], 'last_available_at': None, 'ordinary': 0,
                'verified': 0, 'net_available': 0, 'settled': 0})
            cohort['started_at'] = min(cohort['started_at'], submitted['at'])
        for item in state.get('items',[]):
            if item.get('disposition') in ('SAME_CONTENT_SKIP','ALIAS'):continue
            key=(item['canonical_document_id'],item['version_id'])
            if key in seen:continue
            seen.add(key)
            current=frappe.db.get_value('HBOS Knowledge Document',key[0],
                ['current_version','withdrawn','ingestion_status','source_hash'],as_dict=True)
            published=m.is_published_target(item,current) and current['source_hash']==item['sha256']
            automatic=item.get('automatic_quality') or {}
            review=quality.get(key[1]) or {}
            receipt=review.get('retrieval_verified') or {}
            ready=(published and review.get('status')=='Passed' and receipt.get('status')=='VERIFIED'
                   and receipt.get('reader_paths_verified') is True
                   and receipt.get('published_current_version')==key[1])
            available += ready
            queue=automatic.get('queue') or (job.get('managed_admission') or {}).get('queue_kind') or queue_kind(item)
            withdrawn=bool(current and current.get('withdrawn') and current.get('current_version')==key[1])
            superseded=bool(current and current.get('current_version')!=key[1]
                            and item.get('expected_current_version')!=current.get('current_version'))
            unresolved=(job.get('status')=='Running' and (job.get('lease_expires_at') or 0)<time.time() and not safe_resume(state,job))
            revalidating=job.get('operation')=='validate' and job.get('status') in ('Queued','Running')
            status=('WITHDRAWN' if withdrawn else 'SUPERSEDED' if superseded else 'AVAILABLE' if ready else 'PUBLISHED_RETRIEVAL_PENDING' if published
                    else 'RECONCILIATION_REQUIRED' if unresolved
                    else 'REVALIDATING' if revalidating and should_revalidate(item)
                    else 'READY_FOR_ADOPTION' if automatic.get('status')=='AUTO_VERIFIED_PENDING_REVIEW'
                    else 'REPAIR_REQUIRED' if automatic.get('status')=='REPAIR_REQUIRED' or (not job.get('id') and row.get('last_error'))
                    else item['status'])
            if cohort is not None and queue=='ORDINARY':
                cohort['ordinary'] += 1
                if ready:
                    cohort['verified'] += 1
                    cohort['net_available'] += not item.get('expected_current_version')
                    cohort['last_available_at'] = max(cohort['last_available_at'] or 0, receipt['at'])
                cohort['settled'] += status in ('AVAILABLE', 'WITHDRAWN', 'SUPERSEDED',
                    'REPAIR_REQUIRED', 'RECONCILIATION_REQUIRED')
            records.append({'batch_id':row['name'],'document_id':key[0],'version_id':key[1],
                'title':item['title'],'filename':Path(item['relative_path']).name,
                'relative_path':item['relative_path'],'source_sha256':item['sha256'],'queue':queue,'status':status,
                'reasons':automatic.get('reasons') or ([row.get('last_error')] if row.get('last_error') else []),
                'quality_passed':review.get('status')=='Passed','publication_status':'Published' if published else 'Unpublished',
                'samples':(automatic.get('text_check') or {}).get('samples') or [],
                'verification_intent':(job.get('reader_verification_intents') or {}).get(key[1],{}).get('status'),
                'validation_retry':can_revalidate and should_revalidate(item),
                'resume_safe':(can_revalidate and should_revalidate(item)) or (
                    job.get('status') in ('Paused','Blocked','Failed') and not job.get('nonce') and safe_resume(state,job)),
                'expected_version':item.get('expected_current_version'),
                'operation':'replace' if item.get('expected_current_version') else 'publish'})
    recent = sorted((c for c in cohorts.values() if c['ordinary']),
                    key=lambda c:c['started_at'], reverse=True)[:5]
    # Use the contiguous series of settled submission cohorts, including
    # cohorts that yielded zero, so skipped failures cannot inflate the rate.
    contiguous = []
    for cohort in recent:
        if cohort['ordinary'] != cohort['settled']:
            if contiguous:break
            continue
        contiguous.append(cohort)
    finish = max((c['last_available_at'] or c['started_at'] for c in contiguous), default=0)
    elapsed = max(1, finish-min(c['started_at'] for c in contiguous)) if contiguous else 0
    return {'scope':'MANAGED_MAINTENANCE_JOBS','items':records,'total':len(records),
            'normal_remaining':sum(r['queue']=='ORDINARY' and r['status'] not in
                ('AVAILABLE','WITHDRAWN','SUPERSEDED','READY_FOR_ADOPTION','REPAIR_REQUIRED','RECONCILIATION_REQUIRED') for r in records),
            'exceptions':sum(r['queue']=='COMPLEX' or r['status'] in ('REPAIR_REQUIRED','RECONCILIATION_REQUIRED') for r in records),
            'awaiting_adoption':sum(r['status']=='READY_FOR_ADOPTION' for r in records),
            'available':available,'elapsed_seconds':round(elapsed,3),
            'recent_ordinary_batches':recent,
            'net_available_per_hour':round(sum(c['net_available'] for c in contiguous)*3600/elapsed,3) if elapsed else None,
            'batch_count':len(rows),'scan_truncated':len(rows)==1000,
            'human_interventions':len(manual),'manual_actions':list(manual.values()),
            'controller_continues_without_browser':True}


def begin_reader_check(batch_id,document_id,version_id,query_sha256):
    require()
    if not isinstance(query_sha256,str) or not re.fullmatch('[a-f0-9]{64}',query_sha256):
        raise KnowledgeError('INVALID_REQUEST')
    from . import maintenance as m
    row,_,state=m._row(batch_id,True);job=m._json(row,'job_json',{})
    if not job.get('managed_admission'):raise KnowledgeError('INVALID_REQUEST')
    items=[i for i in state['items'] if i['canonical_document_id']==document_id and i['version_id']==version_id]
    if len(items)!=1:raise KnowledgeError('INVALID_REQUEST')
    item,=items
    current=frappe.db.get_value('HBOS Knowledge Document',document_id,
        ['current_version','withdrawn','ingestion_status'],as_dict=True)
    if not m.is_published_target(item,current):raise KnowledgeError('SOURCE_VERSION_STALE')
    review=m._json(row,'quality_json',{}).get(version_id) or {}
    if review.get('status')!='Passed':raise KnowledgeError('QUALITY_REQUIRED')
    if (review.get('retrieval_verified') or {}).get('reader_paths_verified') is True:
        return {'status':'ALREADY_VERIFIED'}
    intents=job.setdefault('reader_verification_intents',{})
    if version_id in intents:
        return {'status':'RECONCILIATION_REQUIRED'}
    publication_id = (review.get('retrieval_verified') or {}).get('publication_receipt_id')
    request_id='R2-MANAGED-READER-'+hashlib.sha256(json.dumps([
        batch_id,document_id,version_id,item['binding_revision'],publication_id,query_sha256]).encode()).hexdigest()[:48]
    intents[version_id]={'status':'INTENT','request_id':request_id,'query_sha256':query_sha256,
        'requested_by':frappe.session.user,'at':time.time(),'binding_revision':item['binding_revision']}
    frappe.db.set_value(m.TABLE,batch_id,'job_json',m.canonical(job));frappe.db.commit()
    return {'status':'READY','request_id':request_id}


def source_ticket(batch_id,document_id):
    require()
    from . import maintenance as m
    _,frozen,state=m._row(batch_id)
    items=[item for item in state['items'] if item['canonical_document_id']==document_id
           and item.get('disposition') not in ('ALIAS','SAME_CONTENT_SKIP')]
    if len(items)!=1:raise KnowledgeError('INVALID_REQUEST')
    item,=items
    from knowledge_service.ingestion import processing_approved
    if not processing_approved(frozen,item):raise KnowledgeError('SCOPE_REJECTED')
    token=secrets.token_urlsafe(32)
    frappe.cache.set_value('hbos-maintenance-source:'+hashlib.sha256(token.encode()).hexdigest(),
        {'user':frappe.session.user,'batch_id':batch_id,'document_id':document_id,
         'version_id':item['version_id'],'source_sha256':item['sha256']},expires_in_sec=300)
    return {'url':'/api/method/hb_knowledge_app.hb_knowledge.api.get_maintenance_source?token='+token,
            'filename':Path(item['relative_path']).name,'expires_in':300}


def source(token):
    require()
    if not isinstance(token,str) or not re.fullmatch('[A-Za-z0-9_-]{40,64}',token):
        raise KnowledgeError('INVALID_REQUEST')
    cached=frappe.cache.get_value('hbos-maintenance-source:'+hashlib.sha256(token.encode()).hexdigest())
    if not isinstance(cached,dict) or cached.get('user')!=frappe.session.user:
        raise KnowledgeError('SCOPE_REJECTED')
    from . import maintenance as m
    _,frozen,state=m._row(cached['batch_id'])
    item,=[item for item in state['items'] if item['canonical_document_id']==cached['document_id']
           and item['version_id']==cached['version_id'] and item['sha256']==cached['source_sha256']
           and item.get('disposition') not in ('ALIAS','SAME_CONTENT_SKIP')]
    from knowledge_service.ingestion import file_digest,processing_approved
    root=Path(frozen['source_root']);path=root/item['relative_path']
    if (not processing_approved(frozen,item) or path.resolve(strict=True)!=path
            or not path.is_relative_to(root) or file_digest(path)!=cached['source_sha256']):
        raise KnowledgeError('SCOPE_REJECTED')
    # Maintenance original inspection is separately authenticated and never
    # serves active HTML. Employee delivery keeps its existing authorization.
    from werkzeug.wrappers import Response
    from werkzeug.wsgi import wrap_file
    from urllib.parse import quote
    content_type='application/pdf' if path.suffix.lower()=='.pdf' else 'application/octet-stream'
    response=Response(wrap_file(frappe.local.request.environ,path.open('rb')),mimetype=content_type,direct_passthrough=True)
    response.content_length=path.stat().st_size
    disposition='inline' if content_type=='application/pdf' else 'attachment'
    response.headers['Content-Disposition']=disposition+"; filename*=UTF-8''"+quote(path.name)
    response.headers['Cache-Control']='private, no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="sandbox; default-src 'none'"
    return response
