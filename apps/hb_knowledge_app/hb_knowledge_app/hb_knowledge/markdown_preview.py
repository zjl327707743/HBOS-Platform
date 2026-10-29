"""Text preview for a Markdown draft.

Markdown has no original layout to preserve, so the preview is a clearly
labelled rendering of the source text and the original `.md` stays the download.
The renderer is deliberately small and local: headings, paragraphs, bullet and
numbered lists, fenced code, blockquotes and pipe tables. Nothing is fetched and
nothing in the document is executed - the HTML is built from escaped text and
printed by a headless browser that is given no network access.

This lives in the app (not in a private script) so the same reviewed code that
produced a published preview can be re-run from the repository.
"""
from __future__ import annotations

import html
import re
import subprocess
import tempfile
from pathlib import Path

BANNER = ('文本转换预览：本文件由 Markdown 草稿排版生成，用于在线阅读；'
          '原件为 .md 文件，请以原文件为准。')

CSS = """
@page { size: A4; margin: 16mm 14mm; }
html, body, table, th, td, strong, b, code, pre, li, p {
  font-family: "STHeiti", "Arial Unicode MS", sans-serif; font-synthesis: none;
}
body { font-size: 10.5pt; line-height: 1.6; color: #1c2733; }
.banner { margin: 0 0 12px; padding: 6px 10px; border: 1px solid #d8b400;
          background: #fffaea; font-size: 9pt; color: #6b5200; }
h1 { font-size: 18pt; line-height: 1.35; border-bottom: 2px solid #159b89; padding-bottom: 6px; }
h2 { font-size: 14pt; margin-top: 20px; color: #14476b; }
h3 { font-size: 12pt; color: #1f5f55; }
h4 { font-size: 11pt; }
blockquote { margin: 8px 0; padding: 6px 10px; border-left: 3px solid #9fd6c8; background: #f4faf8; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9pt; }
th, td { border: 1px solid #b9c6d4; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #e8f4f1; }
code { background: #f1f4f7; padding: 1px 3px; }
pre { background: #f1f4f7; padding: 8px; font-size: 8.5pt; white-space: pre-wrap;
      word-break: break-word; font-family: "STHeiti", monospace; }
ul, ol { margin: 4px 0 4px 18px; }
hr { border: 0; border-top: 1px solid #cfd8e2; margin: 14px 0; }
"""


def _inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)


def _table(rows):
    head, body = rows[0], rows[2:]
    out = ['<table><thead><tr>' + ''.join(f'<th>{_inline(c)}</th>' for c in head)
           + '</tr></thead><tbody>']
    for row in body:
        out.append('<tr>' + ''.join(f'<td>{_inline(c)}</td>' for c in row) + '</tr>')
    out.append('</tbody></table>')
    return '\n'.join(out)


def render(markdown):
    """HTML body for the source text; every block is escaped before formatting."""
    lines = markdown.splitlines()
    out, index = [], 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if re.fullmatch(r'(-{3,}|\*{3,}|_{3,})', stripped):
            out.append('<hr>')
            index += 1
            continue
        if stripped.startswith('```'):
            fence = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith('```'):
                fence.append(lines[index])
                index += 1
            index += 1
            out.append('<pre>' + html.escape('\n'.join(fence)) + '</pre>')
            continue
        heading = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if heading:
            level = len(heading.group(1))
            out.append(f'<h{level}>{_inline(heading.group(2))}</h{level}>')
            index += 1
            continue
        if stripped.startswith('|') and index + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|$', lines[index + 1].strip()):
            rows = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                rows.append([cell.strip() for cell in lines[index].strip().strip('|').split('|')])
                index += 1
            out.append(_table(rows))
            continue
        if stripped.startswith('>'):
            quote = []
            while index < len(lines) and lines[index].strip().startswith('>'):
                quote.append(lines[index].strip()[1:].strip())
                index += 1
            parts, items = [], []
            for entry in quote:
                item = re.match(r'^(?:[-*+]|\d+[.)])\s+(.*)$', entry)
                if item:
                    items.append(item.group(1))
                    continue
                if items:
                    parts.append('<ul>' + ''.join(f'<li>{_inline(x)}</li>' for x in items) + '</ul>')
                    items = []
                if entry:
                    parts.append(_inline(entry))
            if items:
                parts.append('<ul>' + ''.join(f'<li>{_inline(x)}</li>' for x in items) + '</ul>')
            out.append('<blockquote>' + '<br>'.join(parts) + '</blockquote>')
            continue
        if re.match(r'^[-*+]\s+', stripped):
            items = []
            while index < len(lines) and re.match(r'^[-*+]\s+', lines[index].strip()):
                items.append(re.sub(r'^[-*+]\s+', '', lines[index].strip()))
                index += 1
            out.append('<ul>' + ''.join(f'<li>{_inline(x)}</li>' for x in items) + '</ul>')
            continue
        if re.match(r'^\d+[.)]\s+', stripped):
            items = []
            while index < len(lines) and re.match(r'^\d+[.)]\s+', lines[index].strip()):
                items.append(re.sub(r'^\d+[.)]\s+', '', lines[index].strip()))
                index += 1
            out.append('<ol>' + ''.join(f'<li>{_inline(x)}</li>' for x in items) + '</ol>')
            continue
        paragraph = []
        while (index < len(lines) and lines[index].strip()
               and not lines[index].strip().startswith(('#', '|', '>', '```'))
               and not re.match(r'^[-*+]\s+', lines[index].strip())
               and not re.match(r'^\d+[.)]\s+', lines[index].strip())):
            paragraph.append(lines[index].strip())
            index += 1
        out.append('<p>' + '<br>'.join(_inline(text) for text in paragraph) + '</p>')
    return '\n'.join(out)


def render_html(markdown, *, title=''):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body>'
            f'<div class="banner">{BANNER}</div>{render(markdown)}</body></html>')


def prepare_markdown(source, destination, *, chrome):
    """Write a labelled text-conversion PDF preview; the source is only read."""
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    page = render_html(source.read_text(encoding='utf-8'), title=source.stem)
    with tempfile.TemporaryDirectory(prefix='rc154-md-') as temp:
        html_path = Path(temp) / 'draft.html'
        html_path.write_text(page, encoding='utf-8')
        subprocess.run([str(chrome), '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                        '--no-sandbox', '--virtual-time-budget=4000',
                        f'--print-to-pdf={destination}', html_path.as_uri()],
                       capture_output=True, text=True, timeout=120)
    if not destination.is_file() or destination.stat().st_size < 2000:
        raise ValueError('MARKDOWN_RENDER_FAILED')
    from pypdf import PdfReader
    import hashlib
    return {'path': destination, 'kind': 'DERIVED_PDF',
            'pages': len(PdfReader(str(destination)).pages),
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
