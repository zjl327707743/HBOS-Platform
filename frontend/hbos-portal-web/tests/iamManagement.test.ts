import {expect,it,vi,beforeEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import Antd, {message} from 'ant-design-vue'
vi.mock('@/services/iamWork',async(importOriginal)=>({...await importOriginal<object>(),getWorkSummary:vi.fn(),getEffectiveWork:vi.fn(),previewAppSettings:vi.fn(),saveAppSettings:vi.fn(),previewWork:vi.fn(),workAction:vi.fn()}))
vi.mock('@/services/iamPeople',()=>({getPerson:vi.fn()}))
import {getWorkSummary,getEffectiveWork,previewAppSettings,saveAppSettings,previewWork,workAction} from '@/services/iamWork'
import {getPerson} from '@/services/iamPeople'
import {clearIamAccess,iamSession} from '@/services/iamAccess'
import AdminWorkspace from '@/views/admin/AdminWorkspaceView.vue'
import AppUsageList from '@/components/iam/AppUsageList.vue'
import AttendanceAccessSummary from '@/components/iam/AttendanceAccessSummary.vue'
import AppAccessAction from '@/components/iam/AppAccessAction.vue'
import WorkSettings from '@/components/iam/WorkSettings.vue'
const app={app_id:'attendance',title:'考勤',integrated:true,status:'可以使用',summary:'只显示本人考勤',source_text:'来自所属部门',permission_mode:'personal' as const,operations:[],version:1,context_revision:'r1'}
beforeEach(()=>{clearIamAccess();vi.resetAllMocks()})
it('shows each management entry only for its own capability',()=>{Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.departments.read']});const wrapper=mount(AdminWorkspace,{global:{plugins:[Antd],stubs:{RouterLink:{template:'<a><slot/></a>'},RouterView:true}}});expect(wrapper.text()).toContain('部门安排');expect(wrapper.text()).not.toContain('员工管理');expect(wrapper.text()).not.toContain('变更记录');wrapper.unmount()})
it('reuses the application list in read-only mode without modification controls',async()=>{vi.mocked(getWorkSummary).mockResolvedValue({subject_type:'User',subject_name:'user-a',apps:[app]});const wrapper=mount(AppUsageList,{props:{employeeId:'EMP-a',canEdit:false},global:{plugins:[Antd]}});await flushPromises();expect(wrapper.text()).toContain('只显示本人考勤');expect(wrapper.text()).not.toContain('查看与修改');wrapper.unmount()})
it('configuration summary explains the boundary without rendering target business records',()=>{const wrapper=mount(AttendanceAccessSummary,{props:{app}});expect(wrapper.text()).toContain('配置页只核对权限，不读取员工的考勤记录');expect(wrapper.find('table').exists()).toBe(false)})
it('R2-06: fixed SELF is implicit once, disable sends no scope, and only a server-authorized department link is shown',async()=>{
  Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.people.read','iam.access.manage']})
  vi.mocked(getPerson).mockResolvedValue({employee:{id:'EMP-a',user_id:'user-a',account_status:'active'}} as never)
  const configured={...app,department_default:{id:'synthetic-D1',name:'验收部门甲',enabled:true,suspended:false,can_open:false},operations:[{operation_id:'attendance.read',label:'查看自己的考勤',enabled:false,scopes:[],objects:[{scope_type:'SELF',scope_ref:'',label:'本人'}],source_text:'个人设置',editable:true}]}
  vi.mocked(getEffectiveWork).mockResolvedValue(configured);vi.mocked(previewAppSettings).mockResolvedValue({version:1,context_revision:'r1',changed:true,summary:'仅本人',after:configured})
  const w=mount(WorkSettings,{props:{subjectKind:'employee',subjectId:'EMP-a',appId:'attendance'},global:{plugins:[Antd],stubs:{RouterLink:{template:'<a><slot /></a>'}}}});await flushPromises()
  expect(w.text()).toContain('【验收部门甲】的默认权限：可查看本人考勤');expect(w.findAll('a').some(row=>row.text()==='查看部门默认')).toBe(false)
  await w.findAll('button').find(row=>row.text()==='设置权限')!.trigger('click');expect(w.findAll('input[type="checkbox"]')).toHaveLength(1)
  await w.find('input[type="checkbox"]').setValue(true);await w.find('form').trigger('submit');await flushPromises()
  expect(previewAppSettings).toHaveBeenLastCalledWith(expect.anything(),expect.objectContaining({changes:[{operation_id:'attendance.read',enabled:true,scopes:[{scope_type:'SELF',scope_ref:''}]}]}))
  await w.findAll('button').find(row=>row.text()==='返回核对')!.trigger('click');await w.find('input[type="checkbox"]').setValue(false);await w.find('form').trigger('submit');await flushPromises()
  expect(previewAppSettings).toHaveBeenLastCalledWith(expect.anything(),expect.objectContaining({changes:[{operation_id:'attendance.read',enabled:false,scopes:[]}]}));w.unmount()
})
it('retains an edited work draft after a real conflict and emits no saved success',async()=>{
  Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.people.read','iam.access.manage']})
  vi.mocked(getPerson).mockResolvedValue({employee:{id:'EMP-a',user_id:'user-a',account_status:'active'}} as never)
  const configured={...app,operations:[{operation_id:'attendance.read',label:'查看自己的考勤',enabled:true,scopes:[{scope_type:'SELF',scope_ref:'',label:'本人'}],objects:[{scope_type:'SELF',scope_ref:'',label:'本人'}],source_text:'部门安排',editable:true}]}
  vi.mocked(getEffectiveWork).mockResolvedValue(configured)
  vi.mocked(previewAppSettings).mockResolvedValue({version:1,context_revision:'r1',changed:true,summary:'未安排本人考勤',after:configured})
  vi.mocked(saveAppSettings).mockRejectedValue(Object.assign(new Error('version changed'),{status:409}))
  const success=vi.spyOn(message,'success')
  const wrapper=mount(WorkSettings,{props:{subjectKind:'employee',subjectId:'EMP-a',appId:'attendance'},global:{plugins:[Antd]}})
  await flushPromises()
  const click=async(text:string)=>{const button=wrapper.findAll('button').find(row=>row.text()===text);expect(button).toBeDefined();await button!.trigger('click');await flushPromises()}
  await click('设置权限');await wrapper.find('input[type="checkbox"]').setValue(false);await wrapper.find('form').trigger('submit');await flushPromises();await click('确认保存')
  expect(wrapper.text()).toContain('草稿已保留');expect((wrapper.find('input[type="checkbox"]').element as HTMLInputElement).checked).toBe(false);expect(wrapper.emitted('saved')).toBeUndefined();expect(success).not.toHaveBeenCalled()
  wrapper.unmount();success.mockRestore()
})
it('keeps a temporary disable while changing ordinary permissions and removes pause from the ordinary form',async()=>{
  Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.people.read','iam.access.manage']})
  vi.mocked(getPerson).mockResolvedValue({employee:{id:'EMP-a',user_id:'user-a',account_status:'active'}} as never)
  const configured={...app,suspended:true,operations:[{operation_id:'attendance.read',label:'查看自己的考勤',enabled:false,scopes:[],objects:[{scope_type:'SELF',scope_ref:''}],source_text:'个人设置',editable:true}]}
  vi.mocked(getEffectiveWork).mockResolvedValue(configured)
  vi.mocked(previewAppSettings).mockResolvedValue({version:1,context_revision:'r1',changed:true,summary:'仍临时禁用',after:configured})
  const w=mount(WorkSettings,{props:{subjectKind:'employee',subjectId:'EMP-a',appId:'attendance'},global:{plugins:[Antd]}})
  await flushPromises();await w.findAll('button').find(row=>row.text()==='设置权限')!.trigger('click')
  expect(w.text()).not.toContain('应用总限制');expect(w.find('input[value="paused"]').exists()).toBe(false)
  await w.find('input[type="checkbox"]').setValue(true);await w.find('form').trigger('submit');await flushPromises()
  expect(previewAppSettings).toHaveBeenCalledWith(expect.anything(),expect.objectContaining({access_state:'paused',changes:[{operation_id:'attendance.read',enabled:true,scopes:[{scope_type:'SELF',scope_ref:''}]}]}));w.unmount()
})
it('uses a single more action with server preview, cancellation and the original constrained command',async()=>{
  const configured={...app,suspended:false}
  vi.mocked(previewWork).mockResolvedValue({version:1,context_revision:'confirmed',changed:true,summary:'已禁用',after:{...configured,suspended:true}})
  vi.mocked(workAction).mockResolvedValue({} as never)
  const w=mount(AppAccessAction,{attachTo:document.body,props:{app:configured,target:{subject_type:'User',subject_name:'user-a',app_id:'attendance'}},global:{plugins:[Antd]}})
  const open=async()=>{await w.find('button').trigger('click');await flushPromises();(document.querySelector('[role="menuitem"]') as HTMLElement).click();await flushPromises()}
  await open();expect(previewWork).toHaveBeenCalledWith(expect.objectContaining({changes:[],expected_version:1}),'suspend')
  let buttons=Array.from(document.querySelectorAll('.ant-modal button'));(buttons.find(b=>b.textContent?.replace(/\s/g,'')==='取消') as HTMLElement).click();await flushPromises();expect(workAction).not.toHaveBeenCalled()
  await open();buttons=Array.from(document.querySelectorAll('.ant-modal button'));(buttons.find(b=>b.textContent?.includes('确认临时禁用')) as HTMLElement).click();await flushPromises()
  expect(workAction).toHaveBeenCalledWith('suspend_app',{subject_type:'User',subject_name:'user-a',app_id:'attendance'},1,'confirmed',expect.any(String));expect(w.emitted('saved')).toHaveLength(1);w.unmount()
})
it('keeps an individual preview summary without department impact counts or employee lists',async()=>{
  Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.people.read','iam.access.manage']})
  vi.mocked(getPerson).mockResolvedValue({employee:{id:'EMP-a',user_id:'user-a',account_status:'active'}} as never)
  vi.mocked(getEffectiveWork).mockResolvedValue(app)
  vi.mocked(previewAppSettings).mockResolvedValue({version:1,context_revision:'r1',changed:true,summary:'服务端影响已核对',after:app,impact:{changed:1,personal_preserved:1,unavailable:0,employees:[{name:'员工甲',result:'本次只停用该员工的考勤入口，已有工作安排保留。',personal_preserved:true}]}})
  const wrapper=mount(WorkSettings,{props:{subjectKind:'employee',subjectId:'EMP-a',appId:'attendance'},global:{plugins:[Antd]}})
  await flushPromises();await wrapper.findAll('button').find(row=>row.text()==='设置权限')!.trigger('click');await wrapper.find('input[value="department"]').setValue(true);await wrapper.find('form').trigger('submit');await flushPromises()
  expect(wrapper.text()).toContain('服务端影响已核对')
  expect(wrapper.text()).not.toContain('跟随变化');expect(wrapper.text()).not.toContain('查看全部受影响员工');expect(wrapper.text()).not.toContain('员工甲')
  expect(wrapper.text()).not.toContain('undefined');expect(wrapper.text()).not.toContain('→')
  wrapper.unmount()
})

it('cancels all combined settings without a preview or save request',async()=>{
  Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.people.read','iam.access.manage']})
  vi.mocked(getPerson).mockResolvedValue({employee:{id:'EMP-a',user_id:'user-a',account_status:'active'}} as never)
  vi.mocked(getEffectiveWork).mockResolvedValue(app)
  const wrapper=mount(WorkSettings,{props:{subjectKind:'employee',subjectId:'EMP-a',appId:'attendance'},global:{plugins:[Antd]}})
  await flushPromises();await wrapper.findAll('button').find(row=>row.text()==='设置权限')!.trigger('click');await wrapper.find('input[value="department"]').setValue(true)
  await wrapper.findAll('button').find(row=>row.text()==='取消修改')!.trigger('click');await flushPromises()
  expect(previewAppSettings).not.toHaveBeenCalled();expect(saveAppSettings).not.toHaveBeenCalled();expect(wrapper.emitted('saved')).toBeUndefined();wrapper.unmount()
})
