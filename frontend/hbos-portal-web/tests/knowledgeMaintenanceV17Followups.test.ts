import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent } from 'vue'

// B-owned regression coverage for the two Main-registered v1.7 follow-ups:
// B-UI-FU-1 bounded-projection truncation disclosure on the v17 manage view
// (old contract: versions-view [data-published-projection]);
// B-UI-FU-2 explicit exact-id NOT_FOUND message on the v17 manage view
// (old contract: versions-view [data-published-not-found]) plus a distinct
// no-match hint for empty title searches (old contract: [data-published-empty]).
const api = vi.hoisted(() => ({ status: vi.fn(), dashboard: vi.fn(), feedback: vi.fn(), action: vi.fn(), lineage: vi.fn() }))
vi.mock('@/services/p1Api', async original => ({
  ...(await original<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
}))
vi.mock('@/services/knowledgeMaintenanceApi', async original => ({
  ...(await original<typeof import('@/services/knowledgeMaintenanceApi')>()),
  getMaintenance: api.dashboard,
  getMaintenanceFeedbackPage: api.feedback,
  getVersionLineage: api.lineage,
  maintenanceAction: api.action,
}))
const routeBox = vi.hoisted(() => ({ current: { path: '/hbos/knowledge/maintenance' } }))
const routerBox = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => routeBox.current, useRouter: () => routerBox }))

import MaintenanceView from '@/views/KnowledgeMaintenanceView.vue'
import { DomainApiError } from '@/services/p1Api'

const row = {
  document_id: 'DOC_' + '1'.repeat(24), version_id: 'VER_' + '1'.repeat(24),
  current_version: 'VER_' + '1'.repeat(24), title: '合成现有资料', document_number: 'NO-0001', department: 'production',
}
function dashboard(overrides: Record<string, unknown> = {}) {
  return {
    departments: [{ key: 'production', title: '生产部' }],
    published_documents: [row], published_total: 1103, published_matched: 1103,
    published_truncated: true, published_page: 1, published_page_size: 1000, published_has_more: false,
    overview: { published_total: 1103, pending_quality_check: 0, sharing_pending: 0, feedback_pending: 12 },
    batches: [], selected: null, feedback: { items: [] },
    import_availability: { can_parse: true, can_batch: true, configured: true, blocked: false },
    ...overrides,
  }
}

const Button = defineComponent({
  props: ['disabled', 'loading'],
  emits: ['click'],
  template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
})
const Alert = defineComponent({ props: ['message'], template: '<div class="alert" role="alert">{{ message }}</div>' })
const Tag = defineComponent({ template: '<span class="tag"><slot /></span>' })
const Result = defineComponent({ props: ['title', 'subTitle', 'status'], template: '<div class="result">{{ title }} {{ subTitle }}</div>' })
const InputSearch = defineComponent({
  props: ['value', 'placeholder', 'disabled', 'maxlength'],
  emits: ['update:value', 'search'],
  template: '<input :value="value" :placeholder="placeholder" :disabled="disabled" @input="$emit(\'update:value\', $event.target.value)" @keydown.enter="$emit(\'search\')" />',
})
const Drawer = defineComponent({ props: ['open', 'title'], emits: ['close'], template: '<section v-if="open" data-drawer><slot /></section>' })
const stubs = {
  'a-button': Button, 'a-alert': Alert, 'a-tag': Tag, 'a-drawer': Drawer, 'a-input-search': InputSearch,
  'a-select': true, 'a-input': true, 'a-textarea': true, 'a-checkbox': true, 'a-checkbox-group': true,
  'a-skeleton': true, 'a-result': Result, 'a-popconfirm': true, 'a-collapse': true, 'a-collapse-panel': true,
  'a-pagination': true, 'a-progress': true, 'a-steps': true, 'a-empty': true,
}

const wrappers: VueWrapper[] = []
async function mountView(path = '/hbos/knowledge/maintenance') {
  routeBox.current.path = path
  const wrapper = mount(MaintenanceView, { global: { stubs } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}
async function setPublishedSearch(wrapper: VueWrapper, value: string) {
  await wrapper.get('form.v17-filters input[aria-label="服务端查找资料"]').setValue(value)
}
async function submitPublishedSearch(wrapper: VueWrapper) {
  await wrapper.get('form.v17-filters').trigger('submit')
  await flushPromises()
}
function clearSearchButton(wrapper: VueWrapper) {
  return wrapper.findAll('form.v17-filters button').find(button => button.text() === '清除搜索')!
}
afterEach(() => {
  wrappers.splice(0).forEach(wrapper => { try { wrapper.unmount() } catch { /* already unmounted */ } })
})
beforeEach(() => {
  vi.clearAllMocks()
  routeBox.current.path = '/hbos/knowledge/maintenance'
  api.status.mockResolvedValue({ can_maintain: true })
  api.dashboard.mockResolvedValue(dashboard())
  api.lineage.mockResolvedValue({ document_id: row.document_id, current_version: row.current_version, total: 2, page: 1, page_size: 12, has_more: false, versions: [
    { version_id: row.version_id, enabled: true, created_at: '2026-11-10T00:00:00Z', source_hash: 'synthetic-sha', publication_state: 'PUBLISHED', quality_state: 'VERIFIED', rollback_eligible: false, superseded_by: null, supersedes: null },
  ] })
  api.feedback.mockImplementation((page: number) => Promise.resolve({ items: [], page, page_size: 6, has_more: false }))
})

describe('B-UI-FU-1: bounded-projection truncation disclosure on the v17 manage view', () => {
  it('discloses the 1000-document server projection without breaking the v17 list', async () => {
    const wrapper = await mountView()
    const disclosure = wrapper.get('[data-v17-published-projection]')
    expect(disclosure.text()).toContain('服务端仅投影前 1000 份')
    expect(disclosure.text()).toContain('可在上方搜索定位')
    // The disclosure must not replace the list summary added by the v17 layout.
    expect(wrapper.get('.v17-pagination').text()).toContain('已加载 1 份')
    expect(wrapper.get('.v17-table-wrap').text()).toContain('合成现有资料')
  })

  it('hides the truncation disclosure when the projection is complete', async () => {
    api.dashboard.mockResolvedValue(dashboard({ published_truncated: false }))
    const wrapper = await mountView()
    expect(wrapper.find('[data-v17-published-projection]').exists()).toBe(false)
    expect(wrapper.get('.v17-pagination').text()).toContain('已加载 1 份')
  })

  it('hides the truncation disclosure during a server lookup and restores it after clearing', async () => {
    const wrapper = await mountView()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [{ ...row, title: '服务端命中资料' }], published_matched: 1, published_truncated: false,
      published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setPublishedSearch(wrapper, '合成资料')
    await submitPublishedSearch(wrapper)
    expect(wrapper.find('[data-v17-published-projection]').exists()).toBe(false)
    await clearSearchButton(wrapper).trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-v17-published-projection]').text()).toContain('服务端仅投影前 1000 份')
  })
})

describe('B-UI-FU-2: exact-document-id NOT_FOUND on the v17 manage view', () => {
  it('reports an explicit exact-id NOT_FOUND instead of the generic empty state', async () => {
    const wrapper = await mountView()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [], published_matched: 0, published_truncated: false,
      published_lookup_state: 'NOT_FOUND', published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setPublishedSearch(wrapper, 'DOC_' + '9'.repeat(24))
    await submitPublishedSearch(wrapper)
    expect(wrapper.get('[data-v17-published-not-found]').text()).toContain('没有找到该文档 ID 对应的已发布资料')
    expect(wrapper.text()).toContain('请核对文档标识，或改用标题/文号搜索')
    expect(wrapper.findAll('.v17-table-wrap tbody tr')).toHaveLength(0)
    // The generic empty state must not be shown when the id was explicitly not found.
    expect(wrapper.text()).not.toContain('当前范围没有资料')
    expect(wrapper.find('[data-v17-published-empty]').exists()).toBe(false)
  })

  it('shows a no-match hint (not the generic empty state) for an empty title search', async () => {
    const wrapper = await mountView()
    api.dashboard.mockResolvedValueOnce(dashboard({
      published_documents: [], published_matched: 0, published_truncated: false,
      published_page: 1, published_page_size: 50, published_has_more: false,
    }))
    await setPublishedSearch(wrapper, '不存在的标题')
    await submitPublishedSearch(wrapper)
    expect(wrapper.get('[data-v17-published-empty]').text()).toContain('没有匹配的已发布资料')
    expect(wrapper.find('[data-v17-published-not-found]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('当前范围没有资料')
  })

  it('keeps the generic empty state before any server lookup', async () => {
    api.dashboard.mockResolvedValue(dashboard({ published_documents: [], published_truncated: false }))
    const wrapper = await mountView()
    expect(wrapper.text()).toContain('当前范围没有资料')
    expect(wrapper.find('[data-v17-published-not-found]').exists()).toBe(false)
    expect(wrapper.find('[data-v17-published-empty]').exists()).toBe(false)
  })
})

describe('MC-1: live overview statistics', () => {
  it('renders the server overview values in all four cards', async () => {
    const wrapper = await mountView()
    const cards = wrapper.findAll('.v17-stat')
    expect(cards).toHaveLength(4)
    expect(cards[0].text()).toContain('当前已发布')
    expect(cards[0].text()).toContain('1103')
    expect(cards[1].text()).toContain('待质量核对')
    expect(cards[1].text()).toContain('0')
    expect(cards[2].text()).toContain('共享待确认')
    expect(cards[2].text()).toContain('0')
    expect(cards[3].text()).toContain('员工反馈')
    expect(cards[3].text()).toContain('12')
    expect(wrapper.text()).not.toContain('服务端未提供')
  })

  it('keeps an explicit fallback when the overview field is absent (old candidate)', async () => {
    api.dashboard.mockResolvedValueOnce(dashboard({ overview: undefined }))
    const wrapper = await mountView()
    const cards = wrapper.findAll('.v17-stat')
    for (const index of [1, 2, 3]) {
      expect(cards[index].text()).toContain('-')
      expect(cards[index].text()).toContain('服务端未提供')
    }
  })
})

describe('MC-3: live version lineage', () => {
  it('renders lineage from get_version_lineage on the versions view and drops the old placeholder', async () => {
    const wrapper = await mountView('/hbos/knowledge/maintenance/versions')
    await flushPromises()
    expect(api.lineage).toHaveBeenCalledWith(row.document_id)
    const list = wrapper.get('[data-v17-lineage-list]')
    expect(list.text()).toContain(row.version_id)
    expect(list.text()).toContain('PUBLISHED')
    expect(wrapper.find('[data-v17-lineage-unavailable]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('该候选暂未提供版本沿革接口')
    expect(wrapper.get('[data-v17-lineage-meta]').text()).toContain('共 2 个版本')
    // v1.7 fidelity: versions list keeps the same panel heading rhythm as manage
    expect(wrapper.text()).toContain('版本档案')
    expect(wrapper.text()).toContain('版本沿革与回滚候选')
  })

  it('shows an explicit unavailable state on a genuine lineage denial, without the old candidate placeholder', async () => {
    api.lineage.mockRejectedValueOnce(new DomainApiError('SCOPE_REJECTED', '当前请求不可访问。'))
    const wrapper = await mountView('/hbos/knowledge/maintenance/versions')
    await flushPromises()
    const notice = wrapper.get('[data-v17-lineage-unavailable]')
    expect(notice.text()).toContain('无权查看该资料的版本沿革')
    expect(wrapper.text()).not.toContain('该候选暂未提供版本沿革接口')
    expect(wrapper.find('[data-v17-lineage-list]').exists()).toBe(false)
  })
})

describe('P09: bounded server content search', () => {
  it('enables the free-text box, sends the term to the server, and never scans the queue client-side', async () => {
    const wrapper = await mountView('/hbos/knowledge/maintenance/feedback')
    const search = wrapper.get('input[aria-label="搜索员工反馈"]')
    expect(search.attributes('disabled')).toBeUndefined()
    expect(wrapper.find('[data-v17-feedback-search-limitation]').exists()).toBe(false)
    // Initial load: one bounded page + status only.
    expect(api.feedback).toHaveBeenCalledWith(1, '', '')
    // The term is filtered by the server; page resets to 1 and no extra client scan exists.
    await search.setValue('清洁验证')
    await search.trigger('keydown.enter')
    await flushPromises()
    expect(api.feedback).toHaveBeenLastCalledWith(1, '', '清洁验证')
    for (const call of api.feedback.mock.calls) expect(call.length).toBeLessThanOrEqual(3)
    // v1.7 fidelity: feedback queue uses the same v17 panel heading rhythm as manage.
    const heading = wrapper.get('.kb-staff-feedback-heading')
    expect(heading.text()).toContain('反馈清单')
    expect(heading.text()).toContain('刷新反馈')
    expect(wrapper.get('.kb-heading').text()).toContain('集中核对资料问题，让反馈有清楚的处理结果。')
    expect(wrapper.find('.kb-heading .v17-add').exists()).toBe(false)
  })

  it('keeps an honest limitation fallback when the candidate has no search parameter', async () => {
    api.feedback.mockImplementation((page: number, status: string, query: string) => {
      if (query) return Promise.reject(new DomainApiError('INVALID_REQUEST', '合成旧候选没有 query。'))
      return Promise.resolve({ items: [], page, page_size: 6, has_more: false })
    })
    const wrapper = await mountView('/hbos/knowledge/maintenance/feedback')
    const search = wrapper.get('input[aria-label="搜索员工反馈"]')
    await search.setValue('清洁验证')
    await search.trigger('keydown.enter')
    await flushPromises()
    expect(wrapper.get('[data-v17-feedback-search-limitation]').text()).toContain('当前候选尚未提供内容搜索')
    // The fallback still shows the unfiltered bounded page; it does not fake filtered results.
    expect(api.feedback).toHaveBeenLastCalledWith(1, '', '')
  })
})

describe('permission state: unknown permission must not render as a 403 denial', () => {
  it('shows an unknown-permission retry state when the status endpoint fails', async () => {
    api.status.mockRejectedValueOnce(new Error('合成预览：请求超时'))
    const wrapper = await mountView()
    expect(wrapper.find('.v17-permission-unknown').exists()).toBe(true)
    expect(wrapper.text()).toContain('维护权限状态暂时无法确认')
    expect(wrapper.text()).not.toContain('当前账号没有知识维护权限')
    const retry = wrapper.findAll('button').find(button => button.text().replace(/\s+/g, '') === '重试')
    expect(retry).toBeTruthy()
  })

  it('keeps the 403 result for an explicit permission denial', async () => {
    api.status.mockResolvedValue({ can_maintain: false })
    const wrapper = await mountView()
    expect(wrapper.text()).toContain('当前账号没有知识维护权限')
    expect(wrapper.find('.v17-permission-unknown').exists()).toBe(false)
  })

  it('recovers through the retry action when the status endpoint comes back', async () => {
    api.status.mockRejectedValueOnce(new Error('合成预览：请求超时'))
    const wrapper = await mountView()
    await wrapper.get('.v17-permission-unknown button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('资料清单')
    expect(wrapper.find('.v17-permission-unknown').exists()).toBe(false)
  })
})
