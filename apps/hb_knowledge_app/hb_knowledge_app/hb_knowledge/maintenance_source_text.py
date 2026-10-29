"""Audited source-text admission and conversion rules for maintenance (RC13 B).

Pure functions only: no database, filesystem, network or model access.

Background: the legacy ``public_strings.source_string(strict_glyphs=True)`` gate
was written for model output and rejects any text where a ``<`` is followed by a
letter, because it treats a long comparison run (``压力<V≤50 000 ...``) as one
giant markup token. That gate is too coarse to decide whether a *derived
document text assembled from the original* may be indexed: printing/OCR residue
(``<V``, ``<MESC``), prose labels (``Data:``), inert URLs and placeholders such
as ``<product/processes>`` are ordinary document content, not markup.

This module provides the two reusable pieces:

* ``derived_source_findings`` / ``derived_source_admissible`` - a corrected
  admission gate for derived page text. It rejects only what is actually unsafe
  (well-formed unsafe tags, event-handler attributes, ``javascript:``/
  ``vbscript:`` schemes, data-URI payloads, encoded traversal, credential-like
  values) and reports uncertain content (unknown private-use glyphs, replacement
  characters, control characters) as holds instead of silently accepting it.
* ``convert_pages`` - minimal, recorded conversions for the cases that genuinely
  need text/structure work: real structural HTML tags become paragraph/row
  boundaries and cell separators (attributes such as ``href`` become inert
  text), audited private-use glyphs map to their known character, and line
  endings normalize. Repeated print headers/footers are available only as
  explicitly-requested normalization with recorded changes.

No body text is bulk-deleted, no glyph/control/replacement characters are
silently removed, and hashes are never used as proof of semantic preservation:
classification rests on the corrected gate, the recorded change list and the
digit/unit invariants.
"""
from __future__ import annotations

import re

from .errors import KnowledgeError

CONVERSION_SCHEMA = 'rc13-source-text-admission-v1'
MIN_HEADER_PAGES = 3

# Audited private-use glyph mapping (same table as the index symbol profile).
KNOWN_GLYPHS = {
    '\uf0b7': '•', '\uf0a7': '▪', '\uf06e': '■', '\uf075': '●', '\uf0d8': '•',
    '\uf0fc': '✓', '\uf0a8': '◆', '\uf02d': '-', '\uf0e0': '>', '\uf020': ' ',
    # Audited Wingdings point markers (rendered from the embedded subset font:
    # diamond-framed 1..4); they label figure/table points, not hidden digits.
    '\uf081': '①', '\uf082': '②', '\uf083': '③', '\uf084': '④',
    '\uf0fb': '✗',
}
PUA = re.compile(r'[\ue000-\uf8ff]')
REPLACEMENT = '\ufffd'
CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
DIGITS = re.compile(r'\d')
UNITS = re.compile(r'(?:MPa|kPa|kg|mg|mL|ml|mm|cm|m3|℃|°C|%|小时|分钟|天|年|月|日)')

TAG = re.compile(r'<\s*(/?)\s*([A-Za-z][A-Za-z0-9-]{0,31})((?:\s+[^<>]{0,300})?)\s*(/?)>')
LINK = re.compile(r'<a\b([^>]{0,300})>(.*?)</a>', re.S | re.I)
HREF = re.compile(r'''(?i)\bhref\s*=\s*(?:"([^"]{0,2048})"|'([^']{0,2048})')''')
ATTR_HOLD = re.compile(r'(?i)\bon[a-z]+\s*=|javascript:|vbscript:|data:|api.?key|token|password|secret')
UNSAFE_TAG_START = re.compile(
    r'(?i)<\s*/?\s*(?:script|style|iframe|object|embed|form|input|button|select|'
    r'textarea|link|meta|base|img|svg|math|template|video|audio|source|canvas|'
    r'noscript|frame|frameset|applet|param)\b')
DATA_URI = re.compile(
    r'(?i)\bdata:\s*(?:[a-z][a-z0-9.+-]*/[a-z0-9.+-]+(?:;[a-z0-9=.+-]+)*,|;base64,)')
SCRIPT_SCHEME = re.compile(r'(?i)\b(?:javascript|vbscript):')
ENCODED = re.compile(r'(?i)(?:%2f|%5c|\\\\u[0-9a-f]{4}|\.\.[\\/])')
CREDENTIAL = re.compile(r'(?i)(?:api.?key|token|password|secret)\s*[:=]\s*(\S+)')

TABLE_TAGS = {'table', 'thead', 'tbody', 'tfoot'}
CELL_TAGS = {'td', 'th'}
ROW_TAGS = {'tr'}
BLOCK_TAGS = {'p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
              'pre', 'blockquote', 'section', 'article', 'br'}
INLINE_TAGS = {'b', 'i', 'u', 'em', 'strong', 'span', 'font', 'center', 'small',
               'big', 'sup', 'sub', 'a', 'abbr', 'cite', 'code', 's', 'strike',
               'tt', 'var', 'mark', 'del', 'ins'}


def source_text(pages):
    """Same composition used by the batch derivative writer."""
    return '\n\n'.join(f'【原件物理第{i + 1}页】\n{text}' for i, text in enumerate(pages))


# ---------------------------------------------------------------- corrected gate
def derived_source_findings(text):
    """Blocking/hold findings for a derived document text (not model output).

    ``blocking`` findings mean the text must not be indexed/displayed as-is;
    non-blocking findings mean the content is uncertain and needs the original
    source (unknown glyphs, replacement/control characters). Everything else -
    comparison signs, prose labels, inert URLs, placeholders - is document
    content and is accepted.
    """
    if not isinstance(text, str):
        raise KnowledgeError('INVALID_REQUEST')
    findings = []
    for match in UNSAFE_TAG_START.finditer(text):
        findings.append({'rule': 'UNSAFE_HTML_TAG', 'blocking': True,
                         'offset': match.start(), 'length': len(match.group(0)),
                         'snippet': match.group(0)[:80]})
    for match in TAG.finditer(text):
        attrs = match.group(3) or ''
        if attrs and ATTR_HOLD.search(attrs):
            findings.append({'rule': 'UNSAFE_ATTRIBUTE', 'blocking': True,
                             'offset': match.start(), 'length': len(match.group(0)),
                             'snippet': match.group(0)[:80]})
        if match.group(2).lower() in {'script', 'style', 'iframe', 'object', 'embed'}:
            findings.append({'rule': 'UNSAFE_HTML_TAG', 'blocking': True,
                             'offset': match.start(), 'length': len(match.group(0)),
                             'snippet': match.group(0)[:80]})
    for match in LINK.finditer(text):
        href = HREF.search(match.group(1))
        if href and ATTR_HOLD.search(href.group(1) or href.group(2) or ''):
            findings.append({'rule': 'UNSAFE_ATTRIBUTE', 'blocking': True,
                             'offset': match.start(), 'length': len(match.group(0)),
                             'snippet': match.group(0)[:80]})
    for match in SCRIPT_SCHEME.finditer(text):
        findings.append({'rule': 'SCRIPT_SCHEME', 'blocking': True,
                         'offset': match.start(), 'length': len(match.group(0)),
                         'snippet': match.group(0).lower()})
    for match in DATA_URI.finditer(text):
        findings.append({'rule': 'DATA_URI_PAYLOAD', 'blocking': True,
                         'offset': match.start(), 'length': len(match.group(0)),
                         'snippet': match.group(0)[:40]})
    for match in ENCODED.finditer(text):
        findings.append({'rule': 'ENCODED_OR_TRAVERSAL', 'blocking': True,
                         'offset': match.start(), 'length': len(match.group(0)),
                         'snippet': match.group(0)})
    for match in CREDENTIAL.finditer(text):
        findings.append({'rule': 'CREDENTIAL_LIKE', 'blocking': True,
                         'offset': match.start(), 'length': len(match.group(0)),
                         'snippet': '***'})
    for match in PUA.finditer(text):
        if match.group(0) not in KNOWN_GLYPHS:
            findings.append({'rule': 'PUA_GLYPH_UNMAPPED', 'blocking': False,
                             'offset': match.start(), 'length': 1,
                             'snippet': 'U+%04X' % ord(match.group(0))})
    for index, char in enumerate(text):
        if char == REPLACEMENT:
            findings.append({'rule': 'REPLACEMENT_CHAR_UNMAPPED', 'blocking': False,
                             'offset': index, 'length': 1, 'snippet': 'U+FFFD'})
        elif CONTROL.fullmatch(char):
            findings.append({'rule': 'CONTROL_CHAR_UNMAPPED', 'blocking': False,
                             'offset': index, 'length': 1,
                             'snippet': 'U+%04X' % ord(char)})
    return findings


def derived_source_admissible(text):
    findings = derived_source_findings(text)
    return not any(finding['blocking'] for finding in findings) and not findings


def legacy_gate_findings(text):
    """Diagnostic replay of the legacy strict gate (real regex matches only)."""
    from .public_strings import DANGER_SOURCE
    findings = []
    for match in DANGER_SOURCE.finditer(text):
        findings.append({'rule': 'LEGACY_GATE_MARKUP_TOKEN',
                         'offset': match.start(), 'length': len(match.group(0)),
                         'snippet': match.group(0)[:40]})
    return findings


# ------------------------------------------------------------------- conversions
def repeated_boundary_lines(pages, minimum=MIN_HEADER_PAGES):
    """Exact repeated print header/footer candidates (evidence, never applied)."""
    first = {}
    last = {}
    for number, page in enumerate(pages, start=1):
        lines = [line.strip() for line in page.split('\n') if line.strip()]
        if not lines:
            continue
        first.setdefault(lines[0], []).append(number)
        last.setdefault(lines[-1], []).append(number)
    candidates = []
    for position, source in (('first', first), ('last', last)):
        for text, numbers in source.items():
            if len(numbers) >= minimum and len(text) <= 120:
                candidates.append({'position': position, 'text': text, 'pages': numbers})
    return sorted(candidates, key=lambda item: (item['position'], -len(item['pages'])))


def _tag_replacement(text, changes, holds):
    def replace(match):
        closing, name, attrs = match.group(1), match.group(2).lower(), match.group(3) or ''
        if UNSAFE_TAG_START.match(match.group(0)) or (attrs and ATTR_HOLD.search(attrs)):
            holds.append({'rule': 'UNSAFE_HTML_TAG', 'detail': name,
                          'offset': match.start()})
            return match.group(0)
        if name == 'br':
            changes.append({'rule': 'HTML_BREAK_TO_NEWLINE', 'offset': match.start(), 'count': 1})
            return '\n'
        if name in TABLE_TAGS:
            changes.append({'rule': 'HTML_TABLE_STRUCTURE', 'offset': match.start(), 'count': 1})
            return '\n'
        if name in CELL_TAGS:
            changes.append({'rule': 'HTML_TABLE_CELL_SEPARATOR', 'offset': match.start(), 'count': 1})
            return ' | ' if closing else ''
        if name in ROW_TAGS:
            changes.append({'rule': 'HTML_TABLE_ROW', 'offset': match.start(), 'count': 1})
            return '\n'
        if name in BLOCK_TAGS:
            changes.append({'rule': 'HTML_BLOCK_TO_NEWLINE', 'offset': match.start(), 'count': 1})
            return '\n'
        if name in INLINE_TAGS:
            changes.append({'rule': 'HTML_INLINE_TAG_DROPPED', 'offset': match.start(), 'count': 1})
            return ''
        # Unknown bounded token such as <testitem>: an inert placeholder.
        return match.group(0)
    return TAG.sub(replace, text)


def _link_replacement(text, changes, holds):
    def replace(match):
        attrs, inner = match.group(1), match.group(2)
        href_match = HREF.search(attrs)
        href = (href_match.group(1) or href_match.group(2)) if href_match else None
        if href and ATTR_HOLD.search(href):
            holds.append({'rule': 'UNSAFE_ATTRIBUTE', 'detail': 'a', 'offset': match.start()})
            return match.group(0)
        if href:
            changes.append({'rule': 'LINK_TO_INERT_TEXT', 'offset': match.start(), 'count': 1})
            return inner + '（链接：' + href + '）'
        changes.append({'rule': 'HTML_INLINE_TAG_DROPPED', 'offset': match.start(), 'count': 1})
        return inner
    return LINK.sub(replace, text)


def _glyph_replacement(text, changes, holds):
    out = []
    for index, char in enumerate(text):
        if char == REPLACEMENT:
            holds.append({'rule': 'REPLACEMENT_CHAR_UNMAPPED', 'detail': 'U+FFFD',
                          'offset': index})
            out.append(char)
        elif PUA.fullmatch(char):
            mapped = KNOWN_GLYPHS.get(char)
            if mapped is None:
                holds.append({'rule': 'PUA_GLYPH_UNMAPPED',
                              'detail': 'U+%04X' % ord(char), 'offset': index})
                out.append(char)
            else:
                changes.append({'rule': 'PUA_GLYPH_MAPPED',
                                'detail': 'U+%04X' % ord(char),
                                'offset': index, 'count': 1})
                out.append(mapped)
        elif CONTROL.fullmatch(char):
            holds.append({'rule': 'CONTROL_CHAR_UNMAPPED',
                          'detail': 'U+%04X' % ord(char), 'offset': index})
            out.append(char)
        else:
            out.append(char)
    return ''.join(out)


def _apply_header_normalization(pages, changes):
    candidates = repeated_boundary_lines(pages)
    removed = []
    if not candidates:
        return list(pages), removed
    removable = {(candidate['position'], candidate['text']) for candidate in candidates}
    working = []
    for number, page in enumerate(pages, start=1):
        lines = page.split('\n')
        stripped = [line.strip() for line in lines]
        first_index = next((index for index, line in enumerate(stripped) if line), None)
        last_index = next((index for index in range(len(stripped) - 1, -1, -1)
                           if stripped[index]), None)
        remove = set()
        for index, position in ((first_index, 'first'), (last_index, 'last')):
            if index is None:
                continue
            if number > 1 and (position, stripped[index]) in removable:
                remove.add(index)
        if remove:
            removed.extend(lines[index] for index in sorted(remove))
            lines = [line for index, line in enumerate(lines) if index not in remove]
            changes.append({'rule': 'REPEATED_PRINT_HEADER_NORMALIZED', 'page': number,
                            'count': len(remove)})
        working.append('\n'.join(lines))
    return working, removed


def _convert_one(page):
    changes = []
    holds = []
    text = _link_replacement(page, changes, holds)
    text = _tag_replacement(text, changes, holds)
    text = _glyph_replacement(text, changes, holds)
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    if normalized != text:
        changes.append({'rule': 'LINE_ENDING_NORMALIZED', 'count': 1, 'offset': 0})
    return normalized, changes, holds


def convert_pages(pages, *, page_checks=None, normalize_repeated_headers=False):
    """Return converted pages, recorded changes, holds and the safety class.

    ``SAFE_AUTO`` means the corrected derived-source gate admits the text, no
    uncertain content is present and every textual change is recorded (the
    change list may be empty when the document was only misclassified by the
    legacy model-output gate). ``HOLD_REVIEW`` never returns partially converted
    pages.
    """
    if not isinstance(pages, list) or not pages or not all(isinstance(page, str) for page in pages):
        raise KnowledgeError('INVALID_REQUEST')
    original = list(pages)
    working = list(original)
    changes = []
    holds = []
    removed_by_normalization = []
    if normalize_repeated_headers:
        working, removed_by_normalization = _apply_header_normalization(working, changes)
    converted = []
    for number, page in enumerate(working, start=1):
        text, page_changes, page_holds = _convert_one(page)
        for change in page_changes:
            change['page'] = number
        for hold in page_holds:
            hold['page'] = number
        changes.extend(page_changes)
        holds.extend(page_holds)
        converted.append(text)
    before = source_text(original)
    after = source_text(converted)
    for finding in derived_source_findings(after):
        if finding['blocking']:
            holds.append({'rule': finding['rule'], 'detail': finding.get('snippet'),
                          'offset': finding.get('offset')})
    deliberately_removed = '\n'.join(removed_by_normalization)
    invariants = {'digits_before': len(DIGITS.findall(before)),
                  'digits_after': len(DIGITS.findall(after)),
                  'units_before': len(UNITS.findall(before)),
                  'units_after': len(UNITS.findall(after)),
                  'normalization_removed_chars': len(deliberately_removed)}
    # Only explicitly requested, recorded header/footer normalization may change
    # the digit/unit counts; any other change is a hold.
    if invariants['digits_before'] != invariants['digits_after'] + len(DIGITS.findall(deliberately_removed)):
        holds.append({'rule': 'INVARIANT_DIGITS_CHANGED'})
    if invariants['units_before'] != invariants['units_after'] + len(UNITS.findall(deliberately_removed)):
        holds.append({'rule': 'INVARIANT_UNITS_CHANGED'})
    if page_checks is None:
        holds.append({'rule': 'PAGE_CHECKS_MISSING'})
    else:
        if page_checks.get('quality_pass') is not True:
            holds.append({'rule': 'QUALITY_CHECK_FAILED'})
        if page_checks.get('gap_pages'):
            holds.append({'rule': 'PAGE_GAP_REQUIRES_RETRIEVAL'})
    legacy_before = 'REJECTED' if legacy_gate_findings(before) else 'ACCEPTED'
    legacy_after = 'REJECTED' if legacy_gate_findings(after) else 'ACCEPTED'
    if holds:
        return {'schema': CONVERSION_SCHEMA, 'class': 'HOLD_REVIEW',
                'pages': original, 'changes': changes, 'holds': holds,
                'reason': holds[0].get('rule'),
                'legacy_gate_before': legacy_before, 'legacy_gate_after': legacy_after,
                'invariants': invariants}
    if legacy_before == 'ACCEPTED' and not changes:
        return {'schema': CONVERSION_SCHEMA, 'class': 'NO_CHANGE',
                'pages': converted, 'changes': [], 'holds': [],
                'reason': 'ALREADY_ADMISSIBLE',
                'legacy_gate_before': legacy_before, 'legacy_gate_after': legacy_after,
                'invariants': invariants}
    return {'schema': CONVERSION_SCHEMA, 'class': 'SAFE_AUTO',
            'pages': converted, 'changes': changes, 'holds': [],
            'reason': 'DERIVED_GATE_ADMITS_TEXT' if not changes else changes[0].get('rule'),
            'legacy_gate_before': legacy_before, 'legacy_gate_after': legacy_after,
            'invariants': invariants}


def convert_batch(pages, *, page_checks=None, normalize_repeated_headers=False):
    """Thin alias used by batch tooling; same contract as convert_pages."""
    return convert_pages(pages, page_checks=page_checks,
                         normalize_repeated_headers=normalize_repeated_headers)
