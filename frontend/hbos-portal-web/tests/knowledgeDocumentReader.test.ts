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

const deliveryApi = vi.hoisted(() => ({ capabilities: vi.fn(), create: vi.fn() }))
vi.mock('@/services/knowledgeDelivery', async importOriginal => ({
  ...(await importOriginal<typeof import('@/services/knowledgeDelivery')>()),
  fetchDocumentCapabilities: deliveryApi.capabilities,
  createDocumentDelivery: deliveryApi.create,
}))

const routeBox = vi.hoisted(() => ({
  current: {
    params: { documentId: 'DOC_READER_DEMO' },
    query: { version_id: 'VER_READER_DEMO', from: 'catalog' } as Record<string, unknown>,
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
  status_note: '内部参考',
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
    navigation: { toc: [], toc_source: null, toc_truncated: false },
    disclosure: '正文来自已授权当前版本的索引文本（安全净化派生）。',
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
const stubs = {
  'a-button': { template: '<button><slot /></button>' },
  'a-tag': { template: '<span data-tag><slot /></span>' },
  'a-alert': Alert,
  'a-skeleton': { template: '<div data-loading />' },
  'a-empty': { template: '<p data-empty><slot /></p>' },
  'a-spin': { template: '<span data-spin />' },
  'a-tooltip': { template: '<span><slot /></span>' },
}

function readerProps(overrides: Record<string, unknown> = {}) {
  return {
    from: 'catalog' as const,
    document: { ...documentFixture },
    body: bodyFixture(),
    page: 1,
    pageCount: 2,
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
    previewUrl: null,
    previewKind: null,
    previewFilename: '',
    previewUnavailable: '',
    preparing: false,
    preparingMessage: '',
    canDownload: true,
    downloadBusy: false,
    downloadReason: '',
    notice: '',
    position: { page: 1, zoom: 0 },
    renewPreview: async () => null,
    ...overrides,
  }
}

const wrappers: VueWrapper[] = []
const PdfPreviewStub = defineComponent({
  props: ['url', 'page', 'zoom', 'renew'],
  emits: ['update:page', 'update:zoom', 'access-lost'],
  template: '<div data-pdf><button data-pdf-page-3 @click="$emit(\'update:page\', 3)">p3</button><button data-pdf-zoom @click="$emit(\'update:zoom\', 1.5)">z</button><button data-pdf-renew @click="renew()">renew</button></div>',
})

function mountReader(overrides: Record<string, unknown> = {}) {
  const wrapper = mount(DocumentReader, {
    props: readerProps(overrides),
    global: { stubs: { ...stubs, PdfPreview: PdfPreviewStub } },
  })
  wrappers.push(wrapper)
  return wrapper
}

function mountView() {
  const wrapper = mount(KnowledgeDocumentView, {
    global: { stubs: { ...stubs, PdfPreview: PdfPreviewStub } },
  })
  wrappers.push(wrapper)
  return wrapper
}

beforeEach(() => {
  window.sessionStorage.clear()
  vi.clearAllMocks()
  useKnowledgeReturnStore().clearAll()
  portalBox.user = { id: 'USER_READER_DEMO' }
  routeBox.current = {
    params: { documentId: 'DOC_READER_DEMO' },
    query: { version_id: 'VER_READER_DEMO', from: 'catalog' },
    path: '/hbos/knowledge/document/DOC_READER_DEMO',
  }
  readerApi.open.mockResolvedValue(openPayload())
  readerApi.page.mockResolvedValue({ ...openPayload(), body: bodyFixture({ page: 2, block_total: 2, blocks: [
    { block_id: 'b2', ordinal: 2, page_number: null, section: '1. 目的', text: '第二页匹配片段' },
  ] }) })
  readerApi.search.mockResolvedValue(searchPayload)
  deliveryApi.capabilities.mockResolvedValue({
    document_id: 'DOC_READER_DEMO', version_id: 'VER_READER_DEMO', can_read: true,
    can_preview: true, can_download: true, preview_kind: 'DERIVED_PDF',
    preview_reason: null, download_reason: null,
  })
  deliveryApi.create.mockResolvedValue({
    content_url: '/api/method/hb_knowledge_app.hb_knowledge.api.document_content?ticket=' + 'a'.repeat(43),
    expires_at: 1800000000, filename: '合成受控规程-预览版.pdf', content_type: 'application/pdf',
    sha256: 'a'.repeat(64), kind: 'DERIVED_PDF',
  })
})

afterEach(() => {
  wrappers.splice(0).forEach(wrapper => { try { wrapper.unmount() } catch { /* already unmounted */ } })
})

describe('the file reader', () => {
  it('shows the title, the real metadata and the file, with one toolbar and a real download', () => {
    const wrapper = mountReader({ previewUrl: '/SYNTHETIC?ticket=' + 'a'.repeat(43), previewKind: 'DERIVED_PDF', previewFilename: '合成受控规程-预览版.pdf' })
    const text = wrapper.text()
    expect(text).toContain('合成受控规程')
    expect(text).toContain('SOP-001')
    expect(text).toContain('版本 4.0')
    expect(text).toContain('生产部门资料')
    // A converted preview is labelled as such, and the original download is offered.
    expect(wrapper.find('[data-preview-kind]').text()).toContain('转换预览')
    expect(wrapper.find('[data-reader-download]').exists()).toBe(true)
    // No employee-facing ticket or verification noise anywhere.
    expect(text).not.toContain('票据')
    expect(text).not.toContain('待核')
    expect(text).not.toContain('页码未核验')
  })

  it('labels an original PDF as the original rather than a conversion', () => {
    const wrapper = mountReader({ previewUrl: '/SYNTHETIC', previewKind: 'ORIGINAL_PDF' })
    expect(wrapper.find('[data-preview-kind]').text()).toBe('原文件版式')
  })

  it('keeps the index text out of the way until asked, and still lets it be searched', async () => {
    const wrapper = mountReader({ previewUrl: '/SYNTHETIC' })
    const panel = wrapper.find('[data-reader-text-panel]')
    expect(panel.attributes('open')).toBeUndefined()
    expect(panel.text()).toContain('检索文本')
    await wrapper.find('#reader-search-input').setValue('目的')
    expect(wrapper.emitted('update:searchQuery')?.at(-1)).toEqual(['目的'])
    await wrapper.find('.kb-reader-search').trigger('submit')
    expect(wrapper.emitted('search')).toHaveLength(1)
    // The 500 cp evidence-excerpt projection must not truncate reader text.
    expect(wrapper.find('[data-reader-block="b1"]').text()).toContain('甲'.repeat(1200))
  })

  it('renders search matches and highlights the matched block only', () => {
    const wrapper = mountReader({
      searchQuery: '第二章', searching: false, searchRan: true,
      searchMessage: '找到 1 处 · 已检索 95 段（仅检索部分）',
      matches: [{ ordinal: 2, page: 2, block_id: 'b2', snippet: '第二章内容' }],
      highlightBlockId: 'b2', highlightQuery: '第二章',
    })
    expect(wrapper.find('[data-reader-search-status]').text()).toContain('找到 1 处')
    expect(wrapper.find('[data-reader-block="b2"] mark').text()).toBe('第二章')
    expect(wrapper.find('[data-reader-block="b1"] mark').exists()).toBe(false)
  })

  it('offers the original download when there is no preview at all', async () => {
    const wrapper = mountReader({ previewUnavailable: '这份资料还没有可用的原版式预览。' })
    const state = wrapper.find('[data-reader-no-preview]')
    expect(state.text()).toContain('暂无原版式预览')
    expect(state.text()).toContain('这份资料还没有可用的原版式预览。')
    const download = state.find('button')
    expect(download.text()).toContain('下载原文件')
    await download.trigger('click')
    expect(wrapper.emitted('download')).toHaveLength(1)
  })

  it('says so plainly when the original may not be downloaded', () => {
    const wrapper = mountReader({ canDownload: false, downloadReason: '当前账号不能下载这份原件。' })
    expect(wrapper.find('[data-reader-download]').exists()).toBe(false)
    expect(wrapper.find('[data-reader-download-unavailable]').exists()).toBe(true)
  })

  it('shows preparation progress instead of a prepare button', () => {
    const wrapper = mountReader({ preparing: true, preparingMessage: '正在准备原版式…', canDownload: true })
    expect(wrapper.find('[data-reader-preparing]').text()).toContain('正在准备原版式')
  })

  it('distinguishes unreadable from retryable failures', async () => {
    const unreadable = mountReader({
      document: null, body: null,
      failure: { kind: 'unavailable', code: 'DOCUMENT_READ_UNAVAILABLE', message: '该资料已撤回。', retryable: false },
    })
    expect(unreadable.find('[data-reader-error]').attributes('data-reader-failure')).toBe('unavailable')
    expect(unreadable.text()).toContain('当前不可阅读')
    expect(unreadable.find('[data-reader-retry]').exists()).toBe(false)

    const upstream = mountReader({
      document: null, body: null,
      failure: { kind: 'upstream', code: 'UPSTREAM_UNAVAILABLE', message: '服务暂时不可用，请稍后重试。', retryable: true },
    })
    await upstream.find('[data-reader-retry]').trigger('click')
    expect(upstream.emitted('retry')).toHaveLength(1)
  })

  it('keeps the last readable view with a retry hint after a page-level failure', async () => {
    const wrapper = mountReader({ previewUrl: '/SYNTHETIC', pageFailure: { kind: 'upstream', code: 'UPSTREAM_UNAVAILABLE', message: '服务暂时不可用。', retryable: true } })
    expect(wrapper.find('[data-reader-page-error]').text()).toContain('服务暂时不可用')
    await wrapper.find('[data-reader-page-error] button').trigger('click')
    expect(wrapper.emitted('retry-page')).toHaveLength(1)
  })

  it('emits the file page and zoom the viewer reports', async () => {
    const wrapper = mountReader({ previewUrl: '/SYNTHETIC', position: { page: 1, zoom: 0 } })
    await wrapper.find('[data-pdf-page-3]').trigger('click')
    await wrapper.find('[data-pdf-zoom]').trigger('click')
    expect(wrapper.emitted('page-change')?.[0]).toEqual([3])
    expect(wrapper.emitted('zoom-change')?.[0]).toEqual([1.5])
  })

  it('returns to the entry surface', async () => {
    const wrapper = mountReader({ previewUrl: '/SYNTHETIC' })
    await wrapper.find('[data-reader-back]').trigger('click')
    expect(wrapper.emitted('back')).toHaveLength(1)
  })
})

describe('opening a document like a file', () => {
  it('opens the document and prepares the preview by itself, with no prepare click', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(readerApi.open).toHaveBeenCalledWith(
      { documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' }, expect.any(AbortSignal),
    )
    expect(deliveryApi.capabilities).toHaveBeenCalled()
    expect(deliveryApi.create).toHaveBeenCalledWith('DOC_READER_DEMO', 'VER_READER_DEMO', 'preview')
    expect(wrapper.find('[data-pdf]').exists()).toBe(true)
    expect(wrapper.find('[data-preview-kind]').text()).toContain('转换预览')
  })

  it('downloads the original through the same short-lived channel', async () => {
    const hrefs: string[] = []
    const originalCreate = window.document.createElement.bind(window.document)
    vi.spyOn(window.document, 'createElement').mockImplementation(((tag: string) => {
      const element = originalCreate(tag)
      if (tag === 'a') {
        Object.defineProperty(element, 'href', { set(value: string) { hrefs.push(String(value)) }, get() { return '' } })
        ;(element as HTMLAnchorElement).click = () => {}
      }
      return element
    }) as typeof window.document.createElement)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('[data-reader-download]').trigger('click')
    await flushPromises()
    expect(deliveryApi.create).toHaveBeenLastCalledWith('DOC_READER_DEMO', 'VER_READER_DEMO', 'download')
    expect(hrefs[0]).toContain('ticket=')
    expect(wrapper.text()).toContain('已开始下载')
    vi.restoreAllMocks()
  })

  it('renews an expired preview ticket without asking the reader to do anything', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(deliveryApi.create).toHaveBeenCalledTimes(1)
    deliveryApi.create.mockResolvedValueOnce({
      content_url: '/api/method/hb_knowledge_app.hb_knowledge.api.document_content?ticket=' + 'b'.repeat(43),
      expires_at: 1800000060, filename: '合成受控规程-预览版.pdf', content_type: 'application/pdf',
      sha256: 'a'.repeat(64), kind: 'DERIVED_PDF',
    })
    await wrapper.find('[data-pdf-renew]').trigger('click')
    await flushPromises()
    expect(deliveryApi.create).toHaveBeenCalledTimes(2)
  })

  it('stays on the file when only the preview is unavailable, and still offers the download', async () => {
    deliveryApi.capabilities.mockResolvedValue({
      document_id: 'DOC_READER_DEMO', version_id: 'VER_READER_DEMO', can_read: true,
      can_preview: false, can_download: true, preview_kind: null,
      preview_reason: 'PREVIEW_UNAVAILABLE', download_reason: null,
    })
    deliveryApi.create.mockRejectedValue(new DomainApiError('PREVIEW_UNAVAILABLE', '该资料暂不支持原版式预览。'))
    const wrapper = mountView()
    await flushPromises()
    const state = wrapper.find('[data-reader-no-preview]')
    expect(state.exists()).toBe(true)
    expect(state.text()).toContain('下载原文件')
  })

  it('clears the whole reader when the account loses access', async () => {
    readerApi.open.mockRejectedValueOnce(new DocumentReaderError('DOCUMENT_READ_UNAVAILABLE', 'SAFE_SERVER_COPY', false, 'WITHDRAWN'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-reader-failure="unavailable"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('该资料已撤回')
    expect(wrapper.text()).not.toContain('SAFE_SERVER_COPY')
    expect(deliveryApi.create).not.toHaveBeenCalled()
  })

  it('remembers file page and zoom and reopens exactly there', async () => {
    const first = mountView()
    await flushPromises()
    await first.find('[data-pdf-page-3]').trigger('click')
    await first.find('[data-pdf-zoom]').trigger('click')
    await flushPromises()
    first.unmount()
    expect(useKnowledgeReturnStore().positionFor('USER_READER_DEMO', 'DOC_READER_DEMO', 'VER_READER_DEMO'))
      .toMatchObject({ page: 3, zoom: 1.5 })

    const second = mountView()
    await flushPromises()
    expect(second.find('[data-pdf]').exists()).toBe(true)
    expect(readerApi.open).toHaveBeenLastCalledWith(
      { documentId: 'DOC_READER_DEMO', versionId: 'VER_READER_DEMO' }, expect.any(AbortSignal),
    )
  })

  it('keeps the file page and the index-text page as two separate positions', async () => {
    // A file page is a page of the document itself; the index text has its own
    // paging. Moving inside the file must not be read as an index-text page
    // request, and vice versa.
    const wrapper = mountView()
    await flushPromises()
    readerApi.page.mockClear()
    await wrapper.find('[data-pdf-page-3]').trigger('click')
    await flushPromises()
    expect(readerApi.page).not.toHaveBeenCalled()
    wrapper.unmount()
    expect(useKnowledgeReturnStore().positionFor('USER_READER_DEMO', 'DOC_READER_DEMO', 'VER_READER_DEMO'))
      .toMatchObject({ page: 3 })
  })

  it('returns to the entry surface and keeps the reading position', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('[data-pdf-page-3]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-reader-back]').trigger('click')
    expect(routerBox.push).toHaveBeenCalledWith('/hbos/knowledge/catalog')
    expect(useKnowledgeReturnStore().positionFor('USER_READER_DEMO', 'DOC_READER_DEMO', 'VER_READER_DEMO'))
      .toMatchObject({ page: 3 })
  })
})
