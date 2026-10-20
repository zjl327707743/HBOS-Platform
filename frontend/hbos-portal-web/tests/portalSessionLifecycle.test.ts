import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import MyAttendanceView from '@/views/attendance/MyAttendanceView.vue'
import { defineComponent, onMounted, onBeforeUnmount } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
const api = vi.hoisted(() => ({ association: vi.fn(), attendance: vi.fn(), security: vi.fn(), caps: vi.fn(), bootstrap: vi.fn(), clear: vi.fn(), mounted: vi.fn(), unmounted: vi.fn(), block: vi.fn(), invalidate: vi.fn() }))
const portal = vi.hoisted(() => ({ user: null as null | {id:string}, branding:null, apps:[], tasks:[], bootstrap:api.bootstrap, clearSession:api.clear }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => portal }))
vi.mock('@/services/portalProvider', () => ({ portalDataSource: 'frappe' }))
vi.mock('@/services/iamAccount', () => ({ getIamSecurity: api.security, getMyEmployeeStatus:api.association }))
vi.mock('@/services/iamAccess', () => ({ iamSession:{revision:'r1'}, fetchIamAccess:api.caps, applyIamAccess:vi.fn(), clearIamAccess:vi.fn() }))
vi.mock('@/services/frappeClient', () => ({ blockFrappeWrites:api.block, invalidateFrappeRequests:api.invalidate,frappeDiagnostics:{},developmentObservation:false, isUnauthenticatedError:()=>false, FrappeRequestError:class extends Error {}, logoutFrappeSession:vi.fn() }))
vi.mock('@/services/attendancePersonal',()=>({getMyAttendance:api.attendance}))
import PortalLayout from '@/components/layout/PortalLayout.vue'
import { ensurePortalSession, portalSession, resetPortalSession } from '@/services/portalSessionCoordinator'
const security = (user='A', context='a') => ({ user, session_context:context.repeat(64), identity:{display_name:'测试员工',employee_number:'0001',department:'测试部门',login_name:'test'}, first_password_required:false, proof:{valid:false}, temporary_password_state:{pending:false,temporary:false,can_claim:false,generation:0} })
let wrapper: ReturnType<typeof mount> | undefined
beforeEach(() => {
  vi.useFakeTimers(); vi.clearAllMocks(); api.clear.mockImplementation(()=>{portal.user=null}); resetPortalSession()
  api.association.mockResolvedValue({status:'linked',employee_number:'0001'});api.attendance.mockImplementation(async (query: {date_from?:string;date_to?:string;page?:number})=>({date_from:query.date_from||'2026-09-18',date_to:query.date_to||'2026-10-18',rows:[{id:'1',date:'2026-10-14',source:'Employee Checkin',log_type:'IN',time:'08:11:00'},{id:'2',date:'2026-10-14',source:'Attendance',status:'Present'}],total:2,page:1,page_size:20,summary:{records:2,days:1}}));api.security.mockResolvedValue(security()); api.caps.mockResolvedValue({subject_user:'A',session_context:'a'.repeat(64),policy_revision:'r1',capabilities:[]}); api.bootstrap.mockImplementation(async()=>{portal.user={id:'A'}})
})
afterEach(()=>{wrapper?.unmount(); wrapper=undefined; vi.useRealTimers()})
async function render(path='/hbos/admin/people') {
  const Page = defineComponent({ setup() { onMounted(api.mounted); onBeforeUnmount(api.unmounted) }, template:'<section><input aria-label="筛选" value="" /><textarea aria-label="草稿" /><div style="height:2000px">实际路由内容</div></section>' })
  const router = createRouter({history:createMemoryHistory(),routes:[{path:'/hbos',component:PortalLayout,children:[{path:'admin/people',component:Page},{path:'attendance/me',component:MyAttendanceView}]}]})
  await router.push(path); await router.isReady()
  wrapper=mount(defineComponent({template:'<RouterView />'}),{attachTo:document.body,global:{plugins:[Antd,router],stubs:{GlobalHeader:true,PointerAtmosphere:true,PortalSidebar:true,MobilePortalNav:true,CommandPalette:true,'a-skeleton':true,'a-button':{template:'<button><slot /></button>'},'a-alert':{props:['message'],template:'<div>{{message}}</div>'}}}})
  await flushPromises(); await ensurePortalSession(); await flushPromises(); return wrapper
}
it('R01/R02: actual PortalLayout retains one route instance and draft through ten focus/pageshow/visibility bursts', async()=>{
  const w=await render(); await w.find('input').setValue('0001'); await w.find('textarea').setValue('尚未保存的安排')
  const input=w.find('input').element, area=w.find('textarea').element
  for(let i=0;i<10;i++) { await vi.advanceTimersByTimeAsync(5100); window.dispatchEvent(new Event('focus')); window.dispatchEvent(new Event('pageshow')); document.dispatchEvent(new Event('visibilitychange')); await vi.advanceTimersByTimeAsync(151); await flushPromises() }
  expect(api.security).toHaveBeenCalledTimes(11); expect(api.caps).toHaveBeenCalledTimes(11); expect(api.bootstrap).toHaveBeenCalledTimes(1)
  expect(api.mounted).toHaveBeenCalledTimes(1); expect(api.unmounted).not.toHaveBeenCalled()
  expect(w.find('input').element).toBe(input); expect((input as HTMLInputElement).value).toBe('0001'); expect((area as HTMLTextAreaElement).value).toBe('尚未保存的安排')
})
it('R02: slow and failed checks mask sensitive content and block writes while retaining the draft subtree',async()=>{
  const w=await render(); await w.find('textarea').setValue('保留我'); const area=w.find('textarea').element; (area as HTMLElement).focus()
  let reject!:(reason:unknown)=>void; api.security.mockImplementationOnce(()=>new Promise((_,r)=>{reject=r}))
  const check=ensurePortalSession({force:true}).catch(()=>undefined); await vi.advanceTimersByTimeAsync(801); await flushPromises()
  expect(w.find('.session-content').attributes('inert')).toBeDefined(); expect(w.find('.session-content').classes()).toContain('session-content-hidden')
  reject(new Error('offline')); await check; await flushPromises(); expect(portalSession.phase).toBe('unconfirmed'); expect(w.find('textarea').element).toBe(area); expect((area as HTMLTextAreaElement).value).toBe('保留我'); expect(api.block).toHaveBeenLastCalledWith(true)
  await ensurePortalSession({force:true}); await flushPromises(); expect(w.find('.session-content').classes()).not.toContain('session-content-hidden'); expect(api.unmounted).not.toHaveBeenCalled(); expect(document.activeElement).toBe(area)
})
it('R05: a new native session for the same User clears the old view and rejects a previous coordinator response',async()=>{
  const w=await render(); await w.find('textarea').setValue('旧会话'); api.security.mockResolvedValueOnce(security('A','b'))
  await ensurePortalSession({force:true}); await flushPromises(); expect(api.unmounted).toHaveBeenCalledTimes(1); expect((w.find('textarea').element as HTMLTextAreaElement).value).toBe('')
  let resolve!:(v:unknown)=>void; api.security.mockImplementationOnce(()=>new Promise(r=>{resolve=r})); const pending=ensurePortalSession({force:true}); resetPortalSession(); resolve(security()); await expect(pending).rejects.toThrow(); expect(portalSession.mounted).toBe(false)
})

it('R01: the actual attendance component retains dates, results and instance after ten focus rounds without requery',async()=>{
  const w=await render('/hbos/attendance/me')
  await w.find('[aria-label="考勤开始日期"]').setValue('2026-10-14');await w.find('[aria-label="考勤结束日期"]').setValue('2026-10-14')
  await w.findAll('button').find(button=>button.text()==='查询本人考勤')!.trigger('click');await flushPromises()
  const instance=w.find('.my-attendance').attributes('data-view-instance'), initialCalls=api.attendance.mock.calls.length
  for(let i=0;i<10;i++){await vi.advanceTimersByTimeAsync(5100);window.dispatchEvent(new Event('focus'));window.dispatchEvent(new Event('pageshow'));document.dispatchEvent(new Event('visibilitychange'));await vi.advanceTimersByTimeAsync(151);await flushPromises()}
  expect(w.find('.my-attendance').attributes('data-view-instance')).toBe(instance)
  expect((w.find('[aria-label="考勤开始日期"]').element as HTMLInputElement).value).toBe('2026-10-14')
  expect((w.find('[aria-label="考勤结束日期"]').element as HTMLInputElement).value).toBe('2026-10-14')
  expect(api.attendance).toHaveBeenCalledTimes(initialCalls);expect(api.bootstrap).toHaveBeenCalledTimes(1)
  expect(w.text()).toContain('原始打卡');expect(w.text()).toContain('每日考勤结果');expect(w.text()).toContain('签到');expect(w.text()).toContain('出勤')
})
it('R04: a pending password gate also retains its own subtree during same-session focus checks',async()=>{
  api.security.mockResolvedValue({...security(),first_password_required:true,temporary_password_state:{pending:true,temporary:true,can_claim:false,generation:1}})
  const w=await render(); const gate=w.find('.first-gate').element
  const fields=w.findAll('input[autocomplete="new-password"]');await fields[0]!.setValue('unsubmitted synthetic draft');await fields[1]!.setValue('unsubmitted synthetic draft')
  for(let i=0;i<3;i++){await vi.advanceTimersByTimeAsync(5100);window.dispatchEvent(new Event('focus'));await vi.advanceTimersByTimeAsync(151);await flushPromises()}
  expect(w.find('.first-gate').element).toBe(gate);expect((w.find('input[autocomplete="new-password"]').element as HTMLInputElement).value).toBe('unsubmitted synthetic draft')
  expect(api.bootstrap).not.toHaveBeenCalled()
})
