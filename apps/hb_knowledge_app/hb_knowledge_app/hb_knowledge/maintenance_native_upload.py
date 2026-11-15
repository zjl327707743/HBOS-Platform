"""Apply private Main-locked native templates only to new upload manifests.

No publication, restore or authorization is granted here. Existing frozen
batches and exact duplicate identities remain byte-for-byte unchanged.
"""
import copy,hashlib
from pathlib import Path
from .errors import KnowledgeError
from .maintenance_contract import configured_max_source_bytes

TEMPLATES=[{'key':'auto','title':'按文件类型推荐'},
           {'key':'text_pdf','title':'文字 PDF（可选中文字）'},
           {'key':'scan_pdf','title':'扫描或混合 PDF'}]

def _profiles(cfg):
    value=cfg.get('maintenance_native_upload_profiles')
    if value is None:return None
    try:
        from knowledge_service.native_job_contract import validate_profile
        if not isinstance(value,dict) or set(value) not in ({'plain','deepdoc'},{'plain','deepdoc','workbook'}):raise ValueError()
        for key,layout in [('plain','Plain Text'),('deepdoc','DeepDOC')]+([('workbook','Plain Text')] if 'workbook' in value else []):
            p=validate_profile(value[key]);c=p['parser_config']
            if (p['parser_id']!='naive' or c['layout_recognize']!=layout or c['overlapped_percent']!=0
                    or c['enable_children'] or c['table_context_size'] or c['image_context_size']
                    or 'pages' in c):raise ValueError()
        return value
    except (ValueError,KeyError,TypeError):raise KnowledgeError('POLICY_UNAVAILABLE') from None

def upload_policy(cfg):
    enabled=_profiles(cfg) is not None
    return {'max_source_bytes':configured_max_source_bytes(cfg),
            'native_templates_enabled':enabled,'templates':copy.deepcopy(TEMPLATES) if enabled else []}

def apply_profile(planned,cfg,template='auto',*,mixed_formats=False):
    if template not in ('auto','text_pdf','scan_pdf'):raise KnowledgeError('INVALID_REQUEST')
    profiles=_profiles(cfg)
    if profiles is None:
        if template!='auto':raise KnowledgeError('INVALID_REQUEST')
        return planned
    from knowledge_service.native_job_contract import NATIVE_INPUT,binding_revision_for,validate_native_item
    from knowledge_service.ingestion import canonical
    changed=False
    for item in planned['items']:
        ext=item['extension']
        if template!='auto' and ext!='.pdf' and not mixed_formats:raise KnowledgeError('INVALID_REQUEST')
        if item['disposition']=='SAME_CONTENT_SKIP' or item.get('source_inspection_error'):continue
        # Other formats keep their existing admission/conversion workflow. In
        # particular Markdown must never enter the URL-fetching native parser.
        if ext not in ('.pdf','.docx','.xlsx','.txt'):continue
        layout='plain'
        if ext=='.xlsx' and 'workbook' in profiles:layout='workbook'
        if ext=='.pdf' and template!='text_pdf':
            layout='deepdoc'
            if template=='auto' and planned.get('source_root') and 0<item.get('original_page_count',0)<=320:
                # This is text-layer inspection only. No OCR/render/model call.
                # A mixed or uncertain source stays on the native DeepDOC path.
                from pypdf import PdfReader
                from pypdf.errors import PyPdfError
                source=Path(planned['source_root'])/item['relative_path']
                try:
                    pdf=PdfReader(source)
                    if len(pdf.pages)==item['original_page_count'] and all(
                            len(''.join((page.extract_text() or '').split()))>=8 for page in pdf.pages):
                        layout='plain'
                except (PyPdfError, ValueError, TypeError):
                    # The source passed basic PDF inspection. Defer pages
                    # whose text layer could not be read to the complex lane.
                    pass
        profile=copy.deepcopy(profiles[layout])
        pages=item.get('original_page_count') if ext=='.pdf' else None
        if ext=='.pdf' and (type(pages) is not int or not 1<=pages<=10000):raise KnowledgeError('INVALID_REQUEST')
        item.update(parser_input=NATIVE_INPUT,native_profile=profile,parser_config=copy.deepcopy(profile['parser_config']),
            native_source_proof={'source_sha256':item['sha256'],'original_page_count':pages,
                'covered_pages':list(range(1,pages+1)) if pages is not None else [],
                'full_source_requested':True,'prepared_asset':None})
        item['binding_revision']=binding_revision_for(item)
        try:validate_native_item(item)
        except (ValueError,KeyError,TypeError):raise KnowledgeError('INVALID_REQUEST') from None
        changed=True
    if changed:planned['batch_sha256']=hashlib.sha256(canonical({k:v for k,v in planned.items() if k!='batch_sha256'})).hexdigest()
    return planned
