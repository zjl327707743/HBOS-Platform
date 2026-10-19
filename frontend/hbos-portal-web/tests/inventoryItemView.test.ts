import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { reactive, nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import View from '@/views/InventoryItemReadOnlyView.vue'
import { searchItems, getItem } from '@/services/inventoryItems'
import { FrappeRequestError } from '@/services/frappeClient'
const portal = reactive({ user: { id: 'synthetic-a' } as {id:string}|null, apps: [{id:'inventory'}] })
const route = reactive({ params: {} as Record<string,string>, query: {} as Record<string,string> })
const push = vi.fn(), replace = vi.fn()
vi.mock('@/stores/portal',()=>({usePortalStore:()=>portal}))
vi.mock('@/services/portalProvider',()=>({portalDataSource:'frappe'}))
vi.mock('vue-router',()=>({useRoute:()=>route,useRouter:()=>({push,replace})}))
vi.mock('@/services/inventoryItems',()=>({searchItems:vi.fn(),getItem:vi.fn(),itemMasterGaps:()=>[]}))
const pending = <T,>() => { let resolve!: (value:T)=>void; const promise=new Promise<T>(r=>{resolve=r}); return {promise,resolve} }
const mounted: ReturnType<typeof mount>[]=[]
function render() { const wrapper=mount(View,{global:{stubs:{ForbiddenView:{template:'<div>ACCESS DENIED</div>'}}}});mounted.push(wrapper);return wrapper }
beforeEach(()=>{
  portal.user={id:'synthetic-a'};portal.apps=[{id:'inventory'}];route.params={};route.query={}
  vi.mocked(searchItems).mockReset().mockResolvedValue({rows:[],truncated:false})
  vi.mocked(getItem).mockReset().mockResolvedValue(null)
})
afterEach(()=>{ mounted.splice(0).forEach(w=>w.unmount()); vi.useRealTimers() })
it('makes no data calls when inventory was not granted by bootstrap', async()=>{
  portal.apps=[];const w=render();await flushPromises()
  expect(w.text()).toContain('ACCESS DENIED');expect(searchItems).not.toHaveBeenCalled();expect(getItem).not.toHaveBeenCalled()
})
it('distinguishes a permission failure from an empty visible list', async()=>{
  vi.mocked(searchItems).mockRejectedValue(new FrappeRequestError('FORBIDDEN','hidden',403))
  const w=render();await flushPromises();expect(w.text()).toContain('当前账号无权');expect(w.text()).not.toContain('系统里还没有物料')
})
it('shows normalized detail permission errors without stale content', async()=>{
  route.params={itemCode:'B'};vi.mocked(getItem).mockRejectedValue(new FrappeRequestError('FORBIDDEN','hidden',403))
  const w=render();await flushPromises();expect(w.text()).toContain('当前账号无权');expect(w.text()).not.toContain('可能已被删除')
})
it('ignores an older search response after a newer URL query', async()=>{
  const old=pending<{rows:{name:string,item_name:string}[];truncated:boolean}>()
  vi.mocked(searchItems).mockReturnValueOnce(old.promise).mockResolvedValue({rows:[{name:'NEW',item_name:'New visible'}],truncated:false})
  const w=render();route.query={q:'new'};await flushPromises()
  old.resolve({rows:[{name:'OLD',item_name:'Old stale'}],truncated:false});await flushPromises()
  expect(w.text()).toContain('New visible');expect(w.text()).not.toContain('Old stale')
})
it('ignores old detail after selecting another item and retains search in links', async()=>{
  const old=pending<{name:string,item_name:string}|null>()
  route.query={q:'term'};route.params={itemCode:'OLD'}
  vi.mocked(getItem).mockReturnValueOnce(old.promise).mockResolvedValue({name:'NEW',item_name:'New detail'})
  const w=render();route.params={itemCode:'NEW'};await flushPromises()
  old.resolve({name:'OLD',item_name:'Old detail'});await flushPromises()
  expect(w.text()).toContain('New detail');expect(w.text()).not.toContain('Old detail')
})
it('removes loaded data immediately when bootstrap access is revoked', async()=>{
  vi.mocked(searchItems).mockResolvedValue({rows:[{name:'A',item_name:'Sensitive visible A'}],truncated:false})
  const w=render();await flushPromises();expect(w.text()).toContain('Sensitive visible A')
  portal.apps=[];await nextTick();expect(w.text()).toContain('ACCESS DENIED');expect(w.text()).not.toContain('Sensitive visible A')
})
it('reloads search state from URL when using browser history', async()=>{
  render();await flushPromises();route.query={q:'history'};await flushPromises()
  expect(searchItems).toHaveBeenLastCalledWith('history')
})
it('renders source fields without report or mutation entry points', async()=>{
  route.params={itemCode:'A'};vi.mocked(getItem).mockResolvedValue({name:'A',item_name:'Real projected field'})
  const w=render();await flushPromises();expect(w.text()).toContain('Real projected field');expect(w.text()).not.toContain('看它在哪些货位');expect(w.text()).not.toContain('按批号查货位')
})
