"""Non-authorizing original and directory projections for managed uploads.

The source bytes are never modified. A partial two-file projection update can
be completed by exact replay; neither projection permits reading an unpublished
or withdrawn HBOS version. Both readers still require current authority.
"""
import copy,fcntl,hashlib,json,os,re,stat,tempfile
from pathlib import Path,PurePosixPath
from .document_assets import MAX_MANIFEST_BYTES,safe_filename
from .source_directory import ALLOWED_ROOTS

def require(value,message):
    if not value:raise ValueError(message)

def _canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

def _safe_root(raw):
    require(isinstance(raw,str),'Missing configured source root')
    path=Path(raw)
    require(path.is_absolute() and path.resolve(strict=True)==path and path.is_dir(),'Unsafe source root')
    return path

def _verified_source(root,relative,digest):
    require(isinstance(relative,str) and relative and '\\' not in relative and '\x00' not in relative,'Invalid source path')
    parts=relative.split('/')
    require(not PurePosixPath(relative).is_absolute() and all(p and p not in {'.','..'} for p in parts),'Invalid relative source path')
    path=root.joinpath(*parts)
    require(path.resolve(strict=True)==path and path.is_relative_to(root),'Source symlink or escape')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());require(stat.S_ISREG(before.st_mode),'Source must be regular')
        hasher=hashlib.sha256()
        for block in iter(lambda:stream.read(1024*1024),b''):hasher.update(block)
        after=os.fstat(stream.fileno())
    require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'Source changed while verified')
    require(os.path.samestat(after,path.stat()) and hasher.hexdigest()==digest,'Source hash mismatch')
    return path

def _load(path,schema,value):
    require(path.is_absolute() and path.is_file() and not path.is_symlink() and path.stat().st_size<=MAX_MANIFEST_BYTES,'Unsafe projection')
    result=json.loads(path.read_text());require(result.get(schema)==value and isinstance(result.get('by_version'),dict),'Invalid projection schema')
    return result

def _replace(path,value):
    encoded=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n'
    require(len(encoded)<=MAX_MANIFEST_BYTES,'Projection limit exceeded')
    history=path.parent/'.source-registry-history';history.mkdir(mode=0o770,exist_ok=True)
    require(not history.is_symlink(),'Unsafe history directory')
    before=path.read_bytes();oldhash=hashlib.sha256(before).hexdigest()
    archived=history/(path.name+'.'+oldhash)
    require(not archived.is_symlink(),'Unsafe history entry')
    if not archived.exists():
        with archived.open('xb') as stream:stream.write(before)
        archived.chmod(0o640)
    else:require(archived.read_bytes()==before,'History hash conflict')
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(encoded);stream.flush();os.fsync(stream.fileno())
        os.chmod(name,0o640);os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def register(cfg,frozen):
    """Register only the already admitted upload, before granting publication.

    Existing version metadata is immutable; same-content duplicate uploads keep
    the existing canonical source. This function has no DB, model or HTTP port.
    """
    if cfg.get('maintenance_source_registry_enabled') is not True:return {'status':'DISABLED','registered_versions':[]}
    items=[item for item in frozen['items'] if item.get('disposition') not in ('SAME_CONTENT_SKIP','ALIAS')]
    if not items:return {'status':'NOOP_DUPLICATE','registered_versions':[]}
    base=_safe_root(cfg.get('maintenance_upload_root'));root=_safe_root(frozen.get('source_root'))
    require(root.is_relative_to(base) and root!=base,'Source is not this managed upload')
    require(_safe_root(cfg.get('document_asset_roots',{}).get('uploads'))==base,'Upload delivery root mismatch')
    assets=Path(cfg['document_asset_manifest']);directories=Path(cfg['source_directory_path'])
    require(assets!=directories and assets.parent==directories.parent,'Registry maps must share one lock directory')
    _safe_root(str(assets.parent))
    proposed=[]
    for item in items:
        doc=item['canonical_document_id'];version=item['version_id'];digest=item['sha256'];relative=item['relative_path']
        require(all(isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',x) for x in (doc,version)),'Invalid identity')
        require(isinstance(digest,str) and re.fullmatch('[a-f0-9]{64}',digest),'Invalid source SHA')
        source=_verified_source(root,relative,digest);parts=relative.split('/')
        require(2<=len(parts)<=31 and parts[0] in ALLOWED_ROOTS,'Upload must have a selected HBOS directory')
        record={'root_id':'uploads','relative_path':source.relative_to(base).as_posix(),'filename':safe_filename(source.name)}
        preview={**record,'kind':'ORIGINAL_PDF','sha256':digest} if source.suffix.lower()=='.pdf' else None
        asset={'document_id':doc,'source_sha256':digest,'original':record,'preview':preview}
        occurrence='OCC-'+hashlib.sha256(_canonical([doc,version,digest,relative])).hexdigest()[:24]
        directory={'canonical_document_id':doc,'occurrences':[{'occurrence_id':occurrence,'relative_path':relative,'content_sha256':digest}],
                   'directories':[parts[:-1]],'source_presence':'PRESENT','source_origin':'MANAGED_UPLOAD',
                   'managed_source_root_ref':'SOURCE_ROOT_'+hashlib.sha256(str(root).encode()).hexdigest()[:24]}
        proposed.append((version,asset,directory))
    fd=os.open(assets.parent/'.source-registry.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o640)
    with os.fdopen(fd,'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        current_assets=_load(assets,'schema','hbos-document-assets-v1')
        current_directories=_load(directories,'schema_version',2)
        new_assets=copy.deepcopy(current_assets);new_directories=copy.deepcopy(current_directories)
        for version,asset,directory in proposed:
            for manifest,entry in [(new_assets,asset),(new_directories,directory)]:
                previous=manifest['by_version'].get(version)
                require(previous is None or previous==entry,'Immutable source version projection conflict')
                manifest['by_version'][version]=entry
        changed=False
        for path,before,after in [(assets,current_assets,new_assets),(directories,current_directories,new_directories)]:
            if before!=after:_replace(path,after);changed=True
    return {'status':'REGISTERED' if changed else 'NOOP_ALREADY_REGISTERED','registered_versions':[v for v,_,_ in proposed],
            'source_bytes_changed':False,'publication_or_permission_changed':False}


def register_derived_previews(cfg, frozen, items):
    """Update only the preview slot after the controller completed native ACKs."""
    base = _safe_root(cfg.get('maintenance_upload_root'))
    root = _safe_root(frozen.get('source_root'))
    require(root.is_relative_to(base) and root!=base,'Preview source is outside the admitted uploads')
    require(_safe_root(cfg.get('document_asset_roots',{}).get('uploads'))==base,'Preview mount does not match uploads')
    converter = cfg.get('maintenance_office_preview_converter') or {}
    assets = Path(cfg['document_asset_manifest'])
    _safe_root(str(assets.parent))
    errors = {}
    fd = os.open(assets.parent/'.source-registry.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o640)
    with os.fdopen(fd,'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        before = _load(assets,'schema','hbos-document-assets-v1')
        after = copy.deepcopy(before)
        for item in items:
            version = item['version_id']
            try:
                proof = item['automatic_quality']['office_preview']
                expected_path = (root.parent/'managed-previews'/(version+'.pdf')).relative_to(base).as_posix()
                required = {'schema':'hbos.managed-office-preview.v1','document_id':item['canonical_document_id'],
                    'version_id':version,'source_sha256':item['sha256'],'kind':'DERIVED_PDF',
                    'relative_path':expected_path,'network_denied':True,'original_input_unchanged':True}
                require(all(proof.get(k)==v for k,v in required.items()),'Preview evidence identity changed')
                require(converter.get('sha256')==proof['converter_sha256']
                        and converter.get('version')==proof['converter_version']
                        and converter.get('text_extractor_sha256')==proof['text_extractor_sha256']
                        and converter.get('text_extractor_version')==proof['text_extractor_version'],
                        'Preview converter pin changed')
                digest = proof['sha256']
                require(isinstance(digest,str) and re.fullmatch('[a-f0-9]{64}',digest),'Preview hash required')
                preview = _verified_source(base,expected_path,digest)
                receipt = preview.with_suffix('.json')
                require(receipt.resolve(strict=True)==receipt and receipt.stat().st_size<16384
                        and json.loads(receipt.read_bytes())==proof,'Controller preview receipt changed')
                with preview.open('rb') as stream:
                    require(stream.read(5)==b'%PDF-','Invalid preview PDF')
                prior = after['by_version'][version]
                require(prior['document_id']==item['canonical_document_id']
                        and prior['source_sha256']==item['sha256'],'Original asset identity changed')
                verified = {'root_id':'uploads','relative_path':expected_path,'filename':safe_filename(proof['filename']),
                            'kind':'DERIVED_PDF','sha256':digest}
                require(prior.get('preview') in (None,verified),'Existing preview is immutable')
                prior['preview']=verified
            except (ValueError,OSError,KeyError,TypeError):
                errors[version]='MANAGED_PREVIEW_REGISTRATION_RECHECK'
        if before!=after:
            _replace(assets,after)
    return errors
