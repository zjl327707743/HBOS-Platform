import { callFrappeMethod } from '@/services/frappeClient'

/** Read-only Item projection from PR39. Native Frappe ACL is the data authority. */
export const ITEM_LIST_LIMIT = 200
export interface ItemRow {
  name: string
  item_name: string
  item_group?: string
  stock_uom?: string
  hbos_product_kind?: string
  hbos_workshop?: string
  hbos_storage_condition?: string
  hbos_shelf_life_type?: string
  hbos_shelf_life_months?: number
  has_batch_no?: number
  disabled?: number
}
const ITEM_FIELDS = ['name','item_name','item_group','stock_uom','hbos_product_kind','hbos_workshop','hbos_storage_condition','hbos_shelf_life_type','hbos_shelf_life_months','has_batch_no','disabled']
export async function searchItems(keyword: string): Promise<{rows: ItemRow[]; truncated: boolean}> {
  const q = keyword.trim()
  const rows = await callFrappeMethod<ItemRow[] | null>('frappe.client.get_list', {
    doctype: 'Item', fields: JSON.stringify(ITEM_FIELDS), order_by: 'name asc',
    limit_page_length: ITEM_LIST_LIMIT + 1,
    ...(q ? { or_filters: JSON.stringify([['name','like',`%${q}%`],['item_name','like',`%${q}%`]]) } : {}),
  })
  return { rows: (rows || []).slice(0, ITEM_LIST_LIMIT), truncated: (rows || []).length > ITEM_LIST_LIMIT }
}
export async function getItem(itemCode: string): Promise<ItemRow | null> {
  const name = itemCode.trim()
  if (!name) return null
  return callFrappeMethod<ItemRow | null>('frappe.client.get', { doctype: 'Item', name })
}
export function itemMasterGaps(item: ItemRow): string[] {
  const gaps: string[] = []
  if (!String(item.hbos_storage_condition || '').trim()) gaps.push('储存条件')
  if (!String(item.hbos_workshop || '').trim()) gaps.push('生产车间')
  if (!String(item.hbos_shelf_life_type || '').trim()) gaps.push('效期类型')
  return gaps
}
