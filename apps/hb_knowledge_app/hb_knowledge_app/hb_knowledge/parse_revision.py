"""A technical binding revision preserves the immutable business version."""
import hashlib
import re
from datetime import datetime
from dataclasses import asdict, replace
from .execution_plan import Binding, validate_admission
from .publication import PublicationConflict
from .service_http import canonical


def require(value, message):
    if not value:
        raise PublicationConflict(message)


def revision_key(batch_id, item):
    return hashlib.sha256(canonical([batch_id, item['canonical_document_id'],
        item['version_id'], item['binding_revision']]).encode()).hexdigest()


def effective_revision_key(batch_id, item, approval, read_receipt):
    """A fresh Main review may resume an exactly recorded technical rollback.

    The original forward/rollback audit stays immutable. This admits no new
    source, scope, profile or physical index, and does not enqueue parsing.
    """
    key=revision_key(batch_id,item)
    proof=approval.get('resume_from_rollback') if isinstance(approval,dict) else None
    if proof is None:return key
    require(isinstance(proof,dict) and set(proof)=={'forward_revision_ref',
        'rollback_revision_ref','forward_sha256','rollback_sha256'},'Exact rollback lineage required')
    require(isinstance(proof['forward_revision_ref'],str) and re.fullmatch('PUB_TECH_[0-9a-f]{32}',proof['forward_revision_ref'])
            and isinstance(proof['rollback_revision_ref'],str) and re.fullmatch('PUB_ROLLBACK_[0-9a-f]{32}',proof['rollback_revision_ref']),
            'Invalid rollback lineage reference')
    records=[]
    for label in ('forward','rollback'):
        raw=read_receipt(proof[label+'_revision_ref'])
        require(isinstance(raw,str) and hashlib.sha256(raw.encode()).hexdigest()==proof[label+'_sha256'],
                'Immutable rollback lineage changed')
        try:
            import json
            record=json.loads(raw)
        except (ValueError,TypeError):raise PublicationConflict('Invalid rollback lineage') from None
        require(isinstance(record,dict),'Invalid rollback lineage')
        records.append(record)
    forward,rollback=records
    require(forward.get('schema')=='hbos.parse-revision.v1'
            and rollback.get('schema')=='hbos.parse-rollback.v1','A completed technical rollback is required')
    fields=('batch_sha256','canonical_document_id','version_id','source_sha256',
        'parent_binding_ref','parent_binding_revision','target_dataset_id','target_document_id',
        'target_binding_revision','profile_hash','quality_evidence_sha256','parent_upload_sha256')
    require(all(isinstance(forward.get(k),str) and forward[k] for k in fields)
            and isinstance(forward.get('new_binding_ref'),str)
            and isinstance(forward.get('old_binding'),dict),'Incomplete rollback lineage')
    require(all(approval.get(k)==forward.get(k) for k in fields),'Recovery source/index review drift')
    require(forward.get('canonical_document_id')==item['canonical_document_id']
            and forward.get('version_id')==item['version_id'] and forward.get('source_sha256')==item['sha256']
            and forward.get('old_binding')==item.get('native_parent_binding'), 'Recovery frozen parent changed')
    require(rollback.get('canonical_document_id')==forward['canonical_document_id']
            and rollback.get('version_id')==forward['version_id']
            and rollback.get('source_sha256')==forward['source_sha256']
            and rollback.get('current_binding_ref')==forward['new_binding_ref']
            and rollback.get('return_binding_ref')==forward['parent_binding_ref']
            and rollback.get('parent_upload_sha256')==forward['parent_upload_sha256']
            and rollback.get('old_authorization_snapshot_restored') is False
            and rollback.get('both_backend_indexes_retained') is True,'Rollback lineage target drift')
    require(approval.get('approval_ref') and approval['approval_ref']!=forward.get('approval_ref')
            and re.fullmatch('[0-9a-f]{64}',approval.get('review_receipt_sha256',''))
            and approval['review_receipt_sha256']!=forward.get('review_receipt_sha256'),
            'Fresh Main recovery review required')
    return hashlib.sha256(canonical([key,'REVIEWED_ROLLBACK_RESUME_V1',proof]).encode()).hexdigest()


def reusable_rolled_back_binding(expected, retained, enabled, now):
    """Reuse the unique physical pair without rewriting its original binding."""
    require(not enabled,'Recovery target is already active')
    desired,actual=asdict(expected),asdict(retained)
    # The original activation timestamp is truthful. Every identity, scope,
    # authority and validity end remains equal to the freshly checked target.
    desired.pop('valid_from');actual.pop('valid_from')
    require(desired==actual,'Retained recovery binding changed')
    validate_admission(retained,'production',datetime.fromisoformat(now.replace('Z','+00:00')).timestamp())
    return retained


def replacement(item, current, metadata, parent, quality, approval, batch_sha, now):
    """Validate the locked current source, exact parent and reviewed target.

    This does not grant sharing, restore withdrawal, or modify a business
    version. Backend/source verification is additionally required by the caller.
    """
    require(isinstance(approval, dict), 'Exact parse revision approval required')
    require(item.get('disposition') == 'TECHNICAL_REINDEX'
            and item.get('status') == 'parsed/indexed'
            and item.get('parser_input') == 'VERIFIED_ORIGINAL_NATIVE'
            and item.get('internal_sharing_confirmed') is True
            and item.get('owner_inclusion_confirmed') is True,
            'Technical target is not admitted')
    require(item.get('native_source_proof', {}).get('full_source_requested') is True,
            'A bounded experiment cannot replace a complete source')
    require(current and not current.get('withdrawn')
            and current.get('ingestion_status') == 'published'
            and current.get('current_version') == item['version_id'] == item.get('expected_current_version')
            and current.get('source_hash') == item['sha256'], 'Current source/version changed')
    for field in ('sha256', 'business_version', 'document_number', 'source_type', 'authority_status'):
        require(metadata.get(field) == item.get(field), 'Business version metadata changed')
    require(parent.canonical_document_id == item['canonical_document_id']
            and parent.version_id == item['version_id']
            and parent.space_id == item['space_id']
            and parent.publication_state == 'published' and not parent.withdrawn,
            'Parent scope/version changed')
    frozen_parent = item.get('native_parent_binding', {})
    for field in ('binding_ref', 'binding_revision', 'dataset_id', 'document_id',
                  'canonical_document_id', 'version_id', 'space_id'):
        require(getattr(parent, field) == frozen_parent.get(field), 'Parent binding changed')
    require(quality.get('status') == 'Passed'
            and quality.get('source_sha256') == item['sha256']
            and quality.get('upload_sha256') == item['upload_sha256'], 'Quality receipt missing')
    expected = {'batch_sha256': batch_sha, 'canonical_document_id': item['canonical_document_id'],
        'version_id': item['version_id'], 'source_sha256': item['sha256'],
        'parent_binding_ref': parent.binding_ref, 'parent_binding_revision': parent.binding_revision,
        'target_dataset_id': item['dataset_id'], 'target_document_id': item['ragflow_document_id'],
        'target_binding_revision': item['binding_revision'],
        'profile_hash': item['native_profile']['profile_sha256'],
        'quality_evidence_sha256': quality.get('evidence_sha256')}
    require(all(approval.get(k) == v for k, v in expected.items()), 'Parse revision approval drift')
    require(all(re.fullmatch('[0-9a-f]{64}', approval.get(k, '')) for k in
        ('quality_evidence_sha256', 'review_receipt_sha256', 'profile_hash'))
        and approval.get('approval_ref'), 'Reviewed parse evidence required')
    require((parent.dataset_id, parent.document_id, parent.binding_revision) !=
            (item['dataset_id'], item['ragflow_document_id'], item['binding_revision']),
            'Target is already the parent')
    require(re.fullmatch('[0-9a-f]{64}',approval.get('parent_upload_sha256','')),
            'Retained backend source proof required')
    digest = hashlib.sha256(canonical(expected).encode()).hexdigest()
    result = replace(parent, dataset_id=item['dataset_id'], document_id=item['ragflow_document_id'],
        binding_ref='BIND_TECH_' + digest[:32], binding_revision=item['binding_revision'],
        valid_from=now, valid_until=None)
    validate_admission(result, 'production', datetime.fromisoformat(now.replace('Z', '+00:00')).timestamp())
    return result, {'schema': 'hbos.parse-revision.v1', **expected,
        'new_binding_ref': result.binding_ref, 'old_binding': asdict(parent),
        'new_binding': asdict(result), 'review_receipt_sha256': approval['review_receipt_sha256'],
        'approval_ref': approval['approval_ref'], 'business_version_changed': False,
        'old_backend_retained': True, 'business_metadata': dict(metadata),
        'parent_upload_sha256': approval['parent_upload_sha256'],
        'old_document_technical_metadata': {k:current.get(k) for k in
            ('dataset_id','parser_revision','embedding_revision')}}


def promote(batch_id, document_ids, expected_version, reason):
    """Existing authenticated maintenance flow; one CAS transaction per target."""
    import json
    import time
    import frappe
    from . import maintenance as m
    from .metadata_integrity import IDENTITY_FIELDS, physical_pair_key
    from .execution_plan import iso
    from .reference_admin import _verify_backend
    m.require()
    require(isinstance(document_ids, list) and len(document_ids) == 1
            and isinstance(reason, str) and 3 <= len(reason.strip()) <= 500,
            'One technical target and reason required')
    try:
        row, frozen, state = m._row(batch_id, True)
        m.registered(frozen, state)
        items = [x for x in state['items'] if x['canonical_document_id'] == document_ids[0]
                 and x.get('disposition') == 'TECHNICAL_REINDEX']
        require(len(items) == 1, 'Exact technical target required')
        item = items[0]
        require(expected_version == item['version_id'], 'Expected business version changed')
        cfg = m.configuration()
        approval = cfg.get('parse_revision_approvals', {}).get(revision_key(batch_id, item))
        require(isinstance(approval, dict), 'Main parse revision approval required')
        receipt = 'PUB_TECH_' + effective_revision_key(batch_id,item,approval,
            lambda ref:frappe.db.get_value('HBOS Knowledge Parse Revision',ref,'receipt_json'))[:32]
        rows = frappe.db.sql('SELECT name,current_version,source_hash,withdrawn,ingestion_status,dataset_id,parser_revision,embedding_revision '
            'FROM `tabHBOS Knowledge Document` WHERE name=%s FOR UPDATE', (document_ids[0],), as_dict=True)
        require(len(rows) == 1, 'Current document missing')
        current = rows[0]
        prior = frappe.db.get_value('HBOS Knowledge Publication', receipt,
            ['target_version', 'source_hash', 'approval_ref', 'outcome'], as_dict=True)
        if prior:
            require(prior['target_version'] == expected_version and prior['source_hash'] == item['sha256']
                    and prior['approval_ref'] == approval['approval_ref']
                    and prior['outcome'] == 'TECHNICAL_REINDEXED', 'Technical receipt drift')
            # A later withdrawal/revision must not be silently presented as a
            # successful retry of this now-obsolete promotion.
            active = frappe.get_all('HBOS Knowledge Backend Binding', filters={
                'canonical_document_id': document_ids[0], 'version_id': expected_version,
                'binding_revision': item['binding_revision'], 'enabled': 1}, fields=['name','dataset_id','document_id'])
            require(len(active) == 1 and not current['withdrawn']
                    and current['current_version'] == expected_version
                    and current['source_hash'] == item['sha256']
                    and current['ingestion_status'] == 'published'
                    and active[0]['dataset_id'] == item['dataset_id']
                    and active[0]['document_id'] == item['ragflow_document_id'],
                    'Technical receipt is no longer current')
            frappe.db.commit()
            return {'published_documents': 0, 'technical_revisions': 0, 'outcome': 'NOOP', 'receipt_id': receipt}
        version = frappe.db.get_value('HBOS Knowledge Version', expected_version,
            ['canonical_document_id', 'version_json'], as_dict=True)
        require(version and version['canonical_document_id'] == item['canonical_document_id'], 'Version identity changed')
        parent_rows = frappe.db.sql('SELECT * FROM `tabHBOS Knowledge Backend Binding` '
            'WHERE canonical_document_id=%s AND version_id=%s AND enabled=1 FOR UPDATE',
            (item['canonical_document_id'], expected_version), as_dict=True)
        require(len(parent_rows) == 1, 'Ambiguous active parent binding')
        parent = Binding(**json.loads(parent_rows[0]['binding_json']))
        require(parent_rows[0]['name'] == parent.binding_ref
                and all(parent_rows[0][k] == getattr(parent, k) for k in IDENTITY_FIELDS), 'Parent projection drift')
        quality = m._json(row, 'quality_json', {}).get(expected_version, {})
        from .maintenance_task_facts import require_durable_task_acks
        require_durable_task_acks(m._json(row, 'job_json', {}), [item])
        new, evidence = replacement(item, current, json.loads(version['version_json']), parent,
            quality, approval, state['batch_sha256'], iso(time.time()))
        _verify_backend(cfg, item)
        _verify_backend(cfg, {'dataset_id':parent.dataset_id,'ragflow_document_id':parent.document_id,
            'version_id':parent.version_id,'canonical_document_id':parent.canonical_document_id,
            'binding_revision':parent.binding_revision,'upload_sha256':approval['parent_upload_sha256']})
        if approval.get('resume_from_rollback') is not None:
            target=frappe.db.sql('SELECT * FROM `tabHBOS Knowledge Backend Binding` WHERE name=%s FOR UPDATE',
                                (new.binding_ref,),as_dict=True)
            require(len(target)==1,'Retained recovery index binding missing')
            retained=Binding(**json.loads(target[0]['binding_json']))
            require(target[0]['name']==retained.binding_ref
                    and all(target[0][k]==getattr(retained,k) for k in IDENTITY_FIELDS),
                    'Retained recovery projection drift')
            new=reusable_rolled_back_binding(new,retained,target[0]['enabled'],iso(time.time()))
            evidence.update(new_binding=asdict(new),resumed_after_rollback=approval['resume_from_rollback'],
                            retained_target_binding_reused=True)
            frappe.db.set_value('HBOS Knowledge Backend Binding',new.binding_ref,'enabled',1)
        else:
            frappe.get_doc({'doctype': 'HBOS Knowledge Backend Binding',
                **{k: getattr(new, k) for k in IDENTITY_FIELDS},
                'pair_key': physical_pair_key(new.backend, new.dataset_id, new.document_id),
                'binding_json': canonical(asdict(new)), 'enabled': 1}).insert(ignore_permissions=True)
        frappe.db.set_value('HBOS Knowledge Backend Binding', parent.binding_ref, 'enabled', 0)
        # Business version, source bytes, authority and space stay unchanged.
        frappe.db.set_value('HBOS Knowledge Document', document_ids[0], {
            'dataset_id': new.dataset_id, 'parser_revision': item['native_profile']['profile_sha256'],
            'embedding_revision': item['embedding_model'] + '/' + str(item['embedding_dimensions'])})
        frappe.get_doc({'doctype': 'HBOS Knowledge Publication', 'receipt_id': receipt,
            'canonical_document_id': document_ids[0], 'target_version': expected_version,
            'batch_sha256': state['batch_sha256'], 'operation': 'replace',
            'expected_current_version': expected_version, 'source_hash': item['sha256'],
            'reason': 'TECHNICAL_REINDEX: ' + reason.strip(),
            'approval_ref': approval['approval_ref'], 'outcome': 'TECHNICAL_REINDEXED'}).insert(ignore_permissions=True)
        frappe.get_doc({'doctype':'HBOS Knowledge Parse Revision','revision_ref':receipt,
            'canonical_document_id':document_ids[0],'version_id':expected_version,
            'parent_binding_ref':parent.binding_ref,'target_binding_ref':new.binding_ref,
            'profile_sha256':item['native_profile']['profile_sha256'],
            'receipt_json':canonical(evidence)}).insert(ignore_permissions=True)
        # A durable review receipt belongs to this registered candidate batch;
        # the immutable publication row carries the business identity separately.
        quality['parse_revision_receipt'] = evidence
        reviews = m._json(row, 'quality_json', {})
        reviews[expected_version] = quality
        frappe.db.set_value(m.TABLE, batch_id, 'quality_json', canonical(reviews))
        frappe.db.commit()
        return {'published_documents': 0, 'technical_revisions': 1,
            'outcome': 'TECHNICAL_REINDEXED', 'receipt_id': receipt,
            'business_version_changed': False}
    except Exception:
        frappe.db.rollback()
        raise


def rollback_admission(evidence, current, metadata, active, retained, approval, now):
    """Re-check current facts; a rollback never restores old business grants."""
    require(isinstance(approval,dict),'Exact Main rollback approval required')
    require(asdict(active)==evidence['new_binding'] and asdict(retained)==evidence['old_binding'],
            'Technical rollback binding changed')
    require(not current.get('withdrawn') and current.get('ingestion_status')=='published'
            and current.get('current_version')==evidence['version_id']
            and current.get('source_hash')==evidence['source_sha256']
            and current.get('dataset_id')==active.dataset_id,'Current source/version changed')
    require(metadata==evidence['business_metadata'],'Current immutable metadata changed')
    expected={'canonical_document_id':active.canonical_document_id,'version_id':active.version_id,
        'source_sha256':evidence['source_sha256'],'current_binding_ref':active.binding_ref,
        'return_binding_ref':retained.binding_ref,'parent_upload_sha256':evidence['parent_upload_sha256']}
    require(all(approval.get(k)==v for k,v in expected.items()) and approval.get('approval_ref')
            and re.fullmatch('[0-9a-f]{64}',approval.get('review_receipt_sha256','')),
            'Rollback review drift')
    require(active.space_id==retained.space_id and active.version_id==retained.version_id
            and active.canonical_document_id==retained.canonical_document_id,
            'Rollback cannot change scope or business version')
    technical=evidence['old_document_technical_metadata']
    require(isinstance(technical,dict) and technical.get('dataset_id')==retained.dataset_id,
            'Retained technical metadata changed')
    validate_admission(retained,'production',datetime.fromisoformat(now.replace('Z','+00:00')).timestamp())
    return {'schema':'hbos.parse-rollback.v1',**expected,'approval_ref':approval['approval_ref'],
        # The immutable DocType stores direction/profile for both operations.
        'parent_binding_ref':active.binding_ref,'new_binding_ref':retained.binding_ref,
        'profile_hash':hashlib.sha256(canonical(technical).encode()).hexdigest(),
        'review_receipt_sha256':approval['review_receipt_sha256'],'business_version_changed':False,
        'old_authorization_snapshot_restored':False,'both_backend_indexes_retained':True}


def rollback(batch_id, document_ids, expected_version, reason):
    import json,time,frappe
    from . import maintenance as m
    from .execution_plan import iso
    from .metadata_integrity import IDENTITY_FIELDS
    from .reference_admin import _verify_backend
    m.require()
    require(isinstance(document_ids,list) and len(document_ids)==1 and isinstance(reason,str)
            and 3<=len(reason.strip())<=500,'One technical rollback target and reason required')
    try:
        row,frozen,state=m._row(batch_id,True);m.registered(frozen,state)
        items=[i for i in state['items'] if i['canonical_document_id']==document_ids[0]]
        require(len(items)==1 and expected_version==items[0]['version_id'],'Rollback version changed')
        item=items[0];cfg=m.configuration()
        forward='PUB_TECH_'+effective_revision_key(batch_id,item,
            cfg.get('parse_revision_approvals',{}).get(revision_key(batch_id,item)),
            lambda ref:frappe.db.get_value('HBOS Knowledge Parse Revision',ref,'receipt_json'))[:32]
        prior=frappe.db.get_value('HBOS Knowledge Parse Revision',forward,'receipt_json')
        require(prior,'Recorded technical revision required');evidence=json.loads(prior)
        cfg=m.configuration();approval=cfg.get('parse_rollback_approvals',{}).get(forward)
        require(isinstance(approval,dict),'Main rollback approval required')
        ref='PUB_ROLLBACK_'+hashlib.sha256(canonical([forward,approval.get('approval_ref')]).encode()).hexdigest()[:32]
        rows=frappe.db.sql('SELECT name,current_version,source_hash,withdrawn,ingestion_status,dataset_id '
            'FROM `tabHBOS Knowledge Document` WHERE name=%s FOR UPDATE',(document_ids[0],),as_dict=True)
        require(len(rows)==1,'Current document missing');current=rows[0]
        require(frappe.db.get_value('HBOS Knowledge Space',evidence['old_binding']['space_id'],'enabled'),
                'Current space is not enabled')
        bindings=frappe.db.sql('SELECT * FROM `tabHBOS Knowledge Backend Binding` '
            'WHERE canonical_document_id=%s AND version_id=%s FOR UPDATE',
            (document_ids[0],expected_version),as_dict=True)
        old_ref,new_ref=evidence['old_binding']['binding_ref'],evidence['new_binding']['binding_ref']
        by_id={b['name']:b for b in bindings};require(old_ref in by_id and new_ref in by_id,'Retained binding missing')
        old=Binding(**json.loads(by_id[old_ref]['binding_json']));active=Binding(**json.loads(by_id[new_ref]['binding_json']))
        for binding in [old,active]:
            require(all(by_id[binding.binding_ref][k]==getattr(binding,k) for k in IDENTITY_FIELDS),
                    'Binding projection changed')
        enabled=[b['name'] for b in bindings if b['enabled']]
        if frappe.db.exists('HBOS Knowledge Publication',ref):
            require(enabled==[old_ref] and not current['withdrawn'] and current['current_version']==expected_version
                    and current['source_hash']==evidence['source_sha256'] and current['ingestion_status']=='published'
                    and current['dataset_id']==old.dataset_id,'Rollback receipt is no longer current')
            frappe.db.commit();return {'outcome':'NOOP','receipt_id':ref,'technical_revisions':0}
        require(enabled==[new_ref],'Current technical binding changed')
        version=frappe.db.get_value('HBOS Knowledge Version',expected_version,['canonical_document_id','version_json'],as_dict=True)
        require(version and version['canonical_document_id']==document_ids[0],'Version identity changed')
        proof=rollback_admission(evidence,current,json.loads(version['version_json']),active,old,approval,iso(time.time()))
        _verify_backend(cfg,{'dataset_id':old.dataset_id,'ragflow_document_id':old.document_id,
            'version_id':old.version_id,'canonical_document_id':old.canonical_document_id,
            'binding_revision':old.binding_revision,'upload_sha256':evidence['parent_upload_sha256']})
        frappe.db.set_value('HBOS Knowledge Backend Binding',new_ref,'enabled',0)
        frappe.db.set_value('HBOS Knowledge Backend Binding',old_ref,'enabled',1)
        technical=evidence['old_document_technical_metadata'];require(technical.get('dataset_id')==old.dataset_id,'Retained document projection changed')
        frappe.db.set_value('HBOS Knowledge Document',document_ids[0],technical)
        frappe.get_doc({'doctype':'HBOS Knowledge Publication','receipt_id':ref,'canonical_document_id':document_ids[0],
            'target_version':expected_version,'batch_sha256':state['batch_sha256'],'operation':'replace',
            'expected_current_version':expected_version,'source_hash':evidence['source_sha256'],
            'reason':'TECHNICAL_BINDING_ROLLBACK: '+reason.strip(),'approval_ref':approval['approval_ref'],
            'outcome':'TECHNICAL_ROLLED_BACK'}).insert(ignore_permissions=True)
        frappe.get_doc({'doctype':'HBOS Knowledge Parse Revision','revision_ref':ref,
            'canonical_document_id':document_ids[0],'version_id':expected_version,'parent_binding_ref':new_ref,
            'target_binding_ref':old_ref,'profile_sha256':proof['profile_hash'],
            'receipt_json':canonical(proof)}).insert(ignore_permissions=True)
        frappe.db.commit();return {'outcome':'TECHNICAL_ROLLED_BACK','receipt_id':ref,'technical_revisions':1,'business_version_changed':False}
    except Exception:frappe.db.rollback();raise
