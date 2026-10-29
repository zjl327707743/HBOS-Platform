"""Original-directory metadata; callers supply only freshly authorized rows."""
import functools
import hashlib
import json
from pathlib import Path
from .errors import KnowledgeError
from .public_strings import safe_string

MAP = Path('/run/hbos-reference/source-directory.json')
ROOT = 'SOURCE_ROOT'
ALLOWED_ROOTS = ('安全部门','法规文档','人事部门','设备部建模图','生产部门','无菌车间')

@functools.lru_cache(maxsize=2)
def _read_map(stamp, size):
    data=json.loads(MAP.read_text())
    if data.get('schema_version')!=1 or not isinstance(data.get('by_version'),dict):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    return data['by_version']

def directories(binding):
    try:metadata=MAP.stat()
    except FileNotFoundError:return []
    try:entry=_read_map(metadata.st_mtime_ns,metadata.st_size).get(binding.version_id)
    except (OSError,ValueError,TypeError):raise KnowledgeError('POLICY_UNAVAILABLE') from None
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

def select(documents, selected=ROOT):
    if not isinstance(selected,str) or len(selected)>40:raise KnowledgeError('INVALID_REQUEST')
    selected=selected or ROOT
    paths={ROOT:[]}
    for doc in documents:
        for parts in doc.get('source_directories',[]):
            for end in range(1,len(parts)+1):paths[folder_id(parts[:end])]=parts[:end]
    # A guessed folder cannot reveal its name, descendants or count.
    if selected not in paths:raise KnowledgeError('SCOPE_REJECTED')
    prefix=paths[selected];chosen=[];children={}
    for doc in documents:
        relevant=[parts for parts in doc.get('source_directories',[]) if parts[:len(prefix)]==prefix]
        if not prefix or relevant:chosen.append(doc)
        for parts in relevant:
            if len(parts)<=len(prefix):continue
            child=parts[:len(prefix)+1];key=folder_id(child)
            entry=children.setdefault(key,{'folder_id':key,'name':child[-1],'documents':set()})
            entry['documents'].add(doc['document_id'])
    return chosen,{'folder_id':selected,'breadcrumbs':[{'folder_id':folder_id(prefix[:i]),'name':prefix[i-1]} for i in range(1,len(prefix)+1)],
                   'children':[{'folder_id':v['folder_id'],'name':v['name'],'count':len(v['documents'])} for v in sorted(children.values(),key=lambda v:v['name'])]}
