import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, nextTick, reactive } from 'vue'
import type { KnowledgeReturnSnapshot } from '@/contracts/knowledgeReturn'

const api = vi.hoisted(() => ({
  status: vi.fn(), spaces: vi.fn(), search: vi.fn(), resolve: vi.fn(), catalog: vi.fn(),
  activity: vi.fn(), activityPage: vi.fn(), feedback: vi.fn(), feedbackPage: vi.fn(),
  ask: vi.fn(), open: vi.fn(), remove: vi.fn(), saveBookmark: vi.fn(), submitFeedback: vi.fn(), saveDocBookmark: vi.fn(),
}))
vi.mock('@/services/p1Api', async importOriginal => ({
  ...(await importOriginal<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
  getKnowledgeSpaces: api.spaces,
  searchKnowledge: api.search,
  resolveKnowledgeEvidence: api.resolve,
  getKnowledgeEmployeeCatalogPage: api.catalog,
  getKnowledgeActivity: api.activity,
  getKnowledgeActivityPage: api.activityPage,
  getKnowledgeFeedback: api.feedback,
  getKnowledgeFeedbackPage: api.feedbackPage,
  askKnowledgeReference: api.ask,
  openKnowledgeSaved: api.open,
  removeKnowledgeSaved: api.remove,
  saveKnowledgeBookmark: api.saveBookmark,
  sendKnowledgeFeedback: api.submitFeedback,
  saveKnowledgeDocumentBookmark: api.saveDocBookmark,
}))

const routeBox = vi.hoisted(() => ({
  current: { path: '/hbos/knowledge', query: {} as Record<string, unknown>, params: undefined as Record<string, string> | undefined },
}))
const routerBox = vi.hoisted(() => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => routeBox.current, useRouter: () => routerBox }))
const portalBox = vi.hoisted(() => ({ user: { id: 'USER_QA_DEMO' } }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => portalBox }))

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

import KnowledgeView from '@/views/KnowledgeView.vue'
import KnowledgeDocumentView from '@/views/KnowledgeDocumentView.vue'
import EvidenceDrawer from '@/components/knowledge/EvidenceDrawer.vue'
import { DomainApiError } from '@/services/p1Api'
import { useKnowledgeReturnStore } from '@/stores/knowledgeReturn'

const evidence = {
  document_id: 'DOC_A_DEMO', title: '合成资料 A', version: '4.0', status_note: '内部参考／有效性待核',
  section: null, page_number: null, excerpt: 'SYNTHETIC_EXCERPT_A_DEMO', evidence_id: 'EV_A_DEMO',
  space_id: 'DEPT_PRODUCTION', source_type: 'COMPANY_CONTROLLED',
}
const catalogDocument = {
  document_id: 'DOC_CAT_DEMO', title: '合成目录资料', space_id: 'DEPT_PRODUCTION', department: '生产部门',
  document_number: 'SOP-002', version: '3.0', status_note: '内部参考／有效性待核', version_id: 'VER_CAT_DEMO',
}

const Drawer = defineComponent({
  props: { open: Boolean, title: String },
  emits: ['close'],
  template: '<section v-if="open" data-drawer><slot name="title"/><slot/><button data-close @click="$emit(\'close\')">close</button></section>',
})
const Alert = defineComponent({
  props: { message: String, description: String },
  template: '<p data-error>{{ message }}<span v-if="description">{{ description }}</span></p>',
})
const InputSearch = defineComponent({
  props: { value: String },
  emits: ['update:value', 'search'],
  template: '<input :value="value" @input="$emit(\'update:value\', $event.target.value)" @keydown.enter="$emit(\'search\')" />',
})
const stubs = {
  PdfPreview: defineComponent({ props: { page: Number, zoom: Number, url: String }, template: '<div data-pdf :data-page="page" />' }),
  'a-drawer': Drawer,
  'a-alert': Alert,
  'a-tag': { template: '<span><slot /></span>' },
  'a-skeleton': { template: '<div data-loading />' },
  'a-spin': { template: '<span data-spin />' },
  'a-button': { template: '<button><slot /></button>' },
  'a-empty': defineComponent({ props: { description: String }, template: '<p data-empty>{{ description }}</p>' }),
  'a-tooltip': { template: '<span><slot /></span>' },
  'a-input-search': InputSearch,
  'a-pagination': { template: '<div data-pagination />' },
  'a-modal': defineComponent({ props: { open: Boolean }, template: '<div v-if="open"><slot /></div>' }),
  RouterLink: { template: '<span><slot /></span>' },
}
const wrappers: VueWrapper[] = []

function snapshot(overrides: Partial<KnowledgeReturnSnapshot> = {}): KnowledgeReturnSnapshot {
  return {
    view: 'query', query: '已保存问题', mode: 'search', selectedSpace: 'DEPT_PRODUCTION',
    searchMode: 'STANDARD', searchContext: null, results: [evidence], hasSearched: true,
    searchState: 'retrieved', tools: null,
    catalog: { query: '', page: 1, lawCategory: '', sourceFolder: 'SOURCE_ROOT' },
    scrollTop: 0,
    ...overrides,
  }
}

async function renderView(path = '/hbos/knowledge') {
  routeBox.current = { path, query: {} }
  const wrapper = mount(KnowledgeView, { global: { stubs } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

async function runSearch(wrapper: VueWrapper, results: Record<string, unknown>[] = [evidence], query = 'SYNTHETIC query') {
  api.search.mockResolvedValue({ request_id: 'REQ_SEARCH_DEMO', mode: 'retrieval', results })
  await wrapper.findAll('button').find(button => button.text() === '搜资料')!.trigger('click')
  await wrapper.find('#knowledge-query').setValue(query)
  await wrapper.find('.knowledge-search').trigger('submit')
  await flushPromises()
}

function documentRoute(query: Record<string, unknown>) {
  return { params: { documentId: 'DOC_A_DEMO' }, query, path: '/hbos/knowledge/document/DOC_A_DEMO' }
}

async function mountDocumentView(query: Record<string, unknown>) {
  routeBox.current = documentRoute(query)
  const wrapper = mount(KnowledgeDocumentView, { global: { stubs } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  // Each test is a fresh tab: the per-identity workspace store must not
  // carry a previous case's filters into this one.
  window.sessionStorage.clear()
  vi.clearAllMocks()
  useKnowledgeReturnStore().clearAll()
  portalBox.user = { id: 'USER_QA_DEMO' }
  routeBox.current = { path: '/hbos/knowledge', query: {} }
  api.status.mockResolvedValue({
    can_enter: true, can_search: true, gateway_configured: true, ask_enabled: true,
    mode: 'retrieval', environment: 'production',
  })
  api.spaces.mockResolvedValue([{ space_id: 'DEPT_PRODUCTION', title: '生产部门资料', document_count: 1 }])
  api.activity.mockResolvedValue([])
  api.activityPage.mockResolvedValue({ items: [], page: 1, page_size: 6, has_more: false })
  api.feedback.mockResolvedValue([])
  api.feedbackPage.mockResolvedValue({ items: [], page: 1, page_size: 6, has_more: false })
  api.catalog.mockResolvedValue({ documents: [{ ...catalogDocument, file_formats: ['pdf'] }], total_documents: 1, category_options: [], format_options: ['pdf'], page: 1, page_size: 20 })
  api.resolve.mockResolvedValue(evidence)
  readerApi.open.mockResolvedValue({
    document: {
      document_id: 'DOC_A_DEMO', version_id: 'VER_A_DEMO', title: '合成资料 A', document_number: null,
      space_id: 'DEPT_PRODUCTION', space_title: '生产部门资料', business_version: '4.0', status_note: '内部参考',
      reference_state: 'CURRENT', authorization: 'AUTHORIZED', source_type: 'COMPANY_CONTROLLED',
    },
    body: {
      origin: 'INDEXED_CHUNKS', page_numbering: 'UNAVAILABLE', derived: true,
      page: 1, page_count: 2, block_total: 1,
      blocks: [{ block_id: 'b1', ordinal: 1, page_number: null, section: null, text: '合成正文' }],
    },
    navigation: { toc: [], toc_source: null, toc_truncated: false },
    disclosure: '正文来自已授权当前版本的索引文本（安全净化派生）。',
  })
  readerApi.page.mockResolvedValue({
    document: {
      document_id: 'DOC_A_DEMO', version_id: 'VER_A_DEMO', title: '合成资料 A', document_number: null,
      space_id: 'DEPT_PRODUCTION', space_title: '生产部门资料', business_version: '4.0', status_note: '内部参考',
      reference_state: 'CURRENT', authorization: 'AUTHORIZED', source_type: 'COMPANY_CONTROLLED',
    },
    body: {
      origin: 'INDEXED_CHUNKS', page_numbering: 'UNAVAILABLE', derived: true,
      page: 2, page_count: 2, block_total: 1,
      blocks: [{ block_id: 'b2', ordinal: 2, page_number: null, section: null, text: '第二段正文' }],
    },
    navigation: { toc: [], toc_source: null, toc_truncated: false },
    disclosure: '正文来自已授权当前版本的索引文本（安全净化派生）。',
  })
  readerApi.search.mockResolvedValue({ matches: [], searched_blocks: 0, capped: false })
  deliveryApi.capabilities.mockResolvedValue({
    document_id: 'DOC_A_DEMO', version_id: 'VER_A_DEMO', can_read: true,
    can_preview: true, can_download: true, preview_kind: 'DERIVED_PDF',
    preview_reason: null, download_reason: null,
  })
  deliveryApi.create.mockResolvedValue({
    content_url: '/api/method/hb_knowledge_app.hb_knowledge.api.document_content?ticket=' + 'a'.repeat(43),
    expires_at: 1800000000, filename: '合成资料-预览版.pdf', content_type: 'application/pdf',
    sha256: 'a'.repeat(64), kind: 'DERIVED_PDF',
  })
})

afterEach(() => {
  wrappers.splice(0).forEach(wrapper => { try { wrapper.unmount() } catch { /* already unmounted */ } })
})

describe('source drawer reader entry', () => {
  it('emits the document identity and lets the server resolve the version when absent', async () => {
    const wrapper = mount(EvidenceDrawer, { props: { open: true, loading: false, evidence, error: null }, global: { stubs } })
    wrappers.push(wrapper)
    const button = wrapper.find('[data-reader-open]')
    expect(button.attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('打开时会重新核验当前身份与版本')
    await button.trigger('click')
    expect(wrapper.emitted('read')?.[0]).toEqual([{ documentId: 'DOC_A_DEMO' }])
  })

  it('forwards a supplied logical version without disabling the entry', async () => {
    const wrapper = mount(EvidenceDrawer, { props: { open: true, loading: false, evidence, error: null, versionId: 'VER_A_DEMO' }, global: { stubs } })
    wrappers.push(wrapper)
    await wrapper.find('[data-reader-open]').trigger('click')
    expect(wrapper.emitted('read')?.[0]).toEqual([{ documentId: 'DOC_A_DEMO', versionId: 'VER_A_DEMO' }])
  })
})

describe('three entries route into the single reader', () => {
  it('opens a search result directly in the reader and captures the workspace snapshot', async () => {
    const wrapper = await renderView()
    await runSearch(wrapper)
    await wrapper.find('[data-search-open-document]').trigger('click')
    expect(routerBox.push).toHaveBeenCalledWith({
      name: 'knowledge-document',
      params: { documentId: 'DOC_A_DEMO' },
      query: { from: 'search' },
    })
    const captured = useKnowledgeReturnStore().peek()
    expect(captured?.query).toBe('SYNTHETIC query')
    expect(captured?.results[0]!.document_id).toBe('DOC_A_DEMO')
  })

  it('forwards a search result version when the response carries one', async () => {
    const wrapper = await renderView()
    await runSearch(wrapper, [{ ...evidence, version_id: 'VER_SEARCH_DEMO' }])
    await wrapper.find('[data-search-open-document]').trigger('click')
    expect(routerBox.push).toHaveBeenCalledWith({
      name: 'knowledge-document',
      params: { documentId: 'DOC_A_DEMO' },
      query: { from: 'search', version_id: 'VER_SEARCH_DEMO' },
    })
  })

  it('keeps the search origin when the reader is opened from the evidence drawer', async () => {
    const wrapper = await renderView()
    await runSearch(wrapper)
    await wrapper.find('.result-card .kb-doc-main').trigger('click')
    await flushPromises()
    expect(api.resolve).toHaveBeenCalledWith('EV_A_DEMO', expect.any(AbortSignal))
    await wrapper.find('[data-reader-open]').trigger('click')
    expect(routerBox.push).toHaveBeenCalledWith({
      name: 'knowledge-document',
      params: { documentId: 'DOC_A_DEMO' },
      query: { from: 'search' },
    })
  })

  it('opens the catalog detail in the reader with its version and returns to the catalog', async () => {
    const wrapper = await renderView('/hbos/knowledge/catalog')
    expect(api.catalog).toHaveBeenCalled()
    await wrapper.find('.catalog-row .kb-doc-main').trigger('click')
    await flushPromises()
    expect(routerBox.push).toHaveBeenCalledWith({
      name: 'knowledge-document',
      params: { documentId: 'DOC_CAT_DEMO' },
      query: { from: 'catalog', version_id: 'VER_CAT_DEMO' },
    })
    expect(useKnowledgeReturnStore().peek()).toMatchObject({ view: 'catalog', catalog: { focusDocument: 'DOC_CAT_DEMO' } })
  })
})

describe('verified physical page locates the file view only', () => {
  const evidenceWith = (page: unknown) => ({ ...evidence, page_number: page }) as unknown as typeof evidence

  it('carries a trusted evidence page through the drawer read event', async () => {
    const wrapper = mount(EvidenceDrawer, { props: { open: true, loading: false, evidence: evidenceWith(7), error: null }, global: { stubs } })
    wrappers.push(wrapper)
    await wrapper.find('[data-reader-open]').trigger('click')
    expect(wrapper.emitted('read')?.[0]).toEqual([{ documentId: 'DOC_A_DEMO', physicalPage: 7 }])
  })

  it.each([null, 0, -1, 2.5, 10001, Number.NaN, '7'])('leaves the reader entry unchanged for an untrusted page hint (%s)', async hint => {
    const wrapper = mount(EvidenceDrawer, { props: { open: true, loading: false, evidence: evidenceWith(hint), error: null }, global: { stubs } })
    wrappers.push(wrapper)
    await wrapper.find('[data-reader-open]').trigger('click')
    expect(wrapper.emitted('read')?.[0]).toEqual([{ documentId: 'DOC_A_DEMO' }])
  })

  it('adds physical_page to the search entry route but not for an entry without a page', async () => {
    const wrapper = await renderView()
    await runSearch(wrapper, [{ ...evidence, page_number: 9 }])
    await wrapper.find('[data-search-open-document]').trigger('click')
    expect(routerBox.push).toHaveBeenCalledWith({
      name: 'knowledge-document',
      params: { documentId: 'DOC_A_DEMO' },
      query: { from: 'search', physical_page: '9' },
    })
  })

  it('opens the body at page 1 for a physical-page entry and shows that PDF page', async () => {
    useKnowledgeReturnStore().rememberPosition('USER_QA_DEMO', 'DOC_A_DEMO', 'VER_A_DEMO', { page: 2, zoom: 0, searchQuery: '' })
    const wrapper = await mountDocumentView({ version_id: 'VER_A_DEMO', from: 'search', physical_page: '5' })
    expect(readerApi.open).toHaveBeenCalledWith(
      { documentId: 'DOC_A_DEMO', versionId: 'VER_A_DEMO' }, expect.any(AbortSignal),
    )
    expect(readerApi.page).not.toHaveBeenCalled()
    expect(wrapper.find('[data-pdf]').attributes('data-page')).toBe('5')
  })

  it.each(['0', '-1', '1.5', '1e3', '10001', '999999999999999999999', 'abc'])('ignores an invalid physical_page hint (%s) and uses the remembered page', async hint => {
    useKnowledgeReturnStore().rememberPosition('USER_QA_DEMO', 'DOC_A_DEMO', 'VER_A_DEMO', { page: 2, zoom: 0, searchQuery: '' })
    const wrapper = await mountDocumentView({ version_id: 'VER_A_DEMO', from: 'search', physical_page: hint })
    expect(wrapper.find('[data-pdf]').attributes('data-page')).toBe('2')
    expect(readerApi.page).toHaveBeenCalledWith(
      { documentId: 'DOC_A_DEMO', versionId: 'VER_A_DEMO' }, 2, expect.any(AbortSignal),
    )
  })

  it('rejects an array hint and keeps the remembered page', async () => {
    useKnowledgeReturnStore().rememberPosition('USER_QA_DEMO', 'DOC_A_DEMO', 'VER_A_DEMO', { page: 2, zoom: 0, searchQuery: '' })
    const wrapper = await mountDocumentView({ version_id: 'VER_A_DEMO', from: 'search', physical_page: ['5'] })
    expect(wrapper.find('[data-pdf]').attributes('data-page')).toBe('2')
  })

  it('follows a new physical_page for the same document without re-reading the body', async () => {
    routeBox.current = reactive(documentRoute({ version_id: 'VER_A_DEMO', from: 'search', physical_page: '5' }))
    const wrapper = mount(KnowledgeDocumentView, { global: { stubs } })
    wrappers.push(wrapper)
    await flushPromises()
    readerApi.page.mockClear()
    routeBox.current.query.physical_page = '8'
    await flushPromises()
    await nextTick()
    expect(wrapper.find('[data-pdf]').attributes('data-page')).toBe('8')
    expect(readerApi.page).not.toHaveBeenCalled()
  })
})

describe('returning from the reader restores the workspace without re-asking', () => {
  it('restores the question, search results and scroll position without calling search or ask', async () => {
    const scrollSpy = vi.spyOn(window, 'scrollTo')
    useKnowledgeReturnStore().capture('USER_QA_DEMO', snapshot({ scrollTop: 240 }))
    const wrapper = await renderView()
    await flushPromises()
    expect((wrapper.find('#knowledge-query').element as HTMLTextAreaElement).value).toBe('已保存问题')
    expect(wrapper.find('.result-card').exists()).toBe(true)
    expect(wrapper.find('.result-card').text()).toContain('SYNTHETIC_EXCERPT_A_DEMO')
    expect(api.search).not.toHaveBeenCalled()
    expect(api.ask).not.toHaveBeenCalled()
    expect(scrollSpy).toHaveBeenCalledWith(0, 240)
    expect(useKnowledgeReturnStore().takeFor('USER_QA_DEMO')).toBeNull()
  })

  it('restores the answered conversation and the follow-up draft without a new model call', async () => {
    const answer = {
      request_id: 'REQ_SAVED_DEMO', turn_id: 'TURN_SAVED_DEMO', conversation_id: 'TURN_SAVED_DEMO',
      mode: 'internal_reference_generation', answer_status: 'REFERENCE_ANSWERED', answerable: true,
      answer: '保存的回答正文', citations: [], answer_origin: 'KNOWLEDGE', model_alias: 'gpt-6-luna',
    }
    useKnowledgeReturnStore().capture('USER_QA_DEMO', snapshot({
      mode: 'ask', query: '草稿追问', hasSearched: false, results: [],
      tools: { question: '草稿追问', conversation: 'TURN_SAVED_DEMO', turns: [{ ...answer, question: '已保存问题' }], queryState: 'success' },
    }))
    const wrapper = await renderView()
    await flushPromises()
    expect(wrapper.find('.kb-answer-copy').text()).toContain('保存的回答正文')
    const followup = wrapper.find('#knowledge-query')
    expect(followup.exists()).toBe(true)
    expect((followup.element as HTMLTextAreaElement).value).toBe('草稿追问')
    expect(wrapper.find('#knowledge-question').exists()).toBe(false)
    expect(api.ask).not.toHaveBeenCalled()
    expect(api.search).not.toHaveBeenCalled()
  })

  it('never restores a previous identity’s snapshot', async () => {
    useKnowledgeReturnStore().capture('USER_OTHER_DEMO', snapshot())
    const wrapper = await renderView()
    await flushPromises()
    expect((wrapper.find('#knowledge-query').element as HTMLTextAreaElement).value).toBe('')
    expect(wrapper.find('.result-card').exists()).toBe(false)
    expect(useKnowledgeReturnStore().takeFor('USER_QA_DEMO')).toBeNull()
  })

  it('shows the existing stale-source copy when a restored evidence handle cannot be resolved', async () => {
    api.resolve.mockRejectedValueOnce(new DomainApiError('EVIDENCE_UNAVAILABLE', '该证据不可用或已失效。'))
    const wrapper = await renderView()
    await runSearch(wrapper)
    await wrapper.find('.result-card .kb-doc-main').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-drawer]').text()).toContain('该证据不可用或已失效')
    expect(api.ask).not.toHaveBeenCalled()
    expect(wrapper.find('.result-card').exists()).toBe(false)
  })
})
