"""Local administrator publication from verified ingestion state; no public upload API."""
import json
from dataclasses import asdict
from pathlib import Path
from .execution_plan import Binding, iso, validate_admission
from .metadata_integrity import physical_pair_key
from .service_http import canonical

def publish(manifest_path):
    import frappe,time
    from .shared_reference import configuration
    cfg=configuration();frappe.only_for('System Manager')
    state=json.loads(Path(manifest_path).read_text())
    assert state['batch_sha256']==cfg['approved_batch_sha256']
    space_id='DEPT_'+state['department_key'].upper()
    assert space_id in cfg['approved_space_ids']
    if not frappe.db.exists('HBOS Knowledge Space',space_id):
        frappe.get_doc({'doctype':'HBOS Knowledge Space','space_id':space_id,'title':state['department_title'],
                        'required_role':cfg['reader_role'],'enabled':1}).insert(ignore_permissions=True)
    count=0
    for item in state['items']:
        if item['status']!='parsed/indexed':continue
        assert item['internal_sharing_confirmed'] and item['owner_inclusion_confirmed']
        assert item['dataset_id'] in cfg['approved_dataset_ids'] and item['canonical_document_id'] in cfg['approved_document_ids']
        doc,version=item['canonical_document_id'],item['version_id']
        if not frappe.db.exists('HBOS Knowledge Document',doc):
            frappe.get_doc({'doctype':'HBOS Knowledge Document','document_id':doc,'source_hash':item['sha256'],
                'source_reference':'OWNER_LOCAL_ONLY:'+state['run_id'],'version':item.get('business_version'),
                'ingestion_status':'reviewed','approval_status':'CONTROLLED_REFERENCE_REVIEWED',
                'dataset_id':item['dataset_id'],'embedding_revision':'qwen3.7-text-embedding/1024',
                'parser_revision':'ragflow-v0.27.0/naive','withdrawn':0}).insert(ignore_permissions=True)
        version_data={k:item.get(k) for k in ['sha256','upload_sha256','document_number','business_version','source_type','authority_status']}
        if not frappe.db.exists('HBOS Knowledge Version',version):
            frappe.get_doc({'doctype':'HBOS Knowledge Version','version_id':version,'canonical_document_id':doc,
                'version_json':canonical(version_data)}).insert(ignore_permissions=True)
        else:
            assert frappe.db.get_value('HBOS Knowledge Version',version,'version_json')==canonical(version_data)
        frappe.db.set_value('HBOS Knowledge Document',doc,{'current_version':version,'source_hash':item['sha256'],
            'version':item.get('business_version'),'ingestion_status':'published','withdrawn':0})
        # A new immutable binding is required for every technical version.
        reference='BIND_'+version.removeprefix('VER_')
        b=Binding(space_id,doc,version,item.get('business_version'),item['dataset_id'],item['ragflow_document_id'],
            'DEPARTMENT_'+state['department_key'].upper(),reference,item['binding_revision'],item['source_type'],item['authority_status'],
            '2026-10-08T00:00:00Z',title=item['title'][:240],document_number=item.get('document_number'))
        validate_admission(b,'production',time.time())
        if not frappe.db.exists('HBOS Knowledge Backend Binding',reference):
            frappe.get_doc({'doctype':'HBOS Knowledge Backend Binding',**{k:getattr(b,k) for k in
                ['binding_ref','space_id','canonical_document_id','version_id','dataset_id','backend','document_id','dataset_alias','binding_revision']},
                'pair_key':physical_pair_key(b.backend,b.dataset_id,b.document_id),'binding_json':canonical(asdict(b)),
                'enabled':1}).insert(ignore_permissions=True)
        else:
            assert frappe.db.get_value('HBOS Knowledge Backend Binding',reference,'binding_json')==canonical(asdict(b))
        count+=1
    frappe.db.commit();return {'published_documents':count,'batch_sha256':state['batch_sha256']}

def get_catalog(runtime,actor):
    from .public_strings import safe_string
    def project(snapshot):
        titles=dict(snapshot.space_titles);seen=set();out=[]
        for b in snapshot.bindings:
            key=(b.space_id,b.canonical_document_id,b.version_id)
            if key in seen:continue
            try:validate_admission(b,runtime.profile,runtime.provider.clock())
            except Exception:continue
            seen.add(key)
            out.append({'document_id':safe_string(b.canonical_document_id,120),'title':safe_string(b.title,240,nullable=True),
                'space_id':b.space_id,'department':safe_string(titles.get(b.space_id,''),120),
                'document_number':safe_string(b.document_number,120,nullable=True),'version':b.business_version,
                'status_note':'内部参考／有效性待核' if b.authority_status=='CONTROLLED_REFERENCE_REVIEWED' else b.authority_status})
        return {'documents':out}
    value=project(runtime.provider._current(actor,runtime.client))
    if value!=project(runtime.provider._current(actor,runtime.client)):raise RuntimeError('Catalog changed')
    return value
