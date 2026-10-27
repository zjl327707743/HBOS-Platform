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
