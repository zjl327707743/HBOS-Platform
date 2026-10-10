import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import Tools from '@/components/knowledge/KnowledgeTools.vue'
import { checkKnowledgeConnection } from '@/services/knowledgeConnectionCheck'
import type { ConnectionInfo } from '@/services/p1Api'
const api=vi.hoisted(()=>({page:vi.fn(),remove:vi.fn(),open:vi.fn(),ask:vi.fn()}))
vi.mock('@/services/p1Api',async original=>({...await original<typeof import('@/services/p1Api')>(),getKnowledgeActivityPage:api.page,removeKnowledgeSaved:api.remove,openKnowledgeSaved:api.open,askKnowledgeReference:api.ask,getKnowledgeDocumentsPage:async()=>({documents:[],total:0,page:1,page_size:50})}))
const Button=defineComponent({props:['disabled','htmlType'],template:'<button :disabled="disabled" :type="htmlType||\'button\'"><slot/></button>'})
const stubs={'a-button':Button,'a-drawer':true,'a-alert':true,'a-skeleton':true,'a-empty':true,'a-tag':true}
const item=(id:string)=>({id,query:'SYNTHETIC 问题',titles:['SYNTHETIC '+id],created_at:'2026-10-10',available:true,bookmark_type:'Document',document_ids:['DOC_DEMO'],version_ids:['VER_DEMO']})
const wrappers:ReturnType<typeof mount>[]=[]
async function view(){const w=mount(Tools,{props:{view:'favorites',subject:'A',query:'',selectedSpace:''},global:{stubs}});wrappers.push(w);await flushPromises();return w}
function deferred(){let resolve!:(value:any)=>void;const promise=new Promise(r=>{resolve=r});return {promise,resolve}}
beforeEach(()=>{vi.clearAllMocks();api.page.mockImplementation((_kind:string,page:number,pageSize:number)=>Promise.resolve({items:[item('PAGE_'+page)],page,page_size:pageSize,has_more:page===1}));api.remove.mockResolvedValue(undefined)})
afterEach(()=>{wrappers.splice(0).forEach(w=>w.unmount());vi.unstubAllGlobals()})
describe('UAT2 independent record views — synthetic boundary checks',()=>{
 it('keeps the server second page without clamping it to the local row count',async()=>{const w=await view();await w.findAll('button').find(b=>b.text()==='下一页')!.trigger('click');await flushPromises();expect(api.page).toHaveBeenLastCalledWith('Bookmark',2,4);expect(w.text()).toContain('PAGE_2');expect(w.text()).toContain('第 2 页');expect(w.text()).not.toContain('PAGE_1')})
 it('rejects the former user’s late record page',async()=>{const pending=deferred();api.page.mockReturnValueOnce(pending.promise);const w=await view();await w.setProps({subject:'B'});await flushPromises();pending.resolve({items:[item('PRIVATE_A')],page:1,page_size:4,has_more:false});await flushPromises();expect(w.text()).not.toContain('PRIVATE_A');expect(w.text()).toContain('PAGE_1')})
 it('opens an authorized Document bookmark as a summary without generating an answer',async()=>{const document={document_id:'DOC_DEMO',version_id:'VER_DEMO',title:'SYNTHETIC 资料',department:'SYNTHETIC',space_id:'SPACE_DEMO'};api.open.mockResolvedValue({query:'',space_ids:['SPACE_DEMO'],document,bookmark_type:'Document'});const w=await view();await w.get('.kb-doc-main').trigger('click');await flushPromises();expect(w.emitted('document')?.[0]).toEqual([document]);expect(api.ask).not.toHaveBeenCalled();expect(w.emitted('replay')).toBeUndefined()})
 it('only removes a favorite from the view after native deletion succeeds',async()=>{api.remove.mockRejectedValueOnce(new Error('SYNTHETIC failure'));const w=await view();await w.get('[aria-label="取消收藏"]').trigger('click');await flushPromises();expect(w.text()).toContain('PAGE_1');expect(api.remove).toHaveBeenCalledWith('PAGE_1')})
})
describe('MCP checks — synthetic protocol, not installed client claims',()=>{
 const info={endpoint:'http://localhost:3000/mcp',query_blocked:false} as ConnectionInfo
 const response=(result:any)=>({ok:true,text:async()=>JSON.stringify({result})})
 const envelope=(data:any)=>response({structuredContent:{ok:true,data}})
 it('stops at revoked authentication and never searches',async()=>{const fetcher=vi.fn().mockResolvedValue({ok:false,status:401});vi.stubGlobal('fetch',fetcher);const result=await checkKnowledgeConnection(info,'SYNTHETIC', '合成词',new AbortController().signal,()=>{});expect(result.authentication).toBe('failed');expect(result.search).toBe('pending');expect(fetcher).toHaveBeenCalledTimes(1)})
 it('rejects a tool list exposing get_source before making a search',async()=>{const fetcher=vi.fn().mockResolvedValueOnce(envelope({spaces:[]})).mockResolvedValueOnce(response({tools:['list_knowledge_spaces','search_knowledge','get_evidence','ask_knowledge','get_source'].map(name=>({name}))}));vi.stubGlobal('fetch',fetcher);const result=await checkKnowledgeConnection(info,'SYNTHETIC','合成词',new AbortController().signal,()=>{});expect(result.authentication).toBe('passed');expect(result.tools).toBe('failed');expect(fetcher).toHaveBeenCalledTimes(2)})
 it('validates identity, four tools, search and evidence separately without calling ask',async()=>{const fetcher=vi.fn().mockResolvedValueOnce(envelope({spaces:[]})).mockResolvedValueOnce(response({tools:['list_knowledge_spaces','search_knowledge','get_evidence','ask_knowledge'].map(name=>({name}))})).mockResolvedValueOnce(envelope({results:[{evidence_id:'EV_DEMO'}]})).mockResolvedValueOnce(envelope({title:'SYNTHETIC'}));vi.stubGlobal('fetch',fetcher);const result=await checkKnowledgeConnection(info,'SYNTHETIC','合成词',new AbortController().signal,()=>{});expect(result).toMatchObject({authentication:'passed',tools:'passed',search:'passed',evidence:'passed'});expect(fetcher.mock.calls.map(([,init])=>JSON.parse(init.body).params.name).filter(Boolean)).toEqual(['list_knowledge_spaces','search_knowledge','get_evidence'])})
})
