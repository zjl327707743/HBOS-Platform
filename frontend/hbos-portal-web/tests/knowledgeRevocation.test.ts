import { mount, flushPromises } from '@vue/test-utils'
import { reactive, defineComponent } from 'vue'
import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest'
import KnowledgeView from '@/views/KnowledgeView.vue'
import EvidenceDrawer from '@/components/knowledge/EvidenceDrawer.vue'
import type { KnowledgeEvidence } from '@/contracts/p1'
import { DomainApiError } from '@/services/p1Api'

const api = vi.hoisted(() => ({ status:vi.fn(), spaces:vi.fn(), search:vi.fn(), resolve:vi.fn() }))
vi.mock('@/services/p1Api', async importOriginal => ({
  ...(await importOriginal<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
  getKnowledgeSpaces: api.spaces,
  searchKnowledge: api.search,
  resolveKnowledgeEvidence: api.resolve,
}))
vi.mock('vue-router', () => ({ useRoute: () => ({query:{},path:'/hbos/knowledge'}) }))
const subject = reactive<{ user:{id:string}|null }>({user:{id:'USER_QA_DEMO'}})
vi.mock('@/stores/portal', () => ({ usePortalStore:() => subject }))

const Drawer = defineComponent({props:{open:Boolean},emits:['close'],
  template:'<section v-if="open" data-drawer><slot name="title"/><slot/><button data-close @click="$emit(\'close\')">close</button></section>'})
const Alert = defineComponent({props:{message:String},template:'<p data-error>{{message}}</p>'})
const stubs = {'a-drawer':Drawer,'a-alert':Alert,'a-tag':{template:'<span><slot/></span>'},
  'a-skeleton':{template:'<div data-loading/>'},'a-button':{template:'<button><slot/></button>'},
  'a-empty':{template:'<p data-empty/>'},RouterLink:{template:'<span><slot/></span>'}}
const wrappers: ReturnType<typeof mount>[] = []
const card = (suffix='A'):KnowledgeEvidence => ({
  document_id:'DOC_'+suffix+'_DEMO',title:'SYNTHETIC card '+suffix,version:null,status_note:'SYNTHETIC_ONLY',
  section:null,page_number:null,excerpt:'SYNTHETIC_EXCERPT_'+suffix+'_DEMO',evidence_id:'EV_'+suffix+'_DEMO',
  space_id:'SPACE_QA_DEMO',source_type:'SYNTHETIC_TEST',
})
function deferred<T>() {
  let resolve!:(value:T)=>void, reject!:(reason:unknown)=>void
  const promise = new Promise<T>((yes,no) => {resolve=yes;reject=no})
  return {promise,resolve,reject}
}
async function view(items=[card()]) {
  api.search.mockResolvedValue({request_id:'REQ_SEARCH_DEMO',mode:'retrieval',results:items})
  const wrapper = mount(KnowledgeView,{global:{stubs}})
  wrappers.push(wrapper)
  await flushPromises()
  await wrapper.find('input').setValue('SYNTHETIC query')
  await wrapper.find('form').trigger('submit')
  await flushPromises()
  return wrapper
}
beforeEach(() => {
  vi.clearAllMocks()
  subject.user = {id:'USER_QA_DEMO'}
  api.status.mockResolvedValue({can_enter:true,can_search:true,gateway_configured:true,ask_enabled:false,mode:'retrieval'})
  api.spaces.mockResolvedValue([{space_id:'SPACE_QA_DEMO',title:'SYNTHETIC QA',document_count:1}])
  api.resolve.mockResolvedValue(card())
})
afterEach(() => {wrappers.splice(0).forEach(wrapper => wrapper.unmount())})

describe('A36 real KnowledgeView/EvidenceDrawer component boundary, SYNTHETIC only', () => {
  it('each open performs resolve, never reuses the preview as evidence', async () => {
    const wrapper = await view()
    await wrapper.find('.result-card button').trigger('click')
    await flushPromises()
    expect(api.resolve).toHaveBeenCalledTimes(1)
    expect(wrapper.find('blockquote').text()).toBe(card().excerpt)
    await wrapper.find('[data-close]').trigger('click')
    expect(wrapper.find('blockquote').exists()).toBe(false)
    await wrapper.find('.result-card button').trigger('click')
    await flushPromises()
    expect(api.resolve).toHaveBeenCalledTimes(2)
  })

  it('clears old excerpt before a second resolve starts', async () => {
    const wrapper=await view([card(),card('B')])
    await wrapper.findAll('.result-card button')[0].trigger('click')
    await flushPromises()
    const next=deferred<KnowledgeEvidence>(); api.resolve.mockReturnValueOnce(next.promise)
    await wrapper.findAll('.result-card button')[1].trigger('click')
    expect(wrapper.find('blockquote').exists()).toBe(false)
    next.resolve(card('B')); await flushPromises()
    expect(wrapper.find('blockquote').text()).toBe(card('B').excerpt)
  })

  it('rapid A then B: slow A cannot replace B', async () => {
    const wrapper=await view([card(),card('B')])
    const a=deferred<KnowledgeEvidence>(), b=deferred<KnowledgeEvidence>()
    api.resolve.mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise)
    await wrapper.findAll('.result-card button')[0].trigger('click')
    const signalA=api.resolve.mock.calls[0][1] as AbortSignal
    await wrapper.findAll('.result-card button')[1].trigger('click')
    expect(signalA.aborted).toBe(true)
    b.resolve(card('B')); await flushPromises()
    a.resolve(card()); await flushPromises()
    expect(wrapper.find('blockquote').text()).toBe(card('B').excerpt)
  })

  it('close cancels and late success cannot reopen', async () => {
    const wrapper=await view()
    const pending=deferred<KnowledgeEvidence>(); api.resolve.mockReturnValueOnce(pending.promise)
    await wrapper.find('.result-card button').trigger('click')
    const signal=api.resolve.mock.calls[0][1] as AbortSignal
    await wrapper.find('[data-close]').trigger('click')
    pending.resolve(card()); await flushPromises()
    expect(signal.aborted).toBe(true)
    expect(wrapper.find('[data-drawer]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('正在核验依据')
  })

  it.each(['USER_PROD_DEMO',null])('switch user / logout clears and rejects late success: %s',async id => {
    const wrapper=await view()
    const pending=deferred<KnowledgeEvidence>(); api.resolve.mockReturnValueOnce(pending.promise)
    await wrapper.find('.result-card button').trigger('click')
    subject.user=id?{id}:null
    await flushPromises()
    pending.resolve(card()); await flushPromises()
    expect(wrapper.find('blockquote').exists()).toBe(false)
    expect(wrapper.text()).not.toContain(card().excerpt)
    expect(wrapper.find('.result-card').exists()).toBe(false)
  })

  it('same user logout/login still invalidates the request generation',async () => {
    const wrapper=await view()
    const pending=deferred<KnowledgeEvidence>(); api.resolve.mockReturnValueOnce(pending.promise)
    await wrapper.find('.result-card button').trigger('click')
    subject.user=null
    subject.user={id:'USER_QA_DEMO'}
    pending.resolve(card()); await flushPromises()
    expect(wrapper.find('blockquote').exists()).toBe(false)
    expect(wrapper.text()).not.toContain(card().excerpt)
  })

  it('revoked evidence clears drawer and previous result previews',async () => {
    const wrapper=await view()
    await wrapper.find('.result-card button').trigger('click'); await flushPromises()
    await wrapper.find('[data-close]').trigger('click')
    api.resolve.mockRejectedValueOnce(new DomainApiError('EVIDENCE_UNAVAILABLE','该证据不可用或已失效。'))
    await wrapper.find('.result-card button').trigger('click'); await flushPromises()
    expect(wrapper.find('blockquote').exists()).toBe(false)
    expect(wrapper.find('[data-error]').text()).toBe('该证据不可用或已失效。')
    expect(wrapper.text()).not.toContain(card().excerpt)
  })

  it('late old failure cannot clear a newer successful evidence',async () => {
    const wrapper=await view([card(),card('B')]); const a=deferred<KnowledgeEvidence>()
    api.resolve.mockReturnValueOnce(a.promise).mockResolvedValueOnce(card('B'))
    await wrapper.findAll('.result-card button')[0].trigger('click')
    await wrapper.findAll('.result-card button')[1].trigger('click'); await flushPromises()
    a.reject(new Error('SYNTHETIC old failure')); await flushPromises()
    expect(wrapper.find('blockquote').text()).toBe(card('B').excerpt)
    expect(wrapper.find('[data-error]').exists()).toBe(false)
  })

  it('unknown service error is fixed text; no raw path is rendered',async () => {
    const wrapper=await view()
    api.resolve.mockRejectedValueOnce(new Error('/SYNTHETIC/private/file.pdf'))
    await wrapper.find('.result-card button').trigger('click'); await flushPromises()
    expect(wrapper.find('blockquote').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('/SYNTHETIC')
  })

  it('unknown business version/page stay explicitly unverified',async () => {
    const wrapper=await view()
    await wrapper.find('.result-card button').trigger('click'); await flushPromises()
    expect(wrapper.find('[data-drawer]').text()).toContain('版本未核')
    expect(wrapper.find('[data-drawer]').text()).toContain('定位未核')
    expect(wrapper.find('[data-drawer]').text()).toContain('SYNTHETIC_ONLY')
    expect(wrapper.find('a[href]').exists()).toBe(false)
  })

  it('closed EvidenceDrawer never exposes retained props',async () => {
    const wrapper=mount(EvidenceDrawer,{props:{open:false,loading:false,error:null,evidence:card()},global:{stubs}})
    wrappers.push(wrapper)
    expect(wrapper.text()).not.toContain(card().excerpt)
  })

  it('search response arriving after logout cannot refill result previews',async () => {
    const pending=deferred<{request_id:string,mode:'retrieval',results:KnowledgeEvidence[]}>()
    api.search.mockReturnValueOnce(pending.promise)
    const wrapper=mount(KnowledgeView,{global:{stubs}}); wrappers.push(wrapper); await flushPromises()
    await wrapper.find('input').setValue('SYNTHETIC query'); await wrapper.find('form').trigger('submit')
    subject.user=null; pending.resolve({request_id:'REQ_LATE_DEMO',mode:'retrieval',results:[card()]})
    await flushPromises()
    expect(wrapper.text()).not.toContain(card().excerpt)
    expect(wrapper.find('.result-card').exists()).toBe(false)
  })

  it('unmount invalidates pending evidence',async () => {
    const wrapper=await view(); const pending=deferred<KnowledgeEvidence>()
    api.resolve.mockReturnValueOnce(pending.promise)
    await wrapper.find('.result-card button').trigger('click')
    const signal=api.resolve.mock.calls[0][1] as AbortSignal
    wrapper.unmount(); pending.resolve(card()); await flushPromises()
    expect(signal.aborted).toBe(true)
  })
})
