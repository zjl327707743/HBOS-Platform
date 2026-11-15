/**
 * Safe structural rendering for a knowledge answer.
 *
 * The model writes short, conventional Markdown (a heading, bold lead-ins,
 * bullet lists, numbered lists, inline code). The page used to print that text
 * verbatim, so an employee saw literal `**` and `-` markers, and the only way to
 * avoid that would have been to tell the model not to structure long answers.
 *
 * This renderer escapes the whole answer first and then re-introduces a fixed,
 * closed set of tags. Nothing in the source text can become markup: there is no
 * attribute, no link, no image and no raw HTML pass-through, so a document or a
 * model that emits `<script>` yields the literal characters.
 *
 * Grammar (deliberately small):
 *   # / ## / ### heading          - or * bullet item
 *   1. / 1) numbered item         **bold**   `code`
 *   blank line                    paragraph break
 */

const ESCAPES: Record<string, string> = {
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}

export function escapeAnswerText(value: string): string {
  return value.replace(/[&<>"']/g, char => ESCAPES[char]!)
}

function inline(escaped: string): string {
  // Escaped text only: the characters that create tags are already entities.
  return escaped
    .replace(/\*\*([^*\n]{1,400})\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[\s(（：:])\*([^*\n]{1,200})\*(?=$|[\s)），。；:])/g, '$1<em>$2</em>')
    .replace(/`([^`\n]{1,200})`/g, '<code>$1</code>')
}

const HEADING = /^(#{1,3})\s+(.{1,200})$/
const BULLET = /^\s*[-*•]\s+(.{1,4000})$/
const NUMBERED = /^\s*(\d{1,3})[.、)]\s+(.{1,4000})$/
const TABLE_ROW = /^\s*\|(.+)\|\s*$/
const TABLE_RULE = /^\s*\|[\s:|-]+\|\s*$/

/** Render one answer as safe HTML. Never returns an attribute or a link. */
export function renderAnswer(value: string): string {
  const text = String(value ?? '').replace(/\r\n?/g, '\n')
  if (!text.trim()) return ''
  const lines = text.split('\n')
  const out: string[] = []
  let list: 'ul' | 'ol' | null = null
  let paragraph: string[] = []
  let code = false
  let table: string[][] | null = null

  const closeList = () => { if (list) { out.push(`</${list}>`); list = null } }
  const flushParagraph = () => {
    if (!paragraph.length) return
    out.push(`<p>${paragraph.map(inline).join('<br>')}</p>`)
    paragraph = []
  }
  const flushTable = () => {
    if (!table) return
    const [head, ...rows] = table
    const cells = (row: string[], tag: 'th' | 'td') =>
      `<tr>${row.map(cell => `<${tag}>${inline(cell)}</${tag}>`).join('')}</tr>`
    out.push(`<table><thead>${cells(head || [], 'th')}</thead><tbody>${rows.map(row => cells(row, 'td')).join('')}</tbody></table>`)
    table = null
  }
  const flushAll = () => { flushParagraph(); closeList(); flushTable() }

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '')
    if (/^\s*```/.test(line)) {
      // A fenced block is shown as its own text, never as markup.
      flushAll()
      out.push(code ? '</pre>' : '<pre>')
      code = !code
      continue
    }
    if (code) { out.push(escapeAnswerText(raw)); continue }
    if (!line.trim()) { flushAll(); continue }

    const heading = HEADING.exec(line)
    if (heading) {
      flushAll()
      const level = Math.min(heading[1]!.length + 2, 5) // h3..h5: inside the answer card
      out.push(`<h${level}>${inline(escapeAnswerText(heading[2]!.trim()))}</h${level}>`)
      continue
    }
    if (TABLE_RULE.test(line)) continue
    const row = TABLE_ROW.exec(line)
    if (row) {
      flushParagraph(); closeList()
      const cells = row[1]!.split('|').map(cell => cell.trim())
      table = table ? [...table, cells] : [cells]
      continue
    }
    flushTable()

    const bullet = BULLET.exec(line)
    if (bullet) {
      flushParagraph()
      if (list !== 'ul') { closeList(); out.push('<ul>'); list = 'ul' }
      out.push(`<li>${inline(escapeAnswerText(bullet[1]!.trim()))}</li>`)
      continue
    }
    const numbered = NUMBERED.exec(line)
    if (numbered) {
      flushParagraph()
      if (list !== 'ol') { closeList(); out.push('<ol>'); list = 'ol' }
      out.push(`<li>${inline(escapeAnswerText(numbered[2]!.trim()))}</li>`)
      continue
    }
    closeList()
    paragraph.push(escapeAnswerText(line.trim()))
  }
  if (code) out.push('</pre>')
  flushAll()
  return out.join('')
}
