"""RC13 B-class: corrected derived-source gate + minimal recorded conversions.

The legacy model-output gate is too coarse for derived document text: comparison
signs, prose labels, inert URLs and placeholders must not reject a whole source.
Unsafe markup and genuinely uncertain content still must not be auto-admitted.
"""
import pytest

from hb_knowledge_app.hb_knowledge import maintenance_source_text as rules
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def run(pages, **kwargs):
    kwargs.setdefault('page_checks', {'quality_pass': True})
    return rules.convert_pages(pages, **kwargs)


def admissible(pages):
    return rules.derived_source_admissible(rules.source_text(pages))


def test_comparison_symbols_are_document_content_not_markup():
    pages = ['阀前压力<V≤50 000 Pa，回油压力P>100 kPa\n公称直径D≤100 mm\n温度t≤270 ℃',
             '第二页：<L≤182 40 MPa，上限L>235 MPa']
    result = run(pages)
    assert result['class'] == 'SAFE_AUTO'
    # Fidelity: nothing in the body is rewritten to satisfy the legacy gate.
    assert result['pages'] == pages
    assert result['changes'] == []
    assert admissible(result['pages'])
    assert result['invariants']['digits_before'] == result['invariants']['digits_after']
    assert result['invariants']['units_before'] == result['invariants']['units_after']
    # The legacy gate is recorded as still rejecting this text, honestly.
    assert result['legacy_gate_before'] == 'REJECTED'


def test_unknown_angle_placeholder_stays_inert_text():
    pages = ['产品模板<product/processes>用于质量审核，编号<testitem>。']
    result = run(pages)
    assert result['class'] == 'SAFE_AUTO'
    assert result['pages'] == pages
    assert admissible(result['pages'])
    assert '</' not in result['pages'][0] or '<product/processes>' in result['pages'][0]


def test_structural_html_tags_preserve_paragraph_and_table_semantics():
    pages = ['<p>标准条款正文</p><br>'
             '<table><tr><th>项目</th><th>限值</th></tr>'
             '<tr><td>压力</td><td>3 MPa</td></tr>'
             '<tr><td>温度</td><td>40 ℃</td></tr></table>']
    result = run(pages)
    assert result['class'] == 'SAFE_AUTO'
    text = result['pages'][0]
    assert '标准条款正文' in text
    assert '项目' in text and '限值' in text and '压力' in text
    assert '3 MPa' in text and '40 ℃' in text
    assert '<p>' not in text and '<td>' not in text
    assert '|' in text and '\n' in text
    assert result['invariants']['digits_before'] == result['invariants']['digits_after']
    assert result['invariants']['units_before'] == result['invariants']['units_after']
    assert admissible(result['pages'])
    rule_ids = {change['rule'] for change in result['changes']}
    assert {'HTML_TABLE_CELL_SEPARATOR', 'HTML_TABLE_ROW'} <= rule_ids


def test_public_link_is_kept_as_inert_readable_text():
    pages = ['参考公开文献<a href="https://example.org/report/2026">年度报告</a>，不得自动跳转。']
    result = run(pages)
    assert result['class'] == 'SAFE_AUTO'
    text = result['pages'][0]
    assert '年度报告' in text and 'https://example.org/report/2026' in text
    assert '（链接：' in text
    assert '<a' not in text
    assert admissible(result['pages'])


def test_ordinary_print_url_is_not_rejected_because_it_looks_like_a_url():
    pages = ['公开文献来源 https://example.org/standard/1234 与 www.example.org 均在正文中惰性呈现。']
    result = run(pages)
    assert result['class'] in ('NO_CHANGE', 'SAFE_AUTO')
    assert result['pages'] == pages
    assert admissible(result['pages'])


def test_active_script_link_is_held_never_auto_converted():
    result = run(['<a href="javascript:alert(1)">点我</a>'])
    assert result['class'] == 'HOLD_REVIEW'
    assert result['holds'][0]['rule'] in ('UNSAFE_ATTRIBUTE', 'SCRIPT_SCHEME')
    assert result['pages'] == ['<a href="javascript:alert(1)">点我</a>']


def test_script_and_style_tags_are_held_without_partial_conversion():
    original = ['<script>alert(1)</script>正文']
    result = run(original)
    assert result['class'] == 'HOLD_REVIEW'
    assert result['pages'] == original
    assert any(hold['rule'] == 'UNSAFE_HTML_TAG' for hold in result['holds'])


def test_scheme_looking_prose_label_is_admissible_without_rewriting():
    result = run(['Data: 完整性要求\nFile: 附件清单'])
    assert result['class'] == 'SAFE_AUTO'
    assert result['pages'] == ['Data: 完整性要求\nFile: 附件清单']
    assert result['changes'] == []
    assert admissible(result['pages'])


def test_mailto_contact_address_stays_lazy_text():
    pages = ['联系人：mailto:someone@example.com']
    result = run(pages)
    assert result['class'] == 'SAFE_AUTO'
    assert result['pages'] == pages
    assert admissible(result['pages'])


def test_data_uri_payload_is_a_hold_not_a_text_conversion():
    result = run(['嵌入图 data:image/png;base64,iVBORw0KGgo='])
    assert result['class'] == 'HOLD_REVIEW'
    assert result['holds'][0]['rule'] == 'DATA_URI_PAYLOAD'


@pytest.mark.parametrize('text,rule', [
    ('api key: abcdef123456', 'CREDENTIAL_LIKE'),
    ('password = hunter2', 'CREDENTIAL_LIKE'),
    ('路径 ..\\windows\\system32', 'ENCODED_OR_TRAVERSAL'),
    ('参数 %2fetc%2fpasswd', 'ENCODED_OR_TRAVERSAL'),
    ('脚本 javascript:alert(1)', 'SCRIPT_SCHEME'),
])
def test_unsafe_residue_is_held_and_never_guessed(text, rule):
    result = run([text])
    assert result['class'] == 'HOLD_REVIEW'
    assert result['holds'][0]['rule'] == rule
    assert result['pages'] == [text]


def test_known_private_use_glyph_is_mapped_with_an_audit_record():
    result = run(['\uf0b7 第一条要求\n\uf0fc 已确认'])
    assert result['class'] == 'SAFE_AUTO'
    assert '• 第一条要求' in result['pages'][0]
    assert '✓ 已确认' in result['pages'][0]
    assert admissible(result['pages'])
    mapped = [change for change in result['changes'] if change['rule'] == 'PUA_GLYPH_MAPPED']
    assert len(mapped) == 2


def test_unknown_private_use_glyph_is_held_not_deleted():
    result = run(['符号\uf0ff未知含义'])
    assert result['class'] == 'HOLD_REVIEW'
    assert result['holds'][0]['rule'] in ('PUA_GLYPH_UNMAPPED', 'INVARIANT_DIGITS_CHANGED')
    assert result['pages'] == ['符号\uf0ff未知含义']


def test_replacement_character_is_held_even_when_gate_would_otherwise_pass():
    result = run(['正文缺失\ufffd数字单位'])
    assert result['class'] == 'HOLD_REVIEW'
    assert any(hold['rule'] == 'REPLACEMENT_CHAR_UNMAPPED' for hold in result['holds'])


def test_control_character_is_held_but_line_endings_normalize():
    held = run(['正文\x01控制符'])
    assert held['class'] == 'HOLD_REVIEW'
    assert any(hold['rule'] == 'CONTROL_CHAR_UNMAPPED' for hold in held['holds'])
    normalized = run(['第一行\r\n第二行'])
    assert normalized['pages'] == ['第一行\n第二行']
    assert normalized['class'] == 'SAFE_AUTO'
    assert any(change['rule'] == 'LINE_ENDING_NORMALIZED' for change in normalized['changes'])


def test_page_checks_are_required_before_any_auto_classification():
    missing = rules.convert_pages(['压力<V≤50'])
    assert missing['class'] == 'HOLD_REVIEW'
    assert any(hold['rule'] == 'PAGE_CHECKS_MISSING' for hold in missing['holds'])
    gap = run(['压力<V≤50'], page_checks={'quality_pass': True, 'gap_pages': [2]})
    assert gap['class'] == 'HOLD_REVIEW'
    assert any(hold['rule'] == 'PAGE_GAP_REQUIRES_RETRIEVAL' for hold in gap['holds'])


def test_numeric_attribute_loss_is_caught_by_the_invariant_not_ignored():
    result = run(['<table><tr><td colspan="3">数值</td></tr></table>'])
    assert result['class'] == 'HOLD_REVIEW'
    assert any(hold['rule'] == 'INVARIANT_DIGITS_CHANGED' for hold in result['holds'])


def test_repeated_print_headers_are_reported_but_not_removed_by_default():
    repeated = ['标准编号 SH/T 3001\n正文一', '标准编号 SH/T 3001\n正文二',
                '标准编号 SH/T 3001\n正文三']
    candidates = rules.repeated_boundary_lines(repeated)
    assert any(candidate['text'] == '标准编号 SH/T 3001' for candidate in candidates)
    untouched = run(repeated)
    assert untouched['pages'] == repeated
    normalized = run(repeated, normalize_repeated_headers=True)
    assert normalized['class'] == 'SAFE_AUTO'
    assert '标准编号 SH/T 3001' in normalized['pages'][0]
    assert '标准编号 SH/T 3001' not in normalized['pages'][1]
    assert any(change['rule'] == 'REPEATED_PRINT_HEADER_NORMALIZED'
               for change in normalized['changes'])


def test_no_change_means_legacy_gate_already_admissible():
    result = run(['普通正文，没有残留。'])
    assert result['class'] == 'NO_CHANGE'
    assert result['changes'] == [] and result['holds'] == []


def test_findings_mask_credentials_and_report_offsets():
    findings = rules.derived_source_findings('前缀 api key: very-secret-value 后缀')
    credential = [finding for finding in findings if finding['rule'] == 'CREDENTIAL_LIKE']
    assert credential and credential[0]['snippet'] == '***'
    assert 'very-secret-value' not in str(findings)
    assert credential[0]['offset'] > 0


def test_audited_glyph_table_matches_the_service_symbol_profile_when_available():
    try:
        from knowledge_service.ingestion import SYMBOL_GLYPHS
    except ImportError:
        pytest.skip('service package not importable in this environment')
    assert rules.KNOWN_GLYPHS == SYMBOL_GLYPHS


def test_classification_is_not_proven_by_a_hash():
    result = run(['压力<V≤50 000'])
    rendered = str(result)
    assert 'sha256' not in rendered
    assert result['invariants']['digits_before'] == result['invariants']['digits_after']


def test_invalid_pages_input_is_rejected():
    with pytest.raises(KnowledgeError):
        rules.convert_pages([])
    with pytest.raises(KnowledgeError):
        rules.convert_pages(['ok', 3])


def test_audited_wingdings_point_markers_map_to_circled_numbers():
    from hb_knowledge_app.hb_knowledge.maintenance_source_text import convert_pages, derived_source_findings
    result = convert_pages(['Figure 3.1 points \uf081 and \uf082; step \uf083; row \uf084.'],
                           page_checks={'quality_pass': True})
    text = result['pages'][0]
    assert '①' in text and '②' in text and '③' in text and '④' in text
    assert not derived_source_findings(text)
    assert result['changes']
