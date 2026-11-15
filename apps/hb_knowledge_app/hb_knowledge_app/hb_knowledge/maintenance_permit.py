"""Temporary narrowing of the existing controller; never adds permissions."""
import re
import time
import math
from .errors import KnowledgeError


def controller_permit(config, now=None):
    value=config.get('maintenance_batch_permit')
    if value is None:
        if config.get('maintenance_claim_scope_required') is True:
            raise KnowledgeError('POLICY_UNAVAILABLE')
        return None
    keys={'manifest_sha256','expires_at','by_batch'}
    if (not isinstance(value,dict) or set(value) not in (keys,keys|{'task_manifest_sha256'},keys|{'prepare_only'})
            or not isinstance(value['manifest_sha256'],str)
            or not re.fullmatch('[a-f0-9]{64}',value['manifest_sha256'])
            or type(value['expires_at']) not in (int,float)
            or not math.isfinite(value['expires_at'])
            or not isinstance(value['by_batch'],dict) or not 0<=len(value['by_batch'])<=60):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    if 'prepare_only' in value and (value['prepare_only'] is not True
            or config.get('maintenance_task_checkpoint_required') is not True):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    if 'task_manifest_sha256' in value and (
            not isinstance(value['task_manifest_sha256'],str)
            or not re.fullmatch('[a-f0-9]{64}',value['task_manifest_sha256'])):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    if value['expires_at'] <= (time.time() if now is None else now):
        raise KnowledgeError('IMPORT_BUSY')
    total=0
    for batch,documents in value['by_batch'].items():
        if (not isinstance(batch,str) or not re.fullmatch(r'IMP_[a-f0-9]{32}',batch)
                or not isinstance(documents,dict) or not documents):
            raise KnowledgeError('POLICY_UNAVAILABLE')
        total+=len(documents)
        for document,entry in documents.items():
            if (not isinstance(document,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}',document)
                    or not isinstance(entry,dict) or set(entry)!={'version_id','source_sha256'}
                    or not isinstance(entry['version_id'],str)
                    or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',entry['version_id'])
                    or not isinstance(entry['source_sha256'],str)
                    or not re.fullmatch('[a-f0-9]{64}',entry['source_sha256'])):
                raise KnowledgeError('POLICY_UNAVAILABLE')
    if total>60:raise KnowledgeError('POLICY_UNAVAILABLE')
    return value


def permit_matches(permit,batch_id,job,frozen):
    if permit is None:return True
    allowed=permit['by_batch'].get(batch_id,{})
    selected=job.get('document_ids')
    if (not isinstance(selected,list) or not 1<=len(selected)<=4
            or len(set(selected))!=len(selected) or not set(selected)<=set(allowed)):
        return False
    rows={item['canonical_document_id']:item for item in frozen.get('items',[])}
    return all(document in rows and rows[document].get('version_id')==allowed[document]['version_id']
               and rows[document].get('sha256')==allowed[document]['source_sha256']
               and rows[document].get('owner_inclusion_confirmed') is True
               and rows[document].get('internal_sharing_confirmed') is True
               for document in selected)


def require_technical_preparation(config, batch_id, job, frozen, items, now=None):
    """Require the exact registered manifest before queuing technical work."""
    permit = controller_permit(config, now)
    if (not permit or permit.get('prepare_only') is not True
            or permit['manifest_sha256'] != frozen.get('batch_sha256')
            or frozen.get('approval_status') != 'OWNER_APPROVED'
            or job.get('operation') != 'parse' or not permit_matches(permit, batch_id, job, frozen)):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    for item in items:
        parent = item.get('native_parent_binding') or {}
        if (item.get('disposition') != 'TECHNICAL_REINDEX'
                or item.get('parser_input') != 'VERIFIED_ORIGINAL_NATIVE'
                or (item.get('native_source_proof') or {}).get('full_source_requested') is not True
                or item.get('expected_current_version') != item['version_id']
                or parent.get('version_id') != item['version_id']
                or parent.get('canonical_document_id') != item['canonical_document_id']
                or parent.get('space_id') != item.get('space_id') or not parent.get('binding_ref')):
            raise KnowledgeError('POLICY_UNAVAILABLE')
