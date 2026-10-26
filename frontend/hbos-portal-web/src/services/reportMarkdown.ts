/**
 * AI 报告 Markdown → 结构化块。**纯函数，可单测**。
 *
 * 为什么不引 markdown 解析库：
 *
 *   - 报告实际只用到三种语法：`## 标题`、`- 列表`、普通段落
 *   - 为三种语法装一个 parser 不划算
 *   - **安全**：模型偶尔会在正文里输出原样的 HTML（比如 `<b>`、`<script>`）。
 *     这里输出的是一组纯文本块，渲染层用 `{{ }}` 插值 —— 不会被执行。
 *     换成 `v-html` + 通用 markdown 库就丢掉了这层保障。
 *
 * 「改进建议」段单独归成 `sug` 块：那段由 Python 渲染（`parse.render_suggestions`），
 * 格式固定是 `1. **[高]** 动作` 加 `   - 依据：…`，与正文分开显示更好扫读。
 */

export type ReportBlock =
  | { type: 'h'; text: string }
  | { type: 'p'; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'sug'; text: string }

/** 「改进建议」段的识别标记 —— 与 `parse.render_suggestions` 的标题逐字一致。 */
const SUGGESTION_HEADING = '改进建议'

export function parseReport(markdown: string | null | undefined): ReportBlock[] {
  const raw = (markdown || '').trim()
  if (!raw) return []

  const blocks: ReportBlock[] = []
  let inSuggest = false
  let list: string[] | null = null

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
      blocks.push({ type: 'sug', text: t.replace(/^[-*]\s*/, '') })
      continue
    }

    if (/^[-*]\s+/.test(t) || /^\d+\.\s+/.test(t)) {
      if (!list) list = []
      list.push(t.replace(/^([-*]|\d+\.)\s+/, ''))
      continue
    }

    flushList()
    blocks.push({ type: 'p', text: t })
  }
  flushList()
  return blocks
}
