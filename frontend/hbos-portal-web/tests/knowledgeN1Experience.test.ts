import { mount, flushPromises } from '@vue/test-utils'
import { reactive, defineComponent } from 'vue'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import KnowledgeView from '@/views/KnowledgeView.vue'
import { DomainApiError } from '@/services/p1Api'
import type { KnowledgeEvidence } from '@/contracts/p1'

const api = vi.hoisted(() => ({ status: vi.fn(), spaces: vi.fn(), documents: vi.fn(), search: vi.fn(), ask: vi.fn(), resolve: vi.fn(), activity: vi.fn(), open: vi.fn(), remove: vi.fn(), bookmark: vi.fn(), feedback: vi.fn(), getFeedback: vi.fn() }))
vi.mock('@/services/p1Api', async importOriginal => ({ ...(await importOriginal<typeof import('@/services/p1Api')>()), getKnowledgeStatus: api.status, getKnowledgeSpaces: api.spaces, getKnowledgeDocumentsPage: api.documents, searchKnowledge: api.search, askKnowledgeReference: api.ask, resolveKnowledgeEvidence: api.resolve, getKnowledgeActivity: api.activity, openKnowledgeSaved: api.open, removeKnowledgeSaved: api.remove, saveKnowledgeBookmark: api.bookmark, sendKnowledgeFeedback: api.feedback, getKnowledgeFeedback: api.getFeedback, getKnowledgeActivityPage: async (kind: string, page: number, pageSize: number) => ({items: await api.activity(kind),page,page_size:pageSize,has_more:false}), getKnowledgeFeedbackPage: async (page: number, pageSize: number) => ({items:await api.getFeedback(),page,page_size:pageSize,has_more:false}) }))
const session = reactive<{ user: { id: string } | null }>({ user: { id: 'USER_N1_DEMO' } })
const route = reactive({ path: '/hbos/knowledge', query: {} as Record<string, string> })
vi.mock('@/stores/portal', () => ({ usePortalStore: () => session }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({push: async (path: string) => {const [p,q]=path.split('?'); route.path=p!;route.query=q?{tab:'feedback'}:{} }}) }))
const Button = defineComponent({ props: ['disabled', 'htmlType', 'loading'], template: '<button :type="htmlType || \'button\'" :disabled="disabled"><slot/></button>' })
const Modal = defineComponent({ props: ['open'], emits: ['cancel'], template: '<section v-if="open" role="dialog"><slot/><button data-modal-close @click="$emit(\'cancel\')">关闭反馈</button></section>' })
const Drawer = defineComponent({ props: ['open'], emits: ['close'], template: '<section v-if="open" role="dialog" data-evidence><slot name="title"/><slot/><button data-close @click="$emit(\'close\')">关闭来源</button></section>' })
const Pagination = defineComponent({ props: ['current', 'total', 'pageSize'], emits: ['update:current'], template: '<button data-next-page @click="$emit(\'update:current\', current + 1)">下一页</button>' })
const SearchInput=defineComponent({props:['value'],emits:['update:value','search'],template:'<input :value="value" @input="$emit(\'update:value\', $event.target.value)" @keydown.enter="$emit(\'search\')"/>'})
const stubs = { 'a-input-search':SearchInput, RouterLink: { template: '<span><slot/></span>' }, 'a-button': Button, 'a-modal': Modal, 'a-drawer': Drawer, 'a-pagination': Pagination, 'a-alert': { props: ['message', 'description'], template: '<p role="alert">{{ message }} {{ description }}</p>' }, 'a-tag': { template: '<span><slot/></span>' }, 'a-skeleton': { template: '<p data-loading>正在加载</p>' }, 'a-empty': { props: ['description'], template: '<p data-empty>{{ description }}</p>' } }
const card: KnowledgeEvidence = { document_id: 'DOC_N1_DEMO', title: '合成资料标题', version: null, document_number: null, status_note: 'SYNTHETIC_ONLY', section: null, page_number: null, excerpt: 'SYNTHETIC 必要摘录', evidence_id: 'EV_N1_DEMO', space_id: 'SPACE_N1_DEMO', source_type: 'SYNTHETIC_TEST' }
const doc = { document_id: 'DOC_N1_DEMO', title: '合成资料标题', space_id: 'SPACE_N1_DEMO', department: '合成部门', document_number: null, version: null, status_note: 'SYNTHETIC_ONLY' }
const ready = { can_enter: true, can_search: true, gateway_configured: true, ask_enabled: true, mode: 'retrieval', environment: 'production', retrieval_availability: { status: 'UNKNOWN', blocked: false, budget_status: 'READY', last_success_at: null } }
const answer = { request_id: 'REQ_N1_DEMO', turn_id: 'TURN_N1_DEMO', mode: 'internal_reference_generation', answer_status: 'GENERATED_WITH_SOURCES', answer_origin: 'KNOWLEDGE', model_alias: 'gpt-6-luna', answer: 'SYNTHETIC 内部参考回答', answerable: true, citations: [{ ...card, citation_label: 'C1' }] }
const wrappers: ReturnType<typeof mount>[] = []
function deferred<T = unknown>() { let resolve!: (value: T) => void, reject!: (reason: unknown) => void; const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail }); return { promise, resolve, reject } }
async function view() { const wrapper = mount(KnowledgeView, { attachTo: document.body, global: { stubs } }); wrappers.push(wrapper); await flushPromises(); await clickText(wrapper,'搜资料'); return wrapper }
async function clickText(wrapper: ReturnType<typeof mount>, value: string) { if(['最近查阅','我的收藏','我的反馈','资料目录'].includes(value)){route.path='/hbos/knowledge/'+(value==='我的收藏'?'favorites':value==='资料目录'?'catalog':'history');route.query=value==='我的反馈'?{tab:'feedback'}:{};await flushPromises();return} if(value==='刷新状态'){await (wrapper.vm as any).refreshStatus();await flushPromises();return} if(value==='查看依据'){await wrapper.get('.result-card .kb-doc-main').trigger('click');await flushPromises();return} const aliases:Record<string,string>={'重新查阅':'继续查阅','提交一般反馈':'反馈与建议','删除':'取消收藏'}; const button = wrapper.findAll('button').find(b => b.text() === (aliases[value]||value) || (Boolean(aliases[value]) && b.attributes('aria-label')===aliases[value]) || b.attributes('aria-label')===value); expect(button, `button ${value}`).toBeDefined(); await button!.trigger('click'); await flushPromises() }
async function askMode(wrapper: ReturnType<typeof mount>) { await clickText(wrapper, '问知识') }
async function search(wrapper: ReturnType<typeof mount>) { await wrapper.get('#knowledge-query').setValue('合成关键词'); await wrapper.get('.knowledge-search').trigger('submit'); await flushPromises() }

beforeEach(() => {
  vi.clearAllMocks(); session.user = { id: 'USER_N1_DEMO' }; route.query = {}; route.path='/hbos/knowledge'
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
    await w.get('#knowledge-query').trigger('keydown', { key: 'Enter', metaKey: true }); await flushPromises(); expect(api.ask).toHaveBeenCalledWith('合成问题', '', undefined, 'STANDARD', 'gpt-6-luna', false); expect(w.text()).toContain(answer.answer)
  })
  it('does not turn a canceled search into zero hits or accept its late response', async () => {
    const pending = deferred(); api.search.mockReturnValue(pending.promise); const w = await view(); await w.get('#knowledge-query').setValue('合成关键词'); await w.get('.knowledge-search').trigger('submit'); await clickText(w, '返回编辑')
    pending.resolve({ request_id: 'REQ_LATE_DEMO', mode: 'retrieval', results: [card] }); await flushPromises()
    expect(w.find('.result-card').exists()).toBe(false); expect(w.text()).not.toContain('未找到相关依据'); expect(w.get('#knowledge-query').element).toHaveProperty('value', '合成关键词')
  })
  it('changing department discards a slow answer and starts the next turn without old context', async () => {
    const pending = deferred(); api.ask.mockReturnValueOnce(pending.promise); const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('合成问题'); await w.get('.knowledge-search').trigger('submit')
    await w.get('#knowledge-space').setValue('SPACE_N1_SECOND'); pending.resolve({ ...answer, answer: 'OLD_SCOPE_ANSWER' }); await flushPromises(); expect(w.text()).not.toContain('OLD_SCOPE_ANSWER')
    await w.get('#knowledge-query').setValue('另一范围问题'); await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.ask).toHaveBeenLastCalledWith('另一范围问题', 'SPACE_N1_SECOND', undefined, 'STANDARD', 'gpt-6-luna', false)
  })
  it('switching user suppresses a late answer and clears personal state', async () => {
    const pending = deferred(); api.ask.mockReturnValueOnce(pending.promise); const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('A用户问题'); await w.get('.knowledge-search').trigger('submit')
    session.user = { id: 'USER_N1_OTHER' }; await flushPromises(); pending.resolve({ ...answer, answer: 'OLD_USER_PRIVATE' }); await flushPromises(); expect(w.text()).not.toContain('OLD_USER_PRIVATE'); expect(w.get('#knowledge-query').element).toHaveProperty('value', '')
  })
  it('reads catalog pages from the server without model calls and resets filters to page one', async () => {
    const w = await view(); await clickText(w,'资料目录'); await w.get('[data-next-page]').trigger('click'); await flushPromises(); expect(api.documents).toHaveBeenLastCalledWith('', '', 2, 4, undefined, 'SOURCE_ROOT')
    vi.useFakeTimers(); await w.get('#catalog-query').setValue('合成标题'); await vi.advanceTimersByTimeAsync(200); await flushPromises(); expect(api.documents).toHaveBeenLastCalledWith('合成标题', '', 1, 4, undefined, 'SOURCE_ROOT'); expect(api.ask).not.toHaveBeenCalled(); expect(api.search).not.toHaveBeenCalled()
  })
  it.each(['department', 'filter'])('catalog %s changes show pending state through debounce and only show empty after completion', async change => {
    const w = await view(); await clickText(w,'资料目录'); const pending = deferred(); api.documents.mockReturnValueOnce(pending.promise); vi.useFakeTimers()
    if (change === 'department') await w.get('#catalog-department').setValue('SPACE_N1_SECOND')
    else await w.get('#catalog-query').setValue('未匹配合成词')
    expect(w.get('.catalog-heading').text()).toContain('更新中'); expect(w.find('.catalog-content [data-loading]').exists()).toBe(true); expect(w.find('.catalog-content [data-empty]').exists()).toBe(false)
    await vi.advanceTimersByTimeAsync(200); await flushPromises(); expect(w.get('.catalog-heading').text()).toContain('更新中'); expect(w.find('.catalog-content [data-empty]').exists()).toBe(false)
    pending.resolve({ documents: [], total: 0, page: 1, page_size: 4 }); await flushPromises()
    expect(w.get('.catalog-heading').text()).toContain('0 份'); expect(w.find('.catalog-content [data-loading]').exists()).toBe(false); expect(w.get('.catalog-content [data-empty]').text()).toContain(change === 'department' ? '当前范围暂无' : '没有匹配的资料')
  })
  it('late old catalog responses cannot refill a newly selected department', async () => {
    const old = deferred(); api.documents.mockReturnValueOnce(old.promise); const w = await view(); await clickText(w,'资料目录'); vi.useFakeTimers(); await w.get('#catalog-department').setValue('SPACE_N1_SECOND'); api.documents.mockResolvedValue({ documents: [], total: 0, page: 1, page_size: 4 }); await vi.advanceTimersByTimeAsync(200); await flushPromises()
    old.resolve({ documents: [{ ...doc, title: 'OLD_SCOPE_CATALOG' }], total: 1, page: 1, page_size: 4 }); await flushPromises(); expect(w.text()).not.toContain('OLD_SCOPE_CATALOG'); expect(w.text()).toContain('当前范围暂无可查阅')
  })
  it('saved replay restores its own context and displays that range before fresh search', async () => {
    route.query = { equipment_id: 'EQ_CURRENT_DEMO', asset_id: 'ASSET_CURRENT_DEMO' }
    api.activity.mockResolvedValue([{ id: 'SAVED_CONTEXT_DEMO', query: '合成旧问题', created_at: '2026-10-10', available: true, titles: ['合成标题'] }])
    const context = { equipment_id: 'EQ_SAVED_DEMO', asset_id: 'ASSET_SAVED_DEMO', component_id: 'COMPONENT_SAVED_DEMO' }
    api.open.mockResolvedValue({ query: '合成旧问题', space_ids: ['SPACE_N1_DEMO'], context })
    api.search.mockImplementation(() => { expect(document.body.textContent).toContain('设备上下文 EQ_SAVED_DEMO'); expect(document.body.textContent).toContain('资产范围 ASSET_SAVED_DEMO'); return Promise.resolve({ request_id: 'REQ_N1_DEMO', mode: 'retrieval', results: [] }) })
    const w = await view(); await clickText(w, '最近查阅'); await clickText(w, '重新查阅')
    expect(api.search).toHaveBeenCalledWith('合成旧问题', context, ['SPACE_N1_DEMO'], 'STANDARD'); expect(w.text()).not.toContain('EQ_CURRENT_DEMO'); expect(w.text()).toContain('组件范围 COMPONENT_SAVED_DEMO')
  })
  it('a legacy saved record without context does not inherit an unrelated current device range', async () => {
    route.query = { equipment_id: 'EQ_CURRENT_DEMO' }
    api.activity.mockResolvedValue([{ id: 'SAVED_LEGACY_DEMO', query: '合成旧问题', created_at: '2026-10-10', available: true, titles: [] }]); api.open.mockResolvedValue({ query: '合成旧问题', space_ids: [] })
    const w = await view(); await clickText(w, '最近查阅'); await clickText(w, '重新查阅')
    expect(api.search).toHaveBeenCalledWith('合成旧问题', {}, undefined, 'STANDARD'); expect(w.text()).not.toContain('设备上下文 EQ_CURRENT_DEMO')
  })
  it('a saved multi-department scope never silently replays against all departments', async () => {
    api.activity.mockResolvedValue([{ id: 'SAVED_MULTI_SCOPE_DEMO', query: '合成多部门问题', created_at: '2026-10-10', available: true, titles: [] }])
    const context = { equipment_id: 'EQ_SAVED_DEMO' }; api.open.mockResolvedValue({ query: '合成多部门问题', space_ids: ['SPACE_N1_DEMO', 'SPACE_N1_SECOND'], context })
    const w = await view(); await clickText(w, '最近查阅'); await clickText(w, '重新查阅')
    expect(w.get('#knowledge-query').element).toHaveProperty('value', '合成多部门问题'); expect(w.text()).toContain('这条记录包含多个部门'); expect(api.search).not.toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
    await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.search).not.toHaveBeenCalled()
    await w.get('#knowledge-space').setValue('SPACE_N1_DEMO'); expect(api.search).not.toHaveBeenCalled(); await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.search).toHaveBeenCalledWith('合成多部门问题', context, ['SPACE_N1_DEMO'], 'STANDARD')
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
    expect(w.text()).toContain('说明资料、回答或使用中的问题'); expect(w.get('#feedback-category').element).toHaveProperty('value', '其他'); expect(w.get('#feedback-note').attributes()).toHaveProperty('required')
    await w.get('#feedback-note').setValue('   '); await w.get('.feedback-form form').trigger('submit'); await flushPromises(); expect(api.feedback).not.toHaveBeenCalled(); expect(w.text()).toContain('请填写反馈说明')
    api.getFeedback.mockResolvedValue([{ id: 'FEEDBACK_GENERAL_DEMO', category: '其他', note: '合成一般使用问题', status: 'Pending', created_at: '2026-10-10', updated_at: '2026-10-10' }])
    await w.get('#feedback-note').setValue(' 合成一般使用问题 '); await clickText(w, '提交反馈')
    expect(api.feedback).toHaveBeenCalledWith(undefined, '其他', '合成一般使用问题'); expect(w.text()).toContain('待处理'); expect(api.search).not.toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
  })
  it('general feedback does not retain a previously selected evidence token', async () => {
    const w = await view(); await search(w); await clickText(w, '反馈'); await w.get('[data-evidence] [data-close]').trigger('click'); await clickText(w, '我的反馈'); await clickText(w, '提交一般反馈')
    await w.get('#feedback-note').setValue('合成一般问题'); await clickText(w, '提交反馈'); expect(api.feedback).toHaveBeenCalledWith(undefined, '其他', '合成一般问题'); expect(api.feedback).not.toHaveBeenCalledWith(card.evidence_id, expect.anything(), expect.anything())
  })
  it('general feedback blocks duplicate sends and drops late success after a user switch', async () => {
    const pending = deferred(); api.feedback.mockReturnValue(pending.promise)
    const w = await view(); await clickText(w, '我的反馈'); await clickText(w, '提交一般反馈'); await w.get('#feedback-note').setValue('A 用户合成问题'); await w.get('.feedback-form form').trigger('submit'); await w.get('.feedback-form form').trigger('submit'); expect(api.feedback).toHaveBeenCalledTimes(1)
    session.user = { id: 'USER_N1_OTHER' }; await flushPromises(); pending.resolve(undefined); await flushPromises(); expect(w.find('#feedback-note').exists()).toBe(false); expect(w.text()).not.toContain('A 用户合成问题'); expect(w.text()).not.toContain('反馈已提交')
  })
  it('does not expose invalid bookmark titles, and deletion requires server success', async () => {
    api.activity.mockImplementation((kind: string) => Promise.resolve(kind === 'Bookmark' ? [{ id: 'SAVED_N1_DEMO', query: '合成旧问题', created_at: '2026-10-10', available: false, titles: ['WITHDRAWN_PRIVATE_TITLE'] }] : []))
    const w = await view(); await clickText(w, '我的收藏'); expect(w.text()).not.toContain('WITHDRAWN_PRIVATE_TITLE'); expect(w.text()).toContain('依据已下架、换版或授权变化')
    api.remove.mockRejectedValueOnce(new DomainApiError('SERVICE_ERROR', '删除暂未完成')); await clickText(w, '删除'); expect(w.text()).toContain('合成旧问题')
    api.activity.mockResolvedValue([]); await clickText(w, '删除'); expect(api.remove).toHaveBeenCalledWith('SAVED_N1_DEMO'); expect(w.text()).not.toContain('合成旧问题')
  })
  it('returns focus to a retained evidence trigger and distinguishes service failure from revocation', async () => {
    const w = await view(); await search(w); const trigger = w.get('.result-card button').element as HTMLElement; trigger.focus(); await clickText(w, '查看依据'); await w.get('[data-close]').trigger('click'); expect(document.activeElement).toBe(trigger)
    api.resolve.mockRejectedValueOnce(new DomainApiError('UPSTREAM_UNAVAILABLE', '来源服务暂不可用')); await clickText(w, '查看依据'); expect(w.get('[data-evidence]').text()).toContain('来源核验暂不可用'); expect(w.get('[data-evidence]').text()).not.toContain('依据已失效'); expect(w.find('blockquote').exists()).toBe(false)
  })
  it('personal records use independent routes and retain secondary feedback navigation', async () => { const w=await view(); await clickText(w,'最近查阅'); expect(route.path).toBe('/hbos/knowledge/history'); expect(w.text()).toContain('仅本人可见'); await clickText(w,'我的反馈'); expect(route.query.tab).toBe('feedback'); expect(w.find('#knowledge-query').exists()).toBe(false) })
  it('financial diagnostics cannot override actual unblocked retrieval capability', async () => {
    api.status.mockResolvedValue({ ...ready, retrieval_availability: { ...ready.retrieval_availability, status: 'AVAILABLE', blocked: false, budget_status: 'ACCOUNTING_PENDING' } }); const w = await view(); await w.get('#knowledge-query').setValue('合成问题'); await w.get('.knowledge-search').trigger('submit')
    expect(api.search).toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
  })
  it('a refreshed access denial clears results and personal catalog without waiting for a new identity', async () => {
    const w = await view(); await search(w); expect(w.text()).toContain(card.excerpt); api.status.mockRejectedValueOnce(new DomainApiError('FORBIDDEN', '当前请求不可访问。')); await clickText(w, '刷新状态'); expect(w.text()).not.toContain(card.excerpt); expect(w.find('.catalog-row').exists()).toBe(false); expect(w.find('.kb-tools').exists()).toBe(false)
  })
  it('prefills deep links but refresh and department changes still issue zero model requests', async () => {
    route.query = { q: '合成深链问题', auto: '1' }; const w = await view(); expect(w.get('#knowledge-query').element).toHaveProperty('value', '合成深链问题'); await clickText(w, '刷新状态'); await w.get('#knowledge-space').setValue('SPACE_N1_DEMO'); expect(api.search).not.toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
  })
  it.each(['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE'])('same user/revision loses reader access through spaces: %s clears all visible private state', async code => {
    api.status.mockResolvedValue({ ...ready, policy_revision: 'FIXED_REVISION_DEMO' })
    api.activity.mockImplementation((kind: string) => Promise.resolve(kind === 'History' ? [{ id: 'PRIVATE_HISTORY_DEMO', query: '个人合成问题', created_at: '2026-10-10', available: true, titles: ['OLD_PRIVATE_HISTORY_TITLE'] }] : []))
    const w = await view(); await search(w); api.spaces.mockRejectedValueOnce(new DomainApiError(code, '当前请求不可访问。')); await clickText(w, '刷新状态')
    expect(session.user?.id).toBe('USER_N1_DEMO'); expect(w.text()).not.toContain(card.excerpt); expect(w.text()).not.toContain(doc.title); expect(w.text()).not.toContain('OLD_PRIVATE_HISTORY_TITLE'); expect(w.find('.kb-tools').exists()).toBe(false); expect(w.find('#knowledge-space option[value="SPACE_N1_DEMO"]').exists()).toBe(false)
  })
  it('a catalog scope rejection propagates the access loss and clears prior personal records', async () => {
    const w = await view(); await search(w); api.documents.mockRejectedValueOnce(new DomainApiError('SCOPE_REJECTED', '当前请求不可访问。')); await clickText(w,'资料目录'); await flushPromises()
    expect(w.find('.kb-tools').exists()).toBe(false); expect(w.text()).not.toContain(card.excerpt); expect(w.text()).not.toContain(doc.title)
  })
  it('a current-user feedback scope rejection clears the same user’s existing catalog and records', async () => {
    const w = await view(); api.getFeedback.mockRejectedValueOnce(new DomainApiError('SCOPE_REJECTED', '当前请求不可访问。')); await clickText(w, '我的反馈')
    expect(session.user?.id).toBe('USER_N1_DEMO'); expect(w.find('.kb-tools').exists()).toBe(false); expect(w.text()).not.toContain(doc.title)
  })
  it('explains an accounting block from its budget gate rather than a recent retrieval error', async () => {
    api.status.mockResolvedValue({ ...ready, retrieval_availability: { ...ready.retrieval_availability, status: 'AVAILABLE', blocked: true, budget_status: 'ACCOUNTING_PENDING' } }); const w = await view()
    expect(w.text()).toContain('查询暂不可用'); expect(w.text()).not.toContain('费用核验'); await w.get('.knowledge-search').trigger('submit'); expect(api.search).not.toHaveBeenCalled(); expect(api.ask).not.toHaveBeenCalled()
  })
  it('source invalidation immediately hides old saved source titles while waiting for a fresh server read', async () => {
    api.activity.mockImplementation((kind: string) => Promise.resolve(kind === 'History' ? [{ id: 'PRIVATE_HISTORY_DEMO', query: '个人合成问题', created_at: '2026-10-10', available: true, titles: ['WITHDRAWN_PRIVATE_TITLE'] }] : []))
    const w = await view(); await search(w); const current = deferred<never[]>(); api.activity.mockReturnValue(current.promise); api.resolve.mockRejectedValueOnce(new DomainApiError('EVIDENCE_UNAVAILABLE', '该证据不可用或已失效。')); await clickText(w, '查看依据'); await clickText(w, '最近查阅')
    expect(w.text()).not.toContain('WITHDRAWN_PRIVATE_TITLE'); expect(w.text()).not.toContain(card.excerpt); expect(w.find('blockquote').exists()).toBe(false); current.resolve([]); await flushPromises()
  })

  it('UAT5 shows a failed answer once, keeps read views clean, and allows a fresh question', async () => {
    api.ask.mockRejectedValueOnce(new DomainApiError('CITATION_SUPPORT_FAILED', '回答未通过来源支持校验，本次未展示回答。'))
    const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('合成引用问题'); await w.get('.knowledge-search').trigger('submit'); await flushPromises()
    expect(w.findAll('[role="alert"]').map(a => a.text())).toEqual(['回答未通过来源支持校验，本次未展示回答。'])
    expect(w.attributes('data-query-state')).toBe('error'); expect(w.find('.kb-start-grid').exists()).toBe(false)
    for (const label of ['我的收藏', '资料目录', '最近查阅']) {
      await clickText(w, label); expect(w.find('[role="alert"]').exists()).toBe(false)
    }
    route.path = '/hbos/knowledge'; await flushPromises()
    expect(w.find('[role="alert"]').exists()).toBe(false)
    await w.get('.knowledge-search').trigger('submit'); await flushPromises()
    expect(api.ask).toHaveBeenCalledTimes(2); expect(w.text()).toContain(answer.answer); expect(w.attributes('data-query-state')).toBe('success')
  })
  it.each(['success', 'failure'])('UAT5 view changes discard late answer %s without blocking favorites', async outcome => {
    const pending = deferred(); api.ask.mockReturnValueOnce(pending.promise)
    const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('合成慢问题'); await w.get('.knowledge-search').trigger('submit')
    expect(w.attributes('data-query-state')).toBe('answering')
    await clickText(w, '我的收藏')
    if (outcome === 'success') pending.resolve({ ...answer, answer: 'LATE_VIEW_ANSWER' })
    else pending.reject(new DomainApiError('MODEL_RATE_LIMITED', 'LATE_VIEW_ERROR'))
    await flushPromises(); expect(w.find('[role="alert"]').exists()).toBe(false); expect(w.text()).not.toContain('LATE_VIEW')
    route.path = '/hbos/knowledge'; await flushPromises()
    expect(w.text()).not.toContain('LATE_VIEW'); expect(w.get('#knowledge-query').attributes('disabled')).toBeUndefined()
    await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.ask).toHaveBeenLastCalledWith('合成慢问题', '', undefined, 'STANDARD', 'gpt-6-luna', false)
  })
  it('UAT5 mode changes discard late answer failure and preserve editable input', async () => {
    const pending = deferred(); api.ask.mockReturnValueOnce(pending.promise)
    const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('合成慢问题'); await w.get('.knowledge-search').trigger('submit')
    await clickText(w, '搜资料'); pending.reject(new DomainApiError('ANSWER_SCHEMA_INVALID', 'OLD_MODE_FAILURE')); await flushPromises()
    expect(w.find('[role="alert"]').exists()).toBe(false); expect(w.get('#knowledge-query').element).toHaveProperty('value', '合成慢问题')
    await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.search).toHaveBeenCalledTimes(1)
  })
  it('UAT5 view changes discard late search failures instead of refilling another page', async () => {
    const pending = deferred(); api.search.mockReturnValueOnce(pending.promise)
    const w = await view(); await w.get('#knowledge-query').setValue('合成慢检索'); await w.get('.knowledge-search').trigger('submit')
    await clickText(w, '资料目录'); pending.reject(new DomainApiError('RETRIEVAL_UPSTREAM_FAILED', 'OLD_QUERY_FAILURE')); await flushPromises()
    expect(w.find('[role="alert"]').exists()).toBe(false); expect(w.text()).toContain(doc.title)
    route.path = '/hbos/knowledge'; await flushPromises(); expect(w.text()).not.toContain('OLD_QUERY_FAILURE'); expect(w.text()).not.toContain('未找到相关依据')
  })
  it('UAT5 capability warnings stay in the query view and blocked retrieval cannot use general fallback', async () => {
    api.status.mockResolvedValue({ ...ready, answer_availability: { configured: true, available: false }, retrieval_availability: { ...ready.retrieval_availability, blocked: true } })
    const w = await view(); await askMode(w); expect(w.findAll('[role="alert"]')).toHaveLength(1)
    await w.get('#knowledge-query').setValue('合成一般问题'); await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.ask).not.toHaveBeenCalled()
    for (const label of ['我的收藏', '资料目录', '最近查阅']) { await clickText(w, label); expect(w.find('[role="alert"]').exists()).toBe(false) }
  })
  it('UAT5 a failed status refresh does not duplicate a query failure or persist into catalog', async () => {
    const w = await view(); api.status.mockRejectedValueOnce(new DomainApiError('SERVICE_ERROR', 'STATE_FAILURE'))
    api.search.mockRejectedValueOnce(new DomainApiError('RETRIEVAL_UPSTREAM_FAILED', '本次资料检索失败'))
    await search(w); expect(w.findAll('[role="alert"]').map(a => a.text())).toEqual(['本次资料检索失败'])
    await clickText(w, '资料目录'); expect(w.find('[role="alert"]').exists()).toBe(false)
  })
  it('UAT5 feedback failure appears only in its drawer and clears when it closes', async () => {
    const w = await view(); await clickText(w, '我的反馈'); await clickText(w, '提交一般反馈')
    api.feedback.mockRejectedValueOnce(new DomainApiError('SERVICE_ERROR', '本次反馈提交失败'))
    await w.get('#feedback-note').setValue('合成反馈'); await w.get('.feedback-form form').trigger('submit'); await flushPromises()
    expect(w.findAll('[role="alert"]')).toHaveLength(1); expect(w.get('.feedback-form [role="alert"]').text()).toContain('本次反馈提交失败')
    await w.get('[data-close]').trigger('click'); await flushPromises(); expect(w.find('[role="alert"]').exists()).toBe(false)
  })
  it('UAT5 transient source failure retains successful results and does not invalidate personal sources', async () => {
    const w = await view(); await search(w)
    api.resolve.mockRejectedValueOnce(new DomainApiError('RETRIEVAL_UPSTREAM_FAILED', '来源核验暂时失败'))
    await clickText(w, '查看依据'); expect(w.get('[data-evidence]').text()).toContain('来源核验暂不可用')
    expect(w.findAll('[role="alert"]')).toHaveLength(1); expect(w.find('.result-card').exists()).toBe(true)
    await w.get('[data-close]').trigger('click'); await flushPromises(); expect(w.find('.result-card').exists()).toBe(true)
  })
  it('UAT5 successful answers survive read-only navigation without another model call', async () => {
    const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('合成已答问题'); await w.get('.knowledge-search').trigger('submit'); await flushPromises()
    await clickText(w, '资料目录'); route.path = '/hbos/knowledge'; await flushPromises()
    expect(w.text()).toContain(answer.answer); expect(api.ask).toHaveBeenCalledTimes(1)
  })

  it('UAT5 filters public laws by reviewed category, resets pagination, and labels unknown effectiveness', async () => {
    api.spaces.mockResolvedValue([{ space_id: 'SPACE_N1_DEMO', title: '合成部门', document_count: 1 }, { space_id: 'DEPT_PUBLIC_LAW', title: '公司公共法律法规知识', document_count: 25 }])
    const law = { ...doc, document_id: 'DOC_LAW_SYNTHETIC', space_id: 'DEPT_PUBLIC_LAW', title: '合成法规', legal_metadata: { category: '国家法律法规', level: null, issuer: null, published_date: null, region: null, applicability: null, effective_status: '待核' } }
    api.documents.mockImplementation((_q: string, space: string, page: number, size: number) => Promise.resolve({ documents: space === 'SPACE_N1_DEMO' ? [doc] : [law], total: 25, page, page_size: size }))
    const w = await view(); await clickText(w, '资料目录'); expect(w.text()).toContain('效力待核'); expect(w.text()).toContain('发布机构待核')
    await w.get('[data-next-page]').trigger('click'); await flushPromises(); expect(api.documents).toHaveBeenLastCalledWith('', '', 2, 4, undefined, 'SOURCE_ROOT')
    vi.useFakeTimers(); await w.get('#catalog-law-category').setValue('国家法律法规'); await vi.advanceTimersByTimeAsync(200); await flushPromises()
    expect(api.documents).toHaveBeenLastCalledWith('', '', 1, 4, '国家法律法规', 'SOURCE_ROOT'); expect(api.ask).not.toHaveBeenCalled(); expect(api.search).not.toHaveBeenCalled()
    await w.get('#catalog-department').setValue('SPACE_N1_DEMO'); await vi.advanceTimersByTimeAsync(200); await flushPromises()
    expect(w.find('#catalog-law-category').exists()).toBe(false); expect(api.documents).toHaveBeenLastCalledWith('', 'SPACE_N1_DEMO', 1, 4, undefined, 'SOURCE_ROOT')
  })

  it('UAT5 restores an authorized answer after route, mode and department props settle without generation', async () => {
    const saved = { ...answer, question: '合成已保存问题' }
    api.activity.mockResolvedValue([{ id: 'SAVED_UAT5_SYNTHETIC', query: saved.question, created_at: '2026-10-15', available: true, titles: [card.title] }])
    api.open.mockResolvedValue({ query: saved.question, space_ids: ['SPACE_N1_DEMO'], context: {}, restored: { mode: 'ask', search_mode: 'STANDARD', results: [], turns: [saved] } })
    const w = await view(); await clickText(w, '最近查阅'); await clickText(w, '重新查阅'); await flushPromises()
    expect(route.path).toBe('/hbos/knowledge'); expect(w.text()).toContain(saved.answer); expect(w.text()).toContain('合成已保存问题')
    expect(w.attributes('data-query-state')).toBe('success'); expect(api.ask).not.toHaveBeenCalled(); expect(api.search).not.toHaveBeenCalled()
  })
  it('UAT5 general answers identify their origin without displaying company sources', async () => {
    api.ask.mockResolvedValue({ ...answer, answer_origin: 'GENERAL', answer: '合成一般知识说明', citations: [] })
    const w = await view(); await askMode(w); await w.get('#knowledge-query').setValue('合成一般知识问题'); await w.get('.knowledge-search').trigger('submit'); await flushPromises()
    expect(w.text()).toContain('通用 AI 回答'); expect(w.text()).not.toContain('已使用知识库'); expect(w.find('.kb-citation-row').exists()).toBe(false)
  })

  it('UAT5 status refresh from an earlier visit cannot refill errors after leaving and returning', async () => {
    const w = await view(), pending = deferred(); api.status.mockReturnValueOnce(pending.promise)
    const refreshing = (w.vm as any).refreshStatus()
    await clickText(w, '资料目录'); route.path = '/hbos/knowledge'; await flushPromises()
    pending.reject(new DomainApiError('SERVICE_ERROR', 'EARLIER_VISIT_STATUS_FAILURE')); await refreshing; await flushPromises()
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  it('UAT5 revisiting after a completed failed search does not turn the failure into zero hits', async () => {
    api.search.mockRejectedValueOnce(new DomainApiError('RETRIEVAL_UPSTREAM_FAILED', '合成检索失败'))
    const w = await view(); await search(w); expect(w.attributes('data-query-state')).toBe('error')
    await clickText(w, '我的收藏'); route.path = '/hbos/knowledge'; await flushPromises()
    expect(w.find('[role="alert"]').exists()).toBe(false); expect(w.text()).not.toContain('未找到相关依据'); expect(w.attributes('data-query-state')).toBe('idle')
    await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.search).toHaveBeenCalledTimes(2)
  })
  it('UAT5 unmounting an IME input while navigating clears composition state for the new editor', async () => {
    const w = await view(); await w.get('#knowledge-query').setValue('合成中文问题'); await w.get('#knowledge-query').trigger('compositionstart')
    await clickText(w, '资料目录'); route.path = '/hbos/knowledge'; await flushPromises()
    await w.get('.knowledge-search').trigger('submit'); await flushPromises(); expect(api.search).toHaveBeenCalledTimes(1)
  })
  it('UAT5 answer availability changes leave an in-flight favorites read intact', async () => {
    const w = await view(), pending = deferred(); await askMode(w); api.activity.mockReturnValueOnce(pending.promise)
    await clickText(w, '我的收藏'); api.status.mockResolvedValueOnce({ ...ready, ask_enabled: false })
    await (w.vm as any).refreshStatus(); pending.resolve([{ id: 'FAVORITE_UAT5_SYNTHETIC', query: '合成收藏', titles: ['合成收藏标题'], available: true, created_at: '2026-10-15' }]); await flushPromises()
    expect(w.text()).toContain('合成收藏标题'); expect(w.find('[role="alert"]').exists()).toBe(false)
  })

})
