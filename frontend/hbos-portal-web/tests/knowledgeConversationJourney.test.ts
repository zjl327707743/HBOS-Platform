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
const answer = { request_id: 'REQ_N1_DEMO', turn_id: 'TURN_N1_DEMO', mode: 'internal_reference_generation', answer_status: 'GENERATED_WITH_SOURCES', answer_origin: 'KNOWLEDGE', model_alias: 'deepseek-flash', answer: 'SYNTHETIC 内部参考回答', answerable: true, citations: [{ ...card, citation_label: 'C1' }] }
const wrappers: ReturnType<typeof mount>[] = []
function deferred<T = unknown>() { let resolve!: (value: T) => void, reject!: (reason: unknown) => void; const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail }); return { promise, resolve, reject } }
async function view() { const wrapper = mount(KnowledgeView, { attachTo: document.body, global: { stubs } }); wrappers.push(wrapper); await flushPromises(); await clickText(wrapper,'搜资料'); return wrapper }
async function clickText(wrapper: ReturnType<typeof mount>, value: string) { if(['最近查阅','我的收藏','我的反馈','资料目录'].includes(value)){route.path='/hbos/knowledge/'+(value==='我的收藏'?'favorites':value==='资料目录'?'catalog':'history');route.query=value==='我的反馈'?{tab:'feedback'}:{};await flushPromises();return} if(value==='刷新状态'){await (wrapper.vm as any).refreshStatus();await flushPromises();return} if(value==='查看依据'){await wrapper.get('.result-card .kb-doc-main').trigger('click');await flushPromises();return} const aliases:Record<string,string>={'重新查阅':'继续查阅','提交一般反馈':'反馈与建议','删除':'取消收藏'}; const button = wrapper.findAll('button').find(b => b.text() === (aliases[value]||value) || (Boolean(aliases[value]) && b.attributes('aria-label')===aliases[value]) || b.attributes('aria-label')===value); expect(button, `button ${value}`).toBeDefined(); await button!.trigger('click'); await flushPromises() }
async function askMode(wrapper: ReturnType<typeof mount>) { await clickText(wrapper, '问知识') }
async function search(wrapper: ReturnType<typeof mount>) { await wrapper.get('#knowledge-query').setValue('合成关键词'); await wrapper.get('.knowledge-search').trigger('submit'); await flushPromises() }

beforeEach(() => {
  // Each test is a fresh tab: the per-identity workspace store must not
  // carry a previous case's filters into this one.
  window.sessionStorage.clear()
  vi.clearAllMocks(); session.user = { id: 'USER_N1_DEMO' }; route.query = {}; route.path='/hbos/knowledge'
  api.status.mockResolvedValue(ready); api.spaces.mockResolvedValue([{ space_id: 'SPACE_N1_DEMO', title: '合成部门', document_count: 25 }, { space_id: 'SPACE_N1_SECOND', title: '另一合成部门', document_count: 0 }])
  api.documents.mockImplementation((_query: string, _space: string, page: number, pageSize: number) => Promise.resolve({ documents: [doc], total: 25, page, page_size: pageSize }))
  api.activity.mockResolvedValue([]); api.getFeedback.mockResolvedValue([]); api.search.mockResolvedValue({ request_id: 'REQ_N1_DEMO', mode: 'retrieval', results: [card] }); api.ask.mockResolvedValue(answer); api.resolve.mockResolvedValue(card); api.feedback.mockResolvedValue(undefined); api.remove.mockResolvedValue(undefined)
})
afterEach(() => { wrappers.splice(0).forEach(w => w.unmount()); vi.useRealTimers(); document.body.innerHTML = '' })

describe('four-turn conversation and grouped evidence journey', () => {
  it('uses one composer, carries the exact previous turn, groups source handles and starts a clean conversation', async () => {
    const w=await view(); await askMode(w)
    for(let i=1;i<=4;i++) {
      api.ask.mockResolvedValueOnce({...answer,turn_id:`TURN_JOURNEY_${i}`,answer:`第${i}轮完整回答。末句仍在。`,citations:[
        {...card,citation_label:'C1',section:'第一条'},
        {...card,citation_label:'C2',section:'第二条',evidence_id:'EV_SECOND_JOURNEY'},
      ]})
      await w.get('#knowledge-query').setValue(`问题${i}`)
      await w.get('.knowledge-search').trigger('submit'); await flushPromises()
      expect(api.ask).toHaveBeenLastCalledWith(`问题${i}`,'',i===1?undefined:`TURN_JOURNEY_${i-1}`,'STANDARD',false)
      expect(w.findAll('textarea#knowledge-query')).toHaveLength(1)
      expect(w.find('#knowledge-question').exists()).toBe(false)
      expect(w.findAll('.answer-card')).toHaveLength(i)
    }
    expect(w.findAll('.kb-citation-group')).toHaveLength(4)
    expect(w.findAll('.kb-source-link')).toHaveLength(8)
    await w.findAll('.kb-source-link')[1]!.trigger('click'); await flushPromises()
    expect(api.resolve.mock.calls.at(-1)?.[0]).toBe('EV_SECOND_JOURNEY')
    await w.get('[data-close]').trigger('click'); await flushPromises()
    expect(w.text()).toContain('第4轮完整回答。末句仍在。')
    const reset=w.findAll('button').find(b=>b.text()==='新建对话')!;await reset.trigger('click'); await flushPromises()
    expect(w.findAll('.answer-card')).toHaveLength(0)
    expect(w.get('#knowledge-query').element).toHaveProperty('value','')
    await w.get('#knowledge-query').setValue('另一个主题'); await w.get('.knowledge-search').trigger('submit');await flushPromises()
    expect(api.ask).toHaveBeenLastCalledWith('另一个主题','',undefined,'STANDARD',false)
  })
  it('retains a draft and the four answers through catalog navigation without generating again', async () => {
    const w=await view();await askMode(w)
    for(let i=1;i<=4;i++) {api.ask.mockResolvedValueOnce({...answer,turn_id:`TURN_NAV_${i}`,answer:`回答${i}末句`});await w.get('#knowledge-query').setValue(`追问${i}`);await w.get('.knowledge-search').trigger('submit');await flushPromises()}
    await w.get('#knowledge-query').setValue('尚未提交的追问草稿')
    await clickText(w,'资料目录');route.path='/hbos/knowledge';await flushPromises()
    expect(w.get('#knowledge-query').element).toHaveProperty('value','尚未提交的追问草稿')
    expect(w.findAll('.answer-card')).toHaveLength(4)
    expect(w.text()).toContain('回答4末句');expect(api.ask).toHaveBeenCalledTimes(4)
    session.user={id:'USER_OTHER_JOURNEY'};await flushPromises()
    expect(w.findAll('.answer-card')).toHaveLength(0)
    expect(w.get('#knowledge-query').element).toHaveProperty('value','')
  })
  it('preserves a service failure as retryable evidence failure without marking every saved record withdrawn', async () => {
    const w=await view();await askMode(w);await w.get('#knowledge-query').setValue('合成问题');await w.get('.knowledge-search').trigger('submit');await flushPromises()
    api.resolve.mockRejectedValueOnce(new DomainApiError('RETRIEVAL_UPSTREAM_FAILED','来源服务暂不可用'))
    await w.get('.kb-source-link').trigger('click');await flushPromises()
    expect(w.get('[data-evidence]').text()).toContain('来源核验暂不可用')
    expect(w.text()).toContain(answer.answer)
    expect(w.text()).not.toContain('依据已失效')
    expect(api.ask).toHaveBeenCalledTimes(1)
  })
})


describe('refresh resumes the authorized server conversation', () => {
  it('stores only the last turn pointer and restores four turns without generating or replacing the draft', async () => {
    const w=await view();await askMode(w)
    const restoredTurns=[]
    for(let i=1;i<=4;i++) {
      const item={...answer,turn_id:`TURN_REFRESH_${i}`,answer:`刷新前第${i}轮完整末句`,question:`问题${i}`}
      restoredTurns.push(item);api.ask.mockResolvedValueOnce(item)
      await w.get('#knowledge-query').setValue(item.question);await w.get('.knowledge-search').trigger('submit');await flushPromises()
    }
    await w.get('#knowledge-query').setValue('刷新后仍未发送的草稿')
    w.unmount()
    const pointer=window.sessionStorage.getItem('hbos.knowledge.resume.v1:USER_N1_DEMO')
    expect(pointer).toBe('TURN_REFRESH_4')
    expect(pointer).not.toContain('完整末句')
    api.open.mockResolvedValueOnce({query:'问题4',space_ids:[],restored:{mode:'ask',search_mode:'STANDARD',results:[],turns:restoredTurns}})
    const returned=mount(KnowledgeView,{attachTo:document.body,global:{stubs}});wrappers.push(returned);await flushPromises()
    expect(api.open).toHaveBeenCalledWith('TURN_REFRESH_4')
    expect(returned.findAll('.answer-card')).toHaveLength(4)
    expect(returned.text()).toContain('刷新前第4轮完整末句')
    expect(returned.get('#knowledge-query').element).toHaveProperty('value','刷新后仍未发送的草稿')
    expect(api.ask).toHaveBeenCalledTimes(4)
    session.user={id:'USER_REFRESH_OTHER'};await flushPromises()
    expect(returned.findAll('.answer-card')).toHaveLength(0)
    expect(window.sessionStorage.getItem('hbos.knowledge.resume.v1:USER_REFRESH_OTHER')).toBeNull()
    expect(api.open).toHaveBeenCalledTimes(1)
  })
})

describe('reopening a saved record keeps a draft only for the open conversation', () => {
  const record = (query: string) => [{ id: 'SAVED_N1_RECORD', query, created_at: '2026-11-04T00:00:00', available: true, titles: ['合成资料标题'] }]
  const savedTurns = (prefix: string, question: string) => [1, 2, 3, 4].map(i => ({ ...answer, turn_id: `${prefix}_${i}`, answer: `${prefix}第${i}轮末句`, question: `${question}${i}` }))
  async function fourTurns(w: ReturnType<typeof mount>, prefix: string, question = '问题') {
    const turns = savedTurns(prefix, question)
    for (const item of turns) { api.ask.mockResolvedValueOnce(item); await w.get('#knowledge-query').setValue(item.question); await w.get('.knowledge-search').trigger('submit'); await flushPromises() }
    return turns
  }
  async function reopen(w: ReturnType<typeof mount>, query: string, restored: object) {
    api.activity.mockResolvedValue(record(query))
    await clickText(w, '最近查阅')
    api.open.mockResolvedValueOnce({ query, space_ids: [], restored })
    await clickText(w, '继续查阅')
  }
  it('preserves the unsent draft when the record is the open conversation latest turn', async () => {
    const w = await view(); await askMode(w)
    const turns = await fourTurns(w, 'TURN_SELF')
    await w.get('#knowledge-query').setValue('重新查阅后仍未发送的草稿')
    await reopen(w, '问题4', { mode: 'ask', search_mode: 'STANDARD', results: [], turns })
    expect(api.open).toHaveBeenLastCalledWith('SAVED_N1_RECORD')
    expect(w.findAll('.answer-card')).toHaveLength(4)
    expect(w.text()).toContain('TURN_SELF第4轮末句')
    expect(w.get('#knowledge-query').element).toHaveProperty('value', '重新查阅后仍未发送的草稿')
    expect(api.ask).toHaveBeenCalledTimes(4)
  })
  it('replaces the draft when the record is a different conversation', async () => {
    const w = await view(); await askMode(w)
    await fourTurns(w, 'TURN_OPEN')
    await w.get('#knowledge-query').setValue('另一条记录不应保留的草稿')
    await reopen(w, '另一条问题', { mode: 'ask', search_mode: 'STANDARD', results: [], turns: savedTurns('TURN_OTHER', '另一条问题') })
    expect(w.findAll('.answer-card')).toHaveLength(4)
    expect(w.text()).toContain('TURN_OTHER第4轮末句')
    expect(w.get('#knowledge-query').element).toHaveProperty('value', '')
    expect(api.ask).toHaveBeenCalledTimes(4)
  })
  it('replaces the draft with the saved query for a search record', async () => {
    const w = await view(); await askMode(w)
    await fourTurns(w, 'TURN_SEARCH')
    await w.get('#knowledge-query').setValue('搜索记录不应保留的草稿')
    await reopen(w, '合成关键词', { mode: 'search', search_mode: 'STANDARD', results: [card], turns: [] })
    expect(w.get('#knowledge-query').element).toHaveProperty('value', '合成关键词')
    expect(w.findAll('.result-card')).toHaveLength(1)
    expect(api.search).not.toHaveBeenCalled()
    expect(api.ask).toHaveBeenCalledTimes(4)
  })
})

describe('an in-flight scope change requires fresh status', () => {
  it.each([true,false])('refreshes status once without replay and respects can_enter=%s',async (allowed) => {
    const w=await view();await askMode(w)
    api.ask.mockRejectedValueOnce(new DomainApiError('SCOPE_REJECTED','当前请求不可访问。'))
    api.status.mockResolvedValueOnce({...ready,can_enter:allowed,can_search:allowed,ask_enabled:allowed})
    await w.get('#knowledge-query').setValue('范围变更时的未发送草稿')
    await w.get('.knowledge-search').trigger('submit');await flushPromises()
    expect(api.status).toHaveBeenCalledTimes(2)
    expect(api.ask).toHaveBeenCalledTimes(1)
    expect(w.findAll('.answer-card')).toHaveLength(0)
    const submit=w.get('.knowledge-search button[type="submit"]')
    expect(submit.attributes('disabled')!==undefined).toBe(!allowed)
  })
})
