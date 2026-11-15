import { describe, expect, it } from 'vitest'
import { renderAnswer, escapeAnswerText } from '@/services/knowledgeAnswerFormat'

/**
 * The answer formatter is the only place where model text becomes markup, so it
 * is pinned from the unsafe side: whatever the source says, the output may only
 * contain the fixed set of structural tags this renderer writes itself.
 */
describe('knowledge answer rendering', () => {
  it('turns the conventional structure into real elements instead of literal markers', () => {
    const html = renderAnswer('**结论**\n\n### 一、洁净区等级\n- 悬浮粒子\n- 微生物\n\n1. 第一步\n2. 第二步')
    expect(html).toContain('<strong>结论</strong>')
    expect(html).toContain('<h5>一、洁净区等级</h5>')
    expect(html).toContain('<ul><li>悬浮粒子</li><li>微生物</li></ul>')
    expect(html).toContain('<ol><li>第一步</li><li>第二步</li></ol>')
    expect(html).not.toContain('**')
    expect(html).not.toContain('- 悬浮粒子')
  })

  it('never lets source text become markup, a link or an attribute', () => {
    const hostile = [
      '<script>alert(1)</script>',
      '<img src=x onerror=alert(1)>',
      '[点击](https://evil.example/x)',
      '<a href="javascript:alert(1)">x</a>',
      '<div style="position:fixed">overlay</div>',
    ].join('\n')
    const html = renderAnswer(hostile)
    // Strip the renderer's own structural tags; nothing else may be a tag.
    const stripped = html.replace(/<\/?(?:p|br|strong|em|code|pre|ul|ol|li|h3|h4|h5|table|thead|tbody|tr|th|td)>/g, '')
    expect(stripped).not.toContain('<')
    expect(stripped).not.toContain('>')
    expect(html).toContain('&lt;script&gt;')
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;')
    // A markdown link keeps its text; no anchor is produced.
    expect(html).toContain('[点击](https://evil.example/x)')
  })

  it('keeps inline code and fenced blocks as text', () => {
    const html = renderAnswer('见 `SOP-LC-3-00-006`\n```\n<script>x</script>\n```')
    expect(html).toContain('<code>SOP-LC-3-00-006</code>')
    expect(html).toContain('<pre>&lt;script&gt;x&lt;/script&gt;</pre>')
  })

  it('renders a simple pipe table without any attribute', () => {
    const html = renderAnswer('| 等级 | 要求 |\n|---|---|\n| A | 单向流 |\n| B | 层流 |')
    expect(html).toContain('<table><thead><tr><th>等级</th><th>要求</th></tr></thead>')
    expect(html).toContain('<tr><td>A</td><td>单向流</td></tr>')
    expect(html).not.toContain('<table ')
  })

  it('keeps blank-line paragraphs and single newlines distinguishable', () => {
    const html = renderAnswer('第一段第一行\n第一段第二行\n\n第二段')
    expect(html).toBe('<p>第一段第一行<br>第一段第二行</p><p>第二段</p>')
  })

  it('escapes every dangerous character before any replacement runs', () => {
    expect(escapeAnswerText('<&">\''))
      .toBe('&lt;&amp;&quot;&gt;&#39;')
    // Bold markers around escaped text still produce a real tag, not raw angle brackets.
    expect(renderAnswer('**a < b**')).toBe('<p><strong>a &lt; b</strong></p>')
  })

  it('leaves an empty answer empty rather than emitting an empty paragraph', () => {
    expect(renderAnswer('')).toBe('')
    expect(renderAnswer('   \n\n  ')).toBe('')
  })
})
