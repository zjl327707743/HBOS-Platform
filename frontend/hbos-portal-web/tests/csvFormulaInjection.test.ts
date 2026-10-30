import { describe, expect, it } from 'vitest'
import { neutralizeFormula } from '@/services/inventoryReports'

/**
 * CSV 公式注入防护。
 *
 * 不是理论风险：物料名、供应商、批号、备注都可能来自**外部标签**或人工录入，
 * 用户在 Excel 里打开导出文件时，`=HYPERLINK(...)` 会把单元格内容带出去，
 * DDE 在旧版 Excel 上还能执行命令。
 */
describe('CSV 公式注入防护', () => {
  it('以 = 开头的文本要加引号前缀', () => {
    expect(neutralizeFormula('=1+1', '=1+1')).toBe("'=1+1")
    expect(neutralizeFormula('=HYPERLINK("http://x","y")', '=HYPERLINK("http://x","y")')).toBe(
      "'" + '=HYPERLINK("http://x","y")',
    )
  })

  it('+ - @ Tab CR 开头同样处理', () => {
    expect(neutralizeFormula('+cmd', '+cmd')).toBe("'+cmd")
    expect(neutralizeFormula('-cmd', '-cmd')).toBe("'-cmd")
    expect(neutralizeFormula('@SUM(A1)', '@SUM(A1)')).toBe("'@SUM(A1)")
    expect(neutralizeFormula('\tx', '\tx')).toBe("'\tx")
    expect(neutralizeFormula('\rx', '\rx')).toBe("'\rx")
  })

  it('合法负数（number 类型）不加前缀，仍然是数值', () => {
    expect(neutralizeFormula('-1', -1)).toBe('-1')
    expect(neutralizeFormula('-1.5', -1.5)).toBe('-1.5')
    expect(neutralizeFormula('0', 0)).toBe('0')
  })

  it('负数文本也不加前缀 —— 库存报表里数量列常是字符串', () => {
    // 加前缀会把这列变成文本，下游没法求和；且它本来就不是公式
    expect(neutralizeFormula('-1', '-1')).toBe('-1')
    expect(neutralizeFormula('-123.45', '-123.45')).toBe('-123.45')
  })

  it('含逗号被加了引号时，前缀写在引号里面', () => {
    expect(neutralizeFormula('"=1,2"', '=1,2')).toBe(`"'=1,2"`)
  })

  it('普通文本原样返回', () => {
    expect(neutralizeFormula('4BMA', '4BMA')).toBe('4BMA')
    expect(neutralizeFormula('亚胺培南', '亚胺培南')).toBe('亚胺培南')
    expect(neutralizeFormula('', '')).toBe('')
  })

  it('null/undefined 视为空串', () => {
    expect(neutralizeFormula('', null)).toBe('')
    expect(neutralizeFormula('', undefined)).toBe('')
  })
})
