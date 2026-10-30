import { describe, expect, it } from 'vitest'
import { findShortages, shortageKey, type PickLocation } from '@/services/inventoryPick'

/**
 * 短缺判定必须按「物料 + 批次」，不能只按物料。
 *
 * 同一物料两个批次各要 5kg 时，若只按物料汇总，任一货位凑到 10kg 就判「够了」——
 * 批次级拣货数量是错的，操作员据此做的移库单/领用单也会错。
 */
function loc(itemCode: string, batchNo: string, qty: number): PickLocation {
  return {
    itemCode,
    batchNo,
    qty,
    uom: 'kg',
    warehouse: 'WH',
    stockQty: qty,
    pickedQty: null,
  }
}

describe('拣货短缺按批次判定', () => {
  it('两个批次各要 5kg、只凑到一个批次 10kg → 另一个仍短缺', () => {
    const required = {
      [shortageKey('ITEM-A', 'B1')]: 5,
      [shortageKey('ITEM-A', 'B2')]: 5,
    }
    const shortages = findShortages(required, [loc('ITEM-A', 'B1', 10)])
    expect(shortages).toHaveLength(1)
    expect(shortages[0]?.batchNo).toBe('B2')
    expect(shortages[0]?.gap).toBe(5)
  })

  it('两个批次都凑够 → 无短缺', () => {
    const required = {
      [shortageKey('ITEM-A', 'B1')]: 5,
      [shortageKey('ITEM-A', 'B2')]: 5,
    }
    expect(findShortages(required, [loc('ITEM-A', 'B1', 5), loc('ITEM-A', 'B2', 5)])).toEqual([])
  })

  it('无批次物料用空批次作键，仍能正常比较', () => {
    const required = { [shortageKey('ITEM-B', '')]: 3 }
    expect(findShortages(required, [loc('ITEM-B', '', 3)])).toEqual([])
    expect(findShortages(required, [loc('ITEM-B', '', 1)])[0]?.gap).toBe(2)
  })
})
