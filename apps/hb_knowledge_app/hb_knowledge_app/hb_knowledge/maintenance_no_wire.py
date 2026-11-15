"""Reconcile an exact, proven before-wire interruption under Main's live permit."""

import hashlib
import json
import math
from pathlib import Path
import re
import time

from .errors import KnowledgeError
from .maintenance_permit import controller_permit, permit_matches
from .maintenance_task_facts import TASK_ID, admission_identity, task_manifest
from .service_http import canonical


PROOF = Path('/run/hbos-r2-config/native-no-wire-recovery.json')
HEX = re.compile('[a-f0-9]{64}')


def recovery_approved(config, task_id, digest, now=None):
    allowed = config.get('maintenance_no_wire_recovery')
    return (isinstance(allowed, dict) and set(allowed) == {'task_id','proof_sha256','expires_at'}
            and isinstance(task_id,str) and bool(TASK_ID.fullmatch(task_id))
            and allowed['task_id'] == task_id and allowed['proof_sha256'] == digest
            and isinstance(digest, str) and bool(HEX.fullmatch(digest))
            and type(allowed['expires_at']) in (int,float) and math.isfinite(allowed['expires_at'])
            and allowed['expires_at'] > (time.time() if now is None else now))


def _request_sha256(value):
    payload = {'input':[value],'model':'qwen3.7-text-embedding','encoding_format':'float','drop_params':True}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def reconcile(config, raw, protected):
    """Restore eligibility while retaining every original task and provider fact."""
    from knowledge_service.provider_epoch import local_epoch
    from knowledge_service.provider_budget import BudgetStopped
    from . import maintenance as m
    import frappe

    task_id, proof_digest = raw['task_id'], raw['proof_sha256']
    if not recovery_approved(config, task_id, proof_digest):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    try:
        with PROOF.open('rb') as stream:
            contents = stream.read(65537)
        if len(contents) > 65536 or hashlib.sha256(contents).hexdigest() != proof_digest:
            raise ValueError()
        proof = json.loads(contents)
        notification=proof['redis_notification']
        if (proof['task_id'] != task_id or proof['batch_id'] != raw['batch_id']
                or proof['body_embedding_sent'] is not False or proof['retry_parent_available'] is not True
                or notification['pending'] is not True or notification['marker'] is not None
                or notification['consumer'] != 'task_executor_common_r2' or notification['native_cancelled'] is not False
                or proof['native_document_sql']['run'] != '4' or proof['native_document_sql']['progress'] != -1):
            raise ValueError()
        probe, cancelled = (proof[key] for key in ('settled_dimension_probe','cancelled_filename_embedding'))
        epoch = local_epoch()
        if epoch is None or not epoch.confirmed_native_no_wire(task_id,probe,cancelled):
            raise ValueError()
    except (OSError,ValueError,KeyError,TypeError,BudgetStopped):
        raise KnowledgeError('POLICY_UNAVAILABLE') from None
    row, frozen, state = m._row(raw['batch_id'],True)
    job = m._json(row,'job_json',{})
    permit = controller_permit(config)
    if (permit is None or not permit_matches(permit,row['name'],job,frozen)
            or permit.get('task_manifest_sha256') != proof['task_manifest_sha256']
            or job.get('r2_task_manifest_sha256') != proof['task_manifest_sha256']
            or job.get('id') != proof['terminal_job_id'] or job.get('lease_generation') != proof['terminal_job_generation']
            or row['status'] != 'Blocked' or job.get('status') != 'Blocked' or job.get('nonce')):
        raise KnowledgeError('IMPORT_BUSY')
    tasks = task_manifest(config,permit)
    entry = tasks.get(task_id)
    selected = [item for item in state['items'] if entry and item['canonical_document_id']==entry['document_id']]
    if (len(selected)!=1 or task_id not in job.get('r2_task_ids',[])
            or protected(entry['dataset_id'],entry['native_document_id'])):
        raise KnowledgeError('IMPORT_BUSY')
    item = selected[0]
    identity,_ = admission_identity(tasks,{'task_id':task_id,**entry},item,
                                    config.get('maintenance_default_native_patch_sha256'))
    facts = job.get('task_facts',{})
    previous = facts.get(task_id)
    attempts = previous.get('attempts',{}) if isinstance(previous,dict) else {}
    existing = previous.get('known_no_wire_recovery') if isinstance(previous,dict) else None
    expected_attempts={probe['attempt_id']}
    expected_status='PROVIDER_DONE'
    after_claim='after_claim_stop_sha256' in proof
    if existing is not None:
        stop_proof=proof.get('preclaim_stop_sha256')
        elapsed_generations=job['lease_generation']-previous['generation']
        cancel_receipt=existing['proof_sha256']
        if after_claim:
            stop_proof=proof['after_claim_stop_sha256']
            cancel_receipt=proof.get('original_cancel_proof_sha256')
            native_task=proof.get('native_task_sql',{})
            if (elapsed_generations!=0 or 'native_retry_count' in existing
                    or 'verified_no_wire_claim' in previous
                    or proof.get('prior_recovery_proof_sha256')!=existing['proof_sha256']
                    or not isinstance(cancel_receipt,str) or not HEX.fullmatch(cancel_receipt)
                    or cancel_receipt==existing['proof_sha256']
                    or not isinstance(native_task,dict) or type(native_task.get('retry')) is not int
                    or native_task['retry']!=2 or native_task.get('progress')!=-1 or native_task.get('chunks')!=[]
                    or native_task.get('pages')!=[entry['from_page'],entry['to_page']]):
                raise KnowledgeError('IMPORT_BUSY')
        elif elapsed_generations==3:
            cancel_receipt=proof.get('original_cancel_proof_sha256')
            earlier_stop=proof.get('prior_verified_preclaim_stop_sha256')
            if (not all(isinstance(value,str) and HEX.fullmatch(value) for value in (cancel_receipt,earlier_stop))
                    or cancel_receipt==existing['proof_sha256'] or earlier_stop==stop_proof):
                raise KnowledgeError('IMPORT_BUSY')
        expected_attempts.add(cancelled['attempt_id'])
        expected_status='CLAIMED' if after_claim else 'CANCELLED_BEFORE_WIRE'
        if (not isinstance(stop_proof,str) or not HEX.fullmatch(stop_proof)
                or job.get('operation')!='resume' or (not after_claim and elapsed_generations not in (2,3))
                or existing['proof_sha256']==proof_digest
                or any(existing[key]!=cancelled[source] for key,source in (
                    ('parent_attempt_id','attempt_id'),('operation_id','operation_id'),('request_sha256','request_sha256')))
                or attempts.get(cancelled['attempt_id'])!={
                    'operation_id':cancelled['operation_id'],'outcome':'CANCELLED_BEFORE_WIRE',
                    'receipt_sha256':cancel_receipt,'provider_request_id':None}):
            raise KnowledgeError('IMPORT_BUSY')
    elif after_claim or 'preclaim_stop_sha256' in proof:
        raise KnowledgeError('IMPORT_BUSY')
    if (not isinstance(previous,dict) or identity != proof['task_identity_sha256'] or previous != proof['original_fact']
            or previous['status'] != expected_status or previous['generation'] != proof['task_fact_generation']
            or set(attempts) != expected_attempts or attempts[probe['attempt_id']]['outcome'] != 'SUCCESS'
            or attempts[probe['attempt_id']]['operation_id'] != probe['operation_id']
            or item['status'] != 'parse_failed' or item['native_profile']['embedding_dimensions'] != 1024
            or _request_sha256('ok') != probe['request_sha256']
            or _request_sha256(item['upload_name']) != cancelled['request_sha256']
            or set(facts) != set(job['r2_task_ids'])
            or any(fact['status'] != 'ACKED' or fact['ack_count'] != 1 for key,fact in facts.items() if key!=task_id)):
        raise KnowledgeError('IMPORT_BUSY')
    recovery = {'proof_sha256':proof_digest,'parent_attempt_id':cancelled['attempt_id'],
                'operation_id':cancelled['operation_id'],'request_sha256':cancelled['request_sha256'],
                'embedding_dimensions':1024}
    if existing is None:
        attempts[cancelled['attempt_id']] = {'operation_id':cancelled['operation_id'],'outcome':'CANCELLED_BEFORE_WIRE',
                                           'receipt_sha256':proof_digest,'provider_request_id':None}
    if after_claim:
        recovery['native_retry_count']=2
        previous['verified_no_wire_claim']={
            'generation':previous['generation'],'fact_sha256':hashlib.sha256(canonical(proof['original_fact']).encode()).hexdigest(),
            'stop_sha256':proof['after_claim_stop_sha256'],'prior_proof_sha256':existing['proof_sha256']}
    previous.update(status='CANCELLED_BEFORE_WIRE',known_no_wire_recovery=recovery)
    item['status'] = 'parse_queued'
    m.registered(frozen,state)
    frappe.db.set_value(m.TABLE,row['name'],{'job_json':canonical(job),'state_json':canonical(state)})
    return {'task_id':task_id,'proof_sha256':proof_digest,'reconciled':True,'provider_send_authorized':False}
