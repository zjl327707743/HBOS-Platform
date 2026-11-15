"""Signed private controller port; no credentials or physical IDs in employee DTOs."""
import hashlib,json,math,re,secrets,time
import frappe
from .errors import KnowledgeError
from .frappe_factory import _service_request,_authority_envelope,configuration
from .service_http import canonical
from . import maintenance as m

DEFAULT_LEASE_SECONDS = 1800
MIN_LEASE_SECONDS = 5
MAX_LEASE_SECONDS = 86400


def _protected_physical(dataset_id, native_document_id):
    # Even a disabled historical binding is a protected physical index.
    return frappe.db.exists('HBOS Knowledge Backend Binding',
                            {'dataset_id':dataset_id, 'document_id':native_document_id})


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
        elif action=='reconcile_no_wire' and set(raw)=={'action','batch_id','task_id','proof_sha256'}:
            from .maintenance_no_wire import reconcile
            result=reconcile(cfg,raw,_protected_physical)
        elif action=='update' and set(raw)=={'action','batch_id','state'}:
            row,frozen,old=m._row(raw['batch_id'],True)
            job=m._json(row,'job_json',{})
            if job.get('status')=='Running' or job.get('r2_preparation') or job.get('r2_task_manifest_sha256'):
                raise KnowledgeError('IMPORT_BUSY')
            m.registered(frozen,raw['state']);frappe.db.set_value(m.TABLE,row['name'],'state_json',canonical(raw['state']));result={'updated':True}
        elif action in ('claim','claim_preparation') and set(raw)=={'action'}:
            # Bounded sweep first: only a Running batch whose own lease has
            # already expired is requeued, and only that row is touched. A live
            # Running batch is never reset here.
            from .maintenance_batch import reclaim_expired
            from .maintenance_permit import controller_permit,permit_matches
            from .maintenance_managed import claimable
            managed=claimable(cfg,action)
            try:permit=managed[0] if managed else controller_permit(cfg)
            except KnowledgeError as error:
                # An expired historical permit closes only its own work. It
                # cannot prevent a later managed execution claim.
                if cfg.get('maintenance_managed_policy') and error.code=='IMPORT_BUSY':
                    frappe.db.commit()
                    return {'job':None,'reclaimed':0}
                raise
            if permit is None and cfg.get('maintenance_task_checkpoint_required') is True:
                raise KnowledgeError('POLICY_UNAVAILABLE')
            preparation=(permit or {}).get('prepare_only') is True
            if (action=='claim_preparation') != preparation:
                return {'job':None,'reclaimed':0}
            if permit is not None and not permit['by_batch']:
                # Main can drain/start the sole controller without authorizing
                # any work. An empty exact permit is a closed gate, not a
                # fallback to the unscoped legacy claim path.
                return {'job':None,'reclaimed':0}
            if managed:
                permit,rows,preparation,reclaimed=managed
            elif permit is None:
                reclaimed=reclaim_expired(actor=cfg['maintenance_coordinator_user'],reason='LEASE_EXPIRED')
                rows=frappe.db.sql('SELECT name FROM `tabHBOS Knowledge Import Batch` WHERE status=%s ORDER BY modified ASC LIMIT 1 FOR UPDATE',('Queued',),as_dict=True)
            else:
                reclaimed=[]
                for batch_id in permit['by_batch']:
                    permit_row,permit_frozen,_=m._row(batch_id)
                    permit_job=m._json(permit_row,'job_json',{})
                    if (permit_matches(permit,batch_id,permit_job,permit_frozen)
                            and (not preparation or permit_job.get('r2_preparation') is True)):
                        reclaimed.extend(reclaim_expired(actor=cfg['maintenance_coordinator_user'],
                            batch_id=batch_id,reason='LEASE_EXPIRED'))
                identifiers=tuple(permit['by_batch'])
                placeholders=','.join(['%s']*len(identifiers))
                rows=frappe.db.sql('SELECT name FROM `tabHBOS Knowledge Import Batch` WHERE status=%s '
                    'AND name IN ('+placeholders+') ORDER BY modified ASC LIMIT 60 FOR UPDATE',
                    ('Queued',*identifiers),as_dict=True)
                eligible=[]
                for entry in rows:
                    candidate_row,candidate_frozen,candidate_state=m._row(entry['name'])
                    candidate_job=m._json(candidate_row,'job_json',{})
                    if not permit_matches(permit,entry['name'],candidate_job,candidate_frozen):continue
                    if preparation:
                        items=[item for item in candidate_state['items']
                               if item['canonical_document_id'] in candidate_job['document_ids']]
                        if (candidate_job.get('r2_prepared_tasks_by_document') or candidate_job.get('task_facts')
                                or candidate_job.get('r2_task_manifest_sha256') or candidate_job.get('operation')!='parse'
                                or len(items)!=len(candidate_job['document_ids'])
                                or any(item['status'] not in ('planned','upload_intent','uploaded') for item in items)):
                            continue
                    eligible.append(entry)
                rows=eligible
            if not rows:return {'job':None,'reclaimed':len(reclaimed)}
            row,frozen,state=m._row(rows[0]['name'],True);job=m._json(row,'job_json',{})
            if job.get('status')!='Queued':raise KnowledgeError('IMPORT_BUSY')
            selected = [item for item in state['items'] if item['canonical_document_id'] in job.get('document_ids',())]
            if job.get('technical_preparation'):
                if (not permit or permit['manifest_sha256'] != frozen['batch_sha256']
                        or not selected or any(item['disposition']!='TECHNICAL_REINDEX' for item in selected)):
                    raise KnowledgeError('POLICY_UNAVAILABLE')
                m.require_current_technical_sources(selected)
            if job.get('operation')=='validate':
                from .maintenance_managed import can_validate_existing_result
                if not managed or not can_validate_existing_result(state,job):raise KnowledgeError('IMPORT_BUSY')
            from .maintenance_access import permitted
            if not permitted(job.get('requested_by')):
                job['status']='Blocked'
                frappe.db.set_value(m.TABLE,row['name'],{'job_json':canonical(job),'status':'Blocked','last_error':'RECONCILIATION_REQUIRED'})
                frappe.db.commit();return {'job':None,'reclaimed':len(reclaimed)}
            task_manifest_sha=(permit or {}).get('task_manifest_sha256')
            r2_required=(cfg.get('maintenance_task_checkpoint_required') is True
                         or bool(job.get('r2_task_manifest_sha256')) or bool(job.get('r2_preparation'))
                         or bool(job.get('r2_prepared_tasks_by_document')))
            if r2_required and not (task_manifest_sha or preparation):
                raise KnowledgeError('POLICY_UNAVAILABLE')
            if preparation:
                if job.get('operation')!='parse' or job.get('task_facts') or job.get('r2_task_manifest_sha256'):
                    raise KnowledgeError('IMPORT_BUSY')
                job['r2_preparation']=True
            if task_manifest_sha:
                from .maintenance_task_facts import batch_tasks, task_manifest
                if job.get('r2_task_manifest_sha256',task_manifest_sha)!=task_manifest_sha:
                    raise KnowledgeError('IMPORT_BUSY')
                by_document=batch_tasks(task_manifest(cfg,permit,job),row['name'],selected,
                                        cfg.get('maintenance_default_native_patch_sha256'))
                expected=sorted(task_id for tasks in by_document.values() for task_id in tasks)
                if (job.get('r2_task_ids',expected)!=expected
                        or job.get('r2_tasks_by_document',by_document)!=by_document):
                    raise KnowledgeError('IMPORT_BUSY')
                if r2_required and job.get('r2_prepared_tasks_by_document')!=by_document:
                    raise KnowledgeError('POLICY_UNAVAILABLE')
                job.update(r2_task_manifest_sha256=task_manifest_sha,r2_task_ids=expected,r2_tasks_by_document=by_document)
                job.pop('r2_preparation',None)
            generation=int(job.get('lease_generation') or 0)+1;now=time.time()
            job.update(status='Running',nonce=secrets.token_hex(24),lease_expires_at=now+lease_seconds(cfg),
                lease_generation=generation,claimed_at=now,pause_requested=False,
                holder_hash=hashlib.sha256(canonical([cfg['maintenance_coordinator_user'],
                    row['name'],generation]).encode('utf-8')).hexdigest()[:16])
            frappe.db.set_value(m.TABLE,row['name'],{'job_json':canonical(job),'status':'Running'})
            result={'batch_id':row['name'],'job':job,'frozen':frozen,'state':state,
                'reclaimed':len(reclaimed)}
        elif action in ('check_task_lease','task_checkpoint','authorize_preparation'):
            fields={'action','batch_id','job_id','nonce','lease_generation','document_id','version_id',
                    'source_sha256','dataset_id','native_document_id','task_id'}
            if action=='task_checkpoint':
                fields|={'operation','details'}
            if action=='authorize_preparation':
                fields=(fields-{'task_id'})|{'upload_sha256','profile_sha256','binding_revision'}
            if set(raw)!=fields:raise KnowledgeError('INVALID_REQUEST')
            # The legacy lease check stays observational. R2 transitions also
            # bind the prepared shard and message under this same row lock.
            if ((action!='authorize_preparation' and (not isinstance(raw['task_id'],str) or not re.fullmatch('[a-f0-9]{32}',raw['task_id'])))
                or not isinstance(raw['dataset_id'],str) or not re.fullmatch('[a-f0-9]{32}',raw['dataset_id'])
                or not isinstance(raw['native_document_id'],str) or not re.fullmatch('[a-f0-9]{32}',raw['native_document_id'])
                or not isinstance(raw['nonce'],str) or not re.fullmatch('[a-f0-9]{48}',raw['nonce'])
                or not isinstance(raw['source_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',raw['source_sha256'])
                or not isinstance(raw['document_id'],str) or not isinstance(raw['version_id'],str)
                or type(raw['lease_generation']) is not int):raise KnowledgeError('INVALID_REQUEST')
            row,frozen,state=m._row(raw['batch_id'],True);job=m._json(row,'job_json',{})
            if job.get('operation')=='validate':raise KnowledgeError('IMPORT_BUSY')
            now=time.time()
            if (row.get('status')!='Running' or job.get('status')!='Running'
                or not isinstance(raw['nonce'],str) or not isinstance(job.get('nonce'),str)
                or not secrets.compare_digest(job['nonce'],raw['nonce'])
                or job.get('id')!=raw['job_id'] or type(job.get('lease_generation')) is not int
                or job['lease_generation']!=raw['lease_generation']
                or type(job.get('lease_expires_at')) not in (int,float)
                or not math.isfinite(job['lease_expires_at'])
                or job['lease_expires_at']<=now):raise KnowledgeError('IMPORT_BUSY')
            from .maintenance_permit import permit_matches
            from .maintenance_managed import transition_permit
            permit=transition_permit(cfg,row['name'],frozen,job,now=now)
            if permit is None or not permit_matches(permit,raw['batch_id'],job,frozen):raise KnowledgeError('POLICY_UNAVAILABLE')
            from .maintenance_access import permitted
            if not permitted(job.get('requested_by')):raise KnowledgeError('SCOPE_REJECTED')
            matches=[i for i in state.get('items',[]) if i.get('canonical_document_id')==raw['document_id']]
            if (len(matches)!=1 or raw['document_id'] not in job.get('document_ids',[])
                or any(matches[0].get(k)!=raw[r] for k,r in (
                    ('version_id','version_id'),('sha256','source_sha256'),
                    ('dataset_id','dataset_id'),('ragflow_document_id','native_document_id')))):
                raise KnowledgeError('POLICY_UNAVAILABLE')
            if job['lease_expires_at']<=time.time() or permit['expires_at']<=time.time():
                raise KnowledgeError('IMPORT_BUSY')
            if action=='authorize_preparation':
                from .maintenance_task_facts import preparation_sha, prepared_profile_sha
                item=matches[0]
                if (permit.get('prepare_only') is not True or job.get('r2_preparation') is not True
                        or job.get('pause_requested') or item.get('status')!='uploaded'
                        or raw['upload_sha256']!=item.get('upload_sha256')
                        or raw['binding_revision']!=item.get('binding_revision')
                        or raw['profile_sha256']!=prepared_profile_sha(item,cfg.get('maintenance_default_native_patch_sha256'))
                        or not all(isinstance(raw[k],str) and re.fullmatch('[a-f0-9]{64}',raw[k])
                                   for k in ('upload_sha256','profile_sha256'))
                        or not isinstance(raw['binding_revision'],str)
                        or _protected_physical(raw['dataset_id'],raw['native_document_id'])):
                    raise KnowledgeError('POLICY_UNAVAILABLE')
                grants=job.setdefault('r2_preparation_admissions',{})
                identity=preparation_sha(row['name'],item,cfg.get('maintenance_default_native_patch_sha256'))
                if raw['document_id'] not in grants:
                    grants[raw['document_id']]=identity
                    frappe.db.set_value(m.TABLE,row['name'],'job_json',canonical(job))
                elif grants[raw['document_id']]!=identity:
                    raise KnowledgeError('IMPORT_BUSY')
                result={'authorizes_preparation':True,'authorizes_send':False,
                        'expires_at':min(job['lease_expires_at'],permit['expires_at'])}
            elif action=='task_checkpoint':
                from .maintenance_task_facts import admission_identity, advance, task_manifest
                if (not job.get('r2_task_manifest_sha256')
                    or permit.get('task_manifest_sha256')!=job['r2_task_manifest_sha256']
                    or raw['task_id'] not in job.get('r2_task_ids',[])):
                    raise KnowledgeError('POLICY_UNAVAILABLE')
                identity, entry=admission_identity(task_manifest(cfg,permit,job),raw,matches[0],
                                                  cfg.get('maintenance_default_native_patch_sha256'))
                if raw['operation'] in ('claim','send_intent','index_write','result_durable') and _protected_physical(
                        entry['dataset_id'],entry['native_document_id']):
                    raise KnowledgeError('IMPORT_BUSY')
                if job['lease_expires_at']<=time.time() or permit['expires_at']<=time.time():
                    raise KnowledgeError('IMPORT_BUSY')
                facts=job.setdefault('task_facts',{})
                recovery=(facts.get(raw['task_id']) or {}).get('known_no_wire_recovery')
                approved=False
                if recovery:
                    from .maintenance_no_wire import recovery_approved
                    approved=recovery_approved(cfg,raw['task_id'],recovery['proof_sha256'])
                result=advance(facts,raw['task_id'],identity,job['lease_generation'],raw['operation'],raw['details'],
                               recovery_approved=approved)
                result.update(stream=entry['stream'],group=entry['group'],message_id=entry['message_id'])
                if raw['operation'] not in ('inspect','authorize_ack'):
                    frappe.db.set_value(m.TABLE,row['name'],'job_json',canonical(job))
            else:
                result={'lease_valid_now':True,'lease_expires_at':job['lease_expires_at'],
                        'lease_generation':job['lease_generation'],
                        'native_task_membership_verified':False,'authorizes_send':False,
                        'authorizes_result_write':False,'authorizes_ack':False}
        elif action=='progress' and ({'action','batch_id','job_id','nonce','state','outcome','error'}<=set(raw)
                and set(raw)<={'action','batch_id','job_id','nonce','state','outcome','error','lease_generation','prepared_manifest'}):
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
            if (raw['outcome'] not in ('Running','Completed','Blocked','Failed','Prepared')
                    or (raw['outcome']=='Prepared')!=('prepared_manifest' in raw)):
                raise KnowledgeError('INVALID_REQUEST')
            preparing=job.get('r2_preparation') is True
            if preparing or raw['outcome']=='Prepared':
                from .maintenance_permit import permit_matches
                from .maintenance_managed import transition_permit
                permit=transition_permit(cfg,row['name'],frozen,job)
                if (not preparing or not permit or permit.get('prepare_only') is not True
                        or not permit_matches(permit,row['name'],job,frozen) or raw['outcome']=='Completed'):
                    raise KnowledgeError('IMPORT_BUSY')
            if raw['outcome']=='Completed' and job.get('r2_task_manifest_sha256'):
                from .maintenance_permit import permit_matches
                from .maintenance_managed import transition_permit
                permit=transition_permit(cfg,row['name'],frozen,job)
                if (not permit or permit.get('task_manifest_sha256')!=job['r2_task_manifest_sha256']
                        or not permit_matches(permit,row['name'],job,frozen)):
                    raise KnowledgeError('IMPORT_BUSY')
                facts=job.get('task_facts',{})
                expected=job['r2_task_ids']
                if any(facts.get(task,{}).get('status')!='ACKED' for task in expected):
                    raise KnowledgeError('IMPORT_BUSY')
            # Only the explicitly claimed group may change; previous successful
            # items and every other item must remain byte-for-byte unchanged.
            selected=set(job['document_ids'])
            for before,after in zip(old['items'],raw['state']['items']):
                if before['canonical_document_id'] not in selected and before!=after:raise KnowledgeError('INVALID_REQUEST')
                if job.get('operation')=='validate':
                    mutable={'automatic_quality','parse_provenance'}
                    if {k:v for k,v in before.items() if k not in mutable}!={k:v for k,v in after.items() if k not in mutable}:
                        raise KnowledgeError('INVALID_REQUEST')
                if (preparing and before['canonical_document_id'] in selected
                        and raw['outcome']!='Prepared' and after['status'] not in
                        ('planned','upload_intent','uploaded','quarantined')):
                    raise KnowledgeError('INVALID_REQUEST')
            outcome=raw['outcome']
            if outcome=='Completed' and job.get('managed_admission'):
                previews=[item for item in raw['state']['items'] if item['canonical_document_id'] in selected
                    and item['extension'] in ('.docx','.txt')
                    and (item.get('automatic_quality') or {}).get('status')=='AUTO_VERIFIED_PENDING_REVIEW']
                if previews:
                    from .managed_source_registry import register_derived_previews
                    try:
                        errors=register_derived_previews(cfg,frozen,previews)
                    except (ValueError,OSError,KeyError,TypeError):
                        errors={item['version_id']:'MANAGED_PREVIEW_REGISTRATION_RECHECK' for item in previews}
                    for item in previews:
                        reason=errors.get(item['version_id'])
                        if reason:
                            item['automatic_quality'].update(status='REPAIR_REQUIRED',reasons=[reason],
                                next_action='RECHECK_MOUNT_AND_PREVIEW_RECEIPT')
            if outcome=='Prepared':
                from .maintenance_task_facts import batch_tasks, manifest_tasks, preparation_sha
                manifest=raw['prepared_manifest']
                tasks=manifest_tasks(manifest)
                before={item['canonical_document_id']:item for item in old['items'] if item['canonical_document_id'] in selected}
                after=[item for item in raw['state']['items'] if item['canonical_document_id'] in selected]
                fields=('dataset_id','ragflow_document_id','upload_sha256')
                default_patch=cfg.get('maintenance_default_native_patch_sha256')
                grants=job.get('r2_preparation_admissions',{})
                if (job.get('pause_requested') or len(before)!=len(selected) or len(after)!=len(selected)
                        or any(item['status']!='parse_queued' or before[item['canonical_document_id']]['status']!='uploaded'
                               or any(item.get(key)!=before[item['canonical_document_id']].get(key) for key in fields)
                               or grants.get(item['canonical_document_id'])!=preparation_sha(row['name'],item,default_patch)
                               or _protected_physical(item['dataset_id'],item['ragflow_document_id']) for item in after)):
                    raise KnowledgeError('POLICY_UNAVAILABLE')
                by_document=batch_tasks(tasks,row['name'],after,default_patch)
                if set(by_document)!=selected or {task for ids in by_document.values() for task in ids}!=set(tasks):
                    raise KnowledgeError('POLICY_UNAVAILABLE')
                job['r2_prepared_tasks_by_document']=by_document
                job['r2_prepared_sha256']=hashlib.sha256(canonical(manifest).encode()).hexdigest()
                if job.get('managed_admission'):
                    # Persist the exact controller-produced plan in the same
                    # fenced SQL row. No browser or Main file handoff is needed.
                    job['r2_prepared_manifest']=manifest
                outcome='Queued'
            job['status']=outcome
            # The lease was set once at claim, so a parse that outlived it could
            # never report again and the batch stayed Running forever. Progress
            # while still Running renews it by the same 30 minutes; a terminal
            # outcome keeps the original lease so nothing looks live afterwards.
            if raw['outcome']=='Running':job['lease_expires_at']=time.time()+lease_seconds(cfg)
            else:job['nonce']=None
            safe=raw['error'] if raw['error'] in ('BUDGET_BLOCKED','PARSE_FAILED','SOURCE_CHANGED','EXECUTOR_STOPPED','RECONCILIATION_REQUIRED','PAUSED_BY_MAINTAINER') else None
            frappe.db.set_value(m.TABLE,row['name'],{'state_json':canonical(raw['state']),'job_json':canonical(job),'status':outcome,'last_error':safe})
            result={'updated':True}
            if raw['outcome']=='Prepared':
                result['r2_prepared_sha256']=job['r2_prepared_sha256']
            if job.get('r2_task_manifest_sha256'):
                facts=job.get('task_facts',{})
                result['r2_acked_task_ids']=[task for task in job['r2_task_ids']
                                            if facts.get(task,{}).get('status')=='ACKED']
            if job.get('pause_requested'):result['pause_requested']=True
        else:raise KnowledgeError('INVALID_REQUEST')
        frappe.db.commit();return result
    return _authority_envelope(run)
