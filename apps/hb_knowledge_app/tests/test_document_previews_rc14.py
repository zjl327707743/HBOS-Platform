import zipfile
import pytest

from hb_knowledge_app.hb_knowledge.document_previews import office_admitted, prepare_pdf


@pytest.mark.parametrize('entry,content,reason',[
    ('word/vbaProject.bin',b'not executed','OFFICE_ACTIVE_CONTENT'),
    ('word/embeddings/object.bin',b'not executed','OFFICE_ACTIVE_CONTENT'),
    ('word/_rels/document.xml.rels',b'<Relationships><Relationship TargetMode="External" Target="file:///private/secret"/></Relationships>','OFFICE_EXTERNAL_LINK'),
    ('word/document.xml',b'<document><instrText>DDEAUTO cmd</instrText></document>','OFFICE_ACTIVE_FIELD'),
    ('word/document.xml',b'<document><instrText>INCLUDETEXT /private/secret</instrText></document>','OFFICE_ACTIVE_FIELD'),
])
def test_office_active_content_is_rejected_before_converter_runs(tmp_path,entry,content,reason):
    path=tmp_path/'synthetic.docx'
    with zipfile.ZipFile(path,'w') as archive:archive.writestr(entry,content)
    with pytest.raises(ValueError,match=reason):office_admitted(path)


def test_pdf_actions_are_removed_from_a_separate_layout_preserving_copy(tmp_path):
    pytest.importorskip('pypdf')
    from pypdf import PdfWriter, PdfReader
    from pypdf.generic import NameObject, DictionaryObject, TextStringObject, ArrayObject
    writer=PdfWriter();page=writer.add_blank_page(width=250,height=400)
    action=DictionaryObject({NameObject('/S'):NameObject('/JavaScript'),NameObject('/JS'):TextStringObject('synthetic_not_executed()')})
    writer._root_object[NameObject('/OpenAction')]=action
    page[NameObject('/Annots')]=ArrayObject([DictionaryObject({NameObject('/A'):action})])
    path=tmp_path/'original.pdf'
    with path.open('wb') as f:writer.write(f)
    original=path.read_bytes();target=tmp_path/'preview.pdf'
    result=prepare_pdf(path,target)
    assert result['kind']=='DERIVED_PDF' and result['path']==target
    assert path.read_bytes()==original
    preview=PdfReader(target,strict=True)
    assert '/OpenAction' not in preview.trailer['/Root']
    assert '/Annots' not in preview.pages[0]
    assert tuple(preview.pages[0].mediabox)==(0,0,250,400)


def test_inert_pdf_can_use_exact_original_bytes(tmp_path):
    pytest.importorskip('pypdf')
    from pypdf import PdfWriter
    path=tmp_path/'original.pdf';writer=PdfWriter();writer.add_blank_page(width=250,height=400)
    with path.open('wb') as f:writer.write(f)
    result=prepare_pdf(path,tmp_path/'unused-preview.pdf')
    assert result['kind']=='ORIGINAL_PDF' and result['path']==path


def test_pdf_resource_names_do_not_get_removed_as_actions(tmp_path):
    pytest.importorskip('pypdf')
    from pypdf import PdfWriter, PdfReader
    from pypdf.generic import NameObject, DictionaryObject
    path=tmp_path/'resources.pdf';writer=PdfWriter();page=writer.add_blank_page(width=250,height=400)
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/A'):DictionaryObject(),NameObject('/JS'):DictionaryObject()})
    with path.open('wb') as f:writer.write(f)
    result=prepare_pdf(path,tmp_path/'preview.pdf')
    assert result['kind']=='ORIGINAL_PDF'
    assert '/A' in PdfReader(path).pages[0]['/Resources']


def test_navigation_name_tree_is_not_treated_as_active_content(tmp_path):
    pytest.importorskip('pypdf')
    from pypdf import PdfReader
    from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject
    writer_source = tmp_path/'with_dests.pdf'
    from pypdf import PdfWriter
    writer=PdfWriter();page=writer.add_blank_page(width=250,height=400)
    dests=DictionaryObject({NameObject('/Names'):ArrayObject([TextStringObject('anchor'),
                                                             ArrayObject([page.indirect_reference,NameObject('/Fit')])])})
    writer._root_object[NameObject('/Names')]=DictionaryObject({NameObject('/Dests'):dests})
    with writer_source.open('wb') as f:writer.write(f)
    result=prepare_pdf(writer_source,tmp_path/'preview.pdf')
    # A pure /Dests tree is in-document navigation: the exact original is usable.
    assert result['kind']=='ORIGINAL_PDF' and result['path']==writer_source


def test_script_name_tree_is_still_removed(tmp_path):
    pytest.importorskip('pypdf')
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject
    source=tmp_path/'with_js_names.pdf'
    writer=PdfWriter();writer.add_blank_page(width=250,height=400)
    writer._root_object[NameObject('/Names')]=DictionaryObject({NameObject('/JavaScript'):
        DictionaryObject({NameObject('/Names'):ArrayObject([TextStringObject('s'),
                        DictionaryObject({NameObject('/S'):NameObject('/JavaScript'),
                                          NameObject('/JS'):TextStringObject('synthetic_not_executed()')})])})})
    with source.open('wb') as f:writer.write(f)
    result=prepare_pdf(source,tmp_path/'preview.pdf')
    assert result['kind']=='DERIVED_PDF'
    preview=PdfReader(tmp_path/'preview.pdf',strict=True)
    names=preview.trailer['/Root'].get('/Names')
    assert names is None or '/JavaScript' not in names.get_object()


def test_owner_password_only_pdf_opens_but_user_password_pdf_is_refused(tmp_path):
    pytest.importorskip('pypdf')
    from pypdf import PdfReader, PdfWriter
    writer=PdfWriter();writer.add_blank_page(width=250,height=400)
    plain=tmp_path/'plain.pdf'
    with plain.open('wb') as f:writer.write(f)
    owner_only=tmp_path/'owner_only.pdf';writer.encrypt('',owner_password='owner',algorithm='RC4-128')
    with owner_only.open('wb') as f:writer.write(f)
    result=prepare_pdf(owner_only,tmp_path/'preview.pdf')
    # An owner-locked file is readable with the empty user password, so it gets a
    # preview; the bytes the browser receives open without any password.
    assert result['kind'] in {'ORIGINAL_PDF','DERIVED_PDF'} and result['pages']==1
    served=PdfReader(result['path'],strict=True)
    if served.is_encrypted: assert served.decrypt('')
    assert len(served.pages)==1
    user_locked=tmp_path/'user_locked.pdf'
    locked=PdfWriter();locked.add_blank_page(width=250,height=400);locked.encrypt('user-secret',owner_password='owner')
    with user_locked.open('wb') as f:locked.write(f)
    with pytest.raises(ValueError,match='PDF_USER_PASSWORD_REQUIRED'):prepare_pdf(user_locked,tmp_path/'nope.pdf')


def test_page_geometry_tolerates_float_rewrite_but_not_a_real_resize(tmp_path):
    from hb_knowledge_app.hb_knowledge.document_previews import _same_boxes
    assert _same_boxes([(0.0,0.0,595.299988,841.900024)],[(0.0,0.0,595.29998779,841.90002441)])
    assert not _same_boxes([(0.0,0.0,595.0,842.0)],[(0.0,0.0,595.0,841.0)])
    assert not _same_boxes([(0.0,0.0,595.0,842.0)],[(0.0,0.0,595.0,842.0),(0.0,0.0,595.0,842.0)])
