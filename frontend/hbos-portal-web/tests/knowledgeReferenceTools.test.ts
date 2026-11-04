import {expect,it,vi,beforeEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import KnowledgeTools from '@/components/knowledge/KnowledgeTools.vue'
const mock=vi.hoisted(()=>({ask:vi.fn(),activity:vi.fn(),open:vi.fn(),remove:vi.fn(),save:vi.fn(),feedback:vi.fn()}))
vi.mock('@/services/p1Api',()=>({askKnowledgeReference:mock.ask,getKnowledgeActivity:mock.activity,openKnowledgeSaved:mock.open,removeKnowledgeSaved:mock.remove,saveKnowledgeBookmark:mock.save,sendKnowledgeFeedback:mock.feedback,DomainApiError:class extends Error{}}))
beforeEach(()=>{vi.clearAllMocks();mock.activity.mockResolvedValue([])})
const props={subject:'user-a',query:'当前检索',selectedSpace:'DEPT_PRODUCTION',askEnabled:true}
it('suppresses a previous user’s in-flight answer and activity after account change',async()=>{
 let resolve!:(v:unknown)=>void;mock.ask.mockReturnValue(new Promise(r=>{resolve=r}))
 const w=mount(KnowledgeTools,{props,global:{stubs:{'a-button':{template:'<button><slot/></button>'},'a-alert':true,'a-tag':true}}})
 await flushPromises();await w.get('#knowledge-question').setValue('问题');await w.get('form').trigger('submit')
 await w.setProps({subject:'user-b'});resolve({turn_id:'old',answer:'previous-user-private-answer',citations:[],answerable:false});await flushPromises()
 expect(w.text()).not.toContain('previous-user-private-answer');expect(w.text()).not.toContain('继续追问');w.unmount()
})
it('reopens a saved reference through the server before emitting a fresh search',async()=>{
 mock.activity.mockImplementation((kind:string)=>Promise.resolve(kind==='Bookmark'?[{id:'saved',query:'旧问题',created_at:'2026-10-08',available:true,titles:['资料']}]:[]))
 mock.open.mockResolvedValue({query:'verified query',space_ids:['DEPT_PRODUCTION']})
 const w=mount(KnowledgeTools,{props,global:{stubs:{'a-button':{template:'<button><slot/></button>'},'a-alert':true,'a-tag':true}}})
 await flushPromises();await w.findAll('[role="tab"]')[1]!.trigger('click');await w.findAll('button').find(b=>b.text()==='重新查阅')!.trigger('click');await flushPromises()
 expect(mock.open).toHaveBeenCalledWith('saved');expect(w.emitted('replay')?.[0]).toEqual(['verified query',['DEPT_PRODUCTION']]);w.unmount()
})
it('restores a source-validated saved answer while new paid retrieval is blocked',async()=>{
 mock.activity.mockImplementation((kind:string)=>Promise.resolve(kind==='History'?[{id:'saved-answer',query:'已存问题',created_at:'2026-10-10',available:true,titles:['资料']}]:[]))
 const restored={query:'已存问题',space_ids:['DEPT_PRODUCTION'],restored:{mode:'ask',search_mode:'STANDARD',results:[],turns:[{turn_id:'saved-answer',question:'已存问题',answer:'已存答案',citations:[],answerable:true}]}}
 mock.open.mockResolvedValue(restored)
 const w=mount(KnowledgeTools,{props:{...props,retrievalBlocked:true},global:{stubs:{'a-button':{template:'<button><slot/></button>'},'a-alert':true,'a-tag':true}}})
 await flushPromises();const button=w.findAll('button').find(b=>b.text()==='重新查阅')!
 expect(button.attributes('disabled')).toBeUndefined();await button.trigger('click');await flushPromises()
 expect(mock.open).toHaveBeenCalledWith('saved-answer');expect(mock.ask).not.toHaveBeenCalled();expect(w.emitted('restored')?.[0]).toEqual([restored]);expect(w.text()).toContain('已存答案');w.unmount()
})
