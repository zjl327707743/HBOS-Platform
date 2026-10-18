import { beforeEach, expect, it, vi } from 'vitest'
import { fetchAiAnalysis, fetchProductionBoard } from '@/services/productionBoard'
import { PortalApiError } from '@/services/portalApi'

const rpc = vi.hoisted(() => vi.fn())
vi.mock('@/services/frappeClient', () => ({ callFrappeMethod: rpc }))
beforeEach(() => { rpc.mockReset() })

it.each([fetchProductionBoard, fetchAiAnalysis])('preserves a backend access denial instead of returning empty data', async read => {
  rpc.mockResolvedValue({ ok: false, error: { code: 'FORBIDDEN', message: '无权访问', retryable: false } })
  await expect(read()).rejects.toMatchObject({ code: 'FORBIDDEN', retryable: false })
})

it('distinguishes an empty successful AI result from an unavailable service', async () => {
  rpc.mockResolvedValueOnce({ ok: true, data: { rows: [] } })
  await expect(fetchAiAnalysis()).resolves.toEqual([])
  rpc.mockResolvedValueOnce({ ok: false, error: { code: 'PROVIDER_ERROR', message: '服务不可用', retryable: true } })
  await expect(fetchAiAnalysis()).rejects.toBeInstanceOf(PortalApiError)
})

it('does not disguise an invalid AI payload as an empty table', async () => {
  rpc.mockResolvedValue({ ok: true, data: { rows: 'invalid' } })
  await expect(fetchAiAnalysis()).rejects.toMatchObject({ code: 'PROVIDER_ERROR' })
})

it('propagates native session errors to the page', async () => {
  const expired = Object.assign(new Error('登录失效'), { code: 'UNAUTHENTICATED' })
  rpc.mockRejectedValue(expired)
  await expect(fetchProductionBoard({ refresh: true })).rejects.toBe(expired)
  expect(rpc).toHaveBeenCalledWith('hbos_portal.api.production.get_board', { refresh: 1 })
})
