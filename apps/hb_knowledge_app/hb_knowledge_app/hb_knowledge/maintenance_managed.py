"""Server-owned admission for the existing, fenced maintenance controller.

The browser supplies files and business choices. It never supplies a lease,
physical dataset, task manifest, provider budget, or controller permit.
Historical jobs remain behind their original exact permits.
"""
import hashlib
import math
from pathlib import Path
import re
import time

from .errors import KnowledgeError
from .service_http import canonical

SCHEMA = 'hbos.maintenance-managed-policy.v1'
ADMISSION = 'hbos.maintenance-managed-admission.v1'
SHA = re.compile(r'[a-f0-9]{64}')


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def queue_kind(item):
    layout = (item.get('native_profile') or {}).get('parser_config', {}).get('layout_recognize')
    return 'COMPLEX' if (item.get('source_inspection_error') or layout=='DeepDOC'
                         or item.get('extension') not in ('.pdf','.docx','.txt')) else 'ORDINARY'


def policy(cfg, now=None):
    value = cfg.get('maintenance_managed_policy')
    if value is None:
        return None
    now = time.time() if now is None else now
    if (not isinstance(value, dict) or value.get('schema') != SCHEMA
            or value.get('enabled') is not True
            or not isinstance(value.get('approval_ref'), str) or not value['approval_ref'].strip()
            or type(value.get('expires_at')) not in (int, float)
            or not math.isfinite(value['expires_at']) or value['expires_at'] <= now
            or not isinstance(value.get('profile_sha256'), list) or not value['profile_sha256']
            or any(not isinstance(x, str) or not SHA.fullmatch(x) for x in value['profile_sha256'])
            or not isinstance(value.get('departments'), list) or not value['departments']
            or not isinstance(value.get('write_datasets'), dict)
            or any(not isinstance(value['write_datasets'].get(d), str)
                   or not re.fullmatch(r'[a-f0-9]{32}', value['write_datasets'][d]) for d in value['departments'])
            or cfg.get('maintenance_task_checkpoint_required') is not True
            or cfg.get('maintenance_source_registry_enabled') is not True):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    return value


def _scope(cfg, frozen, document_ids, actor, now=None):
    p = policy(cfg, now)
    if p is None:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    if (frozen.get('approval_status') != 'OWNER_APPROVED'
            or frozen.get('department_key') not in p['departments']
            or not isinstance(document_ids, list) or not 1 <= len(document_ids) <= 4
            or len(document_ids) != len(set(document_ids)) or not isinstance(actor, str) or not actor):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    root = Path(frozen.get('source_root', ''))
    uploads = Path(cfg.get('maintenance_upload_root', ''))
    if (not root.is_absolute() or not uploads.is_absolute() or root == uploads
            or not root.is_relative_to(uploads) or root.resolve(strict=True) != root
            or uploads.resolve(strict=True) != uploads):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    items = [i for i in frozen.get('items', []) if i.get('canonical_document_id') in document_ids]
    if len(items) != len(document_ids):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    identities = []
    complex_queue=False
    from knowledge_service.native_job_contract import validate_native_item
    from knowledge_service.ingestion import processing_approved
    for item in items:
        try:
            validate_native_item(item)
        except (KeyError, TypeError, ValueError):
            raise KnowledgeError('POLICY_UNAVAILABLE') from None
        if (item['native_profile']['profile_sha256'] not in p['profile_sha256']
                or item.get('disposition') not in ('NEW', 'UPDATE_CONFIRMED')
                or not processing_approved(frozen, item)
                or not all(item.get(k) is True for k in
                           ('owner_inclusion_confirmed', 'internal_sharing_confirmed'))):
            raise KnowledgeError('POLICY_UNAVAILABLE')
        identities.append({k: item[k] for k in ('canonical_document_id', 'version_id', 'sha256', 'binding_revision')})
        complex_queue=complex_queue or queue_kind(item)=='COMPLEX'
    return {'schema': ADMISSION, 'policy_sha256': digest(p),
            'frozen_sha256': frozen['batch_sha256'], 'requested_by': actor,
            'write_dataset_id': p['write_datasets'][frozen['department_key']],
            'queue_kind':'COMPLEX' if complex_queue else 'ORDINARY',
            'identities': sorted(identities, key=lambda i: i['canonical_document_id'])}


def admit(cfg, frozen, job, now=None):
    """Called only after the native maintenance role and source checks passed."""
    from .maintenance_access import permitted
    if not permitted(job.get('requested_by')):
        raise KnowledgeError('SCOPE_REJECTED')
    scope = _scope(cfg, frozen, job['document_ids'], job['requested_by'], now)
    job['managed_admission'] = {**scope, 'sha256': digest(scope)}
    return job


def batch_permit(cfg, batch_id, frozen, job, now=None):
    """Revalidate authority and the exact admission on every leased transition."""
    marker = job.get('managed_admission')
    if not marker:
        return None
    from .maintenance_access import permitted
    if not permitted(job.get('requested_by')):
        raise KnowledgeError('SCOPE_REJECTED')
    scope = _scope(cfg, frozen, job.get('document_ids'), job.get('requested_by'), now)
    if marker != {**scope, 'sha256': digest(scope)}:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    documents = {i['canonical_document_id']: {'version_id': i['version_id'], 'source_sha256': i['sha256']}
                 for i in scope['identities']}
    result = {'by_batch': {batch_id: documents}, 'manifest_sha256': frozen['batch_sha256'],
              'expires_at': policy(cfg, now)['expires_at'], 'managed': True}
    manifest = job.get('r2_prepared_manifest')
    if manifest is None:
        result['prepare_only'] = True
    else:
        from .maintenance_task_facts import manifest_tasks
        manifest_tasks(manifest)
        result['task_manifest_sha256'] = digest(manifest)
        if result['task_manifest_sha256'] != job.get('r2_prepared_sha256'):
            raise KnowledgeError('POLICY_UNAVAILABLE')
    return result


def transition_permit(cfg, batch_id, frozen, job, now=None):
    managed = batch_permit(cfg, batch_id, frozen, job, now)
    if managed is not None:
        return managed
    from .maintenance_permit import controller_permit
    return controller_permit(cfg, now=now)


def safe_resume(state,job):
    """A lease can recover only untouched work or the same durable result."""
    selected=set(job.get('document_ids') or [])
    items=[item for item in state.get('items',[]) if item.get('canonical_document_id') in selected]
    if not selected or len(items)!=len(selected) or any(item.get('status') not in
            ('planned','uploaded','parse_queued','parsed/indexed','skipped_duplicate') for item in items):return False
    facts=job.get('task_facts') or {}
    return all(fact.get('status') in ('RESULT_DURABLE','ACK_UNCERTAIN','ACKED')
               or (fact.get('status')=='CLAIMED' and not fact.get('attempts')) for fact in facts.values())


REVALIDATION_REASONS = frozenset({'AUTOMATIC_VALIDATION_UNAVAILABLE','LOCKED_OFFICE_CONVERTER_UNAVAILABLE',
    'OFFICE_PREVIEW_VALIDATION_UNAVAILABLE','MANAGED_PREVIEW_REGISTRATION_RECHECK'})


def can_validate_existing_result(state,job):
    selected=set(job.get('document_ids') or [])
    items=[item for item in state.get('items',[]) if item['canonical_document_id'] in selected]
    task_map=job.get('r2_tasks_by_document') or {}
    task_ids=job.get('r2_task_ids') or []
    facts=job.get('task_facts') or {}
    if (not isinstance(task_map,dict) or not isinstance(task_ids,list) or not isinstance(facts,dict)
            or any(not isinstance(ids,list) for ids in task_map.values())):
        return False
    return bool(job.get('managed_admission') and job.get('r2_task_manifest_sha256') and selected
        and len(items)==len(selected) and all(item['status']=='parsed/indexed' for item in items)
        and set(task_map)==selected and all(task_map.values()) and task_ids
        and {key for ids in task_map.values() for key in ids}==set(task_ids)
        and all(facts.get(key,{}).get('status')=='ACKED' for key in task_ids))


def should_revalidate(item):
    quality=item.get('automatic_quality') or {}
    reasons=quality.get('reasons') or []
    return quality.get('status')=='REPAIR_REQUIRED' and bool(reasons) and set(reasons)<=REVALIDATION_REASONS


def claimable(cfg, action):
    """Choose only queued jobs previously admitted by a normal maintenance action.

    An invalid/expired job is isolated; it cannot stall other normal jobs.
    Running jobs and their provider calls are never reclaimed by this selector.
    """
    configured = cfg.get('maintenance_managed_policy')
    if configured is None or (isinstance(configured,dict) and configured.get('schema')==SCHEMA
                              and configured.get('enabled') is False):
        return None
    policy(cfg)
    import frappe
    from . import maintenance as m
    if action=='claim_preparation':
        # The sole controller checks the registered worker before asking for
        # a claim. Only its own expired, safe native leases are reclaimed here.
        from .maintenance_batch import reclaim_expired
        expired=frappe.db.sql('SELECT name FROM `tabHBOS Knowledge Import Batch` '
            'WHERE status=%s AND LOCATE(%s,job_json)>0 ORDER BY modified ASC LIMIT 16',
            ('Running','"managed_admission"'),as_dict=True)
        for entry in expired:
            reclaim_expired(actor=cfg['maintenance_coordinator_user'],batch_id=entry['name'],
                            reason='MANAGED_SAFE_LEASE_RECOVERY')
    ordinary="JSON_UNQUOTE(JSON_EXTRACT(job_json,'$.managed_admission.queue_kind'))='ORDINARY'"
    rows = frappe.db.sql('SELECT name FROM `tabHBOS Knowledge Import Batch` '
        'WHERE status=%s AND LOCATE(%s,job_json)>0 AND (%s=1 OR '+ordinary+') '
        'ORDER BY CASE WHEN '+ordinary+' THEN 0 ELSE 1 END, modified ASC LIMIT 60 FOR UPDATE',
        ('Queued', '"managed_admission"', int(cfg.get('maintenance_complex_claims_enabled') is True)), as_dict=True)
    for entry in rows:
        row, frozen, _ = m._row(entry['name'])
        job = m._json(row, 'job_json', {})
        try:
            permit = batch_permit(cfg, row['name'], frozen, job)
        except KnowledgeError as error:
            job['status'] = 'Blocked'
            frappe.db.set_value(m.TABLE, row['name'], {'job_json': canonical(job),
                'status': 'Blocked', 'last_error': error.code})
            continue
        preparing = permit.get('prepare_only') is True
        if preparing == (action == 'claim_preparation'):
            return permit, [entry], preparing, []
    return None


def public_template(item):
    """Actual frozen document settings, never dataset defaults."""
    profile = item.get('native_profile') or {}
    provenance=item.get('parse_provenance') or {}
    config = provenance.get('effective_document_parser_config') or profile.get('parser_config') or item.get('parser_config') or {}
    source = item.get('native_source_proof') or {}
    prepared = source.get('prepared_asset')
    return {'profile_sha256': profile.get('profile_sha256'),
            'parser': profile.get('parser_id'), 'parser_version': provenance.get('parser_implementation_commit') or profile.get('ragflow_base_commit'),
            'parser_patch_sha256': profile.get('candidate_patch_sha256'),
            'parser_config':config,
            'chunk_tokens': config.get('chunk_token_num'), 'overlap_percent': config.get('overlapped_percent'),
            'table_context': config.get('table_context_size'), 'image_context': config.get('image_context_size'),
            'embedding_model': profile.get('embedding_model'), 'embedding_dimensions': profile.get('embedding_dimensions'),
            'input_kind': 'DERIVED' if prepared else 'ORIGINAL',
            'input_sha256': item.get('upload_sha256') or (prepared or {}).get('sha256') or item.get('sha256'),
            'parser_input': item.get('parser_input'),
            'provenance': item.get('parse_provenance'),
            'effective_document_profile': bool(provenance)}
