import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { KnowledgeReturnSnapshot } from '@/contracts/knowledgeReturn'

const transport = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }))
vi.mock('@/services/frappeClient', () => ({
  callFrappePostMethod: transport.post,
  callFrappeMethod: transport.get,
}))

import {
  DocumentReaderError,
  classifyReaderFailure,
  openKnowledgeDocument,
  readKnowledgeDocumentPage,
  searchKnowledgeDocument,
} from '@/services/documentReaderApi'
import { DomainApiError } from '@/services/p1Api'
import { useKnowledgeReturnStore } from '@/stores/knowledgeReturn'

const documentFixture = {
  document_id: 'DOC_READER_DEMO',
  version_id: 'VER_READER_DEMO',
  title: '合成受控规程',
  document_number: 'SOP-001',
  space_id: 'DEPT_PRODUCTION',
  space_title: '生产部门资料',
  business_version: '4.0',
  status_note: '内部参考／有效性待核',
  reference_state: 'CURRENT',
  authorization: 'AUTHORIZED',
  source_type: 'COMPANY_CONTROLLED',
}

// 1200 cp is well above the 500 cp evidence-excerpt projection: reader body
// text must never inherit that limit.
const longText = '正文第一段' + '甲'.repeat(1200)

function bodyFixture(overrides: Record<string, unknown> = {}) {
  return {
    origin: 'INDEXED_CHUNKS',
    page_numbering: 'UNAVAILABLE',
    derived: true,
    page: 1,
    page_count: 2,
    block_total: 3,
    blocks: [
      { block_id: 'b1', ordinal: 1, page_number: null, section: '1. 目的', text: longText },
      { block_id: 'b2', ordinal: 2, page_number: null, section: '1. 目的', text: '第二章内容' },
      { block_id: 'b3', ordinal: 3, page_number: null, section: '2. 范围', text: '范围内容' },
    ],
    ...overrides,
  }
}

function openPayload(overrides: Record<string, unknown> = {}) {
  return {
    document: { ...documentFixture },
    body: bodyFixture(),
    navigation: { toc: [{ title: '1. 目的', ordinal: 1, page_number: null }], toc_source: 'ORIGINAL_HEADING_LINES', toc_truncated: false },
    disclosure: '正文来自已授权当前版本的索引文本（安全净化派生），不是原件下载；页码未核验。',
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  useKnowledgeReturnStore().clearAll()
})

describe('document reader BFF projection (§4 contract)', () => {
  it('opens by document identity alone and never forwards physical metadata', async () => {
    const payload = openPayload({
      document: { ...documentFixture, dataset_id: 'PHYSICAL_DATASET_DEMO', ragflow_document_id: 'RAW_DOC_DEMO' },
      body: bodyFixture({ raw_json: { content: 'PRIVATE' } }),
    })
    transport.post.mockResolvedValue({ ok: true, data: payload })
    const result = await openKnowledgeDocument({ documentId: 'DOC_READER_DEMO' })
    expect(transport.post).toHaveBeenCalledWith('hb_knowledge_app.hb_knowledge.api.open_document', { document_id: 'DOC_READER_DEMO' })
    expect(result.document).toEqual(documentFixture)
    expect(result.document as Record<string, unknown>).not.toHaveProperty('dataset_id')
    expect(result.document as Record<string, unknown>).not.toHaveProperty('ragflow_document_id')
    expect(result.body as unknown as Record<string, unknown>).not.toHaveProperty('raw_json')
    // No 500 cp truncation for reader body text.
    expect(result.body.blocks[0]!.text).toHaveLength([...longText].length)
    expect(result.body.page_numbering).toBe('UNAVAILABLE')
    expect(result.body.derived).toBe(true)
    expect(result.navigation.toc[0]!.page_number).toBeNull()
  })

  it('sends a supplied version and reads pages/search with the resolved version', async () => {
    const resolved = { ...openPayload(), document: { ...documentFixture, version_id: 'VER_RESOLVED_DEMO' } }
    transport.post.mockResolvedValueOnce({ ok: true, data: openPayload() })
    await openKnowledgeDocument({ documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' })
    expect(transport.post).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.open_document', {
      document_id: 'DOC_READER_DEMO', version_id: 'VER_READER_DEMO',
    })

    // The server may resolve the current version when the entry omitted it.
    transport.post.mockResolvedValueOnce({ ok: true, data: resolved })
    const opened = await openKnowledgeDocument({ documentId: 'DOC_READER_DEMO' })
    expect(opened.document.version_id).toBe('VER_RESOLVED_DEMO')

    transport.post.mockResolvedValueOnce({ ok: true, data: { ...resolved, body: bodyFixture({ page: 2 }) } })
    const pageTwo = await readKnowledgeDocumentPage({ documentId: 'DOC_READER_DEMO', versionId: opened.document.version_id }, 2)
    expect(transport.post).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.read_document_page', {
      document_id: 'DOC_READER_DEMO', version_id: 'VER_RESOLVED_DEMO', page: 2,
    })
    expect(pageTwo.body.page).toBe(2)

    transport.post.mockResolvedValueOnce({ ok: true, data: { matches: [{ ordinal: 12, page: 2, block_id: 'b12', snippet: '匹配片段' }], searched_blocks: 95, capped: false } })
    const found = await searchKnowledgeDocument({ documentId: 'DOC_READER_DEMO', versionId: opened.document.version_id }, '匹配')
    expect(transport.post).toHaveBeenLastCalledWith('hb_knowledge_app.hb_knowledge.api.search_document', {
      document_id: 'DOC_READER_DEMO', version_id: 'VER_RESOLVED_DEMO', query: '匹配', limit: 20,
    })
    expect(found).toEqual({ matches: [{ ordinal: 12, page: 2, block_id: 'b12', snippet: '匹配片段' }], searched_blocks: 95, capped: false })
  })

  it('maps empty pages and page counts without inventing content or page numbers', async () => {
    transport.post.mockResolvedValue({ ok: true, data: openPayload({ body: bodyFixture({ blocks: [], page_count: 0, block_total: 0 }) }) })
    const result = await openKnowledgeDocument({ documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' })
    expect(result.body.blocks).toEqual([])
    expect(result.body.page_count).toBe(0)
    expect(result.body.page_numbering).toBe('UNAVAILABLE')
  })

  it('keeps a full bounded search snippet (no client truncation)', async () => {
    transport.post.mockResolvedValue({
      ok: true,
      data: { matches: [{ ordinal: 3, page: 1, block_id: 'b3', snippet: '关键词'.repeat(80) }], searched_blocks: 12, capped: true },
    })
    const result = await searchKnowledgeDocument({ documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' }, '关键词')
    expect(result.matches[0]!.snippet).toBe('关键词'.repeat(80))
    expect(result.capped).toBe(true)
  })

  it('rejects malformed reader responses instead of rendering them', async () => {
    transport.post.mockResolvedValueOnce({ ok: true, data: openPayload({ body: bodyFixture({ blocks: [{ block_id: 'b1', ordinal: 1, page_number: null, section: null, text: '甲'.repeat(4001) }] }) }) })
    await expect(openKnowledgeDocument({ documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' })).rejects.toBeInstanceOf(DomainApiError)

    transport.post.mockResolvedValueOnce({ ok: true, data: openPayload({ document: { ...documentFixture, version_id: null, dataset_id: 'PHYSICAL' } }) })
    await expect(openKnowledgeDocument({ documentId: 'DOC_READER_DEMO' })).rejects.toBeInstanceOf(DomainApiError)

    transport.post.mockResolvedValueOnce({ ok: true, data: openPayload({ body: bodyFixture({ page: 3, page_count: 2 }) }) })
    await expect(openKnowledgeDocument({ documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' })).rejects.toBeInstanceOf(DomainApiError)
    expect(transport.post).toHaveBeenCalledTimes(3)
  })

  it('validates request input before calling the BFF', async () => {
    await expect(openKnowledgeDocument({ documentId: 'bad id!' })).rejects.toBeInstanceOf(DomainApiError)
    await expect(readKnowledgeDocumentPage({ documentId: 'DOC_READER_DEMO' }, 0)).rejects.toBeInstanceOf(DomainApiError)
    await expect(searchKnowledgeDocument({ documentId: 'DOC_READER_DEMO' }, '   ')).rejects.toBeInstanceOf(DomainApiError)
    await expect(searchKnowledgeDocument({ documentId: 'DOC_READER_DEMO' }, '甲'.repeat(121))).rejects.toBeInstanceOf(DomainApiError)
    await expect(searchKnowledgeDocument({ documentId: 'DOC_READER_DEMO' }, '甲', 0)).rejects.toBeInstanceOf(DomainApiError)
    expect(transport.post).not.toHaveBeenCalled()
  })

  it('preserves the optional server state on an unreadable document', async () => {
    transport.post.mockResolvedValue({ ok: false, error: { code: 'DOCUMENT_READ_UNAVAILABLE', message: 'SAFE_SERVER_COPY', retryable: false, state: 'WITHDRAWN' } })
    await expect(openKnowledgeDocument({ documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' })).rejects.toMatchObject({
      code: 'DOCUMENT_READ_UNAVAILABLE', state: 'WITHDRAWN',
    })
    // The rendered message is fixed UI copy, not the raw server message.
    await expect(openKnowledgeDocument({ documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' })).rejects.toMatchObject({
      message: '该资料已撤回，正文不再提供。',
    })
  })
})

describe('reader failure classification', () => {
  it.each([
    ['WITHDRAWN', '该资料已撤回'],
    ['VERSION_STALE', '版本已变化'],
    ['NOT_AUTHORIZED', '没有阅读该资料的权限'],
    ['NOT_PUBLISHED', '尚未发布'],
    ['VERSION_AMBIGUOUS', '无法唯一定位当前版本'],
  ])('distinguishes the %s state as unreadable and non-retryable', (state, expected) => {
    const failure = classifyReaderFailure(new DocumentReaderError('DOCUMENT_READ_UNAVAILABLE', 'x', false, state))
    expect(failure.kind).toBe('unavailable')
    expect(failure.retryable).toBe(false)
    expect(failure.message).toContain(expected)
  })

  it('falls back to the generic unreadable message when no state is exposed', () => {
    const failure = classifyReaderFailure(new DomainApiError('DOCUMENT_READ_UNAVAILABLE', 'server copy'))
    expect(failure.kind).toBe('unavailable')
    expect(failure.message).toContain('当前不可阅读')
    expect(failure.message).not.toContain('server copy')
  })

  it('treats upstream outage as retryable and page range as a recoverable navigation case', () => {
    expect(classifyReaderFailure(new DomainApiError('UPSTREAM_UNAVAILABLE', 'x'))).toMatchObject({ kind: 'upstream', retryable: true })
    expect(classifyReaderFailure(new DomainApiError('DOCUMENT_READ_PAGE_OUT_OF_RANGE', 'x'))).toMatchObject({ kind: 'page-range', retryable: true })
    expect(classifyReaderFailure(new Error('network down'))).toMatchObject({ kind: 'upstream', retryable: true })
    expect(classifyReaderFailure(new DomainApiError('INVALID_REQUEST', 'x'))).toMatchObject({ kind: 'invalid', retryable: false })
  })
})

describe('return-state store privacy and reader positions', () => {
  const evidence = {
    document_id: 'DOC_RETURN_DEMO', title: '合成资料', version: null, status_note: null,
    section: null, page_number: null, excerpt: '摘录', evidence_id: 'EV_RETURN_DEMO',
  }
  function snapshot(): KnowledgeReturnSnapshot {
    return {
      view: 'query', query: '已保存问题', mode: 'search', selectedSpace: 'DEPT_PRODUCTION',
      searchMode: 'STANDARD', searchContext: null, results: [evidence], hasSearched: true,
      searchState: 'retrieved', tools: null,
      catalog: { query: '', page: 1, lawCategory: '', sourceFolder: 'SOURCE_ROOT' }, scrollTop: 240,
    }
  }

  it('restores once for the same identity and drops another identity’s snapshot', () => {
    const store = useKnowledgeReturnStore()
    store.capture('USER_A_DEMO', snapshot())
    expect(store.takeFor('USER_B_DEMO')).toBeNull()
    expect(store.takeFor('USER_A_DEMO')).toBeNull()

    store.capture('USER_A_DEMO', snapshot())
    const restored = store.takeFor('USER_A_DEMO')
    expect(restored?.query).toBe('已保存问题')
    expect(restored?.results[0]!.document_id).toBe('DOC_RETURN_DEMO')
    expect(restored?.scrollTop).toBe(240)
    expect(store.takeFor('USER_A_DEMO')).toBeNull()
  })

  it('remembers reader pages per document/version and per identity', () => {
    const store = useKnowledgeReturnStore()
    store.rememberPosition('USER_A_DEMO', 'DOC_READER_DEMO', 'VER_READER_DEMO', { page: 3, searchQuery: '匹配' })
    expect(store.positionFor('USER_A_DEMO', 'DOC_READER_DEMO', 'VER_READER_DEMO')).toMatchObject({ page: 3, searchQuery: '匹配' })
    expect(store.positionFor('USER_A_DEMO', 'DOC_READER_DEMO', 'VER_OTHER_DEMO')).toBeNull()
    expect(store.positionFor('USER_B_DEMO', 'DOC_READER_DEMO', 'VER_READER_DEMO')).toBeNull()
  })
})
