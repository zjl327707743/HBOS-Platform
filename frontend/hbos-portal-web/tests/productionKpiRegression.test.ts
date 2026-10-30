import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

/**
 * 生产看板 KPI 的**语义**回归 —— 这几条都踩过，且都属于「看起来合理、其实错了」。
 *
 * 这里做源码级断言而不是挂载组件：KPI 全是 `computed`，而模板渲染依赖
 * 一整套 ant-design 组件与全局样式；挂载成本高、脆弱，且断言的点仍然是
 * 「这两个函数在边界上的返回值」。
 */
const here = dirname(fileURLToPath(import.meta.url))
const source = readFileSync(resolve(here, '../src/views/ProductionDashboardView.vue'), 'utf8')

describe('生产看板 KPI 语义', () => {
  it('分母为 0 时计划完成率返回 null，而不是 0', () => {
    // 月初还没导入计划时显示 0.0% 会被读成「生产完全没完成」
    expect(source).toMatch(/totalTarget\.value > 0 \? \(totalDone\.value \/ totalTarget\.value\) \* 100 : null/)
  })

  it('没有收率数据时收率达标率返回 null，而不是 0', () => {
    expect(source).toMatch(
      /yieldRows\.value\.length > 0 \? \(metCount\.value \/ yieldRows\.value\.length\) \* 100 : null/,
    )
  })

  it('pctText 只在 null/NaN 时显示破折号，真实的 0 显示 0.0%', () => {
    // 早先是 `v > 0 ? … : '—'` —— 把「一批都没完成」显示成「无数据」
    const fn = source.match(/function pctText\([\s\S]*?\n\}/)?.[0] ?? ''
    expect(fn).toContain('Number.isNaN')
    expect(fn).not.toMatch(/v > 0/)
    expect(fn).toContain('toFixed(1)')
  })

  it('KPI 文案不再出现「近 12 个月」', () => {
    // 口径已改为只看当月；旧文案会让人以为检查了整年
    expect(source).not.toContain('近 12 个月')
    expect(source).toContain('当月无异常记录')
  })

  it('质量数据有时间戳与 board 分开标注', () => {
    expect(source).toContain('qualityDataAsOf')
  })
})

describe('收率达标率分母', () => {
  it('缺目标收率的品种不得进入达标率分母', () => {
    // 早先只要求 yieldRate !== null，目标缺失的品种会进分母却永远不达标，
    // 等于被系统当成未达标 —— 目标表少录一个产品，KPI 就被人为拉低。
    const block = source.match(/const yieldRows = computed\([\s\S]*?\)\n/)?.[0] ?? ''
    expect(block).toContain('targetYieldRate !== null')
  })

  it('缺目标收率的品种要单独点名', () => {
    expect(source).toContain('yieldMissingTarget')
    expect(source).toContain('缺目标收率')
  })
})
