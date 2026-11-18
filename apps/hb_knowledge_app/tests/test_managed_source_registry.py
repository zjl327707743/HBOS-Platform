"""Real disposable source files/maps; mappings never grant document access."""
import copy,hashlib,json
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import pytest
from hb_knowledge_app.hb_knowledge import managed_source_registry as registry
from hb_knowledge_app.hb_knowledge.document_assets import LocalDocumentAssets
from hb_knowledge_app.hb_knowledge import source_directory

def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False))

def fixture(tmp_path,tag='a'):
    uploads=tmp_path/'uploads';root=uploads/tag/'source';file=root/'生产部门'/(tag+'.pdf')
    file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'%PDF-1.4\n'+tag.encode()+b'\n%%EOF\n')
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    cfg={'maintenance_source_registry_enabled':True,'maintenance_upload_root':str(uploads),
         'document_asset_roots':{'uploads':str(uploads)},
         'document_asset_manifest':str(tmp_path/'registry/assets.json'),
         'source_directory_path':str(tmp_path/'registry/source-directory.json')}
    item={'canonical_document_id':'DOC_'+tag,'version_id':'VER_'+tag,'sha256':digest,
          'relative_path':'生产部门/'+tag+'.pdf','disposition':'NEW'}
    frozen={'source_root':str(root),'items':[item]}
    if not Path(cfg['document_asset_manifest']).exists():
        write(Path(cfg['document_asset_manifest']),{'schema':'hbos-document-assets-v1','by_version':{'OLD':{'retained':True}}})
        write(Path(cfg['source_directory_path']),{'schema_version':2,'by_version':{'OLD':{'retained':True}}})
    return cfg,frozen,file

def test_new_upload_has_real_original_pdf_and_authorized_directory_position(tmp_path,monkeypatch):
    cfg,frozen,file=fixture(tmp_path);before=file.read_bytes();result=registry.register(cfg,frozen)
    assert result['registered_versions']==['VER_a']
    binding=SimpleNamespace(version_id='VER_a',canonical_document_id='DOC_a')
    assets=LocalDocumentAssets(cfg['document_asset_manifest'],cfg['document_asset_roots'],lambda b:frozen['items'][0]['sha256'])
    preview,original=assets.resolve(binding,'preview')
    assert original.path==file and preview.path==file and preview.kind=='ORIGINAL_PDF'
    assert original.path.read_bytes()==before
    monkeypatch.setattr(source_directory,'MAP',Path(cfg['source_directory_path']))
    source_directory._read_map.cache_clear()
    docs=[{'document_id':'DOC_a','version_id':'VER_a','source_directories':source_directory.directories(binding)}]
    rows,tree=source_directory.select(docs)
    assert len(rows)==1 and rows[0]['source_filename']=='a.pdf'
    assert tree['children'][0]['name']=='生产部门' and tree['children'][0]['count']==1
    # No supplied authorized rows -> no document or directory disclosure.
    assert source_directory.select([])[0]==[]

def test_exact_repeat_noop_and_prior_assets_and_versions_kept(tmp_path):
    cfg,frozen,file=fixture(tmp_path);registry.register(cfg,frozen)
    before={key:Path(cfg[key]).read_bytes() for key in ['document_asset_manifest','source_directory_path']}
    assert registry.register(cfg,frozen)['status']=='NOOP_ALREADY_REGISTERED'
    assert all(Path(cfg[key]).read_bytes()==data for key,data in before.items())
    assert json.loads(before['document_asset_manifest'])['by_version']['OLD']=={'retained':True}
    frozen['items'][0]['canonical_document_id']='DOC_OTHER'
    with pytest.raises(ValueError):registry.register(cfg,frozen)
    assert all(Path(cfg[key]).read_bytes()==data for key,data in before.items())

@pytest.mark.parametrize('change',['bytes','symlink','outside','wrong_directory','path_escape'])
def test_untrusted_changed_or_foreign_source_does_not_change_either_map(tmp_path,change):
    cfg,frozen,file=fixture(tmp_path)
    before={key:Path(cfg[key]).read_bytes() for key in ['document_asset_manifest','source_directory_path']}
    if change=='bytes':file.write_bytes(b'changed bytes')
    elif change=='symlink':
        target=file.with_suffix('.keep');file.rename(target);file.symlink_to(target)
    elif change=='outside':cfg['maintenance_upload_root']=str(tmp_path/'not-uploads')
    elif change=='wrong_directory':frozen['items'][0]['relative_path']='other/a.pdf'
    else:frozen['items'][0]['relative_path']='../a.pdf'
    with pytest.raises((ValueError,OSError)):registry.register(cfg,frozen)
    assert all(Path(cfg[key]).read_bytes()==data for key,data in before.items())

def test_two_uploads_are_serialized_and_keep_both_versions(tmp_path):
    a,fa,_=fixture(tmp_path,'a');b,fb,_=fixture(tmp_path,'b')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(registry.register,a,fa),pool.submit(registry.register,b,fb)]
        for future in futures:future.result()
    for key in ['document_asset_manifest','source_directory_path']:
        assert set(json.loads(Path(a[key]).read_text())['by_version'])=={'OLD','VER_a','VER_b'}

def test_partial_projection_write_recovers_by_exact_replay(tmp_path,monkeypatch):
    cfg,frozen,file=fixture(tmp_path);real=registry.os.replace;failed=False
    def fail_second(src,dst):
        nonlocal failed
        if Path(dst)==Path(cfg['source_directory_path']) and not failed:
            failed=True;raise OSError('synthetic interruption after assets map installed')
        return real(src,dst)
    monkeypatch.setattr(registry.os,'replace',fail_second)
    with pytest.raises(OSError):registry.register(cfg,frozen)
    assert 'VER_a' in json.loads(Path(cfg['document_asset_manifest']).read_text())['by_version']
    assert 'VER_a' not in json.loads(Path(cfg['source_directory_path']).read_text())['by_version']
    assert registry.register(cfg,frozen)['status']=='REGISTERED'
    assert 'VER_a' in json.loads(Path(cfg['source_directory_path']).read_text())['by_version']
    assert file.read_bytes().startswith(b'%PDF-')

def test_disabled_feature_and_duplicate_upload_make_no_projection_write(tmp_path):
    cfg,frozen,file=fixture(tmp_path);before=Path(cfg['document_asset_manifest']).read_bytes()
    cfg['maintenance_source_registry_enabled']=False
    assert registry.register(cfg,frozen)['status']=='DISABLED'
    cfg['maintenance_source_registry_enabled']=True;frozen['items'][0]['disposition']='SAME_CONTENT_SKIP'
    assert registry.register(cfg,frozen)['status']=='NOOP_DUPLICATE'
    assert Path(cfg['document_asset_manifest']).read_bytes()==before
