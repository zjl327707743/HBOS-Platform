"""Pure, bounded import admission and immutable registered-batch integrity."""
import hashlib,json,re
import xml.etree.ElementTree as ET
import copy
from io import BytesIO
from pathlib import PurePath
from zipfile import ZipFile,BadZipFile
from .errors import KnowledgeError
DEPARTMENTS={'production':'生产','hr':'人事','safety':'安全'}
DEPARTMENT_ALIASES={'ASEPTIC_WORKSHOP':'production','PRODUCTION':'production'}
def normalized_department(value):return DEPARTMENT_ALIASES.get(value,value)
MAX_FILE=20*1024*1024

def initial_state(frozen):
    state={**copy.deepcopy(frozen),'mode':'apply','run_id':'R21_'+frozen['batch_sha256'][:20]}
    for item in state['items']:
        if item['disposition']=='SAME_CONTENT_SKIP':item['status']='skipped_duplicate'
    return state

def admit_file(name,data):
    if (not isinstance(name,str) or not name.strip() or len(name)>240 or
        PurePath(name).name!=name or '/' in name or '\\' in name or
        any(ord(c)<32 for c in name) or name.startswith(('.', '~$')) or
        not isinstance(data,bytes) or not 0<len(data)<=MAX_FILE):
        raise KnowledgeError('INVALID_REQUEST')
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
    from knowledge_service.ingestion import canonical,verify_state
    if (not isinstance(frozen,dict) or normalized_department(frozen.get('department_key')) not in DEPARTMENTS or
        not isinstance(frozen.get('items'),list) or not 1<=len(frozen['items'])<=512):
        raise KnowledgeError('INVALID_REQUEST')
    copy=dict(frozen);sha=copy.pop('batch_sha256',None)
    if not isinstance(sha,str) or hashlib.sha256(canonical(copy)).hexdigest()!=sha:
        raise KnowledgeError('INVALID_REQUEST')
    ids=set()
    for item in frozen['items']:
        if (item.get('department_key')!=frozen['department_key'] or
            not item.get('internal_sharing_confirmed') or not item.get('owner_inclusion_confirmed') or
            not item.get('approval_ref') ):
            raise KnowledgeError('INVALID_REQUEST')
        if item['version_id'] in ids and item.get('disposition')!='SAME_CONTENT_SKIP':raise KnowledgeError('INVALID_REQUEST')
        ids.add(item['version_id'])
    try:verify_state(state,frozen)
    except (ValueError,KeyError,TypeError):raise KnowledgeError('INVALID_REQUEST') from None
    return sha
