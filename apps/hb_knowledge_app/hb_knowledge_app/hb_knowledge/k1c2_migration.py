import os
import frappe

def guard():
    if (frappe.local.site!=os.environ.get('HBOS_K1C2_SITE') or frappe.conf.get('hbos_k1c2_run_id')!=os.environ.get('HBOS_K1C2_RUN_ID')
        or not frappe.conf.get('hbos_k1c2_enabled') or frappe.conf.db_host!='db'):
        frappe.throw('Unregistered integration target',frappe.PermissionError)

def add_indexes():
    if not frappe.conf.get('hbos_k1c2_enabled'): return
    guard()
    frappe.db.add_index('HBOS Knowledge Reference',['actor_key','consume_until'],'k1c2_reference_subject_ttl')
    frappe.db.add_index('HBOS Knowledge Reference',['publication_id','publication_state'],'k1c2_reference_publication')
    frappe.db.add_index('HBOS Knowledge Audit',['publication_id','publication_state'],'k1c2_audit_publication')
    frappe.db.add_index('HBOS Knowledge Backend Binding',['space_id','enabled'],'k1c2_binding_scope')
    frappe.db.add_index('HBOS Knowledge Backend Binding',['version_id','enabled'],'k1c2_binding_version')
    ensure_native_assets()

def ensure_native_assets():
    import pathlib,json
    guard()
    from hbos_portal.auth.migration import _ensure_app_assets
    _ensure_app_assets('frappe')
    out=pathlib.Path(frappe.local.sites_path).resolve()/'assets/assets.json'
    mapping=json.loads(out.read_text()) if out.exists() else {}
    for part in ['css','js']:
        for p in pathlib.Path(frappe.get_app_path('frappe','public','dist',part)).glob('*'):
            bits=p.name.split('.')
            if p.is_file() and len(bits)>3 and 'bundle' in bits:
                mapping['.'.join(bits[:-2])+'.'+bits[-1]]='/assets/frappe/dist/'+part+'/'+p.name
    out.write_text(json.dumps(mapping))

def seed():
    import json,hashlib
    from pathlib import Path
    from .execution_plan import Binding
    from .frappe_authority import configuration
    from .service_http import canonical
    from .metadata_integrity import physical_pair_key
    import redis
    guard(); cfg=configuration()
    if frappe.db.count('HBOS Knowledge Reference') or frappe.db.count('HBOS Knowledge Space'):
        frappe.throw('Seed requires pristine registered synthetic Site')
    private=json.loads(Path('/run/k1c2/init.json').read_text())
    frappe.db.set_single_value('System Settings','time_zone','UTC')
    for role in ['K1C2 QA','K1C2 Production','K1C2 Shared']:
        if not frappe.db.exists('Role',role):
            frappe.get_doc({'doctype':'Role','role_name':role,'desk_access':0}).insert(ignore_permissions=True)
    for row in private['users']:
        frappe.get_doc({'doctype':'User','email':row['user'],'first_name':row['label'],'enabled':1,
              'user_type':'Website User','send_welcome_email':0,'new_password':row['password'],
              'roles':[{'role':r} for r in row['roles']]}).insert(ignore_permissions=True)
    for space,role in [('SPACE_QA_SYNTHETIC','K1C2 QA'),('SPACE_PROD_SYNTHETIC','K1C2 Production'),('SPACE_SHARED_SYNTHETIC','K1C2 Shared')]:
        frappe.get_doc({'doctype':'HBOS Knowledge Space','space_id':space,'required_role':role,'enabled':1}).insert(ignore_permissions=True)
    for doc in ['DOC_SYNTHETIC_SHARED','DOC_SYNTHETIC_PROD']:
        frappe.get_doc({'doctype':'HBOS Knowledge Document','document_id':doc,'source_hash':hashlib.sha256(doc.encode()).hexdigest(),
            'ingestion_status':'published','withdrawn':0}).insert(ignore_permissions=True)
    for vid,doc in [('VERSION_SYNTHETIC_SHARED_1','DOC_SYNTHETIC_SHARED'),('VERSION_SYNTHETIC_PROD_1','DOC_SYNTHETIC_PROD')]:
        frappe.get_doc({'doctype':'HBOS Knowledge Version','version_id':vid,'canonical_document_id':doc,
             'version_json':canonical({'source_type':'SYNTHETIC_TEST','business_version':None,'marker_only':True})}).insert(ignore_permissions=True)
        frappe.db.set_value('HBOS Knowledge Document',doc,'current_version',vid)
    for raw in cfg['synthetic_bindings']:
        b=Binding(**raw)
        frappe.get_doc({'doctype':'HBOS Knowledge Backend Binding','binding_ref':b.binding_ref,'space_id':b.space_id,
            'canonical_document_id':b.canonical_document_id,'version_id':b.version_id,'dataset_id':b.dataset_id,
            'backend':b.backend,'document_id':b.document_id,'dataset_alias':b.dataset_alias,'binding_revision':b.binding_revision,
            'pair_key':physical_pair_key(b.backend,b.dataset_id,b.document_id),
            'binding_json':canonical(raw),'enabled':1}).insert(ignore_permissions=True)
    frappe.db.commit()
    client=redis.Redis.from_url(cfg['redis_url'],decode_responses=True)
    if not client.set(cfg['prefix']+'ready',cfg['run_id'],nx=True):
        frappe.throw('Redis recovery sentinel already initialized')
    return {'site':frappe.local.site,'synthetic_users':len(private['users']),'bindings':3,'seeded':True}
