import { beforeEach, describe, expect, it, vi } from 'vitest'
import { searchKnowledge, DomainApiError } from '@/services/p1Api'

const transport = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }))
vi.mock('@/services/frappeClient', () => ({ callFrappePostMethod: transport.post, callFrappeMethod: transport.get }))

const emptyResult = { ok: true, data: { request_id: 'REQ_SYNTHETIC', mode: 'retrieval', results: [] } }

beforeEach(() => {
  // Each test is a fresh tab: the per-identity workspace store must not
  // carry a previous case's filters into this one.
  window.sessionStorage.clear()
  vi.clearAllMocks()
  transport.post.mockResolvedValue(emptyResult)
})

describe('search context follows the backend CONTEXT_KEYS whitelist', () => {
  it.each([
    [{ asset_id: 'ASSET_SYNTHETIC' }],
    [{ component_id: 'COMPONENT_SYNTHETIC' }],
    [{ equipment_id: 'EQ_SYNTHETIC', component_id: 'COMPONENT_SYNTHETIC' }],
    [{ equipment_id: 'EQ-1.A_2', asset_id: 'ASSET_SYNTHETIC', component_id: 'COMPONENT_SYNTHETIC' }],
  ])('accepts a context of %j', async context => {
    await searchKnowledge('合成问题', context)
    expect(transport.post).toHaveBeenCalledWith('hb_knowledge_app.hb_knowledge.api.search', expect.objectContaining(context))
  })

  it('still rejects keys outside the backend whitelist before any request', async () => {
    await expect(searchKnowledge('合成问题', { asset_id: 'ASSET_SYNTHETIC', dataset_id: 'PHYSICAL_ID' } as never))
      .rejects.toBeInstanceOf(DomainApiError)
    expect(transport.post).not.toHaveBeenCalled()
  })

  it('still rejects a malformed equipment id', async () => {
    await expect(searchKnowledge('合成问题', { equipment_id: 'bad id!' })).rejects.toBeInstanceOf(DomainApiError)
    expect(transport.post).not.toHaveBeenCalled()
  })
})
