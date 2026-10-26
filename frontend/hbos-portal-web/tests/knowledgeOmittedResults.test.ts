import { beforeEach, describe, expect, it, vi } from 'vitest'
import { searchKnowledge, DomainApiError } from '@/services/p1Api'

const transport = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }))
vi.mock('@/services/frappeClient', () => ({ callFrappePostMethod: transport.post, callFrappeMethod: transport.get }))

const card = {
  request_id: 'REQ_SYNTHETIC', mode: 'retrieval', results: [],
  omitted_results: 2,
}

beforeEach(() => {
  vi.clearAllMocks()
  transport.post.mockResolvedValue({ ok: true, data: card })
})

describe('search omitted_results is a bounded, honest degradation field', () => {
  it('keeps 1..5 and exposes it to the view', async () => {
    for (const value of [1, 2, 5]) {
      transport.post.mockResolvedValue({ ok: true, data: { ...card, omitted_results: value } })
      const result = await searchKnowledge('合成问题')
      expect(result.omitted_results).toBe(value)
    }
  })

  it('rejects values the server contract cannot produce', async () => {
    for (const value of [0, 6, -1, 1.5, '2', true]) {
      transport.post.mockResolvedValue({ ok: true, data: { ...card, omitted_results: value } })
      await expect(searchKnowledge('合成问题')).rejects.toBeInstanceOf(DomainApiError)
    }
  })

  it('omits the field entirely when the server did not degrade', async () => {
    transport.post.mockResolvedValue({ ok: true, data: { request_id: 'REQ_SYNTHETIC', mode: 'retrieval', results: [] } })
    const result = await searchKnowledge('合成问题')
    expect(result.omitted_results).toBeUndefined()
  })
})
