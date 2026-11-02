"""Pure, bounded import admission and immutable registered-batch integrity."""
import hashlib,json,re
import xml.etree.ElementTree as ET
import copy
from io import BytesIO
from pathlib import PurePath
from zipfile import ZipFile,BadZipFile
from .errors import KnowledgeError
DEPARTMENTS={'production':'生产','hr':'人事','safety':'安全','engineering':'设备工程',
             'public_law':'公司公共法律法规知识'}
DEPARTMENT_ALIASES={'ASEPTIC_WORKSHOP':'production','PRODUCTION':'production'}
def normalized_department(value):return DEPARTMENT_ALIASES.get(value,value)
# The old constant stays a legacy alias for existing importers/tests. The
# normal maintenance path resolves its per-deployment limit from private config
# (``maintenance_max_source_bytes``), defaulting to 64 MiB and staying inside the
# approved 20..64 MiB normal range. This is a source-file limit only: it does not
# raise any reverse-proxy/API body limit and it does not replace the separate
# manifest-size limit in the batch planner.
MAX_FILE=20*1024*1024
DEFAULT_MAX_SOURCE_BYTES=64*1024*1024
MIN_CONFIGURED_SOURCE_BYTES=20*1024*1024
MAX_CONFIGURED_SOURCE_BYTES=64*1024*1024


def configured_max_source_bytes(cfg):
    """Per-file normal-path limit from private configuration, fail closed."""
    if not isinstance(cfg,dict):raise KnowledgeError('POLICY_UNAVAILABLE')
    value=cfg.get('maintenance_max_source_bytes')
    if value is None:return DEFAULT_MAX_SOURCE_BYTES
    if (type(value) is not int or not MIN_CONFIGURED_SOURCE_BYTES<=value<=MAX_CONFIGURED_SOURCE_BYTES):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    return value


def source_size_budget(cfg):
    """Derived budgets: per item, per <=4-document submission batch, per plan."""
    per_file=configured_max_source_bytes(cfg)
    return {'per_file':per_file,'per_batch':per_file*4,'per_manifest':per_file*16}


def require_source_size(size,maximum):
    if type(size) is not int or size<0:raise KnowledgeError('INVALID_REQUEST')
    if size==0:raise KnowledgeError('INVALID_REQUEST')
    if size>maximum:raise KnowledgeError('SOURCE_SIZE_LIMIT_EXCEEDED')
    return size

def initial_state(frozen):
    state={**copy.deepcopy(frozen),'mode':'apply','run_id':'R21_'+frozen['batch_sha256'][:20]}
    for item in state['items']:
        if item['disposition']=='SAME_CONTENT_SKIP':item['status']='skipped_duplicate'
    return state

def admit_file(name,data,max_bytes=None):
    """Bounded content admission; ``max_bytes`` is the configured source limit.

    Default keeps the legacy 20 MiB admission for old callers/tests; the normal
    maintenance upload path always passes the configured limit explicitly.
    """
    if (not isinstance(name,str) or not name.strip() or len(name)>240 or
        PurePath(name).name!=name or '/' in name or '\\' in name or
        any(ord(c)<32 for c in name) or name.startswith(('.', '~$')) or
        not isinstance(data,bytes)):
        raise KnowledgeError('INVALID_REQUEST')
    limit=MAX_FILE if max_bytes is None else max_bytes
    if not 0<len(data):raise KnowledgeError('INVALID_REQUEST')
    if len(data)>limit:raise KnowledgeError('SOURCE_SIZE_LIMIT_EXCEEDED')
    ext=PurePath(name).suffix.lower()
    if ext=='.pdf':
        if not data.startswith(b'%PDF-'):raise KnowledgeError('INVALID_REQUEST')
    elif ext in ('.docx','.xlsx','.pptx'):
        try:
            with ZipFile(BytesIO(data)) as archive:
                info=archive.infolist()
                if (len(info)>10000 or sum(i.file_size for i in info)>80*1024*1024 or
                    any(i.flag_bits&1 or '..' in PurePath(i.filename).parts or i.filename.startswith('/') or
                        i.file_size>max(1024*1024,i.compress_size*100) for i in info)):
                    raise KnowledgeError('INVALID_REQUEST')
                names={i.filename.lower() for i in info}
                root={'.docx':'word/document.xml','.xlsx':'xl/workbook.xml','.pptx':'ppt/presentation.xml'}[ext]
                if root not in names or any('vbaproject' in n or '/embeddings/' in n for n in names):
                    raise KnowledgeError('INVALID_REQUEST')
                for i in info:
                    if i.filename.lower().endswith('.rels'):
                        xml=archive.read(i)
                        if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():raise KnowledgeError('INVALID_REQUEST')
                        try:relationships=ET.fromstring(xml)
                        except ET.ParseError:raise KnowledgeError('INVALID_REQUEST') from None
                        for node in relationships.iter():
                            mode=node.attrib.get('TargetMode','').casefold();target=node.attrib.get('Target','').strip().casefold()
                            if mode=='external' or '://' in target or target.startswith(('//','file:')):
                                raise KnowledgeError('INVALID_REQUEST')
        except (BadZipFile,KeyError):raise KnowledgeError('INVALID_REQUEST') from None
    elif ext=='.doc':
        if not data.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):raise KnowledgeError('INVALID_REQUEST')
        import olefile
        try:
            with olefile.OleFileIO(BytesIO(data)) as compound:
                streams=['/'.join(parts).casefold() for parts in compound.listdir()]
                if len(streams)>10000 or any(any(marker in n for marker in ('vba','macros','objectpool')) for n in streams):
                    raise KnowledgeError('INVALID_REQUEST')
        except (OSError,ValueError):raise KnowledgeError('INVALID_REQUEST') from None
    elif ext in ('.txt','.md'):
        try:data.decode('utf-8')
        except UnicodeDecodeError:raise KnowledgeError('INVALID_REQUEST') from None
    else:raise KnowledgeError('INVALID_REQUEST')
    return ext,hashlib.sha256(data).hexdigest()


def registered(frozen,state):
    from knowledge_service.ingestion import canonical,verify_state,processing_approved
    if (not isinstance(frozen,dict) or normalized_department(frozen.get('department_key')) not in DEPARTMENTS or
        not isinstance(frozen.get('items'),list) or not 1<=len(frozen['items'])<=512):
        raise KnowledgeError('INVALID_REQUEST')
    copy=dict(frozen);sha=copy.pop('batch_sha256',None)
    if not isinstance(sha,str) or hashlib.sha256(canonical(copy)).hexdigest()!=sha:
        raise KnowledgeError('INVALID_REQUEST')
    ids=set()
    for item in frozen['items']:
        if (item.get('department_key')!=frozen['department_key'] or not processing_approved(frozen,item)):
            raise KnowledgeError('INVALID_REQUEST')
        if item['version_id'] in ids and item.get('disposition')!='SAME_CONTENT_SKIP':raise KnowledgeError('INVALID_REQUEST')
        ids.add(item['version_id'])
    try:verify_state(state,frozen)
    except (ValueError,KeyError,TypeError):raise KnowledgeError('INVALID_REQUEST') from None
    return sha
