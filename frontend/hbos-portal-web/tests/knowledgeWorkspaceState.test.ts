import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent } from 'vue'

/**
 * Reload / tab-switch behaviour of the knowledge workspace.
 *
 * The workspace keeps only presentation state per signed-in identity inside the
 * tab's sessionStorage: the question, mode and scope, the catalogue filter,
 * page and page size, and the reading position. It never stores an answer, a
 * document body or a credential, and another identity sees nothing.
 */

const api = vi.hoisted(() => ({
  status: vi.fn(), spaces: vi.fn(), search: vi.fn(), resolve: vi.fn(),
  documents: vi.fn(), activity: vi.fn(), activityPage: vi.fn(), feedback: vi.fn(),
  feedbackPage: vi.fn(), ask: vi.fn(), open: vi.fn(), remove: vi.fn(),
  saveBookmark: vi.fn(), submitFeedback: vi.fn(), saveDocBookmark: vi.fn(),
  model: vi.fn(),
}))
vi.mock('@/services/p1Api', async importOriginal => ({
  ...(await importOriginal<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
  getKnowledgeSpaces: api.spaces,
  searchKnowledge: api.search,
  resolveKnowledgeEvidence: api.resolve,
  getKnowledgeDocumentsPage: api.documents,
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
  setKnowledgeModelPreference: api.model,
}))

const routeBox = vi.hoisted(() => ({ current: { path: '/hbos/knowledge/catalog', query: {} as Record<string, unknown> } }))
const routerBox = vi.hoisted(() => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => routeBox.current, useRouter: () => routerBox }))
const portalBox = vi.hoisted(() => ({ user: { id: 'USER_STATE_DEMO' } as { id: string } | null }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => portalBox }))

import KnowledgeView from '@/views/KnowledgeView.vue'
import { loadWorkspace, saveWorkspace } from '@/services/knowledgeWorkspace'
import { useKnowledgeReturnStore } from '@/stores/knowledgeReturn'

const stubs = {
  'a-button': { template: '<button><slot /></button>' },
  'a-tag': { template: '<span><slot /></span>' },
  'a-alert': { props: ['message'], template: '<p>{{ message }}</p>' },
  'a-skeleton': { template: '<div data-loading />' },
  'a-empty': { template: '<p data-empty />' },
  'a-spin': { template: '<span />' },
  'a-tooltip': { template: '<span><slot /></span>' },
  'a-input-search': defineComponent({
    props: ['value'], emits: ['update:value', 'search'],
    template: '<input id="catalog-query" :value="value" @input="onInput" />',
    methods: { onInput(event: Event) { this.$emit('update:value', (event.target as HTMLInputElement).value) } },
  }),
  'a-pagination': defineComponent({ props: ['current', 'pageSize', 'total'], template: '<nav data-pagination />' }),
  'a-drawer': defineComponent({ props: ['open'], template: '<section v-if="open" data-drawer><slot /></section>' }),
  'a-popconfirm': { template: '<div><slot /></div>' },
  'a-progress': { template: '<div />' },
  'a-modal': { template: '<div><slot /></div>' },
  'a-input': { template: '<input />' },
  'a-checkbox': { template: '<input type="checkbox" />' },
  'a-collapse': { template: '<div><slot /></div>' },
  'a-collapse-panel': { template: '<div><slot /></div>' },
  'a-result': { template: '<div />' },
}

const wrappers: VueWrapper[] = []
function mountWorkspace() {
  const wrapper = mount(KnowledgeView, { global: { stubs } })
  wrappers.push(wrapper)
  return wrapper
}

beforeEach(() => {
  window.sessionStorage.clear()
  vi.clearAllMocks()
  useKnowledgeReturnStore().clearAll()
  portalBox.user = { id: 'USER_STATE_DEMO' }
  routeBox.current = { path: '/hbos/knowledge/catalog', query: {} }
  api.status.mockResolvedValue({
    can_enter: true, can_search: true, gateway_configured: true, ask_enabled: true,
    environment: 'production', policy_revision: 'P1',
  })
  api.spaces.mockResolvedValue([{ space_id: 'DEPT_PRODUCTION', title: '生产部门资料', document_count: 3 }])
  api.documents.mockImplementation((query: string, space: string, page: number, size: number) =>
    Promise.resolve({ documents: [], total: 0, page, page_size: size }))
  api.activity.mockResolvedValue([])
  api.activityPage.mockResolvedValue({ items: [], page: 1, page_size: 6, has_more: false })
  api.feedback.mockResolvedValue([])
  api.feedbackPage.mockResolvedValue({ items: [], page: 1, page_size: 6, has_more: false })
})

afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()) })

describe('knowledge workspace across reloads and tab switches', () => {
  it('defaults the catalogue to 20 rows per page', async () => {
    const wrapper = mountWorkspace()
    await flushPromises()
    expect(api.documents).toHaveBeenCalledWith('', '', 1, 20, undefined, 'SOURCE_ROOT')
    expect(wrapper.text()).toContain('资料目录')
  })

  it('restores the catalogue filter, page and page size after a reload', async () => {
    saveWorkspace('USER_STATE_DEMO', {
      query: '未提交的问题', mode: 'ask', selectedSpace: '',
      catalogQuery: '合成标题', catalogPage: 3, catalogPageSize: 50,
      lawCategory: '', sourceFolder: 'SOURCE_ROOT', view: 'catalog', scrollTop: 0,
      positions: {},
    })
    mountWorkspace()
    await flushPromises()
    expect(api.documents).toHaveBeenCalledWith('合成标题', '', 3, 50, undefined, 'SOURCE_ROOT')
  })

  it('restores an unsubmitted question without ever calling the answer model', async () => {
    saveWorkspace('USER_STATE_DEMO', {
      query: '未提交的问题', mode: 'ask', selectedSpace: '',
      catalogQuery: '', catalogPage: 1, catalogPageSize: 20,
      lawCategory: '', sourceFolder: 'SOURCE_ROOT', view: 'query', scrollTop: 0,
      positions: {},
    })
    routeBox.current = { path: '/hbos/knowledge', query: {} }
    const wrapper = mountWorkspace()
    await flushPromises()
    expect((wrapper.find('#knowledge-query').element as HTMLTextAreaElement).value).toBe('未提交的问题')
    expect(api.ask).not.toHaveBeenCalled()
    expect(api.search).not.toHaveBeenCalled()
  })

  it('keeps each identity’s state separate and stores no content', async () => {
    saveWorkspace('USER_STATE_DEMO', {
      query: '这个问题只属于 A', mode: 'search', selectedSpace: 'DEPT_PRODUCTION',
      catalogQuery: '', catalogPage: 1, catalogPageSize: 20,
      lawCategory: '', sourceFolder: 'SOURCE_ROOT', view: 'query', scrollTop: 0,
      positions: {},
    })
    routeBox.current = { path: '/hbos/knowledge', query: {} }
    mountWorkspace()
    await flushPromises()
    portalBox.user = { id: 'USER_STATE_OTHER' }
    const other = mountWorkspace()
    await flushPromises()
    expect((other.find('#knowledge-query').element as HTMLTextAreaElement).value).toBe('')
    // The other identity gets its own (empty) state, never A's question.
    expect(loadWorkspace('USER_STATE_OTHER')?.query || '').toBe('')
    expect(api.ask).not.toHaveBeenCalled()
    // Nothing that would be content, a token or a document body is stored.
    const raw = window.sessionStorage.getItem('hbos.knowledge.workspace.v1:USER_STATE_DEMO') || ''
    expect(raw).not.toMatch(/hbos_mcp_|Bearer|excerpt|answer/i)
  })

  it('keeps the reading position per document and version', () => {
    const store = useKnowledgeReturnStore()
    store.rememberPosition('USER_STATE_DEMO', 'DOC_STATE_DEMO', 'VER_STATE_DEMO', { page: 7, zoom: 1.5, searchQuery: '' })
    // A fresh in-memory store re-reads the persisted position for this identity.
    const stored = JSON.parse(window.sessionStorage.getItem('hbos.knowledge.workspace.v1:USER_STATE_DEMO') || '{}')
    expect(stored.positions['DOC_STATE_DEMO::VER_STATE_DEMO']).toMatchObject({ page: 7, zoom: 1.5 })
    // A different identity gets nothing from the same tab.
    expect(useKnowledgeReturnStore().positionFor('USER_STATE_OTHER', 'DOC_STATE_DEMO', 'VER_STATE_DEMO')).toBeNull()
  })
})
