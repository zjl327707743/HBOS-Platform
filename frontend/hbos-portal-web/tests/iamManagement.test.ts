import {expect,it,vi,beforeEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import Antd, {message} from 'ant-design-vue'
vi.mock('@/services/iamWork',async(importOriginal)=>({...await importOriginal<object>(),getWorkSummary:vi.fn(),getEffectiveWork:vi.fn(),previewWork:vi.fn(),saveWork:vi.fn()}))
vi.mock('@/services/iamPeople',()=>({getPerson:vi.fn()}))
import {getWorkSummary,getEffectiveWork,previewWork,saveWork} from '@/services/iamWork'
import {getPerson} from '@/services/iamPeople'
import {clearIamAccess,iamSession} from '@/services/iamAccess'
import AdminWorkspace from '@/views/admin/AdminWorkspaceView.vue'
import AppUsageList from '@/components/iam/AppUsageList.vue'
import AttendanceAccessSummary from '@/components/iam/AttendanceAccessSummary.vue'
import WorkSettings from '@/components/iam/WorkSettings.vue'
const app={app_id:'attendance',title:'考勤',integrated:true,status:'可以使用',summary:'只显示本人考勤',source_text:'部门安排',operations:[],version:1,context_revision:'r1'}
beforeEach(()=>{clearIamAccess();vi.resetAllMocks()})
it('shows each management entry only for its own capability',()=>{Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.departments.read']});const wrapper=mount(AdminWorkspace,{global:{plugins:[Antd],stubs:{RouterLink:{template:'<a><slot/></a>'},RouterView:true}}});expect(wrapper.text()).toContain('部门管理');expect(wrapper.text()).not.toContain('员工管理');expect(wrapper.text()).not.toContain('变更审计');wrapper.unmount()})
it('reuses the application list in read-only mode without modification controls',async()=>{vi.mocked(getWorkSummary).mockResolvedValue({subject_type:'User',subject_name:'user-a',apps:[app]});const wrapper=mount(AppUsageList,{props:{employeeId:'EMP-a',canEdit:false},global:{plugins:[Antd]}});await flushPromises();expect(wrapper.text()).toContain('只显示本人考勤');expect(wrapper.text()).not.toContain('查看与修改');wrapper.unmount()})
it('configuration summary explains the boundary without rendering target business records',()=>{const wrapper=mount(AttendanceAccessSummary,{props:{app}});expect(wrapper.text()).toContain('本人真实考勤请使用自己的会话');expect(wrapper.find('table').exists()).toBe(false)})
it('retains an edited work draft after a real conflict and emits no saved success',async()=>{
  Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.people.read','iam.access.manage']})
  vi.mocked(getPerson).mockResolvedValue({employee:{id:'EMP-a',user_id:'user-a',account_status:'active'}} as never)
  const configured={...app,operations:[{operation_id:'attendance.read',label:'查看自己的考勤',enabled:true,scopes:[{scope_type:'SELF',scope_ref:'',label:'本人'}],objects:[{scope_type:'SELF',scope_ref:'',label:'本人'}],source_text:'部门安排',editable:true}]}
  vi.mocked(getEffectiveWork).mockResolvedValue(configured)
  vi.mocked(previewWork).mockResolvedValue({version:1,context_revision:'r1',changed:true,summary:'未安排本人考勤',after:configured})
  vi.mocked(saveWork).mockRejectedValue(Object.assign(new Error('version changed'),{status:409}))
  const success=vi.spyOn(message,'success')
  const wrapper=mount(WorkSettings,{props:{subjectKind:'employee',subjectId:'EMP-a',appId:'attendance'},global:{plugins:[Antd]}})
  await flushPromises()
  const click=async(text:string)=>{const button=wrapper.findAll('button').find(row=>row.text()===text);expect(button).toBeDefined();await button!.trigger('click');await flushPromises()}
  await click('修改工作与对象');await wrapper.find('input[type="checkbox"]').setValue(false);await click('预览并保存');await click('确认保存一次')
  expect(wrapper.text()).toContain('草稿已保留');expect((wrapper.find('input[type="checkbox"]').element as HTMLInputElement).checked).toBe(false);expect(wrapper.emitted('saved')).toBeUndefined();expect(success).not.toHaveBeenCalled()
  wrapper.unmount();success.mockRestore()
})
it('keeps suspend and reenable previews available when timed ordinary rules are read-only',async()=>{
  Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.people.read','iam.access.manage']})
  vi.mocked(getPerson).mockResolvedValue({employee:{id:'EMP-a',user_id:'user-a',account_status:'active'}} as never)
  for(const suspended of [false,true]) {
    const configured={...app,suspended,operations:[{operation_id:'attendance.read',label:'查看自己的考勤',enabled:true,scopes:[{scope_type:'SELF',scope_ref:''}],source_text:'有期限的个人安排',editable:false}]}
    vi.mocked(getEffectiveWork).mockResolvedValue(configured)
    vi.mocked(previewWork).mockResolvedValue({version:1,context_revision:'r1',changed:true,summary:'服务端已重验安排',after:configured})
    vi.mocked(previewWork).mockClear()
    const wrapper=mount(WorkSettings,{props:{subjectKind:'employee',subjectId:'EMP-a',appId:'attendance'},global:{plugins:[Antd]}})
    await flushPromises()
    expect(wrapper.text()).not.toContain('修改工作与对象')
    const button=wrapper.findAll('button').find(row=>row.text()===(suspended?'重新启用并核对当前安排':'只停用此人此应用'))
    expect(button).toBeDefined();await button!.trigger('click');await flushPromises()
    expect(previewWork).toHaveBeenCalledWith(expect.objectContaining({target:{subject_type:'User',subject_name:'user-a',app_id:'attendance'},changes:[]}),suspended?'reenable':'suspend')
    expect(wrapper.text()).toContain('确认本次变更')
    wrapper.unmount()
  }
})
it('renders the server impact result as natural text without undefined before or after fields',async()=>{
  Object.assign(iamSession,{ready:true,user:'manager',capabilities:['iam.people.read','iam.access.manage']})
  vi.mocked(getPerson).mockResolvedValue({employee:{id:'EMP-a',user_id:'user-a',account_status:'active'}} as never)
  vi.mocked(getEffectiveWork).mockResolvedValue(app)
  vi.mocked(previewWork).mockResolvedValue({version:1,context_revision:'r1',changed:true,summary:'服务端影响已核对',after:app,impact:{changed:1,personal_preserved:1,unavailable:0,employees:[{name:'员工甲',result:'本次只停用该员工的考勤入口，已有工作安排保留。',personal_preserved:true}]}})
  const wrapper=mount(WorkSettings,{props:{subjectKind:'employee',subjectId:'EMP-a',appId:'attendance'},global:{plugins:[Antd]}})
  await flushPromises();await wrapper.findAll('button').find(row=>row.text()==='只停用此人此应用')!.trigger('click');await flushPromises()
  expect(wrapper.text()).toContain('员工甲：本次只停用该员工的考勤入口，已有工作安排保留。')
  expect(wrapper.text()).not.toContain('undefined');expect(wrapper.text()).not.toContain('→')
  wrapper.unmount()
})
