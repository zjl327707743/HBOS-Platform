import type { InventoryOverviewState } from '@/services/portalApi'
import { getFrappeInventoryOverview } from '@/services/portalApi'
import { portalDataSource } from '@/services/portalProvider'

/**
 * 仓储库存概览数据。
 *
 * mock 模式下返回 `null` —— 这一页的四项指标是**真实库存事实**，
 * 编不出一份可信的假数据，也不该编（EA-5.4 §16 明确禁止展示假数字）。
 * 因此 mock 模式一律呈现「取不到」的错误态，这是刻意的。
 */
export async function getInventoryOverview(): Promise<InventoryOverviewState | null> {
  if (portalDataSource === 'frappe') {
    return getFrappeInventoryOverview()
  }
  return null
}

export type { InventoryOverviewState }
