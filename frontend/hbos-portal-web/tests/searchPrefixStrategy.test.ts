import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

/**
 * 搜索策略：**先前缀（走索引）、没命中再退到包含匹配**。
 *
 * 前端的 `%keyword%` 无法利用索引，数据量一大就是全表扫。但直接删掉包含匹配
 * 又会让「搜名称中间的子串」失效 —— 所以保留它作为回退，而不是主路径。
 */
const here = dirname(fileURLToPath(import.meta.url))
const item = readFileSync(resolve(here, '../src/services/inventoryMaster.ts'), 'utf8')
const docs = readFileSync(resolve(here, '../src/services/inventoryDocs.ts'), 'utf8')

describe('搜索前缀优先', () => {
  it('物料搜索先前缀、再包含', () => {
    expect(item).toContain('likePrefix')
    expect(item).toContain('likeContains')
    expect(item.indexOf('likePrefix(q)')).toBeLessThan(item.indexOf('likeContains(q)'))
  })

  it('批次搜索同样前缀优先', () => {
    // 前缀模式先赋值给 usedPattern，命中就不走包含匹配
    const prefixAt = docs.indexOf("usedPattern = `${q}%`")
    const containsAt = docs.indexOf("usedPattern = `%${q}%`")
    expect(prefixAt).toBeGreaterThan(-1)
    expect(containsAt).toBeGreaterThan(-1)
    expect(prefixAt).toBeLessThan(containsAt)
  })

  it('计数与列表用同一个模式', () => {
    // 早期 bug 形态：列表用前缀、计数用包含 → 「匹配 N 个」对不上列表长度
    expect(docs).toContain('countBatches(usedPattern)')
    expect(item).toContain('countItems(q, fallback)')
  })
})
