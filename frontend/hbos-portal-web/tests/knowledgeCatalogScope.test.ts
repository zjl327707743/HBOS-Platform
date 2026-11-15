import { portalSelectStub } from './portalSelectStub'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent } from 'vue'

import type { KnowledgeCatalogFilters } from '@/contracts/p1'
import { DomainApiError } from '@/services/p1Api'

const api = vi.hoisted(() => ({
  status: vi.fn(), spaces: vi.fn(), documents: vi.fn(), search: vi.fn(), resolve: vi.fn(),
  activity: vi.fn(), activityPage: vi.fn(), feedback: vi.fn(), feedbackPage: vi.fn(),
  ask: vi.fn(),
}))
vi.mock('@/services/p1Api', async importOriginal => ({
  ...(await importOriginal<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
  getKnowledgeSpaces: api.spaces,
  getKnowledgeEmployeeCatalogPage: api.documents,
  searchKnowledge: api.search,
  resolveKnowledgeEvidence: api.resolve,
  getKnowledgeActivity: api.activity,
  getKnowledgeActivityPage: api.activityPage,
  getKnowledgeFeedback: api.feedback,
  getKnowledgeFeedbackPage: api.feedbackPage,
  askKnowledgeReference: api.ask,
}))

const routeBox = vi.hoisted(() => ({ current: { path: '/hbos/knowledge/catalog', query: {} as Record<string, unknown> } }))
const routerBox = vi.hoisted(() => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => routeBox.current, useRouter: () => routerBox }))
const portalBox = vi.hoisted(() => ({ user: { id: 'USER_CATALOG_DEMO' } as { id: string } | null }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => portalBox }))

import KnowledgeView from '@/views/KnowledgeView.vue'
import { saveWorkspace } from '@/services/knowledgeWorkspace'
import { useKnowledgeReturnStore } from '@/stores/knowledgeReturn'

const SOP = 'FOLDER_3ea9623531f9c53c41813e42'
const WORKSHOP = 'FOLDER_86c492e2dfd0118334c7c9de'

const stubs = {
  // Declaring `emits` keeps the caller's @click from also landing on the root
  // element, so one click in the test is one click in the component.
  'a-button': defineComponent({
    emits: ['click'],
    template: '<button class="stub-button" @click="$emit(\'click\', $event)"><slot /></button>',
  }),
  'a-tag': { template: '<span><slot /></span>' },
  'a-alert': { props: ['message'], template: '<p>{{ message }}</p>' },
  'a-skeleton': { template: '<div data-loading />' },
  'a-empty': { props: ['description'], template: '<p data-empty>{{ description }}<slot /></p>' },
  'a-spin': { template: '<span />' },
  'a-tooltip': { template: '<span><slot /></span>' },
  'a-input-search': defineComponent({
    props: ['value'], emits: ['update:value', 'search'],
    template: '<input id="catalog-query" :value="value" @input="onInput" />',
    methods: { onInput(event: Event) { this.$emit('update:value', (event.target as HTMLInputElement).value) } },
  }),
  PortalSelect: portalSelectStub,
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
// The catalogue request is debounced by 200 ms so a burst of filter edits costs
// one request; the tests therefore wait past that debounce before asserting.
async function settle() {
  await new Promise(resolve => setTimeout(resolve, 260))
  await flushPromises()
}
// The catalogue is debounced by 200 ms and a SCOPE_REJECTED revalidation schedules a
// second read on that same timer. A fixed sleep can win the race against the timer under
// CPU contention (full-suite parallel run), so wait for the observable condition instead.
async function settleUntil(predicate: () => boolean, timeoutMs = 4000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    await flushPromises()
    if (predicate()) return
    await new Promise(resolve => setTimeout(resolve, 20))
  }
  throw new Error(`settleUntil: condition not met within ${timeoutMs}ms`)
}
function mountCatalog() {
  const wrapper = mount(KnowledgeView, { global: { stubs } })
  wrappers.push(wrapper)
  return wrapper
}

const doc = {
  document_id: 'DOC_SOP', title: '无菌车间SOP', space_id: 'DEPT_PRODUCTION', version_id: 'V1',
  source_directories: [['无菌车间', 'SOP']], file_formats: ['pdf'],
}
function serveCatalogue(documents = [doc], page = 1, pageSize = 20) {
  return { documents, total_documents: documents.length, page, page_size: pageSize,
    category_options: [{ category_id: WORKSHOP, path: ['无菌车间'] }, { category_id: SOP, path: ['无菌车间', 'SOP'] }],
    format_options: ['pdf'] }
}

beforeEach(() => {
  window.sessionStorage.clear()
  vi.clearAllMocks()
  useKnowledgeReturnStore().clearAll()
  portalBox.user = { id: 'USER_CATALOG_DEMO' }
  routeBox.current = { path: '/hbos/knowledge/catalog', query: {} }
  api.status.mockResolvedValue({
    can_enter: true, can_search: true, gateway_configured: true, ask_enabled: true,
    environment: 'production', policy_revision: 'P1',
  })
  api.spaces.mockResolvedValue([
    { space_id: 'DEPT_SAFETY', title: '安全部门', document_count: 334 },
    { space_id: 'DEPT_PRODUCTION', title: '生产部门', document_count: 302 },
  ])
  api.documents.mockImplementation((filters: KnowledgeCatalogFilters, page: number, size: number) =>
    Promise.resolve(serveCatalogue(filters.query === '不存在的标题' ? [] : [doc], page, size)))
  api.activity.mockResolvedValue([])
  api.activityPage.mockResolvedValue({ items: [], page: 1, page_size: 6, has_more: false })
  api.feedback.mockResolvedValue([])
  api.feedbackPage.mockResolvedValue({ items: [], page: 1, page_size: 6, has_more: false })
})

afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()) })

function lastFilters() {
  return api.documents.mock.calls.at(-1)![0]
}

describe('catalogue browsing range', () => {
  it('shares only the pending identical request when Enter and the debounce overlap', async () => {
    const wrapper = mountCatalog()
    await flushPromises()
    let resolve!: (value: ReturnType<typeof serveCatalogue>) => void
    api.documents.mockImplementation(() => new Promise(done => { resolve = done }))
    api.documents.mockClear()
    await wrapper.find('#catalog-query').setValue('精确文号')
    await settle()
    await wrapper.find('form.catalog-filter').trigger('submit')
    await wrapper.find('form.catalog-filter').trigger('submit')
    expect(api.documents).toHaveBeenCalledTimes(1)
    resolve(serveCatalogue())
    await flushPromises()
    // No response cache: the next employee action revalidates on the server.
    await wrapper.find('form.catalog-filter').trigger('submit')
    expect(api.documents).toHaveBeenCalledTimes(2)
    resolve(serveCatalogue())
    await flushPromises()
  })

  it('keeps a changed query independent and refuses the stale response', async () => {
    const wrapper = mountCatalog()
    await flushPromises()
    const replies: Array<(value: ReturnType<typeof serveCatalogue>) => void> = []
    api.documents.mockImplementation(() => new Promise(done => { replies.push(done) }))
    api.documents.mockClear()
    await wrapper.find('#catalog-query').setValue('旧查询')
    await settle()
    await wrapper.find('#catalog-query').setValue('新查询')
    await settle()
    expect(api.documents).toHaveBeenCalledTimes(2)
    replies[1]!(serveCatalogue([{ ...doc, document_id:'CURRENT', title:'新结果' }]))
    await flushPromises()
    replies[0]!(serveCatalogue([{ ...doc, document_id:'STALE', title:'旧结果' }]))
    await flushPromises()
    expect(wrapper.text()).toContain('新结果')
    expect(wrapper.text()).not.toContain('旧结果')
  })

  it('lists descendants under a parent and combines category, query and file type', async () => {
    const wrapper = mountCatalog()
    await flushPromises()
    const workshop = wrapper.findAll('.kb-catalog-categories button').find(button => button.text() === '无菌车间')!
    await workshop.trigger('click')
    await settle()
    expect(lastFilters()).toEqual({ category_ids: [WORKSHOP], query: '', format: null, sort: 'relevance' })
    expect(wrapper.findAll('.catalog-row')).toHaveLength(1)
    expect(wrapper.text()).toContain('找到 1 份资料')
    expect(wrapper.find('.kb-source-folders').exists()).toBe(false)
    await wrapper.get('#catalog-query').setValue('无菌')
    await wrapper.get('#catalog-format').setValue('pdf')
    await wrapper.get('#catalog-subcategory').setValue(SOP)
    await settle()
    expect(lastFilters()).toEqual({ category_ids: [SOP], query: '无菌', format: 'pdf', sort: 'relevance' })
    expect(wrapper.text()).toContain('已选 无菌车间 / SOP')
  })

  it('restores an original category without adding the ask department', async () => {
    saveWorkspace('USER_CATALOG_DEMO', {
      query: '', mode: 'ask', selectedSpace: 'DEPT_SAFETY',
      catalogQuery: '精确文号', catalogPage: 1, catalogPageSize: 20,
      sourceFolder: WORKSHOP, catalogFormat: 'pdf', catalogSort: 'title',
      view: 'catalog', scrollTop: 0, positions: {},
    })
    const wrapper = mountCatalog()
    await settle()
    expect(wrapper.find('#knowledge-space').exists()).toBe(false)
    expect(lastFilters()).toEqual({ category_ids: [WORKSHOP], query: '精确文号', format: 'pdf', sort: 'title' })
  })

  it('revalidates a stored category and resets a withdrawn range', async () => {
    saveWorkspace('USER_CATALOG_DEMO', {
      query: '', mode: 'ask', selectedSpace: '', catalogQuery: '',
      catalogPage: 1, catalogPageSize: 20, sourceFolder: WORKSHOP, view: 'catalog', scrollTop: 0, positions: {},
    })
    api.documents.mockRejectedValueOnce(new DomainApiError('SCOPE_REJECTED', '当前请求不可访问。'))
    const wrapper = mountCatalog()
    await settle()
    // First read carries the restored WORKSHOP category; SCOPE_REJECTED must trigger
    // a second read without it. Wait for that second read instead of assuming the
    // 200 ms debounce timer fired within a fixed 260 ms sleep.
    await settleUntil(() => api.documents.mock.calls.length >= 2 && lastFilters().category_ids.length === 0)
    expect(api.documents.mock.calls.length).toBeGreaterThanOrEqual(2)
    expect(lastFilters().category_ids).toEqual([])
    await settleUntil(() => wrapper.text().includes('找到 1 份资料'))
    expect(wrapper.text()).toContain('找到 1 份资料')
  })

  it('offers a way out of an empty filtered list', async () => {
    const wrapper = mountCatalog()
    await flushPromises()
    await wrapper.get('#catalog-query').setValue('不存在的标题')
    await settle()
    expect(wrapper.text()).toContain('当前条件没有匹配的资料')
    const clear = wrapper.findAll('button').find(button => button.text() === '清除筛选')!
    await clear.trigger('click')
    await settle()
    expect(lastFilters()).toEqual({ query: '', category_ids: [], format: null, sort: 'relevance' })
  })
})
