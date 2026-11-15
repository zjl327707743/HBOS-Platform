import {mount,flushPromises} from '@vue/test-utils'
import {defineComponent} from 'vue'
import {describe,it,expect,vi} from 'vitest'
const api=vi.hoisted(()=>({status:vi.fn(),dashboard:vi.fn()}))
vi.mock('vue-router',()=>({useRoute:()=>({path:'/hbos/knowledge/maintenance'}),useRouter:()=>({push:vi.fn()})}))
vi.mock('@/services/p1Api',async original=>({...await original<typeof import('@/services/p1Api')>(),getKnowledgeStatus:api.status}))
vi.mock('@/services/knowledgeMaintenanceApi',async original=>({...await original<typeof import('@/services/knowledgeMaintenanceApi')>(),getMaintenance:api.dashboard}))
import View from '@/views/KnowledgeMaintenanceView.vue'
const Button=defineComponent({template:'<button><slot/></button>'})
describe('maintenance V3 overview',()=>{
 it('shows four overview cards and an explicit batch entry while preserving bounded lookup',async()=>{
  api.status.mockResolvedValue({can_maintain:true})
  api.dashboard.mockResolvedValue({departments:[],published_documents:[],batches:[],selected:null,import_availability:{can_parse:false}})
  const w=mount(View,{global:{stubs:{KnowledgeBatchMaintenance:true,'a-button':Button,'a-input-search':true,'a-select':true,'a-skeleton':true,'a-result':true,'a-tag':defineComponent({template:'<span><slot/></span>'}),'a-alert':true,'a-drawer':true,'a-empty':true}}})
  await flushPromises()
  expect(w.findAll('.v17-stat')).toHaveLength(4)
  expect(w.get('.v17-batch').text()).toContain('打开批量预演')
  expect(w.find('.v17-table-wrap table').exists()).toBe(true)
  expect(w.find('[data-published-search]').exists()).toBe(true)
  expect(w.get('.v17-stats').text()).toContain('当前已发布—')
  w.unmount()
 })
 it('selects only eligible pending rows and exposes their quality action',async()=>{
  api.status.mockResolvedValue({can_maintain:true})
  const item={document_id:'DOC_SYNTHETIC',version_id:'V1',current_version:'V1',title:'合成待核对',relationship:'NEW',parse_status:'parsed/indexed',quality_status:'Pending',shared_approved:false,publication_status:'Unpublished'}
  api.dashboard.mockResolvedValue({departments:[{key:'production',title:'合成部门'}],published_documents:[],batches:[{name:'B1',label:'合成批次'}],selected:{batch_id:'B1',department:'production',items:[item],page:1,total:1,counts:{parsed:1,quality_passed:0}},import_availability:{can_parse:false}})
  const w=mount(View,{global:{stubs:{KnowledgeBatchMaintenance:true,'a-button':Button,'a-input-search':true,'a-select':true,'a-skeleton':true,'a-result':true,'a-tag':true,'a-alert':true,'a-drawer':true,'a-empty':true}}})
  await flushPromises()
  const row=w.get('input[aria-label="选择 合成待核对"]')
  expect(row.attributes('disabled')).toBeUndefined()
  await row.setValue(true)
  expect(w.text()).toContain('已选 1 份')
  expect(w.text()).toContain('核对质量')
  await row.setValue(false)
  expect(w.text()).not.toContain('已选 1 份')
  w.unmount()
 })

})
