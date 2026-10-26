/**
 * AI 报告 Markdown 解析的单测。
 *
 * 重点钉住三件事：
 *   1. 行内 `**加粗**` 要转成片段，不能原样显示成 `**文本**`
 *   2. 「改进建议」段的优先级标记要抽出来，且**缩进的从属行不能带优先级**
 *      —— 混了就看不出「依据」属于哪条建议
 *   3. 模型输出里的 HTML 原样保留成**文本片段**，不能被当成标签
 */

import { describe, expect, it } from 'vitest'

import { parseInline, parseReport } from '@/services/reportMarkdown'

describe('parseInline', () => {
  it('无标记时返回单个纯文本片段', () => {
    expect(parseInline('普通文本')).toEqual([{ text: '普通文本' }])
  })

  it('拆出加粗片段', () => {
    expect(parseInline('前 **粗** 后')).toEqual([
      { text: '前 ' },
      { text: '粗', bold: true },
      { text: ' 后' },
    ])
  })

  it('开头就是加粗时不留空片段', () => {
    expect(parseInline('**高** 动作')).toEqual([
      { text: '高', bold: true },
      { text: ' 动作' },
    ])
  })

  it('空输入返回空片段，调用方不用判空', () => {
    expect(parseInline('')).toEqual([{ text: '' }])
  })

  it('HTML 原样保留为文本', () => {
    const spans = parseInline('<b>粗体</b> 和 <script>alert(1)</script>')
    expect(spans.map((s) => s.text).join('')).toContain('<script>')
  })
})

describe('parseReport', () => {
  it('空输入返回空数组', () => {
    expect(parseReport('')).toEqual([])
    expect(parseReport(null)).toEqual([])
    expect(parseReport(undefined)).toEqual([])
  })

  it('拆出标题、段落、列表', () => {
    const md = ['## 当前现状', '台账有 30 批记录。', '', '- 第一条', '- 第二条'].join('\n')
    expect(parseReport(md)).toEqual([
      { type: 'h', text: '当前现状' },
      { type: 'p', spans: [{ text: '台账有 30 批记录。' }] },
      {
        type: 'ul',
        items: [[{ text: '第一条' }], [{ text: '第二条' }]],
      },
    ])
  })

  it('七段式能完整拆出来', () => {
    const md = [
      '## 当前现状', 'A',
      '## 目标', 'B',
      '## 参数影响', 'C',
      '## 观察到的偏差', 'D',
      '## 结果判断', 'E',
      '## 数据完整性', 'F',
    ].join('\n')
    const heads = parseReport(md)
      .filter((b) => b.type === 'h')
      .map((b) => (b as { text: string }).text)
    expect(heads).toEqual([
      '当前现状', '目标', '参数影响', '观察到的偏差', '结果判断', '数据完整性',
    ])
  })

  it('改进建议段：优先级抽出来，从属行不带优先级', () => {
    // Python 渲染出来的真实格式（实测 62 份报告全是这一种）
    const md = [
      '## 数据完整性', '记录完整。',
      '## 改进建议',
      '1. **[高]** 补加钯炭干基控制在 2.0kg 以内',
      '   - 依据：低收率组 2.58、高组 1.99（-23%）',
      '   - 预期：收率 +0.1~0.3pt（待验证）',
      '2. **[中]** 每批记录温度',
    ].join('\n')
    const blocks = parseReport(md)
    expect(blocks.filter((b) => b.type === 'ul')).toHaveLength(0)

    const sugs = blocks.filter((b) => b.type === 'sug') as {
      type: 'sug'; priority: string | null; spans: { text: string }[]
    }[]
    expect(sugs).toHaveLength(4)
    expect(sugs[0].priority).toBe('高')
    expect(sugs[1].priority).toBeNull()   // 「依据」是从属行
    expect(sugs[2].priority).toBeNull()
    expect(sugs[3].priority).toBe('中')

    // 优先级标记不能残留在正文里
    const text0 = sugs[0].spans.map((s) => s.text).join('')
    expect(text0).not.toContain('[高]')
    expect(text0).toContain('补加钯炭干基')
  })

  it('数字列表也能识别', () => {
    expect(parseReport('1. 甲\n2. 乙')).toEqual([
      { type: 'ul', items: [[{ text: '甲' }], [{ text: '乙' }]] },
    ])
  })

  it('列表在空行处断开', () => {
    expect(parseReport('- 甲\n- 乙\n\n新段落')).toEqual([
      { type: 'ul', items: [[{ text: '甲' }], [{ text: '乙' }]] },
      { type: 'p', spans: [{ text: '新段落' }] },
    ])
  })

  it('段落里的加粗也生效', () => {
    const blocks = parseReport('设备 **R622** 的转速上限')
    expect((blocks[0] as { spans: unknown[] }).spans).toEqual([
      { text: '设备 ' },
      { text: 'R622', bold: true },
      { text: ' 的转速上限' },
    ])
  })
})
