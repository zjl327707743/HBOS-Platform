import { mount, flushPromises } from '@vue/test-utils'
import { reactive, defineComponent } from 'vue'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import KnowledgeView from '@/views/KnowledgeView.vue'
import { DomainApiError } from '@/services/p1Api'
import type { KnowledgeEvidence } from '@/contracts/p1'

const api = vi.hoisted(() => ({ status: vi.fn(), spaces: vi.fn(), documents: vi.fn(), search: vi.fn(), ask: vi.fn(), resolve: vi.fn(), activity: vi.fn(), open: vi.fn(), remove: vi.fn(), bookmark: vi.fn(), feedback: vi.fn(), getFeedback: vi.fn() }))
vi.mock('@/services/p1Api', async importOriginal => ({ ...(await importOriginal<typeof import('@/services/p1Api')>()), getKnowledgeStatus: api.status, getKnowledgeSpaces: api.spaces, getKnowledgeDocumentsPage: api.documents, searchKnowledge: api.search, askKnowledgeReference: api.ask, resolveKnowledgeEvidence: api.resolve, getKnowledgeActivity: api.activity, openKnowledgeSaved: api.open, removeKnowledgeSaved: api.remove, saveKnowledgeBookmark: api.bookmark, sendKnowledgeFeedback: api.feedback, getKnowledgeFeedback: api.getFeedback }))
const session = reactive<{ user: { id: string } | null }>({ user: { id: 'USER_N1_DEMO' } })
const route = reactive({ query: {} as Record<string, string> })
vi.mock('@/stores/portal', () => ({ usePortalStore: () => session }))
vi.mock('vue-router', () => ({ useRoute: () => route }))
const Button = defineComponent({ props: ['disabled', 'htmlType', 'loading'], template: '<button :type="htmlType || \'button\'" :disabled="disabled"><slot/></button>' })
const Modal = defineComponent({ props: ['open'], emits: ['cancel'], template: '<section v-if="open" role="dialog"><slot/><button data-modal-close @click="$emit(\'cancel\')">关闭反馈</button></section>' })
const Drawer = defineComponent({ props: ['open'], emits: ['close'], template: '<section v-if="open" role="dialog" data-evidence><slot name="title"/><slot/><button data-close @click="$emit(\'close\')">关闭来源</button></section>' })
const Pagination = defineComponent({ props: ['current', 'total', 'pageSize'], emits: ['update:current'], template: '<button data-next-page @click="$emit(\'update:current\', current + 1)">下一页</button>' })
const stubs = { RouterLink: { template: '<span><slot/></span>' }, 'a-button': Button, 'a-modal': Modal, 'a-drawer': Drawer, 'a-pagination': Pagination, 'a-alert': { props: ['message', 'description'], template: '<p role="alert">{{ message }} {{ description }}</p>' }, 'a-tag': { template: '<span><slot/></span>' }, 'a-skeleton': { template: '<p data-loading>正在加载</p>' }, 'a-empty': { props: ['description'], template: '<p data-empty>{{ description }}</p>' } }
const card: KnowledgeEvidence = { document_id: 'DOC_N1_DEMO', title: '合成资料标题', version: null, document_number: null, status_note: 'SYNTHETIC_ONLY', section: null, page_number: null, excerpt: 'SYNTHETIC 必要摘录', evidence_id: 'EV_N1_DEMO', space_id: 'SPACE_N1_DEMO', source_type: 'SYNTHETIC_TEST' }
const doc = { document_id: 'DOC_N1_DEMO', title: '合成资料标题', space_id: 'SPACE_N1_DEMO', department: '合成部门', document_number: null, version: null, status_note: 'SYNTHETIC_ONLY' }
const ready = { can_enter: true, can_search: true, gateway_configured: true, ask_enabled: true, mode: 'retrieval', environment: 'production', retrieval_availability: { status: 'UNKNOWN', blocked: false, budget_status: 'READY', last_success_at: null } }
const answer = { request_id: 'REQ_N1_DEMO', turn_id: 'TURN_N1_DEMO', answer: 'SYNTHETIC 内部参考回答', answerable: true, citations: [{ ...card, citation_label: 'C1' }] }
const wrappers: ReturnType<typeof mount>[] = []
function deferred<T = unknown>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done }); return { promise, resolve } }
async function view() { const wrapper = mount(KnowledgeView, { attachTo: document.body, global: { stubs } }); wrappers.push(wrapper); await flushPromises(); return wrapper }
async function clickText(wrapper: ReturnType<typeof mount>, value: string) { const button = wrapper.findAll('button').find(b => b.text() === value); expect(button, `button ${value}`).toBeDefined(); await button!.trigger('click'); await flushPromises() }
async function askMode(wrapper: ReturnType<typeof mount>) { await clickText(wrapper, '问知识') }
async function search(wrapper: ReturnType<typeof mount>) { await wrapper.get('#knowledge-query').setValue('合成关键词'); await wrapper.get('.knowledge-search').trigger('submit'); await flushPromises() }

beforeEach(() => {
  vi.clearAllMocks(); session.user = { id: 'USER_N1_DEMO' }; route.query = {}
  api.status.mockResolvedValue(ready); api.spaces.mockResolvedValue([{ space_id: 'SPACE_N1_DEMO', title: '合成部门', document_count: 25 }, { space_id: 'SPACE_N1_SECOND', title: '另一合成部门', document_count: 0 }])
  api.documents.mockImplementation((_query: string, _space: string, page: number, pageSize: number) => Promise.resolve({ documents: [doc], total: 25, page, page_size: pageSize }))
  api.activity.mockResolvedValue([]); api.getFeedback.mockResolvedValue([]); api.search.mockResolvedValue({ request_id: 'REQ_N1_DEMO', mode: 'retrieval', results: [card] }); api.ask.mockResolvedValue(answer); api.resolve.mockResolvedValue(card); api.feedback.mockResolvedValue(undefined); api.remove.mockResolvedValue(undefined)
})
afterEach(() => { wrappers.splice(0).forEach(w => w.unmount()); vi.useRealTimers(); document.body.innerHTML = '' })

describe('N1 knowledge experience — synthetic components, no real model or Session claims', () => {
  it('switches question/search modes without losing input or issuing a model call', async () => {
    const w = await view(); await w.get('#knowledge-query').setValue('未提交的问题'); await askMode(w)
    expect(w.get('#knowledge-query').element).toHaveProperty('value', '未提交的问题'); await clickText(w, '搜资料')
    expect(w.get('#knowledge-query').element).toHaveProperty('value', '未提交的问题'); expect(api.search).not.toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
  })
  it('allows IME composition to finish and suppresses duplicate in-flight search', async () => {
    const pending = deferred(); api.search.mockReturnValue(pending.promise); const w = await view()
    await w.get('#knowledge-query').setValue('中文资料'); await w.get('#knowledge-query').trigger('compositionstart'); await w.get('#knowledge-query').trigger('keydown', { key: 'Enter', isComposing: true }); await w.get('.knowledge-search').trigger('submit')
    expect(api.search).not.toHaveBeenCalled(); await w.get('#knowledge-query').trigger('compositionend'); await w.get('#knowledge-query').trigger('keydown', { key: 'Enter' }); await w.get('.knowledge-search').trigger('submit')
    expect(api.search).toHaveBeenCalledTimes(1); pending.resolve({ request_id: 'REQ_N1_DEMO', mode: 'retrieval', results: [] }); await flushPromises()
  })
  it('uses Command/Ctrl+Enter for questions while plain Enter keeps multiline editing', async () => {
    const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('合成问题'); await w.get('#knowledge-query').trigger('keydown', { key: 'Enter' }); expect(api.ask).not.toHaveBeenCalled()
    await w.get('#knowledge-query').trigger('keydown', { key: 'Enter', metaKey: true }); await flushPromises(); expect(api.ask).toHaveBeenCalledWith('合成问题', '', undefined); expect(w.text()).toContain(answer.answer)
  })
  it('does not turn a canceled search into zero hits or accept its late response', async () => {
    const pending = deferred(); api.search.mockReturnValue(pending.promise); const w = await view(); await w.get('#knowledge-query').setValue('合成关键词'); await w.get('.knowledge-search').trigger('submit'); await clickText(w, '返回编辑')
    pending.resolve({ request_id: 'REQ_LATE_DEMO', mode: 'retrieval', results: [card] }); await flushPromises()
    expect(w.find('.result-card').exists()).toBe(false); expect(w.text()).not.toContain('未找到相关依据'); expect(w.get('#knowledge-query').element).toHaveProperty('value', '合成关键词')
  })
  it('changing department discards a slow answer and starts the next turn without old context', async () => {
    const pending = deferred(); api.ask.mockReturnValueOnce(pending.promise); const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('合成问题'); await w.get('.knowledge-search').trigger('submit')
    await w.get('#knowledge-space').setValue('SPACE_N1_SECOND'); pending.resolve({ ...answer, answer: 'OLD_SCOPE_ANSWER' }); await flushPromises(); expect(w.text()).not.toContain('OLD_SCOPE_ANSWER')
    await w.get('#knowledge-query').setValue('另一范围问题'); await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.ask).toHaveBeenLastCalledWith('另一范围问题', 'SPACE_N1_SECOND', undefined)
  })
  it('switching user suppresses a late answer and clears personal state', async () => {
    const pending = deferred(); api.ask.mockReturnValueOnce(pending.promise); const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('A用户问题'); await w.get('.knowledge-search').trigger('submit')
    session.user = { id: 'USER_N1_OTHER' }; await flushPromises(); pending.resolve({ ...answer, answer: 'OLD_USER_PRIVATE' }); await flushPromises(); expect(w.text()).not.toContain('OLD_USER_PRIVATE'); expect(w.get('#knowledge-query').element).toHaveProperty('value', '')
  })
  it('reads catalog pages from the server without model calls and resets filters to page one', async () => {
    const w = await view(); await w.get('[data-next-page]').trigger('click'); await flushPromises(); expect(api.documents).toHaveBeenLastCalledWith('', '', 2, 12)
    vi.useFakeTimers(); await w.get('#catalog-query').setValue('合成标题'); await vi.advanceTimersByTimeAsync(200); await flushPromises(); expect(api.documents).toHaveBeenLastCalledWith('合成标题', '', 1, 12); expect(api.ask).not.toHaveBeenCalled(); expect(api.search).not.toHaveBeenCalled()
  })
  it('late old catalog responses cannot refill a newly selected department', async () => {
    const old = deferred(); api.documents.mockReturnValueOnce(old.promise); const w = await view(); vi.useFakeTimers(); await w.get('#knowledge-space').setValue('SPACE_N1_SECOND'); api.documents.mockResolvedValue({ documents: [], total: 0, page: 1, page_size: 12 }); await vi.advanceTimersByTimeAsync(200); await flushPromises()
    old.resolve({ documents: [{ ...doc, title: 'OLD_SCOPE_CATALOG' }], total: 1, page: 1, page_size: 12 }); await flushPromises(); expect(w.text()).not.toContain('OLD_SCOPE_CATALOG'); expect(w.text()).toContain('当前范围暂无可查阅')
  })
  it('saved replay restores its own context and displays that range before fresh search', async () => {
    route.query = { equipment_id: 'EQ_CURRENT_DEMO', asset_id: 'ASSET_CURRENT_DEMO' }
    api.activity.mockResolvedValue([{ id: 'SAVED_CONTEXT_DEMO', query: '合成旧问题', created_at: '2026-10-10', available: true, titles: ['合成标题'] }])
    const context = { equipment_id: 'EQ_SAVED_DEMO', asset_id: 'ASSET_SAVED_DEMO', component_id: 'COMPONENT_SAVED_DEMO' }
    api.open.mockResolvedValue({ query: '合成旧问题', space_ids: ['SPACE_N1_DEMO'], context })
    api.search.mockImplementation(() => { expect(document.body.textContent).toContain('设备上下文 EQ_SAVED_DEMO'); expect(document.body.textContent).toContain('资产范围 ASSET_SAVED_DEMO'); return Promise.resolve({ request_id: 'REQ_N1_DEMO', mode: 'retrieval', results: [] }) })
    const w = await view(); await clickText(w, '最近查阅'); await clickText(w, '重新查阅')
    expect(api.search).toHaveBeenCalledWith('合成旧问题', context, ['SPACE_N1_DEMO']); expect(w.text()).not.toContain('EQ_CURRENT_DEMO'); expect(w.text()).toContain('组件范围 COMPONENT_SAVED_DEMO')
  })
  it('a legacy saved record without context does not inherit an unrelated current device range', async () => {
    route.query = { equipment_id: 'EQ_CURRENT_DEMO' }
    api.activity.mockResolvedValue([{ id: 'SAVED_LEGACY_DEMO', query: '合成旧问题', created_at: '2026-10-10', available: true, titles: [] }]); api.open.mockResolvedValue({ query: '合成旧问题', space_ids: [] })
    const w = await view(); await clickText(w, '最近查阅'); await clickText(w, '重新查阅')
    expect(api.search).toHaveBeenCalledWith('合成旧问题', {}, undefined); expect(w.text()).not.toContain('设备上下文 EQ_CURRENT_DEMO')
  })
  it('a saved multi-department scope never silently replays against all departments', async () => {
    api.activity.mockResolvedValue([{ id: 'SAVED_MULTI_SCOPE_DEMO', query: '合成多部门问题', created_at: '2026-10-10', available: true, titles: [] }])
    const context = { equipment_id: 'EQ_SAVED_DEMO' }; api.open.mockResolvedValue({ query: '合成多部门问题', space_ids: ['SPACE_N1_DEMO', 'SPACE_N1_SECOND'], context })
    const w = await view(); await clickText(w, '最近查阅'); await clickText(w, '重新查阅')
    expect(w.get('#knowledge-query').element).toHaveProperty('value', '合成多部门问题'); expect(w.text()).toContain('这条记录包含多个部门'); expect(api.search).not.toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
    await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.search).not.toHaveBeenCalled()
    await w.get('#knowledge-space').setValue('SPACE_N1_DEMO'); expect(api.search).not.toHaveBeenCalled(); await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.search).toHaveBeenCalledWith('合成多部门问题', context, ['SPACE_N1_DEMO'])
  })
  it('a device range change discards a slow response from the previous range', async () => {
    route.query = { equipment_id: 'EQ_OLD_DEMO' }; const pending = deferred(); api.search.mockReturnValueOnce(pending.promise)
    const w = await view(); await w.get('#knowledge-query').setValue('合成设备问题'); await w.get('.knowledge-search').trigger('submit'); route.query = { equipment_id: 'EQ_NEW_DEMO' }; await flushPromises()
    pending.resolve({ request_id: 'REQ_OLD_CONTEXT_DEMO', mode: 'retrieval', results: [{ ...card, excerpt: 'OLD_DEVICE_PRIVATE' }] }); await flushPromises(); expect(w.text()).not.toContain('OLD_DEVICE_PRIVATE'); expect(w.text()).toContain('设备上下文 EQ_NEW_DEMO')
  })
  it('opens feedback near its trigger and reads the real pending/resolved state', async () => {
    api.getFeedback.mockResolvedValue([{ id: 'FEEDBACK_N1_DEMO', category: '版本疑问', note: '合成维护问题', status: 'Pending', created_at: '2026-10-10 01:00', updated_at: '2026-10-10 01:00' }])
    const w = await view(); await search(w); await clickText(w, '反馈'); await w.get('#feedback-category').setValue('版本疑问'); await w.get('#feedback-note').setValue('合成维护问题'); await clickText(w, '提交反馈')
    expect(api.feedback).toHaveBeenCalledWith(card.evidence_id, '版本疑问', '合成维护问题'); expect(w.text()).toContain('待处理'); expect(w.find('#feedback-note').exists()).toBe(false)
    api.getFeedback.mockResolvedValue([{ id: 'FEEDBACK_N1_DEMO', category: '版本疑问', note: '合成维护问题', status: 'Resolved', created_at: '2026-10-10 01:00', updated_at: '2026-10-10 01:05' }]); await clickText(w, '刷新记录'); expect(w.text()).toContain('已解决'); expect(w.text()).not.toContain('待处理')
  })
  it('allows general feedback during an accounting block, requires a note and never invents a source', async () => {
    api.status.mockResolvedValue({ ...ready, retrieval_availability: { ...ready.retrieval_availability, blocked: true, budget_status: 'ACCOUNTING_PENDING' } })
    const w = await view(); await clickText(w, '我的反馈'); await clickText(w, '提交一般反馈')
    expect(w.text()).toContain('这条反馈没有关联资料来源'); expect(w.get('#feedback-category').element).toHaveProperty('value', '其他'); expect(w.get('#feedback-note').attributes()).toHaveProperty('required')
    await w.get('#feedback-note').setValue('   '); await w.get('.feedback-form form').trigger('submit'); await flushPromises(); expect(api.feedback).not.toHaveBeenCalled(); expect(w.text()).toContain('请填写反馈说明')
    api.getFeedback.mockResolvedValue([{ id: 'FEEDBACK_GENERAL_DEMO', category: '其他', note: '合成一般使用问题', status: 'Pending', created_at: '2026-10-10', updated_at: '2026-10-10' }])
    await w.get('#feedback-note').setValue(' 合成一般使用问题 '); await clickText(w, '提交反馈')
    expect(api.feedback).toHaveBeenCalledWith(undefined, '其他', '合成一般使用问题'); expect(w.text()).toContain('待处理'); expect(api.search).not.toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
  })
  it('general feedback does not retain a previously selected evidence token', async () => {
    const w = await view(); await search(w); await clickText(w, '反馈'); await clickText(w, '取消'); await clickText(w, '我的反馈'); await clickText(w, '提交一般反馈')
    await w.get('#feedback-note').setValue('合成一般问题'); await clickText(w, '提交反馈'); expect(api.feedback).toHaveBeenCalledWith(undefined, '其他', '合成一般问题'); expect(api.feedback).not.toHaveBeenCalledWith(card.evidence_id, expect.anything(), expect.anything())
  })
  it('general feedback blocks duplicate sends and drops late success after a user switch', async () => {
    const pending = deferred(); api.feedback.mockReturnValue(pending.promise)
    const w = await view(); await clickText(w, '我的反馈'); await clickText(w, '提交一般反馈'); await w.get('#feedback-note').setValue('A 用户合成问题'); await w.get('.feedback-form form').trigger('submit'); await w.get('.feedback-form form').trigger('submit'); expect(api.feedback).toHaveBeenCalledTimes(1)
    session.user = { id: 'USER_N1_OTHER' }; await flushPromises(); pending.resolve(undefined); await flushPromises(); expect(w.find('#feedback-note').exists()).toBe(false); expect(w.text()).not.toContain('A 用户合成问题'); expect(w.text()).not.toContain('反馈已提交')
  })
  it('does not expose invalid bookmark titles, and deletion requires server success', async () => {
    api.activity.mockImplementation((kind: string) => Promise.resolve(kind === 'Bookmark' ? [{ id: 'SAVED_N1_DEMO', query: '合成旧问题', created_at: '2026-10-10', available: false, titles: ['WITHDRAWN_PRIVATE_TITLE'] }] : []))
    const w = await view(); await clickText(w, '我的收藏'); expect(w.text()).not.toContain('WITHDRAWN_PRIVATE_TITLE'); expect(w.text()).toContain('依据已下架或版本变化')
    api.remove.mockRejectedValueOnce(new DomainApiError('SERVICE_ERROR', '删除暂未完成')); await clickText(w, '删除'); expect(w.text()).toContain('合成旧问题')
    api.activity.mockResolvedValue([]); await clickText(w, '删除'); expect(api.remove).toHaveBeenCalledWith('SAVED_N1_DEMO'); expect(w.text()).not.toContain('合成旧问题')
  })
  it('returns focus to a retained evidence trigger and distinguishes service failure from revocation', async () => {
    const w = await view(); await search(w); const trigger = w.get('.result-card button').element as HTMLElement; trigger.focus(); await clickText(w, '查看依据'); await w.get('[data-close]').trigger('click'); expect(document.activeElement).toBe(trigger)
    api.resolve.mockRejectedValueOnce(new DomainApiError('UPSTREAM_UNAVAILABLE', '来源服务暂不可用')); await clickText(w, '查看依据'); expect(w.get('[data-evidence]').text()).toContain('来源核验暂不可用'); expect(w.get('[data-evidence]').text()).not.toContain('依据已失效'); expect(w.find('blockquote').exists()).toBe(false)
  })
  it('record tabs support Arrow/Home/End focus navigation', async () => {
    const w = await view(); const first = w.get('#knowledge-tab-Catalog'); await first.trigger('keydown', { key: 'End' }); await flushPromises(); expect(document.activeElement?.id).toBe('knowledge-tab-Feedback'); expect(w.get('#knowledge-tab-Feedback').attributes('aria-selected')).toBe('true')
    await w.get('#knowledge-tab-Feedback').trigger('keydown', { key: 'Home' }); await flushPromises(); expect(document.activeElement?.id).toBe('knowledge-tab-Catalog')
  })
  it('accounting block overrides an older successful observation and never sends a model request', async () => {
    api.status.mockResolvedValue({ ...ready, retrieval_availability: { ...ready.retrieval_availability, status: 'AVAILABLE', blocked: false, budget_status: 'ACCOUNTING_PENDING' } }); const w = await view(); await w.get('#knowledge-query').setValue('合成问题'); await w.get('.knowledge-search').trigger('submit')
    expect(w.text()).toContain('费用待对账'); expect(w.find('.state-dot.ready').exists()).toBe(false); expect(api.search).not.toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
  })
  it('a refreshed access denial clears results and personal catalog without waiting for a new identity', async () => {
    const w = await view(); await search(w); expect(w.text()).toContain(card.excerpt); api.status.mockRejectedValueOnce(new DomainApiError('FORBIDDEN', '当前请求不可访问。')); await clickText(w, '刷新状态'); expect(w.text()).not.toContain(card.excerpt); expect(w.find('.catalog-row').exists()).toBe(false); expect(w.find('.reference-library').exists()).toBe(false)
  })
  it('prefills deep links but refresh and department changes still issue zero model requests', async () => {
    route.query = { q: '合成深链问题', auto: '1' }; const w = await view(); expect(w.get('#knowledge-query').element).toHaveProperty('value', '合成深链问题'); await clickText(w, '刷新状态'); await w.get('#knowledge-space').setValue('SPACE_N1_DEMO'); expect(api.search).not.toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
  })
  it.each(['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE'])('same user/revision loses reader access through spaces: %s clears all visible private state', async code => {
    api.status.mockResolvedValue({ ...ready, policy_revision: 'FIXED_REVISION_DEMO' })
    api.activity.mockImplementation((kind: string) => Promise.resolve(kind === 'History' ? [{ id: 'PRIVATE_HISTORY_DEMO', query: '个人合成问题', created_at: '2026-10-10', available: true, titles: ['OLD_PRIVATE_HISTORY_TITLE'] }] : []))
    const w = await view(); await search(w); api.spaces.mockRejectedValueOnce(new DomainApiError(code, '当前请求不可访问。')); await clickText(w, '刷新状态')
    expect(session.user?.id).toBe('USER_N1_DEMO'); expect(w.text()).not.toContain(card.excerpt); expect(w.text()).not.toContain(doc.title); expect(w.text()).not.toContain('OLD_PRIVATE_HISTORY_TITLE'); expect(w.find('.reference-library').exists()).toBe(false); expect(w.find('#knowledge-space option[value="SPACE_N1_DEMO"]').exists()).toBe(false)
  })
  it('a catalog scope rejection propagates the access loss and clears prior personal records', async () => {
    const w = await view(); await search(w); api.documents.mockRejectedValueOnce(new DomainApiError('SCOPE_REJECTED', '当前请求不可访问。')); await w.get('.catalog-filter').trigger('submit'); await flushPromises()
    expect(w.find('.reference-library').exists()).toBe(false); expect(w.text()).not.toContain(card.excerpt); expect(w.text()).not.toContain(doc.title)
  })
  it('a current-user feedback scope rejection clears the same user’s existing catalog and records', async () => {
    const w = await view(); api.getFeedback.mockRejectedValueOnce(new DomainApiError('SCOPE_REJECTED', '当前请求不可访问。')); await clickText(w, '我的反馈')
    expect(session.user?.id).toBe('USER_N1_DEMO'); expect(w.find('.reference-library').exists()).toBe(false); expect(w.text()).not.toContain(doc.title)
  })
  it('explains an accounting block from its budget gate rather than a recent retrieval error', async () => {
    api.status.mockResolvedValue({ ...ready, retrieval_availability: { ...ready.retrieval_availability, status: 'AVAILABLE', blocked: true, budget_status: 'ACCOUNTING_PENDING' } }); const w = await view()
    expect(w.text()).toContain('当前阻断来自费用核验与原累计预算门槛'); expect(w.text()).not.toContain('当前提示依据最近真实调用'); expect(w.text()).toContain('较早的检索结果不能放行新调用')
  })
  it('source invalidation immediately hides old saved source titles while waiting for a fresh server read', async () => {
    api.activity.mockImplementation((kind: string) => Promise.resolve(kind === 'History' ? [{ id: 'PRIVATE_HISTORY_DEMO', query: '个人合成问题', created_at: '2026-10-10', available: true, titles: ['WITHDRAWN_PRIVATE_TITLE'] }] : []))
    const w = await view(); await search(w); const current = deferred<never[]>(); api.activity.mockReturnValue(current.promise); api.resolve.mockRejectedValueOnce(new DomainApiError('EVIDENCE_UNAVAILABLE', '该证据不可用或已失效。')); await clickText(w, '查看依据'); await clickText(w, '最近查阅')
    expect(w.text()).not.toContain('WITHDRAWN_PRIVATE_TITLE'); expect(w.text()).not.toContain(card.excerpt); await w.get('[data-close]').trigger('click'); expect(document.activeElement?.id).toBe('knowledge-query'); current.resolve([]); await flushPromises()
  })

})
