import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent } from 'vue'

const readerApi = vi.hoisted(() => ({ open: vi.fn(), page: vi.fn(), search: vi.fn() }))
vi.mock('@/services/documentReaderApi', async importOriginal => ({
  ...(await importOriginal<typeof import('@/services/documentReaderApi')>()),
  openKnowledgeDocument: readerApi.open,
  readKnowledgeDocumentPage: readerApi.page,
  searchKnowledgeDocument: readerApi.search,
}))

const routeBox = vi.hoisted(() => ({
  current: {
    params: { documentId: 'DOC_READER_DEMO' },
    query: { version_id: 'VER_READER_DEMO', from: 'ask' },
    path: '/hbos/knowledge/document/DOC_READER_DEMO',
  },
}))
const routerBox = vi.hoisted(() => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => routeBox.current, useRouter: () => routerBox }))
const portalBox = vi.hoisted(() => ({ user: { id: 'USER_READER_DEMO' } }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => portalBox }))

import DocumentReader from '@/components/knowledge/DocumentReader.vue'
import KnowledgeDocumentView from '@/views/KnowledgeDocumentView.vue'
import { DocumentReaderError } from '@/services/documentReaderApi'
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
const longText = '正文第一段' + '甲'.repeat(1200)
function bodyFixture(overrides: Record<string, unknown> = {}) {
  return {
    origin: 'INDEXED_CHUNKS', page_numbering: 'UNAVAILABLE', derived: true,
    page: 1, page_count: 2, block_total: 3,
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
    navigation: { toc: [{ title: '1. 目的', ordinal: 1, page_number: null }], toc_source: 'ORIGINAL_HEADING_LINES', toc_truncated: true },
    disclosure: '正文来自已授权当前版本的索引文本（安全净化派生），不是原件下载；页码未核验。',
    ...overrides,
  }
}
const searchPayload = {
  matches: [{ ordinal: 2, page: 2, block_id: 'b2', snippet: '第二页匹配片段' }],
  searched_blocks: 95,
  capped: true,
}

const Alert = defineComponent({
  props: { message: String, description: String },
  template: '<div data-alert>{{ message }}<span v-if="description" data-alert-help>{{ description }}</span><slot name="action" /></div>',
})
const Empty = defineComponent({ props: { description: String }, template: '<p data-empty>{{ description }}</p>' })
const stubs = {
  'a-button': { template: '<button><slot /></button>' },
  'a-tag': { template: '<span data-tag><slot /></span>' },
  'a-alert': Alert,
  'a-skeleton': { template: '<div data-loading />' },
  'a-empty': Empty,
}

function readerProps(overrides: Record<string, unknown> = {}) {
  return {
    from: 'ask' as const,
    document: { ...documentFixture },
    body: bodyFixture(),
    navigation: { toc: [{ title: '1. 目的', ordinal: 1, page_number: null }], toc_source: 'ORIGINAL_HEADING_LINES', toc_truncated: true },
    disclosure: openPayload().disclosure,
    page: 1,
    pageCount: 2,
    blockTotal: 3,
    loading: false,
    pageLoading: false,
    failure: null,
    pageFailure: null,
    searchQuery: '',
    searching: false,
    searchRan: false,
    searchMessage: '',
    matches: [],
    highlightBlockId: null,
    highlightQuery: '',
    ...overrides,
  }
}

const wrappers: VueWrapper[] = []
function mountReader(overrides: Record<string, unknown> = {}) {
  const wrapper = mount(DocumentReader, { props: readerProps(overrides), global: { stubs } })
  wrappers.push(wrapper)
  return wrapper
}

function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (reason: unknown) => void
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}

beforeEach(() => {
  vi.clearAllMocks()
  useKnowledgeReturnStore().clearAll()
  portalBox.user = { id: 'USER_READER_DEMO' }
  routeBox.current = {
    params: { documentId: 'DOC_READER_DEMO' },
    query: { version_id: 'VER_READER_DEMO', from: 'ask' },
    path: '/hbos/knowledge/document/DOC_READER_DEMO',
  }
  readerApi.open.mockResolvedValue(openPayload())
  readerApi.page.mockResolvedValue({ ...openPayload(), body: bodyFixture({ page: 2, block_total: 2, blocks: [
    { block_id: 'b2', ordinal: 2, page_number: null, section: '1. 目的', text: '第二页匹配片段' },
  ] }) })
  readerApi.search.mockResolvedValue(searchPayload)
})

afterEach(() => {
  wrappers.splice(0).forEach(wrapper => { try { wrapper.unmount() } catch { /* already unmounted */ } })
})

function mountView() {
  const wrapper = mount(KnowledgeDocumentView, { global: { stubs } })
  wrappers.push(wrapper)
  return wrapper
}

describe('DocumentReader rendering', () => {
  it('renders title, version, catalogue, authorization, derived disclosure and the full body text', () => {
    const wrapper = mountReader()
    const text = wrapper.text()
    expect(text).toContain('合成受控规程')
    expect(text).toContain('业务版本 4.0')
    expect(text).toContain('生产部门资料')
    expect(text).toContain('已授权阅读')
    expect(text).toContain('当前现行版本')
    expect(text).toContain('派生阅读版')
    expect(text).toContain('页码未核验')
    expect(text).toContain('正文来自已授权当前版本的索引文本')
    expect(text).toContain('原件下载未开放')
    // The 500 cp evidence-excerpt projection must not truncate reader text.
    expect(wrapper.find('[data-reader-block="b1"]').text()).toContain('甲'.repeat(1200))
    expect(wrapper.find('[data-reader-block="b1"]').attributes('data-highlight')).toBeUndefined()
    // TOC truncation is honest about its coverage.
    expect(text).toContain('目录仅覆盖前 1 部分')
  })

  it('renders search matches, highlights the matched block only and jumps without inventing a page', async () => {
    const wrapper = mountReader({
      searchQuery: '第二章', searching: false, searchRan: true,
      searchMessage: '找到 1 处匹配 · 已检索 95 段正文（仅检索部分正文）',
      matches: [{ ordinal: 2, page: 2, block_id: 'b2', snippet: '第二章内容' }],
      highlightBlockId: 'b2', highlightQuery: '第二章',
    })
    expect(wrapper.find('[data-reader-search-status]').text()).toContain('找到 1 处匹配')
    expect(wrapper.find('[data-reader-block="b2"] mark').text()).toBe('第二章')
    expect(wrapper.find('[data-reader-block="b1"] mark').exists()).toBe(false)
    await wrapper.find('[data-reader-match]').trigger('click')
    expect(wrapper.emitted('jump-match')?.[0]).toEqual([{ ordinal: 2, page: 2, block_id: 'b2', snippet: '第二章内容' }])
  })

  it('shows the explicit empty-body message instead of a blank page', () => {
    const wrapper = mountReader({ body: bodyFixture({ blocks: [], block_total: 0 }) })
    expect(wrapper.find('[data-reader-empty]').text()).toContain('该资料暂无可读正文（索引正文不可用）')
    expect(wrapper.find('[data-reader-block="b1"]').exists()).toBe(false)
  })

  it('distinguishes a skipped page from a document without indexed text', () => {
    const wrapper = mountReader({ body: bodyFixture({ blocks: [], block_total: 3, page_count: 2 }) })
    expect(wrapper.find('[data-reader-empty]').text()).toContain('本页暂无可展示正文')
    expect(wrapper.find('[data-reader-empty]').text()).not.toContain('该资料暂无可读正文')
    // The pager must stay usable: only the page failed to sanitize.
    expect(wrapper.find('.kb-reader-pager').exists()).toBe(true)
  })

  it('distinguishes unreadable from retryable upstream failures', async () => {
    const unreadable = mountReader({
      document: null, body: null, navigation: null, disclosure: '',
      failure: { kind: 'unavailable', code: 'DOCUMENT_READ_UNAVAILABLE', message: '该资料已撤回，正文不再提供。', retryable: false },
    })
    expect(unreadable.find('[data-reader-error]').attributes('data-reader-failure')).toBe('unavailable')
    expect(unreadable.text()).toContain('当前不可阅读')
    expect(unreadable.text()).toContain('该资料已撤回')
    expect(unreadable.find('[data-reader-body]').exists()).toBe(false)
    expect(unreadable.find('[data-reader-retry]').exists()).toBe(false)

    const upstream = mountReader({
      document: null, body: null, navigation: null, disclosure: '',
      failure: { kind: 'upstream', code: 'UPSTREAM_UNAVAILABLE', message: '正文服务暂时不可用，请稍后重试。', retryable: true },
    })
    expect(upstream.text()).toContain('正文服务暂时不可用')
    await upstream.find('[data-reader-retry]').trigger('click')
    expect(upstream.emitted('retry')).toHaveLength(1)
  })

  it('emits paging, page-jump, search and back intents', async () => {
    const wrapper = mountReader({ page: 2, pageCount: 3 })
    await wrapper.find('[data-reader-prev]').trigger('click')
    await wrapper.find('[data-reader-next]').trigger('click')
    expect(wrapper.emitted('prev')).toHaveLength(1)
    expect(wrapper.emitted('next')).toHaveLength(1)

    await wrapper.find('#reader-page-input').setValue('1')
    await wrapper.find('.kb-reader-jump').trigger('submit')
    expect(wrapper.emitted('go-page')?.[0]).toEqual([1])

    await wrapper.find('#reader-search-input').setValue('目的')
    expect(wrapper.emitted('update:searchQuery')?.at(-1)).toEqual(['目的'])
    await wrapper.find('.kb-reader-search').trigger('submit')
    expect(wrapper.emitted('search')).toHaveLength(1)

    await wrapper.find('[data-reader-back]').trigger('click')
    expect(wrapper.emitted('back')).toHaveLength(1)
  })

  it('keeps the last readable page visible with a retry hint after a page-level upstream failure', async () => {
    const wrapper = mountReader({
      pageFailure: { kind: 'upstream', code: 'UPSTREAM_UNAVAILABLE', message: '正文服务暂时不可用，请稍后重试。', retryable: true },
    })
    expect(wrapper.find('[data-reader-page-error]').text()).toContain('正文服务暂时不可用')
    expect(wrapper.find('[data-reader-block="b1"]').exists()).toBe(true)
    await wrapper.find('[data-reader-page-retry]').trigger('click')
    expect(wrapper.emitted('retry-page')).toHaveLength(1)
  })
})

describe('KnowledgeDocumentView state machine', () => {
  it('opens the authorized document and renders the derived reader', async () => {
    const wrapper = mountView()
    expect(wrapper.find('[data-loading]').exists()).toBe(true)
    await flushPromises()
    expect(readerApi.open).toHaveBeenCalledWith(
      { documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' },
      expect.any(AbortSignal),
    )
    expect(wrapper.text()).toContain('合成受控规程')
    expect(wrapper.find('[data-reader-block="b1"]').text()).toContain('甲'.repeat(1200))
    expect(wrapper.find('[data-loading]').exists()).toBe(false)
  })

  it('opens without a version id, shows the resolved-version note and pages with the server version', async () => {
    routeBox.current = {
      params: { documentId: 'DOC_READER_DEMO' },
      query: { from: 'search' },
      path: '/hbos/knowledge/document/DOC_READER_DEMO',
    }
    readerApi.open.mockResolvedValue({ ...openPayload(), document: { ...documentFixture, version_id: 'VER_CURRENT_DEMO' } })
    const wrapper = mountView()
    await flushPromises()
    expect(readerApi.open).toHaveBeenCalledWith({ documentId: 'DOC_READER_DEMO', versionId: null }, expect.any(AbortSignal))
    expect(wrapper.text()).toContain('按当前授权版本解析')
    await wrapper.find('[data-reader-next]').trigger('click')
    await flushPromises()
    expect(readerApi.page).toHaveBeenCalledWith(
      { documentId: 'DOC_READER_DEMO', versionId: 'VER_CURRENT_DEMO' }, 2, expect.any(AbortSignal),
    )
  })

  it('pages with the version resolved by the server', async () => {
    readerApi.open.mockResolvedValue({ ...openPayload(), document: { ...documentFixture, version_id: 'VER_RESOLVED_DEMO' } })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('[data-reader-next]').trigger('click')
    await flushPromises()
    expect(readerApi.page).toHaveBeenCalledWith(
      { documentId: 'DOC_READER_DEMO', versionId: 'VER_RESOLVED_DEMO' },
      2,
      expect.any(AbortSignal),
    )
    expect(wrapper.find('[data-reader-block="b2"]').text()).toContain('第二页匹配片段')
  })

  it('searches inside the document and jumps to the matched page with a highlight', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('#reader-search-input').setValue('匹配')
    await wrapper.find('.kb-reader-search').trigger('submit')
    await flushPromises()
    expect(readerApi.search).toHaveBeenCalledWith(
      { documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' }, '匹配', 20,
    )
    expect(wrapper.find('[data-reader-search-status]').text()).toContain('仅检索部分正文')
    await wrapper.find('[data-reader-match]').trigger('click')
    await flushPromises()
    expect(readerApi.page).toHaveBeenCalledWith(
      { documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' }, 2, expect.any(AbortSignal),
    )
    expect(wrapper.find('[data-reader-block="b2"] mark').text()).toBe('匹配')
  })

  it('clears the body on an unreadable document and does not pretend it is empty text', async () => {
    readerApi.open.mockRejectedValueOnce(new DocumentReaderError('DOCUMENT_READ_UNAVAILABLE', 'SAFE_SERVER_COPY', false, 'WITHDRAWN'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-reader-failure="unavailable"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('该资料已撤回')
    expect(wrapper.find('[data-reader-body]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('SAFE_SERVER_COPY')
  })

  it('offers a retry for an upstream failure without claiming the document is empty', async () => {
    readerApi.open.mockRejectedValueOnce(new DomainApiError('UPSTREAM_UNAVAILABLE', 'upstream'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-reader-failure="upstream"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('正文服务暂时不可用')
    expect(wrapper.text()).not.toContain('暂无可读正文')
    await wrapper.find('[data-reader-retry]').trigger('click')
    await flushPromises()
    expect(readerApi.open).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('合成受控规程')
  })

  it('shows the explicit empty-body copy for an authorized document without numbered text', async () => {
    readerApi.open.mockResolvedValue(openPayload({ body: bodyFixture({ blocks: [], page_count: 0, block_total: 0 }) }))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-reader-empty]').text()).toContain('该资料暂无可读正文（索引正文不可用）')
  })

  it('falls back to page 1 when the server rejects an out-of-range page', async () => {
    const wrapper = mountView()
    await flushPromises()
    readerApi.page.mockRejectedValueOnce(new DocumentReaderError('DOCUMENT_READ_PAGE_OUT_OF_RANGE', 'range', true))
      .mockResolvedValueOnce(openPayload())
    await wrapper.find('[data-reader-next]').trigger('click')
    await flushPromises()
    expect(readerApi.page.mock.calls.map(call => call[1])).toEqual([2, 1])
    expect(wrapper.text()).toContain('第 1 页')
    expect(wrapper.find('[data-reader-block="b1"]').exists()).toBe(true)
  })

  it('remembers the reader page and reopens at it without re-reading the document body from scratch', async () => {
    const first = mountView()
    await flushPromises()
    await first.find('[data-reader-next]').trigger('click')
    await flushPromises()
    first.unmount()
    expect(useKnowledgeReturnStore().positionFor('USER_READER_DEMO', 'DOC_READER_DEMO', 'VER_READER_DEMO')).toMatchObject({ page: 2 })

    readerApi.open.mockClear()
    readerApi.page.mockClear()
    const second = mountView()
    await flushPromises()
    expect(readerApi.open).toHaveBeenCalledTimes(1)
    expect(readerApi.page).toHaveBeenCalledWith(
      { documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' }, 2, expect.any(AbortSignal),
    )
    expect(second.text()).toContain('第 2 页')
  })

  it('returns to the entry surface and keeps the reader position', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('[data-reader-next]').trigger('click')
    await flushPromises()
    routerBox.push.mockClear()
    await wrapper.find('[data-reader-back]').trigger('click')
    expect(routerBox.push).toHaveBeenCalledWith('/hbos/knowledge')
    expect(useKnowledgeReturnStore().positionFor('USER_READER_DEMO', 'DOC_READER_DEMO', 'VER_READER_DEMO')).toMatchObject({ page: 2 })
  })
})
