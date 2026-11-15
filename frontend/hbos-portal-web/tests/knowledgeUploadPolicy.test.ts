import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, expect, it, vi } from 'vitest'
const api=vi.hoisted(()=>({status:vi.fn(),maintenance:vi.fn(),upload:vi.fn()}))
vi.mock('vue-router',()=>({useRoute:()=>({path:'/hbos/knowledge/maintenance/upload'}),useRouter:()=>({push:vi.fn()})}))
vi.mock('@/services/p1Api',async()=>({...await vi.importActual<any>('@/services/p1Api'),getKnowledgeStatus:api.status}))
vi.mock('@/services/knowledgeMaintenanceApi',()=>({getMaintenance:api.maintenance,getMaintenanceFeedbackPage:vi.fn(),maintenanceAction:vi.fn(),previewImport:vi.fn(),uploadKnowledge:api.upload}))
import View from '@/views/KnowledgeMaintenanceView.vue'
const Button=defineComponent({template:'<button><slot/></button>'})
const Checkbox=defineComponent({props:['checked'],emits:['update:checked'],template:'<input type="checkbox" :checked="checked" @change="$emit(\'update:checked\',$event.target.checked)"/>'})
const Select=defineComponent({template:'<select/>'})
const Alert=defineComponent({props:['message'],template:'<p role="alert">{{message}}</p>'})
function render(){return mount(View,{global:{stubs:{'a-button':Button,'a-checkbox':Checkbox,'a-select':Select,'a-alert':Alert,'a-result':true,'a-skeleton':true,'a-drawer':true,'a-collapse':true,'a-collapse-panel':true,'a-pagination':true,'a-input-search':true,KnowledgeBatchMaintenance:true}}})}
beforeEach(()=>{
 vi.resetAllMocks();api.status.mockResolvedValue({can_maintain:true})
 api.maintenance.mockResolvedValue({departments:[{key:'production',title:'生产'}],published_documents:[],batches:[],selected:null,feedback:{items:[]},import_availability:{can_parse:true},upload_policy:{max_source_bytes:64*1024**2,native_templates_enabled:true,templates:[{key:'auto',title:'按文件类型推荐'},{key:'text_pdf',title:'文字 PDF（可选中文字）'}]}})
 api.upload.mockResolvedValue({batch_id:'IMP_synthetic'})
})
it('uses server size policy and rejects oversize before upload without allocating its body',async()=>{
 const w=render();await flushPromises();expect(w.text()).toContain('64 MiB')
 const f=new File(['%PDF-'],'oversize.pdf');Object.defineProperty(f,'size',{value:64*1024**2+1})
 const input=w.find('input[type=file]');Object.defineProperty(input.element,'files',{configurable:true,value:[f]});await input.trigger('change')
 expect(w.text()).toContain('超过 64 MiB');expect(w.text()).toContain('选择文件');expect(api.upload).not.toHaveBeenCalled();w.unmount()
})
it('shows PDF choices and submits the recommended default with a within-policy upload',async()=>{
 const w=render();await flushPromises();const f=new File(['%PDF-'],'qa.pdf')
 const input=w.find('input[type=file]');Object.defineProperty(input.element,'files',{value:[f]});await input.trigger('change')
 expect(w.find('[aria-label="PDF解析方式"]').exists()).toBe(true)
 await w.find('input[type=checkbox]').setValue(true)
 await w.findAll('button').find(b=>b.text().includes('上传并检查重复'))!.trigger('click');await flushPromises()
 expect(api.upload).toHaveBeenCalledWith(f,'production',true,undefined,'auto');w.unmount()
})
