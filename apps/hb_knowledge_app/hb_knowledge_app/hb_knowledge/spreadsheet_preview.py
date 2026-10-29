"""Readable, clearly labelled preview for a spreadsheet.

A workbook has no page layout of its own: LibreOffice's page-preserving export
keeps every column, but it also keeps each row's *stored* height, so a long
sentence in a cell that was never given a taller row still runs past the page
edge. The text is in the PDF and extractable, but a person reading it sees a
cut-off line - which is not "readable".

This renderer writes the cell text itself: every sheet becomes a table whose
width is the page width, every cell is wrapped, and rows grow to their content.
Columns keep their original order and the sheet name is printed, so the result
is a faithful *text* view of the workbook (labelled 转换预览), never a claim to be
the original layout. The original file remains the download.

Only the offline preview builder calls this; nothing here is reachable from a
request. Values are read from the package; formulas are not evaluated (their
cached result is shown, exactly as the file stores it), macros are never run.
"""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile
from xml.etree import ElementTree

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
_EMPTY = re.compile(r'^\s*$')


def _text(node):
    return ''.join(node.itertext())


def _shared_strings(archive):
    try:
        root = ElementTree.fromstring(archive.read('xl/sharedStrings.xml'))
    except KeyError:
        return []
    return [_text(item) for item in root.findall('m:si', NS)]


def _sheets(archive):
    workbook = ElementTree.fromstring(archive.read('xl/workbook.xml'))
    rels = ElementTree.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
    targets = {relation.get('Id'): relation.get('Target') for relation in rels}
    out = []
    for sheet in workbook.findall('m:sheets/m:sheet', NS):
        relation = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        target = targets.get(relation) or ''
        if target.startswith('/'):
            path = target.lstrip('/')
        elif target.startswith('xl/'):
            path = target
        else:
            path = 'xl/' + target
        out.append((sheet.get('name') or '', path))
    return out


def _column_index(reference):
    letters = re.match(r'([A-Z]+)', reference or '')
    if not letters:
        return None
    value = 0
    for char in letters.group(1):
        value = value * 26 + (ord(char) - 64)
    return value


def read_sheets(path):
    """[(sheet name, [[cell text in column order], ...])] with formulas as values."""
    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        sheets = []
        for name, sheet_path in _sheets(archive):
            try:
                root = ElementTree.fromstring(archive.read(sheet_path))
            except KeyError:
                continue
            rows = []
            width = 0
            for row in root.findall('m:sheetData/m:row', NS):
                cells = {}
                for cell in row.findall('m:c', NS):
                    column = _column_index(cell.get('r'))
                    if column is None:
                        continue
                    kind = cell.get('t')
                    value = cell.find('m:v', NS)
                    if kind == 's' and value is not None:
                        try:
                            text = shared[int(value.text)]
                        except (ValueError, IndexError, TypeError):
                            text = ''
                    elif kind == 'inlineStr':
                        inline = cell.find('m:is', NS)
                        text = _text(inline) if inline is not None else ''
                    else:
                        text = value.text if value is not None and value.text is not None else ''
                    if _EMPTY.match(text or ''):
                        continue
                    cells[column] = text
                    width = max(width, column)
                if cells:
                    rows.append([cells.get(index, '')
                                 for index in range(1, max(cells) + 1)])
            for index, row in enumerate(rows):
                if len(row) < width:
                    rows[index] = row + [''] * (width - len(row))
            sheets.append((name, rows))
        return sheets


CSS = """
@page { size: A3 landscape; margin: 10mm 10mm 12mm; }
html, body { margin: 0; padding: 0; }
body { font-family: "Helvetica Neue", "STHeiti", sans-serif; color: #1c2733; }
.banner { margin: 0 0 8px; padding: 6px 10px; border: 1px solid #d8b400;
          background: #fffaea; font-size: 9pt; color: #6b5200; }
h2 { font-size: 12pt; margin: 14px 0 6px; color: #14476b; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; margin: 0 0 6px; }
/* A row that fits on a page is never split across two: a cell whose sentence
   continued on the next page read as two unrelated fragments. A row taller
   than a whole page still has to break. */
tr { break-inside: avoid; page-break-inside: avoid; }
thead { display: table-header-group; }
td { border: 0.5px solid #b9c6d4; padding: 2px 4px; vertical-align: top;
     font-size: 8pt; line-height: 1.35; white-space: pre-wrap;
     overflow-wrap: anywhere; word-break: break-word; }
thead td { background: #eef4f8; font-weight: 600; font-size: 7.5pt; color: #33475b; }
"""

MAX_COLUMNS_PER_TABLE = 6


def render_html(sheets, *, title):
    parts = ['<div class="banner">文本转换预览：按原表逐行逐列展开，单元格全文换行显示；'
             '原文件的排版（列宽、合并、图片）不在本预览中，请以原文件为准。</div>']
    for name, rows in sheets:
        if not rows:
            continue
        width = max(len(row) for row in rows)
        parts.append('<h2>%s</h2>' % html.escape(name or '工作表'))
        for start in range(0, width, MAX_COLUMNS_PER_TABLE):
            end = min(width, start + MAX_COLUMNS_PER_TABLE)
            parts.append('<table><thead><tr>')
            parts.append(''.join('<td>列 %d</td>' % (index + 1) for index in range(start, end)))
            parts.append('</tr></thead><tbody>')
            for row in rows:
                cells = row[start:end] + [''] * max(0, end - start - len(row[start:end]))
                if not any(cell.strip() for cell in cells):
                    continue
                parts.append('<tr>' + ''.join(
                    '<td>%s</td>' % html.escape(cell) for cell in cells) + '</tr>')
            parts.append('</tbody></table>')
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<title>%s</title><style>%s</style></head><body>%s</body></html>'
            % (html.escape(title), CSS, ''.join(parts)))


def _office_to_xlsx(source, work, soffice):
    target = work / 'source.xlsx'
    result = subprocess.run(
        [str(soffice), '-env:UserInstallation=' + (work / 'convert-profile').as_uri(),
         '--headless', '--nologo', '--nodefault', '--nofirststartwizard',
         '--convert-to', 'xlsx', '--outdir', str(work), str(source)],
        capture_output=True, timeout=120)
    produced = work / (Path(source).stem + '.xlsx')
    if result.returncode or not produced.is_file():
        raise ValueError('OFFICE_CONVERSION_FAILED')
    produced.replace(target)
    return target


def prepare_workbook(source, destination, *, soffice, chrome, title=None):
    """Render a spreadsheet to a wrapped, fully readable PDF preview."""
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='rc154-sheet-', dir=destination.parent) as temp:
        work = Path(temp)
        package = source
        if source.suffix.lower() != '.xlsx':
            package = _office_to_xlsx(source, work, soffice)
        sheets = read_sheets(package)
        if not sheets or not any(rows for _name, rows in sheets):
            raise ValueError('SPREADSHEET_NO_TEXT')
        page = render_html(sheets, title=title or source.name)
        html_path = work / 'sheet.html'
        html_path.write_text(page, encoding='utf-8')
        result = subprocess.run(
            [str(chrome), '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
             '--no-sandbox', '--virtual-time-budget=6000',
             f'--print-to-pdf={destination}', html_path.as_uri()],
            capture_output=True, text=True, timeout=180)
    if not destination.is_file() or destination.stat().st_size < 2000:
        raise ValueError('SPREADSHEET_RENDER_FAILED')
    from pypdf import PdfReader
    pages = len(PdfReader(str(destination)).pages)
    import hashlib
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return {'path': destination, 'kind': 'DERIVED_PDF', 'pages': pages, 'sha256': digest}
