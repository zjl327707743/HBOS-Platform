import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent } from 'vue'

/**
 * Browsing the catalogue by original directory and by department.
 *
 * Owner saw a folder badge promise 208 documents while the list under it read
 * "0 份": the department filter stayed selected when the folder was entered, and
 * the two conditions had no document in common. These tests pin the rule the
 * portal now applies - one range at a time, with the stored/returned state
 * normalised so a reload or a reader return cannot bring the conflict back.
 */

const api = vi.hoisted(() => ({
  status: vi.fn(), spaces: vi.fn(), documents: vi.fn(), search: vi.fn(), resolve: vi.fn(),
  activity: vi.fn(), activityPage: vi.fn(), feedback: vi.fn(), feedbackPage: vi.fn(),
  ask: vi.fn(), model: vi.fn(),
}))
vi.mock('@/services/p1Api', async importOriginal => ({
  ...(await importOriginal<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
  getKnowledgeSpaces: api.spaces,
  getKnowledgeDocumentsPage: api.documents,
  searchKnowledge: api.search,
  resolveKnowledgeEvidence: api.resolve,
  getKnowledgeActivity: api.activity,
  getKnowledgeActivityPage: api.activityPage,
  getKnowledgeFeedback: api.feedback,
  getKnowledgeFeedbackPage: api.feedbackPage,
  askKnowledgeReference: api.ask,
  setKnowledgeModelPreference: api.model,
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
const TSD = 'FOLDER_ff4a691df9541af5d4be32a4'
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
function mountCatalog() {
  const wrapper = mount(KnowledgeView, { global: { stubs } })
  wrappers.push(wrapper)
  return wrapper
}

/** What the server answers for each (department, folder, query) combination. */
function serveCatalogue(space: string, folder: string) {
  const documents = {
    [`|${WORKSHOP}`]: [{ document_id: 'DOC_SOP', title: '无菌车间SOP', space_id: 'DEPT_PRODUCTION', version_id: 'V1' }],
    [`|${SOP}`]: [{ document_id: 'DOC_SOP', title: '无菌车间SOP', space_id: 'DEPT_PRODUCTION', version_id: 'V1' }],
  } as Record<string, Array<Record<string, unknown>>>
  const rows = documents[`${space}|${folder}`] || []
  const directory = folder === 'SOURCE_ROOT'
    ? { folder_id: 'SOURCE_ROOT', breadcrumbs: [], children: [{ folder_id: WORKSHOP, name: '无菌车间', count: 1 }] }
    : folder === WORKSHOP
      ? { folder_id: WORKSHOP, breadcrumbs: [{ folder_id: WORKSHOP, name: '无菌车间' }], children: [{ folder_id: SOP, name: 'SOP', count: 1 }] }
      : { folder_id: SOP, breadcrumbs: [{ folder_id: WORKSHOP, name: '无菌车间' }, { folder_id: SOP, name: 'SOP' }], children: [] }
  return { documents: rows, total: rows.length, page: 1, page_size: 20, source_directory: directory }
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
  api.documents.mockImplementation((_query: string, space: string, _page: number, size: number, _law?: string, folder = 'SOURCE_ROOT') => {
    const value = serveCatalogue(space, folder)
    return Promise.resolve({ ...value, page_size: size })
  })
  api.activity.mockResolvedValue([])
  api.activityPage.mockResolvedValue({ items: [], page: 1, page_size: 6, has_more: false })
  api.feedback.mockResolvedValue([])
  api.feedbackPage.mockResolvedValue({ items: [], page: 1, page_size: 6, has_more: false })
})

afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()) })

function lastCall() {
  const call = api.documents.mock.calls.at(-1)!
  return { query: call[0], space: call[1], page: call[2], size: call[3], law: call[4], folder: call[5] }
}

describe('catalogue browsing range', () => {
  it('entering an original directory drops the department filter instead of showing 0', async () => {
    const wrapper = mountCatalog()
    await flushPromises()
    // The employee picks 安全部门 first, as in the Owner screenshot.
    await wrapper.find('#catalog-department').setValue('DEPT_SAFETY')
    await settle()
    expect(lastCall()).toMatchObject({ space: 'DEPT_SAFETY', folder: 'SOURCE_ROOT' })

    // Then enters 无菌车间: the department must not travel with the directory.
    const folderButton = wrapper.findAll('.kb-source-folders button').find(button => button.text().includes('无菌车间'))!
    await folderButton.trigger('click')
    await settle()

    const call = lastCall()
    expect(call.folder).toBe(WORKSHOP)
    expect(call.space).toBe('')
    expect(call.query).toBe('')
    expect(wrapper.text()).toContain('已切换到原目录浏览')
    expect(wrapper.text()).not.toContain('0 份资料')
  })

  it('opening a child folder of the original directory keeps the same range', async () => {
    const wrapper = mountCatalog()
    await flushPromises()
    await wrapper.find('#catalog-department').setValue('DEPT_SAFETY')
    await settle()
    const workshop = wrapper.findAll('.kb-source-folders button').find(button => button.text().includes('无菌车间'))!
    await workshop.trigger('click')
    await settle()
    const sop = wrapper.findAll('.kb-source-folders button').find(button => button.text().includes('SOP'))!
    await sop.trigger('click')
    await settle()

    expect(lastCall()).toMatchObject({ folder: SOP, space: '' })
    expect(wrapper.text()).toContain('1 份资料')
  })

  it('choosing a department again leaves the directory for the root', async () => {
    const wrapper = mountCatalog()
    await flushPromises()
    const workshop = wrapper.findAll('.kb-source-folders button').find(button => button.text().includes('无菌车间'))!
    await workshop.trigger('click')
    await flushPromises()
    await wrapper.find('#catalog-department').setValue('DEPT_SAFETY')
    await settle()

    expect(lastCall()).toMatchObject({ space: 'DEPT_SAFETY', folder: 'SOURCE_ROOT' })
    expect(wrapper.text()).toContain('已按部门筛选')
  })

  it('a stored department next to a stored directory is normalised on reload', async () => {
    saveWorkspace('USER_CATALOG_DEMO', {
      query: '', mode: 'ask', selectedSpace: 'DEPT_SAFETY',
      catalogQuery: '残留关键词', catalogPage: 2, catalogPageSize: 20,
      lawCategory: '', sourceFolder: WORKSHOP, view: 'catalog', scrollTop: 0,
      positions: {},
    })
    mountCatalog()
    await settle()

    expect(lastCall()).toMatchObject({ space: '', folder: WORKSHOP, query: '' })
    expect(api.documents.mock.calls.some((call: unknown[]) => call[1] === 'DEPT_SAFETY' && call[5] === WORKSHOP)).toBe(false)
  })

  it('offers a way out of an empty filtered list', async () => {
    const wrapper = mountCatalog()
    await flushPromises()
    api.documents.mockImplementation((_query: string, _space: string, _page: number, size: number) =>
      Promise.resolve({ documents: [], total: 0, page: 1, page_size: size }))
    await wrapper.find('#catalog-query').setValue('不存在的标题')
    await settle()

    expect(wrapper.text()).toContain('当前条件没有匹配的资料')
    const clear = wrapper.findAll('button').find(button => button.text().includes('清除全部筛选'))!
    await clear.trigger('click')
    await settle()
    expect(lastCall()).toMatchObject({ query: '', space: '', folder: 'SOURCE_ROOT' })
  })
})
