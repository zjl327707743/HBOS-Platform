/**
 * AI 报告 Markdown 解析的单测。
 *
 * 重点钉住两件事：
 *   1. 「改进建议」段的缩进列表不能和正文列表混在一起
 *      —— 混了就看不出「依据」属于哪条建议
 *   2. 模型输出里的 HTML 原样保留成**文本**，不能被当成标签
 *      —— 渲染层用的是插值不是 v-html，但这层也别自作主张剥掉内容
 */

import { describe, expect, it } from 'vitest'

import { parseReport } from '@/services/reportMarkdown'

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
      { type: 'p', text: '台账有 30 批记录。' },
      { type: 'ul', items: ['第一条', '第二条'] },
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
    expect(heads).toEqual(['当前现状', '目标', '参数影响', '观察到的偏差', '结果判断', '数据完整性'])
  })

  it('改进建议段整段归到 sug，不拆成 ul', () => {
    // Python 渲染出来的格式：`1. **[高]** 动作` + `   - 依据：…` + `   - 预期：…`
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
    const sugs = blocks.filter((b) => b.type === 'sug').map((b) => (b as { text: string }).text)
    expect(sugs).toHaveLength(4)
    expect(sugs[0]).toContain('补加钯炭干基')
    expect(sugs[1]).toContain('依据')
  })

  it('HTML 原样保留为文本，不解析', () => {
    // 模型偶尔会在正文里吐 HTML。这层不做转换，渲染层用 {{ }} 插值 —— 安全。
    const blocks = parseReport('## 现状\n<b>粗体</b> 和 <script>alert(1)</script>')
    const p = blocks.find((b) => b.type === 'p') as { text: string }
    expect(p.text).toContain('<b>粗体</b>')
    expect(p.text).toContain('<script>')
  })

  it('数字列表也能识别', () => {
    const blocks = parseReport('1. 甲\n2. 乙')
    expect(blocks).toEqual([{ type: 'ul', items: ['甲', '乙'] }])
  })

  it('列表在空行处断开', () => {
    const blocks = parseReport('- 甲\n- 乙\n\n新段落')
    expect(blocks).toEqual([
      { type: 'ul', items: ['甲', '乙'] },
      { type: 'p', text: '新段落' },
    ])
  })
})
