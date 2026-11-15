"""Stage one browser upload packet and queue homogeneous native groups."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import secrets
import time
import unicodedata

import frappe

from . import maintenance as m
from .errors import KnowledgeError
from .maintenance_access import require
from .maintenance_batch import _safe_relative_path
from .maintenance_contract import DEPARTMENTS, admit_file, configured_max_source_bytes, initial_state
from .maintenance_managed import policy, queue_kind
from .maintenance_native_upload import apply_profile
from .shared_reference import configuration


def upload_group(department, sharing, relative_paths, space_id):
    require()
    cfg = configuration()
    if not policy(cfg) or department not in DEPARTMENTS or sharing not in (True,1,'1','true'):
        raise KnowledgeError('INVALID_REQUEST')
    from .maintenance_spaces import assign_space, intake_space
    template = intake_space(cfg,space_id,department).get('maintenance_template') or 'auto'
    try:
        paths = json.loads(relative_paths) if isinstance(relative_paths,str) else relative_paths
    except ValueError:
        raise KnowledgeError('INVALID_REQUEST') from None
    files = frappe.local.request.files
    sources = files.getlist('file')
    if set(files)!= {'file'} or not isinstance(paths,list) or not 1<=len(sources)==len(paths)<=4:
        raise KnowledgeError('INVALID_REQUEST')
    limit = configured_max_source_bytes(cfg)
    base = Path(cfg['maintenance_upload_root'])
    if base.resolve(strict=True)!=base:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    directory = base/secrets.token_hex(16)
    directory.mkdir(mode=0o2770)
    root=directory/'source'
    root.mkdir(mode=0o2770)
    rows = []
    path_indices = {}
    path_keys = set()
    total = 0
    for index, (source, raw_path) in enumerate(zip(sources,paths,strict=True)):
        row = {'index':index}
        rows.append(row)
        try:
            relative = _safe_relative_path(raw_path)
            if Path(relative).name!=source.filename or len(Path(relative).parts)>29:
                raise KnowledgeError('INVALID_REQUEST')
            relative = m.managed_relative_path(relative, department)
            key = unicodedata.normalize('NFC',relative.as_posix()).casefold()
            if key in path_keys:
                raise KnowledgeError('IDENTITY_CONFLICT')
            raw = source.stream.read(limit+1)
            total += len(raw)
            if total>limit:
                raise KnowledgeError('BATCH_SOURCE_SIZE_LIMIT_EXCEEDED')
            _, digest = admit_file(source.filename,raw,max_bytes=limit)
            target = root/relative
            target.parent.mkdir(mode=0o2770,parents=True,exist_ok=True)
            with target.open('xb') as stream:
                stream.write(raw)
            target.chmod(0o640)
            path_keys.add(key)
            path_indices[relative.as_posix()] = index
            row.update(sha256=digest, relative_path=relative.as_posix())
        except KnowledgeError as error:
            row.update(status='SOURCE_EXCEPTION',queue_error=error.code)
    if not path_indices:
        return {'items':rows,'queued_jobs':0}
    from knowledge_service.ingestion import approve, canonical, plan, save
    registry = directory/'registry.json'
    save(registry,m._registry())
    approval = 'NATIVE_UPLOAD:'+frappe.session.user+':'+hashlib.sha256(
        canonical([(r.get('relative_path'),r.get('sha256')) for r in rows])).hexdigest()
    planned = plan(root,department,DEPARTMENTS[department],directory/'planned.json',approval,registry,
                   retain_unreadable_source=True)
    accepted = []
    for item in planned['items']:
        row = rows[path_indices[item['relative_path']]]
        if row['sha256']!=item['sha256']:
            raise KnowledgeError('SOURCE_CHANGED')
        disposition = item['disposition']
        row['relationship'] = disposition
        if disposition in ('CONFLICT','UPDATE_CANDIDATE'):
            row.update(status='SOURCE_EXCEPTION',queue_error='IDENTITY_CONFLICT')
        elif disposition=='SAME_CONTENT_SKIP':
            row.update(status='DUPLICATE',job_id=None)
        else:
            accepted.append(item)
    planned['items'] = accepted
    if not accepted:
        return {'items':rows,'queued_jobs':0}
    apply_profile(planned,cfg,template,mixed_formats=True)
    assign_space(planned,cfg,space_id,department)
    groups = defaultdict(list)
    for item in accepted:
        profile = item.get('native_profile')
        key = (queue_kind(item),profile['candidate_patch_sha256']) if profile else ('SOURCE_REPAIR',item['relative_path'])
        groups[key].append(item)
    jobs = 0
    from .managed_source_registry import register
    for index,(key,items) in enumerate(groups.items()):
        group = {**planned,'items':items}
        group['batch_sha256'] = hashlib.sha256(canonical({k:v for k,v in group.items() if k!='batch_sha256'})).hexdigest()
        draft = directory/f'group-{index}.planned.json'
        save(draft,group)
        frozen = approve(draft,directory/f'group-{index}.frozen.json',approval)
        try:
            register(cfg,frozen)
        except (ValueError,OSError):
            raise KnowledgeError('POLICY_UNAVAILABLE') from None
        batch = m.register_batch(frozen,initial_state(frozen),'浏览器批量导入',frappe.session.user)
        frappe.db.set_value(m.TABLE,batch,'job_json',m.canonical({'managed_intake':True,
            'requested_by':frappe.session.user,'requested_at':time.time(),'status':'Imported'}))
        frappe.db.commit()
        queued = None
        failure = None
        if key[0]=='SOURCE_REPAIR':
            failure = items[0].get('source_inspection_error') or 'SOURCE_CONVERSION_REQUIRED'
        else:
            try:
                queued = m.queue(batch,[item['canonical_document_id'] for item in items])
            except KnowledgeError as error:
                frappe.db.rollback()
                failure=error.code
        if failure:
            frappe.db.set_value(m.TABLE,batch,{'last_error':failure})
            frappe.db.commit()
        jobs += bool(queued)
        for item in items:
            row = rows[path_indices[item['relative_path']]]
            row.update(batch_id=batch,job_id=queued['job_id'] if queued else None,
                       status='QUEUED' if queued else 'REPAIR_REQUIRED',queue_error=failure)
    return {'items':rows,'queued_jobs':jobs}
