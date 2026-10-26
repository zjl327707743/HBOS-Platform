/**
 * AI 报告 Markdown → 结构化块。**纯函数，可单测**。
 *
 * 为什么不引 markdown 解析库：
 *
 *   - 报告实际只用到很少的语法（见下），为它装一个 parser 不划算
 *   - **安全**：模型偶尔会在正文里输出原样的 HTML（`<b>`、`<script>`）。
 *     这里输出的是一组**文本片段**，渲染层用 `{{ }}` 插值 —— 不会被执行。
 *     换成 `v-html` + 通用 markdown 库就丢掉了这层保障。
 *
 * 支持的语法（实测 62 份报告，只出现这些）：
 *
 *     ## 标题          段标题
 *     1. / - 列表       有序 / 无序列表
 *     **加粗**          行内加粗（实际只用于建议的 `**[高]**`）
 *
 * 「改进建议」段由 Python 渲染（`parse.render_suggestions`），格式固定是
 * `1. **[高]** 动作` + `   - 依据：…`，单独归成 `sug` 块：那段是给人照做的，
 * 和「当前现状」这类叙述性段落分开显示，扫读时能一眼找到。
 * 开头的 `[高]/[中]/[低]` 会抽出来当优先级标记，不留在正文里。
 */

/** 一段行内文本。`bold` 为真时渲染成 `<strong>`。 */
export interface Inline {
  text: string
  bold?: boolean
}

export type ReportBlock =
  | { type: 'h'; text: string }
  | { type: 'p'; spans: Inline[] }
  | { type: 'ul'; items: Inline[][] }
  | { type: 'sug'; spans: Inline[]; priority: string | null }

/** 「改进建议」段的识别标记 —— 与 `parse.render_suggestions` 的标题逐字一致。 */
const SUGGESTION_HEADING = '改进建议'

/** 建议开头的优先级标记：`[高]` / `[中]` / `[低]`（可能被 `**` 包着）。 */
const PRIORITY_RE = /^\s*(?:\*\*)?\[(高|中|低)\](?:\*\*)?\s*/

/**
 * 行内 `**加粗**` → 片段数组。
 *
 * 不处理嵌套、不处理 `*斜体*` —— 实测 62 份报告里**没有出现过**这两种，
 * 加了只是多一条没被测过的代码路径。真出现了按纯文本显示，不影响可读性。
 */
export function parseInline(text: string): Inline[] {
  const out: Inline[] = []
  const re = /\*\*(.+?)\*\*/g
  let last = 0
  let m: RegExpExecArray | null

  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push({ text: text.slice(last, m.index) })
    out.push({ text: m[1] ?? '', bold: true })
    last = m.index + m[0].length
  }
  if (last < text.length) out.push({ text: text.slice(last) })
  // 空输入也返回一个空片段，调用方不用判空
  return out.length ? out : [{ text: '' }]
}

export function parseReport(markdown: string | null | undefined): ReportBlock[] {
  const raw = (markdown || '').trim()
  if (!raw) return []

  const blocks: ReportBlock[] = []
  let inSuggest = false
  let list: Inline[][] | null = null

  const flushList = () => {
    if (list) {
      blocks.push({ type: 'ul', items: list })
      list = null
    }
  }

  for (const line of raw.split('\n')) {
    const t = line.trim()

    if (!t) {
      flushList()
      continue
    }

    if (t.startsWith('## ')) {
      flushList()
      const title = t.slice(3).trim()
      inSuggest = title.includes(SUGGESTION_HEADING)
      blocks.push({ type: 'h', text: title })
      continue
    }

    // 建议段内的缩进列表（`   - 依据：…`）也是建议的一部分，
    // 不能因为「是列表」就被拆到 ul 里 —— 那样和建议正文分家，看不出属于哪条。
    if (inSuggest) {
      // 序号（`1. `）与列表符号（`- `）都要剥掉，否则优先级标记匹配不到 ——
      // Python 渲染的是 `1. **[高]** 动作`，开头是数字序号（实测踩到）。
      const body = t.replace(/^(\d+\.|[-*])\s*/, '')
      const pm = PRIORITY_RE.exec(body)
      if (pm) {
        // 这一行是建议正文（带优先级标记）
        blocks.push({
          type: 'sug',
          priority: pm[1] ?? null,
          spans: parseInline(body.slice(pm[0].length)),
        })
      } else {
        // 「依据：」「预期：」这类从属行，没有优先级
        blocks.push({ type: 'sug', priority: null, spans: parseInline(body) })
      }
      continue
    }

    if (/^[-*]\s+/.test(t) || /^\d+\.\s+/.test(t)) {
      if (!list) list = []
      list.push(parseInline(t.replace(/^([-*]|\d+\.)\s+/, '')))
      continue
    }

    flushList()
    blocks.push({ type: 'p', spans: parseInline(t) })
  }
  flushList()
  return blocks
}
