"""Original-directory metadata; callers supply only freshly authorized rows."""
import functools
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from .errors import KnowledgeError
from .public_strings import safe_string

MAP = Path(os.environ.get('HBOS_SOURCE_DIRECTORY_FILE','/run/hbos-reference/source-directory.json'))
ROOT = 'SOURCE_ROOT'
ALLOWED_ROOTS = ('安全部门','法规文档','人事部门','设备部建模图','生产部门','无菌车间')

@functools.lru_cache(maxsize=2)
def _read_map(path, file_identity):
    data=json.loads(path.read_text())
    if data.get('schema_version') not in (1,2) or not isinstance(data.get('by_version'),dict):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    return data['by_version']

def registry_entries():
    try:metadata=MAP.stat()
    except FileNotFoundError:return {}
    identity=(metadata.st_ino,metadata.st_ctime_ns,metadata.st_mtime_ns,metadata.st_size)
    try:return _read_map(MAP,identity)
    except (OSError,ValueError,TypeError):raise KnowledgeError('POLICY_UNAVAILABLE') from None

def directories(binding, *, registry=None):
    entry=(registry_entries() if registry is None else registry).get(binding.version_id)
    if not entry or entry.get('canonical_document_id')!=binding.canonical_document_id:return []
    out=[]
    for parts in entry.get('directories',[]):
        if (not isinstance(parts,list) or not 1<=len(parts)<=30
                or parts[0] not in ALLOWED_ROOTS):raise KnowledgeError('POLICY_UNAVAILABLE')
        for segment in parts:
            safe_string(segment,240)
            if not segment or segment in {'.','..'} or '/' in segment or '\\' in segment:
                raise KnowledgeError('POLICY_UNAVAILABLE')
        if parts not in out:out.append(parts)
    return out

def folder_id(parts):
    return ROOT if not parts else 'FOLDER_'+hashlib.sha256(json.dumps(parts,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:24]

def _locations(document, *, registry=None):
    """Read positions only after the caller has authorized this exact version."""
    entry=(registry_entries() if registry is None else registry).get(document.get('version_id'))
    if not entry or 'occurrences' not in entry:return None
    if entry.get('canonical_document_id')!=document['document_id']:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    values=entry['occurrences']
    if not isinstance(values,list) or len(values)>200:raise KnowledgeError('POLICY_UNAVAILABLE')
    out=[];seen=set();identifiers=set()
    for value in values:
        if not isinstance(value,dict) or set(value)!={'occurrence_id','relative_path','content_sha256'}:
            raise KnowledgeError('POLICY_UNAVAILABLE')
        name=value['occurrence_id'];path=value['relative_path'];sha=value['content_sha256']
        if (not isinstance(name,str) or not re.fullmatch(r'OCC-[a-f0-9]{24}',name)
                or not isinstance(sha,str) or not re.fullmatch(r'[a-f0-9]{64}',sha)
                or not isinstance(path,str)):
            raise KnowledgeError('POLICY_UNAVAILABLE')
        parts=path.split('/')
        if not 2<=len(parts)<=31 or parts[0] not in ALLOWED_ROOTS:
            raise KnowledgeError('POLICY_UNAVAILABLE')
        for segment in parts:
            safe_string(segment,240)
            if not segment or segment in {'.','..'} or '\\' in segment:
                raise KnowledgeError('POLICY_UNAVAILABLE')
        if path in seen or name in identifiers:raise KnowledgeError('POLICY_UNAVAILABLE')
        seen.add(path);identifiers.add(name);out.append((name,parts[:-1],parts[-1]))
    return out


def employee_locations(document, registry):
    positions = _locations(document, registry=registry)
    if positions is None:
        return [(tuple(parts), None, None) for parts in document.get('source_directories', ())]
    locations = []
    for _, parts, filename in positions:
        extension = Path(filename).suffix[1:].lower()
        locations.append((tuple(parts), filename, extension if re.fullmatch('[a-z0-9]{1,12}', extension) else None))
    return sorted(locations)


def _catalogue_term(value):
    normalized = unicodedata.normalize('NFKC', value or '').casefold()
    return ''.join('-' if unicodedata.category(c) == 'Pd' or c == '−' else c
                   for c in normalized if not c.isspace())


def _catalogue_revision(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def employee_page(documents, *, query, category_ids, file_format, sort, page, page_size):
    """Search the fresh authorized version set with local paths as filters."""
    categories = {}
    formats = set()
    for document in documents:
        for parts, _, extension in document['_source_locations']:
            for depth in range(1, len(parts) + 1):
                prefix = parts[:depth]
                categories[folder_id(prefix)] = prefix
            if extension:
                formats.add(extension)
    if any(category not in categories for category in category_ids):
        raise KnowledgeError('SCOPE_REJECTED')
    prefixes = [categories[category] for category in category_ids]
    keyword = _catalogue_term(query)
    rows = {}
    for document in documents:
        locations = document['_source_locations']
        matching = [
            (parts, filename, extension) for parts, filename, extension in locations
            if (not prefixes or any(parts[:len(prefix)] == prefix for prefix in prefixes))
            and (not file_format or extension == file_format)
        ]
        if (prefixes or file_format) and not matching:
            continue
        title = _catalogue_term(document['title'])
        number = _catalogue_term(document['document_number'])
        if keyword and not (
            keyword in title or keyword in number
            or any(keyword in _catalogue_term(filename) for _, filename, _ in matching)
        ):
            continue
        identity = (document['document_id'], document['version_id'])
        if identity in rows:
            continue
        row = {key: value for key, value in document.items() if not key.startswith('_')}
        paths = dict.fromkeys(parts for parts, _, _ in matching + locations)
        row['source_directories'] = [list(parts) for parts in paths]
        row['file_formats'] = sorted({extension for _, _, extension in matching if extension})
        rows[identity] = (row, title, number)
    ranked = sorted(rows.values(), key=lambda item: (item[1], item[2], item[0]['document_id'], item[0]['version_id']),
                    reverse=sort == 'title_desc')
    if sort == 'relevance' and keyword:
        ranked.sort(key=lambda item: keyword not in item[1:])
    start = (page - 1) * page_size
    return {
        'documents': [item[0] for item in ranked[start:start + page_size]],
        'total_documents': len(ranked), 'page': page, 'page_size': page_size,
        'category_options': [{'category_id': category, 'path': list(path)}
                             for category, path in sorted(categories.items(), key=lambda item: item[1])],
        'format_options': sorted(formats),
        'applied_filters': {'query': query, 'category_ids': category_ids, 'format': file_format, 'sort': sort},
        'corpus_revision': _catalogue_revision([
            (row['document_id'], row['version_id'], row['_binding_revision']) for row in documents
        ]),
        'directory_revision': _catalogue_revision([
            (row['document_id'], row['version_id'], row['_source_locations']) for row in documents
        ]),
    }


def _select_locations(documents,selected,visible):
    paths={ROOT:[]};positions={};authorized=set();owners={}
    for doc in documents:
        identity=(doc['document_id'],doc.get('version_id'));authorized.add(identity)
        locations=_locations(doc)
        if locations is None:
            # Mixed manifests may retain a legacy document. Its known positions
            # remain addressable, without inventing an extra source filename.
            locations=[('LEGACY_'+hashlib.sha256((doc['document_id']+str(p)).encode()).hexdigest()[:24],p,None)
                       for p in doc.get('source_directories',[])]
        positions[identity]=locations
        for occurrence,parts,_ in locations:
            if occurrence in owners and owners[occurrence]!=identity:
                raise KnowledgeError('POLICY_UNAVAILABLE')
            owners[occurrence]=identity
            for end in range(1,len(parts)+1):paths[folder_id(parts[:end])]=parts[:end]
    if selected not in paths:raise KnowledgeError('SCOPE_REJECTED')
    prefix=paths[selected];chosen=[];children={};direct=set();seen=set()
    for doc in visible:
        identity=(doc['document_id'],doc.get('version_id'))
        if identity not in authorized:raise KnowledgeError('SCOPE_REJECTED')
        for occurrence,parts,filename in positions[identity]:
            if parts[:len(prefix)]!=prefix or occurrence in seen:continue
            seen.add(occurrence)
            row={**doc,'source_directories':[parts],'source_occurrence_id':occurrence}
            if filename is not None:row['source_filename']=filename
            chosen.append(row)
            if len(parts)==len(prefix):direct.add(occurrence)
            else:
                child=parts[:len(prefix)+1];key=folder_id(child)
                entry=children.setdefault(key,{'folder_id':key,'name':child[-1],'positions':set()})
                entry['positions'].add(occurrence)
    chosen.sort(key=lambda d:(d['source_directories'],d.get('source_filename',''),d['document_id']))
    return chosen,{'folder_id':selected,
        'breadcrumbs':[{'folder_id':folder_id(prefix[:i]),'name':prefix[i-1]} for i in range(1,len(prefix)+1)],
        'children':[{'folder_id':v['folder_id'],'name':v['name'],'count':len(v['positions'])}
                    for v in sorted(children.values(),key=lambda v:v['name'])],
        'direct_count':len(direct),'count_kind':'SOURCE_OCCURRENCES'}

def select(documents, selected=ROOT, filtered_documents=None):
    """Resolve `selected` against the authorized rows, then list `visible` rows.

    `documents` is the freshly authorized set and decides whether the folder
    exists at all; `filtered_documents` (the same set narrowed by the caller's
    department, category and keyword filters) decides which rows and which
    child counts are shown. Counting children from the unfiltered set is what
    let a folder badge promise 208 documents while the list under it, filtered
    differently, was empty.
    """
    if not isinstance(selected,str) or len(selected)>40:raise KnowledgeError('INVALID_REQUEST')
    selected=selected or ROOT
    if any(_locations(doc) is not None for doc in documents):
        return _select_locations(documents,selected,
                                 documents if filtered_documents is None else filtered_documents)
    paths={ROOT:[]}
    for doc in documents:
        for parts in doc.get('source_directories',[]):
            for end in range(1,len(parts)+1):paths[folder_id(parts[:end])]=parts[:end]
    # A guessed folder cannot reveal its name, descendants or count.
    if selected not in paths:raise KnowledgeError('SCOPE_REJECTED')
    visible=documents if filtered_documents is None else filtered_documents
    prefix=paths[selected];chosen=[];children={};direct=[]
    for doc in visible:
        relevant=[parts for parts in doc.get('source_directories',[]) if parts[:len(prefix)]==prefix]
        if not prefix or relevant:chosen.append(doc)
        # A document stored directly in this folder (no deeper segment) is a
        # 本级直属文件, not a child-folder member. The catalogue shows both, and
        # the reconciliation has to be able to tell them apart: 无菌车间 holds
        # one direct document besides SOP/TSD/法规指南.
        if any(parts[:len(prefix)]==prefix and len(parts)==len(prefix) for parts in relevant):
            direct.append(doc['document_id'])
        for parts in relevant:
            if len(parts)<=len(prefix):continue
            child=parts[:len(prefix)+1];key=folder_id(child)
            entry=children.setdefault(key,{'folder_id':key,'name':child[-1],'documents':set()})
            entry['documents'].add(doc['document_id'])
    return chosen,{'folder_id':selected,'breadcrumbs':[{'folder_id':folder_id(prefix[:i]),'name':prefix[i-1]} for i in range(1,len(prefix)+1)],
                   'children':[{'folder_id':v['folder_id'],'name':v['name'],'count':len(v['documents'])} for v in sorted(children.values(),key=lambda v:v['name'])],
                   'direct_count':len(set(direct))}
