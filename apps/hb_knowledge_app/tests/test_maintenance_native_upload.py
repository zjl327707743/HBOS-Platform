"""New maintenance uploads reuse explicit locked profiles; never alter old batches."""
import copy,hashlib,json
import pytest
from hb_knowledge_app.hb_knowledge.maintenance_native_upload import apply_profile,upload_policy
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from knowledge_service.native_job_contract import build_profile,validate_native_item

def profile(layout):
    return build_profile('naive',{'chunk_token_num':512,'delimiter':'\n','layout_recognize':layout,
        'html4excel':False,'auto_keywords':0,'auto_questions':0,'raptor':{'use_raptor':False},
        'graphrag':{'use_graphrag':False},'filename_embd_weight':.1,'overlapped_percent':0,
        'table_context_size':0,'image_context_size':0,'enable_children':False,'children_delimiter':''},'a'*64)
def config():
    return {'maintenance_native_upload_profiles':{'plain':profile('Plain Text'),'deepdoc':profile('DeepDOC')}}
def planned(ext='.pdf',disposition='NEW'):
    item={'extension':ext,'canonical_document_id':'DOC_'+'c'*24,'version_id':'VER_'+'b'*24,
        'sha256':'f'*64,'original_page_count':2 if ext=='.pdf' else None,'disposition':disposition,
        'parser_config':{'legacy':True},'binding_revision':'BR_legacy'}
    return {'items':[item],'batch_sha256':'old'}
def test_pdf_defaults_to_locked_native_ocr_with_explicit_zero_overlap_and_full_pages():
    p=planned();before=copy.deepcopy(p);apply_profile(p,config(),'auto');item=p['items'][0]
    assert validate_native_item(item)['parser_config']['layout_recognize']=='DeepDOC'
    assert item['parser_config']['overlapped_percent']==0
    assert item['native_source_proof']['covered_pages']==[1,2]
    assert item['sha256']==before['items'][0]['sha256'] and item['version_id']==before['items'][0]['version_id']
    from knowledge_service.ingestion import canonical
    assert p['batch_sha256']==hashlib.sha256(canonical({k:v for k,v in p.items() if k!='batch_sha256'})).hexdigest()

def test_real_chinese_path_manifest_can_be_verified_approved_and_frozen(tmp_path):
    from pypdf import PdfWriter
    from knowledge_service.ingestion import plan,save,approve,verify_frozen
    root=tmp_path/'source';department=root/'生产部门';department.mkdir(parents=True)
    source=department/'中文换版验收.pdf';writer=PdfWriter();writer.add_blank_page(width=200,height=200)
    with source.open('wb') as output:writer.write(output)
    planned_path=tmp_path/'planned.json';frozen_path=tmp_path/'frozen.json'
    value=plan(root,'production','生产',planned_path,'NATIVE_UPLOAD:qa')
    apply_profile(value,config(),'auto');save(planned_path,value)
    verify_frozen(value,False)
    frozen=approve(planned_path,frozen_path,'NATIVE_UPLOAD:qa');verify_frozen(frozen)
    assert frozen['items'][0]['relative_path']=='生产部门/中文换版验收.pdf'
def test_text_pdf_selection_and_office_full_structure_are_explicit():
    p=planned();apply_profile(p,config(),'text_pdf');assert p['items'][0]['parser_config']['layout_recognize']=='Plain Text'
    p=planned('.txt');apply_profile(p,config(),'auto');assert validate_native_item(p['items'][0])['parser_config']['layout_recognize']=='Plain Text'
    p=planned('.docx');apply_profile(p,config(),'auto');assert validate_native_item(p['items'][0])['parser_config']['overlapped_percent']==0
    assert p['items'][0]['native_source_proof']['original_page_count'] is None
    assert p['items'][0]['native_source_proof']['covered_pages']==[]
def test_duplicates_and_unvalidated_formats_keep_existing_state_without_native_claim():
    for ext,disposition in [('.pdf','SAME_CONTENT_SKIP'),('.pptx','NEW'),('.doc','NEW'),('.md','NEW')]:
        p=planned(ext,disposition);before=copy.deepcopy(p);apply_profile(p,config(),'auto');assert p==before
    p=planned();before=copy.deepcopy(p);apply_profile(p,{},'auto');assert p==before
@pytest.mark.parametrize('change',['unknown','nonzero_overlap','partial_profile','wrong_layout','non_pdf_choice'])
def test_invalid_selection_or_profile_is_refused_before_freezing(change):
    c=config();p=planned();choice='auto'
    if change=='unknown':choice='arbitrary'
    elif change=='nonzero_overlap':c['maintenance_native_upload_profiles']['plain']['parser_config']['overlapped_percent']=10
    elif change=='partial_profile':c['maintenance_native_upload_profiles']['deepdoc'].pop('profile_sha256')
    elif change=='wrong_layout':c['maintenance_native_upload_profiles']['plain']=profile('DeepDOC')
    else:p=planned('.docx');choice='text_pdf'
    with pytest.raises(KnowledgeError):apply_profile(p,c,choice)
def test_policy_exposes_only_size_and_maintainer_choices_never_private_profiles():
    p=upload_policy(config());assert p['max_source_bytes']==64*1024**2 and p['native_templates_enabled']
    assert [x['key'] for x in p['templates']]==['auto','text_pdf','scan_pdf']
    assert 'candidate_patch_sha256' not in json.dumps(p)
