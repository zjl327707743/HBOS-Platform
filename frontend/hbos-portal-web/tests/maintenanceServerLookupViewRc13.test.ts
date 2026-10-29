import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent } from 'vue'

const api = vi.hoisted(() => ({
  status: vi.fn(), dashboard: vi.fn(), feedback: vi.fn(), action: vi.fn(),
}))
vi.mock('@/services/p1Api', async original => ({
  ...(await original<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
}))
vi.mock('@/services/knowledgeMaintenanceApi', async original => ({
  ...(await original<typeof import('@/services/knowledgeMaintenanceApi')>()),
  getMaintenance: api.dashboard,
  getMaintenanceFeedbackPage: api.feedback,
  maintenanceAction: api.action,
}))
const routeBox = vi.hoisted(() => ({ current: { path: '/hbos/knowledge/maintenance' } }))
const routerBox = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => routeBox.current, useRouter: () => routerBox }))

import MaintenanceView from '@/views/KnowledgeMaintenanceView.vue'

const DOCUMENT = 'DOC_' + 'f'.repeat(24)
const VERSION = 'VER_' + 'f'.repeat(24)
const BATCH_ID = 'IMP_' + '4'.repeat(32)
const target = {
  document_id: DOCUMENT, version_id: VERSION, current_version: VERSION,
  title: 'ZZZ 目标资料：道路交叉口设计', document_number: 'GB-WP6-001', department: 'production',
}
const other = {
  document_id: 'DOC_' + '1'.repeat(24), version_id: 'VER_' + '1'.repeat(24), current_version: 'VER_' + '1'.repeat(24),
  title: '合成现有资料', document_number: 'NO-0001', department: 'production',
}
const detailItem = {
  ...target, filename: '目标资料.pdf', sha256: 'a'.repeat(64), relationship: 'NEW', expected_version: null,
  parse_status: 'parsed/indexed', progress: 1, chunk_count: 8, quality_status: 'Passed',
  shared_approved: true, quality_note: '', current_version: VERSION, publication_status: 'Published',
}
const selectedBatch = (page = 3) => ({
  batch_id: BATCH_ID, label: '批次0400', department: 'production', status: 'Published', last_error: null,
  items: [detailItem], total: 1, page, page_size: 12, counts: { parsed: 1, failed: 0, quality_passed: 1 },
})

function dashboard(overrides: Record<string, unknown> = {}) {
  return {
    departments: [{ key: 'production', title: '生产部' }],
    published_documents: [other],
    published_total: 1031, published_matched: 1031, published_truncated: true,
    published_page: 1, published_page_size: 1000, published_has_more: true,
    batches: [], batches_total: 538, batches_matched: 538,
    batches_page: 1, batches_page_size: 100, batches_has_more: true, batch_scan_truncated: false,
    selected: null, feedback: { items: [] },
    import_availability: { can_parse: true, can_batch: true, configured: true, blocked: false },
    ...overrides,
  }
}

const InputSearch = defineComponent({
  props: { value: String, placeholder: String },
  emits: ['update:value', 'search'],
  template: '<input :value="value" :placeholder="placeholder" @input="$emit(\'update:value\', $event.target.value)" @keydown.enter="$emit(\'search\')" />',
})
const Button = defineComponent({
  props: ['disabled', 'loading'],
  emits: ['click'],
  template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot/></button>',
})
const Select = defineComponent({
  props: ['value', 'options', 'disabled', 'placeholder'],
  emits: ['update:value', 'change'],
  template: '<select :value="value" @change="$emit(\'change\', $event.target.value)"><option v-for="option in options || []" :key="option.value" :value="option.value">{{ option.label }}</option></select>',
})
const Alert = defineComponent({ props: ['message'], template: '<div class="alert">{{ message }}</div>' })
const Drawer = defineComponent({ props: ['open', 'title'], emits: ['close'], template: '<section v-if="open" data-drawer><slot /></section>' })
const Panel = defineComponent({ template: '<div><slot /></div>' })
const Empty = defineComponent({ props: ['description'], template: '<p class="empty">{{ description }}</p>' })
const Tag = defineComponent({ template: '<span class="tag"><slot /></span>' })
const stubs = {
  'a-input-search': InputSearch,
  'a-button': Button,
  'a-select': Select,
  'a-alert': Alert,
  'a-drawer': Drawer,
  'a-collapse': Panel,
  'a-collapse-panel': Panel,
  'a-popconfirm': Panel,
  'a-empty': Empty,
  'a-tag': Tag,
  'a-input': true,
  'a-textarea': true,
  'a-checkbox': true,
  'a-checkbox-group': true,
  'a-skeleton': true,
  'a-result': true,
  'a-pagination': true,
  'a-progress': true,
  'a-steps': true,
  'a-modal': true,
}

const wrappers: VueWrapper[] = []
async function mountView(path = '/hbos/knowledge/maintenance') {
  routeBox.current.path = path
  const wrapper = mount(MaintenanceView, { global: { stubs } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}
function searchInputs(wrapper: VueWrapper) {
  return wrapper.findAllComponents(InputSearch)
}
async function setSearchInput(wrapper: VueWrapper, index: number, value: string) {
  const input = searchInputs(wrapper)[index]
  if (!input) throw new Error(`missing input ${index}`)
  await input.find('input').setValue(value)
}
afterEach(() => {
  wrappers.splice(0).forEach(wrapper => { try { wrapper.unmount() } catch { /* already unmounted */ } })
})

beforeEach(() => {
  vi.clearAllMocks()
  routeBox.current.path = '/hbos/knowledge/maintenance'
  api.status.mockResolvedValue({ can_maintain: true })
  api.dashboard.mockImplementation((batch?: string) => Promise.resolve(batch ? dashboard({ selected: selectedBatch() }) : dashboard()))
  api.feedback.mockImplementation((page: number) => Promise.resolve({ items: [], page, page_size: 6, has_more: false }))
})

describe('published projection default stays the legacy bounded window', () => {
  it('reads once with the legacy call shape and reports total/truncated/page', async () => {
    const wrapper = await mountView()
    expect(api.dashboard).toHaveBeenCalledTimes(1)
    expect(api.dashboard.mock.calls[0]).toEqual([undefined, 1])
    expect(wrapper.find('.kb-status-filters').text()).toContain('已发布 1031')
    const projection = wrapper.find('[data-published-projection]').text()
    expect(projection).toContain('当前显示 1 份')
    expect(projection).toContain('第 1 页')
    expect(projection).toContain('服务端仅投影前 1000 份')
    expect(wrapper.text()).toContain('合成现有资料')
    // The existing client-side filter box is still present when no server lookup is active.
    expect(wrapper.find('input[placeholder="查找已加载资料标题"]').exists()).toBe(true)
  })
})

describe('published server-side search and pagination (WP6)', () => {
  it('refuses an empty server search without calling the API', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    await wrapper.find('[data-published-search]').trigger('click')
    await flushPromises()
    expect(api.dashboard).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请输入标题、文号、部门，或精确文档 ID')
  })

  it('searches by title on the server and shows a document outside the first projection', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [target], published_matched: 1, published_truncated: false,
      published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setSearchInput(wrapper, 0, '目标资料')
    await wrapper.find('[data-published-search]').trigger('click')
    await flushPromises()

    expect(api.dashboard).toHaveBeenLastCalledWith(undefined, 1, undefined, {
      published_query: '目标资料', published_page: 1, published_page_size: 50,
    })
    expect(wrapper.text()).toContain('ZZZ 目标资料：道路交叉口设计')
    expect(wrapper.find('[data-published-lookup-meta]').text()).toContain('服务端匹配 1 份 / 共 1031 份')
    expect(wrapper.find('[data-published-lookup-meta]').text()).toContain('第 1 页')
  })

  it('locates by exact document id and forwards published_document_id', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [target], published_matched: 1, published_truncated: false,
      published_lookup_state: 'FOUND', published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setSearchInput(wrapper, 0, DOCUMENT)
    await wrapper.find('[data-published-search]').trigger('click')
    await flushPromises()
    expect(api.dashboard).toHaveBeenLastCalledWith(undefined, 1, undefined, {
      published_document_id: DOCUMENT, published_page: 1, published_page_size: 50,
    })
    expect(wrapper.text()).toContain('ZZZ 目标资料')
  })

  it('reports NOT_FOUND for an unknown exact document id', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [], published_matched: 0, published_truncated: false,
      published_lookup_state: 'NOT_FOUND', published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setSearchInput(wrapper, 0, 'DOC_' + '9'.repeat(24))
    await wrapper.find('[data-published-search]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-published-not-found]').text()).toContain('没有找到该文档 ID 对应的已发布资料')
  })

  it('pages through server results without loading the whole corpus', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [target], published_matched: 120, published_truncated: true,
      published_page: 1, published_page_size: 50, published_has_more: true,
    }))
    await setSearchInput(wrapper, 0, '目标')
    await wrapper.find('[data-published-search]').trigger('click')
    await flushPromises()

    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [{ ...other, title: '第二页资料' }], published_matched: 120, published_truncated: true,
      published_page: 2, published_page_size: 50, published_has_more: false,
    }))
    await wrapper.find('[data-published-next]').trigger('click')
    await flushPromises()
    expect(api.dashboard).toHaveBeenLastCalledWith(undefined, 1, undefined, {
      published_query: '目标', published_page: 2, published_page_size: 50,
    })
    expect(wrapper.find('[data-published-lookup-meta]').text()).toContain('第 2 页')
    expect(wrapper.text()).toContain('第二页资料')
    expect(wrapper.find('[data-published-next]').attributes('disabled')).toBeDefined()
  })

  it('opens a document found beyond the projection via batch_document_id + batch_id/locate', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [target], published_matched: 1, published_truncated: false,
      published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setSearchInput(wrapper, 0, '目标资料')
    await wrapper.find('[data-published-search]').trigger('click')
    await flushPromises()

    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      batches: [{ name: BATCH_ID, label: '批次0400', department_key: 'production', status: 'Published', document_page: 3 }],
      batches_matched: 1, batches_page: 1, batches_page_size: 100, batches_has_more: false,
      batch_lookup_state: 'FOUND',
    }))
    api.dashboard.mockResolvedValueOnce(dashboard({ selected: selectedBatch(3) }))
    await wrapper.findAll('button').find(button => button.text() === '查看资料')!.trigger('click')
    await flushPromises()

    expect(api.dashboard.mock.calls[0]).toEqual([undefined, 1, undefined, {
      batch_document_id: DOCUMENT, batch_page: 1, batch_page_size: 100,
    }])
    expect(api.dashboard.mock.calls[1]).toEqual([BATCH_ID, 3, DOCUMENT])
    expect(wrapper.find('[data-drawer]').text()).toContain('质量已核对')
    expect(wrapper.find('[data-drawer]').text()).not.toContain('未找到该资料对应的处理批次')
  })

  it('reports the batch NOT_FOUND state instead of claiming a readable batch', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [target], published_matched: 1, published_truncated: false,
      published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setSearchInput(wrapper, 0, DOCUMENT)
    await wrapper.find('[data-published-search]').trigger('click')
    await flushPromises()

    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      batches: [], batches_matched: 0, batch_lookup_state: 'NOT_FOUND',
      batches_page: 1, batches_page_size: 100, batches_has_more: false,
    }))
    await wrapper.findAll('button').find(button => button.text() === '查看资料')!.trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-detail-lookup-not-found]').text()).toContain('服务端未找到该资料对应的处理批次')
    expect(wrapper.text()).toContain('当前版本可由员工查阅')
  })
})

describe('batch selector server-side search, pagination and locate', () => {
  it('searches batches on the server and offers a match outside the first 100', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      batches: [{ name: BATCH_ID, label: '批次0400', department_key: 'production', status: 'Published' }],
      batches_matched: 1, batches_page: 1, batches_page_size: 100, batches_has_more: false,
      batch_scan_truncated: true,
    }))
    await setSearchInput(wrapper, 2, '批次0400')
    await wrapper.find('[data-batch-search]').trigger('click')
    await flushPromises()

    expect(api.dashboard).toHaveBeenLastCalledWith(undefined, 1, undefined, {
      batch_query: '批次0400', batch_page: 1, batch_page_size: 100,
    })
    expect(wrapper.find('[data-batch-meta]').text()).toContain('服务端匹配 1 个')
    expect(wrapper.find('[data-batch-meta]').text()).toContain('服务端仅扫描前 1000 个批次')
    expect(wrapper.text()).toContain('批次0400')
  })

  it('locates an old batch by document id and enters batch_id + locate detail', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      batches: [{ name: BATCH_ID, label: '批次0400', department_key: 'production', status: 'Published', document_page: 2 }],
      batches_matched: 1, batches_page: 1, batches_page_size: 100, batches_has_more: false,
      batch_lookup_state: 'FOUND',
    }))
    api.dashboard.mockResolvedValueOnce(dashboard({ selected: selectedBatch(2) }))
    await setSearchInput(wrapper, 2, DOCUMENT)
    await wrapper.find('[data-batch-locate]').trigger('click')
    await flushPromises()

    expect(api.dashboard.mock.calls[0]).toEqual([undefined, 1, undefined, {
      batch_document_id: DOCUMENT, batch_page: 1, batch_page_size: 100,
    }])
    expect(api.dashboard.mock.calls[1]).toEqual([BATCH_ID, 2, DOCUMENT])
    expect(wrapper.text()).toContain('解析完成')
    expect(wrapper.find('[data-batch-not-found]').exists()).toBe(false)
  })

  it('reports NOT_FOUND when no batch contains the document', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      batches: [], batches_matched: 0, batch_lookup_state: 'NOT_FOUND',
      batches_page: 1, batches_page_size: 100, batches_has_more: false,
    }))
    await setSearchInput(wrapper, 2, 'DOC_' + '9'.repeat(24))
    await wrapper.find('[data-batch-locate]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-batch-not-found]').text()).toContain('没有找到包含该文档的处理批次')
  })

  it('pages the default batch projection on the server without a query', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-batch-default-next]').exists()).toBe(true)
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      batches: [{ name: BATCH_ID, label: '批次0100', department_key: 'production', status: 'Published' }],
      batches_matched: 538, batches_page: 2, batches_page_size: 100, batches_has_more: true,
    }))
    await wrapper.find('[data-batch-default-next]').trigger('click')
    await flushPromises()
    expect(api.dashboard).toHaveBeenLastCalledWith(undefined, 1, undefined, {
      batch_page: 2, batch_page_size: 100,
    })
    expect(wrapper.find('[data-batch-meta]').text()).toContain('第 2 页')
    expect(wrapper.text()).toContain('批次0100')
  })

  it('pages batch results with the server page param', async () => {
    const wrapper = await mountView()
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      batches: [{ name: BATCH_ID, label: '批次0400', department_key: 'production', status: 'Published' }],
      batches_matched: 140, batches_page: 1, batches_page_size: 100, batches_has_more: true,
    }))
    await setSearchInput(wrapper, 2, '批次')
    await wrapper.find('[data-batch-search]').trigger('click')
    await flushPromises()
    api.dashboard.mockResolvedValueOnce(dashboard({
      batches: [{ name: 'IMP_' + '5'.repeat(32), label: '批次0500', department_key: 'production', status: 'Published' }],
      batches_matched: 140, batches_page: 2, batches_page_size: 100, batches_has_more: false,
    }))
    await wrapper.find('[data-batch-next]').trigger('click')
    await flushPromises()
    expect(api.dashboard).toHaveBeenLastCalledWith(undefined, 1, undefined, {
      batch_query: '批次', batch_page: 2, batch_page_size: 100,
    })
    expect(wrapper.text()).toContain('批次0500')
  })
})

describe('upload version-relation selector can use the server lookup', () => {
  it('adds a search hit outside the first projection to the replacement options and selects it', async () => {
    const wrapper = await mountView('/hbos/knowledge/maintenance/upload')
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [target], published_matched: 1, published_truncated: false,
      published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setSearchInput(wrapper, 0, '目标资料')
    await wrapper.find('[data-replacement-search]').trigger('click')
    await flushPromises()

    expect(api.dashboard).toHaveBeenLastCalledWith(undefined, 1, undefined, {
      published_query: '目标资料', published_page: 1, published_page_size: 50,
    })
    expect(wrapper.find('[data-replacement-hint]').text()).toContain('已加入上方“版本关系”选项')
    expect(wrapper.text()).toContain('替换：ZZZ 目标资料：道路交叉口设计')

    const selects = wrapper.findAllComponents(Select)
    const versionSelect = selects[selects.length - 1]!
    versionSelect.vm.$emit('change', DOCUMENT)
    await flushPromises()
    expect(wrapper.findAllComponents(Select).at(-1)!.props('value')).toBe(DOCUMENT)
  })

  it('selects the replacement directly for an exact document-id lookup', async () => {
    const wrapper = await mountView('/hbos/knowledge/maintenance/upload')
    api.dashboard.mockClear()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [target], published_matched: 1, published_truncated: false,
      published_lookup_state: 'FOUND', published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setSearchInput(wrapper, 0, DOCUMENT)
    await wrapper.find('[data-replacement-search]').trigger('click')
    await flushPromises()
    expect(api.dashboard).toHaveBeenLastCalledWith(undefined, 1, undefined, {
      published_document_id: DOCUMENT, published_page: 1, published_page_size: 50,
    })
    expect(wrapper.findAllComponents(Select).at(-1)!.props('value')).toBe(DOCUMENT)
  })
})
