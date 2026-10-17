import { beforeEach, expect, it, vi } from 'vitest'
import { callFrappeMethod } from '@/services/frappeClient'
import { getItem, searchItems, ITEM_LIST_LIMIT } from '@/services/inventoryItems'
vi.mock('@/services/frappeClient', () => ({ callFrappeMethod: vi.fn() }))
beforeEach(() => vi.mocked(callFrappeMethod).mockReset())
it('uses the existing permission-aware Item list API with bounded search', async () => {
  vi.mocked(callFrappeMethod).mockResolvedValue([{name:'A',item_name:'Visible'}])
  const result = await searchItems(' needle ')
  expect(result.rows).toHaveLength(1)
  const [method, params] = vi.mocked(callFrappeMethod).mock.calls[0]!
  expect(method).toBe('frappe.client.get_list')
  expect(params?.doctype).toBe('Item')
  expect(params?.limit_page_length).toBe(201)
  expect(JSON.parse(String(params?.or_filters))).toEqual([['name','like','%needle%'],['item_name','like','%needle%']])
  expect(JSON.parse(String(params?.fields))).toContain('hbos_storage_condition')
})
it('uses an extra visible row to report truncation without a false global count', async () => {
  vi.mocked(callFrappeMethod).mockResolvedValue(Array.from({length:201},(_,i)=>({name:String(i),item_name:'Visible'})))
  const result = await searchItems('')
  expect(result.rows).toHaveLength(ITEM_LIST_LIMIT)
  expect(result.truncated).toBe(true)
  expect(callFrappeMethod).toHaveBeenCalledTimes(1)
})
it('preserves permission and transport failures instead of returning empty data', async () => {
  const error = new Error('denied')
  vi.mocked(callFrappeMethod).mockRejectedValue(error)
  await expect(searchItems('')).rejects.toBe(error)
  await expect(getItem('B')).rejects.toBe(error)
})
it('fetches detail only through the current session Item ACL', async () => {
  vi.mocked(callFrappeMethod).mockResolvedValue({name:'A',item_name:'Visible'})
  await getItem(' A ')
  expect(callFrappeMethod).toHaveBeenCalledWith('frappe.client.get',{doctype:'Item',name:'A'})
})
