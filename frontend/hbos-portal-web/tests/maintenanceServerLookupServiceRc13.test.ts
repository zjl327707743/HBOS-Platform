import { beforeEach, describe, expect, it, vi } from 'vitest'

const transport = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), upload: vi.fn() }))
vi.mock('@/services/frappeClient', () => ({
  callFrappeMethod: transport.get,
  callFrappePostMethod: transport.post,
  callFrappeUploadMethod: transport.upload,
}))

import { getMaintenance } from '@/services/knowledgeMaintenanceApi'
import { DomainApiError } from '@/services/p1Api'

const dashboard = { published_documents: [], departments: [], batches: [], selected: null, feedback: { items: [] }, import_availability: { can_parse: true, configured: true, blocked: false } }
const DOCUMENT = 'DOC_' + 'f'.repeat(24)

beforeEach(() => { vi.clearAllMocks(); transport.get.mockResolvedValue({ ok: true, data: dashboard }) })

describe('maintenance dashboard default request stays backward compatible', () => {
  it('sends only the legacy params when no server lookup is requested', async () => {
    await getMaintenance()
    expect(transport.get).toHaveBeenCalledWith('hb_knowledge_app.hb_knowledge.api.get_maintenance', { batch_id: undefined, page: 1, page_size: 12 })
    const params = transport.get.mock.calls[0]![1] as Record<string, unknown>
    for (const key of ['published_query', 'published_document_id', 'published_page', 'published_page_size', 'batch_query', 'batch_document_id', 'batch_page', 'batch_page_size']) {
      expect(params).not.toHaveProperty(key)
    }
  })

  it('keeps the legacy batch/page/locate call shape', async () => {
    await getMaintenance('IMP_' + 'a'.repeat(32), 2, DOCUMENT)
    expect(transport.get).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.get_maintenance', {
      batch_id: 'IMP_' + 'a'.repeat(32), page: 2, page_size: 12, locate: DOCUMENT,
    })
  })

  it('forwards only defined lookup keys so an empty lookup adds nothing', async () => {
    await getMaintenance(undefined, 1, undefined, {})
    expect(transport.get).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.get_maintenance', { batch_id: undefined, page: 1, page_size: 12 })
  })

  it('returns the dashboard data unchanged', async () => {
    expect(await getMaintenance()).toEqual(dashboard)
  })
})

describe('bounded published/batch lookup parameters', () => {
  it('forwards published query and pagination as server-side params', async () => {
    await getMaintenance(undefined, 1, undefined, { published_query: ' 目标资料 ', published_page: 2, published_page_size: 50 })
    expect(transport.get).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.get_maintenance', {
      batch_id: undefined, page: 1, page_size: 12,
      published_query: '目标资料', published_page: 2, published_page_size: 50,
    })
  })

  it('forwards exact document id and batch document locate params', async () => {
    await getMaintenance(undefined, 1, undefined, { published_document_id: DOCUMENT, published_page: 1, published_page_size: 50 })
    expect(transport.get).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.get_maintenance', {
      batch_id: undefined, page: 1, page_size: 12,
      published_document_id: DOCUMENT, published_page: 1, published_page_size: 50,
    })
    await getMaintenance(undefined, 1, undefined, { batch_document_id: DOCUMENT, batch_page: 1, batch_page_size: 100 })
    expect(transport.get).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.get_maintenance', {
      batch_id: undefined, page: 1, page_size: 12,
      batch_document_id: DOCUMENT, batch_page: 1, batch_page_size: 100,
    })
  })

  it('forwards batch query and pagination', async () => {
    await getMaintenance(undefined, 1, undefined, { batch_query: '批次0400', batch_page: 3, batch_page_size: 100 })
    expect(transport.get).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.get_maintenance', {
      batch_id: undefined, page: 1, page_size: 12,
      batch_query: '批次0400', batch_page: 3, batch_page_size: 100,
    })
  })

  it.each([
    { published_query: 'x'.repeat(121) },
    { published_document_id: 'DOC_../escape' },
    { published_document_id: '' },
    { published_page: 0 },
    { published_page: 1.5 },
    { published_page: 'x' as unknown as number },
    { published_page_size: 51 },
    { published_page_size: 0 },
    { batch_query: 'x'.repeat(121) },
    { batch_query: '批次\n注入' },
    { batch_document_id: 'not-a-document' },
    { batch_page: -1 },
    { batch_page_size: 101 },
    { published_query: '目标', published_document_id: DOCUMENT },
    { batch_query: '批次', batch_document_id: DOCUMENT },
  ])('rejects invalid lookup params before any request: %#', async (lookup) => {
    await expect(getMaintenance(undefined, 1, undefined, lookup)).rejects.toBeInstanceOf(DomainApiError)
    expect(transport.get).not.toHaveBeenCalled()
  })

  it('rejects a base page outside the bounded range', async () => {
    await expect(getMaintenance(undefined, 0)).rejects.toBeInstanceOf(DomainApiError)
    await expect(getMaintenance(undefined, 1, 3 as unknown as string)).rejects.toBeInstanceOf(DomainApiError)
    expect(transport.get).not.toHaveBeenCalled()
  })
})
