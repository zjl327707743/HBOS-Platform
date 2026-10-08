import {afterEach,beforeEach,expect,it,vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import KnowledgeView from '@/views/KnowledgeView.vue'

const api=vi.hoisted(()=>({status:vi.fn(),spaces:vi.fn(),documents:vi.fn(),search:vi.fn()}))
vi.mock('vue-router',()=>({useRoute:()=>({query:{q:'SYNTHETIC question',auto:'1'}})}))
vi.mock('@/stores/portal',()=>({usePortalStore:()=>({user:{id:'USER_DEMO'}})}))
vi.mock('@/services/p1Api',()=>({getKnowledgeStatus:api.status,getKnowledgeSpaces:api.spaces,
  getKnowledgeDocuments:api.documents,searchKnowledge:api.search,DomainApiError:class extends Error{}}))
const stubs={RouterLink:{template:'<span><slot/></span>'},KnowledgeTools:{template:'<p>个人记录</p>'},EvidenceDrawer:true,
  'a-alert':{props:['message'],template:'<p role="status">{{message}}</p>'},'a-button':{template:'<button><slot/></button>'},
  'a-tag':{template:'<span><slot/></span>'},'a-empty':true,'a-skeleton':true,'a-pagination':true}
const wrappers:ReturnType<typeof mount>[]=[]
function status(state='UNKNOWN',blocked=false){return {can_enter:true,can_search:true,gateway_configured:true,ask_enabled:true,mode:'retrieval',environment:'production',
  retrieval_availability:{configured:true,status:state,last_success_at:null,observed_at:null,observed_error:blocked?'UPSTREAM_UNAVAILABLE':null,blocked,expires_at:null,manual_recheck_required:blocked}}}
async function view(){const w=mount(KnowledgeView,{global:{stubs}});wrappers.push(w);await flushPromises();return w}
beforeEach(()=>{vi.clearAllMocks();api.status.mockResolvedValue(status());api.spaces.mockResolvedValue([]);api.documents.mockResolvedValue([{document_id:'DOC_DEMO',title:'SYNTHETIC reference',space_id:'SPACE_DEMO',department:'SYNTHETIC'}])})
afterEach(()=>wrappers.splice(0).forEach(w=>w.unmount()))

it('does not infer live availability from configuration or auto-query deep links',async()=>{
 const w=await view();expect(w.text()).toContain('当前可用性待实际检索确认');expect(api.search).not.toHaveBeenCalled()
 expect(w.get('#knowledge-query').element).toHaveProperty('value','SYNTHETIC question')
})
it('keeps catalog and personal records while blocking query and automatic model calls',async()=>{
 api.status.mockResolvedValue(status('OBSERVED_ERROR',true));const w=await view()
 expect(w.text()).toContain('检索服务暂不可用，目录与个人记录仍可查看。');expect(w.text()).toContain('SYNTHETIC reference');expect(w.text()).toContain('个人记录')
 await w.get('form').trigger('submit');expect(api.search).not.toHaveBeenCalled()
})
it('keeps a stale hard block distinct from an unknown current provider state',async()=>{
 api.status.mockResolvedValue(status('UNKNOWN',true));const w=await view()
 expect(w.text()).toContain('检索待恢复');expect(api.search).not.toHaveBeenCalled()
})
it('labels only a recent successful observation as ready',async()=>{
 api.status.mockResolvedValue(status('AVAILABLE'));const w=await view()
 expect(w.text()).toContain('最近检索成功');expect(api.search).not.toHaveBeenCalled()
})
