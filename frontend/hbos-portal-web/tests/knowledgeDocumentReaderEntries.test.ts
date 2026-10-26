import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent } from 'vue'
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
  getKnowledgeDocumentsPage: api.catalog,
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

const routeBox = vi.hoisted(() => ({ current: { path: '/hbos/knowledge', query: {} as Record<string, unknown> } }))
const routerBox = vi.hoisted(() => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => routeBox.current, useRouter: () => routerBox }))
const portalBox = vi.hoisted(() => ({ user: { id: 'USER_QA_DEMO' } }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => portalBox }))

import KnowledgeView from '@/views/KnowledgeView.vue'
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
  'a-drawer': Drawer,
  'a-alert': Alert,
  'a-tag': { template: '<span><slot /></span>' },
  'a-skeleton': { template: '<div data-loading />' },
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

beforeEach(() => {
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
  api.catalog.mockResolvedValue({ documents: [catalogDocument], total: 1, page: 1, page_size: 4 })
  api.resolve.mockResolvedValue(evidence)
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
    expect(wrapper.text()).toContain('当前来源未附版本记录')
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
    expect(wrapper.find('[data-catalog-open-reader]').exists()).toBe(true)
    await wrapper.find('[data-catalog-open-reader]').trigger('click')
    expect(routerBox.push).toHaveBeenCalledWith({
      name: 'knowledge-document',
      params: { documentId: 'DOC_CAT_DEMO' },
      query: { from: 'catalog', version_id: 'VER_CAT_DEMO' },
    })
    expect(useKnowledgeReturnStore().peek()?.view).toBe('catalog')
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
      mode: 'ask', hasSearched: false, results: [],
      tools: { question: '草稿追问', conversation: 'TURN_SAVED_DEMO', turns: [{ ...answer, question: '已保存问题' }], queryState: 'success' },
    }))
    const wrapper = await renderView()
    await flushPromises()
    expect(wrapper.find('.kb-answer-copy').text()).toContain('保存的回答正文')
    const followup = wrapper.find('#knowledge-question')
    expect(followup.exists()).toBe(true)
    expect((followup.element as HTMLTextAreaElement).value).toBe('草稿追问')
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
