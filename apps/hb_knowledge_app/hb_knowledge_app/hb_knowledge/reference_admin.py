"""Local administrator publication from verified ingestion state; no public upload API."""
import hashlib, json, re, time
from dataclasses import asdict
from pathlib import Path
from .execution_plan import Binding, iso, validate_admission
from .metadata_integrity import physical_pair_key, IDENTITY_FIELDS
from .service_http import canonical
from .publication import PublicationConflict, decide, receipt_id, verify_frozen_target, select_publication_items
from .errors import KnowledgeError

def _require(condition, message):
    if not condition:
        raise PublicationConflict(message)


def _verify_backend(cfg, item):
    """Private admin port; employees never receive credentials or originals."""
    import requests
    from urllib.parse import urlparse
    auth = json.loads(Path(cfg['publication_ragflow_auth_file']).read_text())
    base = auth['base_url'].rstrip('/')
    _require(urlparse(base).hostname in {'127.0.0.1', 'localhost', 'host.docker.internal'}
             and urlparse(base).scheme == 'http', 'Unregistered publication backend')
    dataset, document = item['dataset_id'], item['ragflow_document_id']
    with requests.Session() as session:
        session.trust_env = False
        session.headers['Authorization'] = 'Bearer ' + auth['token']
        response = session.get(base + f'/api/v1/datasets/{dataset}/documents',
                               params={'id': document, 'page_size': 2}, timeout=(3, 30), allow_redirects=False)
        response.raise_for_status()
        value = response.json()
        docs = value.get('data', {}).get('docs', [])
        _require(value.get('code') == 0 and len(docs) == 1 and docs[0]['id'] == document,
                 'Backend document cannot be verified')
        actual = docs[0]
        expected = {k: item[k] for k in ('version_id', 'canonical_document_id', 'binding_revision')}
        _require(actual.get('meta_fields') == expected and int(actual.get('chunk_count', 0)) > 0
                 and str(actual.get('run')).upper() in {'DONE', '3'}, 'Backend binding is not indexed')
        # Stream hashing is bounded in memory; it verifies the actual uploaded derivative.
        with session.get(base + f'/api/v1/datasets/{dataset}/documents/{document}',
                         timeout=(3, 60), stream=True, allow_redirects=False) as original:
            original.raise_for_status()
            sha = hashlib.sha256()
            for block in original.iter_content(65536):
                sha.update(block)
        _require(sha.hexdigest() == item['upload_sha256'], 'Backend source hash mismatch')


def publish(manifest_path, operation='publish', expected_current_version=None, reason=None, approval_ref=None,
            selected_document_ids=None):
    import frappe
    from .shared_reference import configuration
    cfg=configuration();frappe.only_for('System Manager')
    state=json.loads(Path(manifest_path).read_text())
    _require(state['batch_sha256'] in cfg.get('approved_batch_sha256s', [cfg.get('approved_batch_sha256')]),
             'Batch is not approved')
    space_id='DEPT_'+state['department_key'].upper()
    _require(space_id in cfg['approved_space_ids'], 'Space is not approved')
    allowed_items = cfg.get('approved_publication_items', {}).get(state['batch_sha256'])
    items=select_publication_items(state,selected_document_ids)
    selection_hash=hashlib.sha256(canonical(sorted(i['canonical_document_id'] for i in items)).encode()).hexdigest()
    if selected_document_ids is not None:
        approved=cfg.get('approved_publication_subsets',{}).get(selection_hash)
        _require(isinstance(approved,dict) and approved.get('batch_sha256')==state['batch_sha256']
                 and approved.get('canonical_document_ids')==sorted(selected_document_ids)
                 and approved.get('approval_ref')
                 and re.fullmatch(r'[0-9a-f]{64}',approved.get('quality_evidence_sha256','')),
                 'Exact quality-verified publication subset approval is required')
    results=[]
    try:
        # Lock the space to serialize first publication and guard a batch atomically.
        if not frappe.db.exists('HBOS Knowledge Space',space_id):
            frappe.get_doc({'doctype':'HBOS Knowledge Space','space_id':space_id,'title':state['department_title'],
                            'required_role':cfg['reader_role'],'enabled':1}).insert(ignore_permissions=True)
        spaces=frappe.db.sql('SELECT name,enabled,required_role FROM `tabHBOS Knowledge Space` WHERE name=%s FOR UPDATE',
                             (space_id,),as_dict=True)
        _require(len(spaces)==1 and spaces[0]['enabled'] and spaces[0]['required_role']==cfg['reader_role'], 'Space changed')
        seen=set()
        for item in items:
            doc,version=item['canonical_document_id'],item['version_id']
            _require(doc not in seen, 'Duplicate canonical item in publication');seen.add(doc)
            _require(item.get('internal_sharing_confirmed') and item.get('owner_inclusion_confirmed'), 'Item is not approved')
            _require(item['dataset_id'] in cfg['approved_dataset_ids'] and doc in cfg['approved_document_ids'], 'Item is outside approved scope')
            _require(all(re.fullmatch(r'[0-9a-f]{64}',item.get(k,'')) for k in ('sha256','upload_sha256')), 'Invalid source hash')
            _require(all(re.fullmatch(r'[0-9a-f]{32}',item.get(k,'')) for k in ('dataset_id','ragflow_document_id')), 'Invalid physical identity')
            if allowed_items is not None:
                frozen=allowed_items.get(doc)
                verify_frozen_target(item, frozen, state['department_key'])
            else:
                # Old approved R2 batches may replay, but cannot introduce new identities.
                _require(frappe.db.exists('HBOS Knowledge Version',version), 'Frozen approved publication target is required')
            rows=frappe.db.sql('SELECT name,document_id,current_version,source_hash,withdrawn,ingestion_status,dataset_id '
                               'FROM `tabHBOS Knowledge Document` WHERE name=%s FOR UPDATE',(doc,),as_dict=True)
            current=rows[0] if rows else None
            if current:_require(current['document_id']==doc, 'Document identity drift')
            outcome=decide(current,version,operation,expected_current_version)
            receipt=receipt_id(state['batch_sha256'],item,operation,expected_current_version,approval_ref if operation!='publish' else None)
            if outcome=='SKIPPED_WITHDRAWN':
                results.append({'document_id':doc,'outcome':outcome});continue
            if operation!='publish':
                intent={'batch_sha256':state['batch_sha256'],'canonical_document_id':doc,'operation':operation,
                        'expected_current_version':expected_current_version,'version_id':version,'sha256':item['sha256'],
                        'approval_ref':approval_ref,'reason':reason}
                _require(reason and approval_ref and intent in cfg.get('approved_publication_intents',[]), 'Separate operation approval is required')
                if outcome!='RECEIPT_REQUIRED':
                    _require(not frappe.db.exists('HBOS Knowledge Publication',receipt), 'Operation approval was already consumed')
            version_data={k:item.get(k) for k in ['sha256','upload_sha256','document_number','business_version','source_type','authority_status']}
            old_version=frappe.db.get_value('HBOS Knowledge Version',version,['name','version_id','canonical_document_id','version_json'],as_dict=True)
            if old_version:
                _require(old_version['name']==version and old_version['version_id']==version
                         and old_version['canonical_document_id']==doc and old_version['version_json']==canonical(version_data), 'Immutable version drift')
            reference='BIND_'+version.removeprefix('VER_')
            old_binding=frappe.db.get_value('HBOS Knowledge Backend Binding',reference,['name',*IDENTITY_FIELDS,'pair_key','binding_json','enabled'],as_dict=True)
            valid_from=json.loads(old_binding['binding_json'])['valid_from'] if old_binding else iso(time.time())
            b=Binding(space_id,doc,version,item.get('business_version'),item['dataset_id'],item['ragflow_document_id'],
                'DEPARTMENT_'+state['department_key'].upper(),reference,item['binding_revision'],item['source_type'],item['authority_status'],
                valid_from,title=item['title'][:240],document_number=item.get('document_number'))
            validate_admission(b,'production',time.time())
            if old_binding:
                _require(old_binding['name']==reference and all(old_binding[k]==getattr(b,k) for k in IDENTITY_FIELDS)
                         and old_binding['pair_key']==physical_pair_key(b.backend,b.dataset_id,b.document_id)
                         and old_binding['binding_json']==canonical(asdict(b)) and old_binding['enabled'], 'Immutable binding drift')
            _verify_backend(cfg,item)
            if outcome in {'NOOP','RECEIPT_REQUIRED'}:
                _require(old_version and old_binding and current['source_hash']==item['sha256']
                         and current['dataset_id']==item['dataset_id'], 'Published source consistency failed')
                if outcome=='RECEIPT_REQUIRED':
                    _require(frappe.db.exists('HBOS Knowledge Publication',receipt), 'CONFLICT: no receipt for this operation')
                results.append({'document_id':doc,'outcome':'NOOP',
                                'receipt_id':receipt if frappe.db.exists('HBOS Knowledge Publication',receipt) else None});continue
            if not current:
                frappe.get_doc({'doctype':'HBOS Knowledge Document','document_id':doc,'source_hash':item['sha256'],
                    'source_reference':'OWNER_LOCAL_ONLY:'+state['run_id'],'version':item.get('business_version'),
                    'ingestion_status':'reviewed','approval_status':item['authority_status'],'dataset_id':item['dataset_id'],
                    'embedding_revision':'qwen3.7-text-embedding/1024','parser_revision':'ragflow-v0.27.0/naive','withdrawn':0}).insert(ignore_permissions=True)
            if not old_version:
                frappe.get_doc({'doctype':'HBOS Knowledge Version','version_id':version,'canonical_document_id':doc,
                                'version_json':canonical(version_data)}).insert(ignore_permissions=True)
            frappe.db.set_value('HBOS Knowledge Document',doc,{'current_version':version,'source_hash':item['sha256'],
                'dataset_id':item['dataset_id'],'version':item.get('business_version'),'ingestion_status':'published','withdrawn':0})
            if not old_binding:
                frappe.get_doc({'doctype':'HBOS Knowledge Backend Binding',**{k:getattr(b,k) for k in IDENTITY_FIELDS},
                    'pair_key':physical_pair_key(b.backend,b.dataset_id,b.document_id),'binding_json':canonical(asdict(b)),
                    'enabled':1}).insert(ignore_permissions=True)
            frappe.get_doc({'doctype':'HBOS Knowledge Publication','receipt_id':receipt,'canonical_document_id':doc,
                'target_version':version,'batch_sha256':state['batch_sha256'],'operation':operation,
                'expected_current_version':expected_current_version,'source_hash':item['sha256'],
                'reason':reason,'approval_ref':approval_ref or item.get('approval_ref'),'outcome':outcome}).insert(ignore_permissions=True)
            results.append({'document_id':doc,'outcome':outcome,'receipt_id':receipt})
        frappe.db.commit()
    except Exception as exc:
        frappe.db.rollback()
        if isinstance(exc,frappe.QueryDeadlockError):
            raise PublicationConflict('CONFLICT: concurrent publisher changed state') from None
        raise
    return {'published_documents':sum(r['outcome'] in {'PUBLISHED','REPLACED','RESTORED'} for r in results),
            'batch_sha256':state['batch_sha256'],'selection_sha256':selection_hash,
            'selected_documents':len(items),'frozen_items':len(state['items']),'results':results}

def _catalog_projection(runtime, snapshot):
    from .public_strings import safe_string
    from .spaces import authorized_spaces
    allowed=authorized_spaces(snapshot,actions=('knowledge.spaces','knowledge.search'))
    titles=dict(snapshot.space_titles);seen=set();out=[]
    for b in snapshot.bindings:
        key=(b.space_id,b.canonical_document_id,b.version_id)
        if (key in seen or b.space_id not in allowed
                or b.dataset_id not in snapshot.allowed_datasets):continue
        try:validate_admission(b,runtime.profile,runtime.provider.clock())
        except KnowledgeError:continue
        seen.add(key)
        out.append({'document_id':safe_string(b.canonical_document_id,120),'title':safe_string(b.title,240,nullable=True),
            'space_id':safe_string(b.space_id,120),'department':safe_string(titles.get(b.space_id,''),120),
            'document_number':safe_string(b.document_number,120,nullable=True),'version':b.business_version,
            'status_note':'内部参考／有效性待核' if b.authority_status in {'CONTROLLED_REFERENCE_REVIEWED','INTERNAL_REFERENCE_REVIEWED'} else b.authority_status})
    return sorted(out,key=lambda d:(d['department'],d['title'] or '',d['document_id'],d['space_id']))


def _catalog_read(runtime,actor,project):
    value=project(_catalog_projection(runtime,runtime.provider._current(actor,runtime.client)))
    runtime.checkpoint('before_catalog_return')
    if value!=project(_catalog_projection(runtime,runtime.provider._current(actor,runtime.client))):
        raise KnowledgeError('SCOPE_REJECTED')
    return value


def get_catalog(runtime,actor):
    return _catalog_read(runtime,actor,lambda docs:{'documents':docs})


def _page_number(value,maximum):
    if isinstance(value,str) and re.fullmatch(r'[0-9]{1,6}',value):value=int(value)
    if type(value) is not int or not 1<=value<=maximum:raise KnowledgeError('INVALID_REQUEST')
    return value


def get_catalog_page(runtime,actor,*,query=None,space_id=None,page=1,page_size=12):
    from .public_strings import safe_string
    page=_page_number(page,100000);page_size=_page_number(page_size,50)
    if query is not None:query=safe_string(query,240).strip().casefold()
    if space_id is not None:space_id=safe_string(space_id,120)
    def project(docs):
        selected=[d for d in docs if (not space_id or d['space_id']==space_id)
                  and (not query or any(query in (d[k] or '').casefold()
                                       for k in ('title','document_number','department')))]
        start=(page-1)*page_size
        return {'documents':selected[start:start+page_size],'total':len(selected),'page':page,'page_size':page_size}
    return _catalog_read(runtime,actor,project)
