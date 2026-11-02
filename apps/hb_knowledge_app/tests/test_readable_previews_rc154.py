"""A published workbook's long cell text must be readable, not searchable only.

RC154 found one published data-integrity workbook whose explanatory sentence sat
in a cell with a fixed row height, so LibreOffice's page-preserving export kept
printing it past the page edge: the text was inside the PDF and extractable, but
a person reading the preview saw a cut-off line. The fix renders the cell text
itself (wrapped, one table per column block) instead of the sheet geometry, and
the same renderer is used for the Markdown draft that previously only had a
private script.

These tests pin the parts that do not need a browser or LibreOffice:
cell extraction (shared strings, inline strings, column order, gaps), the
wrapped HTML, the escaping of cell content, and the Markdown block rendering.
"""
import zipfile

import pytest

from hb_knowledge_app.hb_knowledge import spreadsheet_preview
from hb_knowledge_app.hb_knowledge import markdown_preview


def _workbook(path, sheets=('Sheet1',), shared=(), rows_xml=''):
    """Minimal but valid xlsx package with one worksheet."""
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('xl/workbook.xml',
                         '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                         'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                         '<sheets>' + ''.join(
                             f'<sheet name="{name}" sheetId="{i + 1}" r:id="rId{i + 1}"/>'
                             for i, name in enumerate(sheets)) + '</sheets></workbook>')
        archive.writestr('xl/_rels/workbook.xml.rels',
                         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                         + ''.join(
                             f'<Relationship Id="rId{i + 1}" Type="worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
                             for i in range(len(sheets))) + '</Relationships>')
        archive.writestr('xl/sharedStrings.xml',
                         '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                         + ''.join(f'<si><t>{text}</t></si>' for text in shared) + '</sst>')
        for index in range(len(sheets)):
            archive.writestr(f'xl/worksheets/sheet{index + 1}.xml',
                             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                             '<sheetData>' + (rows_xml if index == 0 else '') + '</sheetData></worksheet>')


def test_shared_inline_gap_and_inline_string_cells_are_read_in_column_order(tmp_path):
    path = tmp_path / 'book.xlsx'
    _workbook(
        path, shared=('列头 A', '长句：该单元格的说明文字应当完整换行显示，而不是被页边裁断。'),
        rows_xml=(
            '<row r="1"><c r="A1" t="s"><v>0</v></c>'
            '<c r="B1" t="inlineStr"><is><t>内联文字</t></is></c></row>'
            # B2 deliberately absent: the column keeps its place instead of shifting.
            '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="C2"><v>42</v></c></row>'))
    sheets = spreadsheet_preview.read_sheets(path)
    assert [name for name, _rows in sheets] == ['Sheet1']
    rows = sheets[0][1]
    assert rows[0][:2] == ['列头 A', '内联文字']
    assert rows[1] == ['长句：该单元格的说明文字应当完整换行显示，而不是被页边裁断。', '', '42']


def test_long_cell_text_is_rendered_wrapped_and_escaped(tmp_path):
    text = '这是一段很长的说明文字，用来确认它会被完整放进单元格并自动换行。'
    html = spreadsheet_preview.render_html([('工作表', [[text, '<b>不是标记</b>']])], title='书名')
    assert text in html
    # A cell that looks like markup is text, never markup.
    assert '&lt;b&gt;不是标记&lt;/b&gt;' in html
    assert 'table-layout: fixed' in html and 'overflow-wrap: anywhere' in html
    assert '文本转换预览' in html


def test_workbook_without_text_is_refused_instead_of_rendering_an_empty_page(tmp_path):
    path = tmp_path / 'empty.xlsx'
    _workbook(path)
    with pytest.raises(ValueError, match='SPREADSHEET_NO_TEXT'):
        spreadsheet_preview.prepare_workbook(path, tmp_path / 'out.pdf',
                                             soffice=tmp_path / 'soffice',
                                             chrome=tmp_path / 'chrome')


def test_markdown_blocks_are_rendered_and_never_executed(tmp_path):
    body = '# 标题\n\n普通段落 **加粗** 与 `<code>`。\n\n- 一\n- 二\n\n| 列 | 值 |\n|---|---|\n| A | 1 |\n\n<script>alert(1)</script>'
    html = markdown_preview.render(body)
    assert '<h1>标题</h1>' in html
    assert '<strong>加粗</strong>' in html
    assert '<li>一</li>' in html
    assert '<th>列</th>' in html and '<td>A</td>' in html
    # The raw script tag is escaped, not emitted.
    assert '<script>' not in html
    assert '&lt;script&gt;' in html


def test_markdown_preview_carries_the_labelled_banner():
    page = markdown_preview.render_html('# 标题', title='草稿')
    assert markdown_preview.BANNER in page
    assert '请以原文件为准' in page
