import {expect,it,vi,beforeEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import Antd from 'ant-design-vue'
vi.mock('@/services/frappeClient',()=>({callFrappeMethod:vi.fn(),callFrappePostMethod:vi.fn(),isUnauthenticatedError:()=>false,clearFrappeCsrfToken:vi.fn(),blockFrappeWrites:vi.fn(),invalidateFrappeRequests:vi.fn(),FrappeRequestError:class extends Error {},logoutFrappeSession:vi.fn()}))
const portal=vi.hoisted(()=>({user:null,branding:null,apps:[],tasks:[],bootstrap:vi.fn(),clearSession:vi.fn()}))
vi.mock('@/stores/portal',()=>({usePortalStore:()=>portal}))
vi.mock('@/services/portalProvider',()=>({portalDataSource:'frappe'}))
vi.mock('vue-router',async(importOriginal)=>({...await importOriginal<object>(),useRoute:()=>({path:'/hbos',fullPath:'/hbos'}),useRouter:()=>({replace:vi.fn()})}))
import {callFrappeMethod,callFrappePostMethod,clearFrappeCsrfToken} from '@/services/frappeClient'
import {getIamSecurity,claimInitialPassword,getMyEmployeeStatus} from '@/services/iamAccount'
import {resetPortalSession} from '@/services/portalSessionCoordinator'
import PortalLayout from '@/components/layout/PortalLayout.vue'
import InitialPasswordDelivery from '@/components/account/InitialPasswordDelivery.vue'
const status={user:'user-a',session_context:'a'.repeat(64),first_password_required:true,temporary_password_state:{pending:true,temporary:false,expires_at:null,generation:1,can_claim:true}}
beforeEach(()=>{vi.resetAllMocks();resetPortalSession()})
it('requires the current subject and complete server state before allowing the gate to open',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue(status);await expect(getIamSecurity('user-b')).rejects.toThrow();vi.mocked(callFrappeMethod).mockResolvedValue({user:'user-a'});await expect(getIamSecurity('user-a')).rejects.toThrow()})
it('claims only for the current session and clears rotated CSRF without persisting credentials',async()=>{const storage=vi.spyOn(Storage.prototype,'setItem');vi.mocked(callFrappePostMethod).mockResolvedValue({claimed:true,temporary_password:'one-response-only',generation:1});await claimInitialPassword();expect(callFrappePostMethod).toHaveBeenCalledWith('hbos_portal.auth.accounts.claim_initial_password');expect(clearFrappeCsrfToken).toHaveBeenCalledOnce();expect(storage).not.toHaveBeenCalled();storage.mockRestore()})
it('also clears CSRF after an uncertain claim so the next proof must fetch a fresh token',async()=>{vi.mocked(callFrappePostMethod).mockRejectedValue(new Error('response lost'));await expect(claimInitialPassword()).rejects.toThrow('response lost');expect(clearFrappeCsrfToken).toHaveBeenCalledOnce()})
it('allows the server-qualified enterprise session to claim once without a second proof',async()=>{
  vi.mocked(callFrappePostMethod).mockResolvedValue({claimed:true,temporary_password:'single-memory-response',generation:1})
  const wrapper=mount(InitialPasswordDelivery,{props:{canClaim:true},global:{plugins:[Antd]}})
  expect(wrapper.find('.proof-form').exists()).toBe(false);expect(wrapper.text()).toContain('当前企业登录已验证本人')
  const claim=wrapper.findAll('button').find(button=>button.text()==='领取一次')!
  await Promise.all([claim.trigger('click'),claim.trigger('click')]);await flushPromises()
  expect(callFrappePostMethod).toHaveBeenCalledOnce();expect(clearFrappeCsrfToken).toHaveBeenCalledOnce()
  expect((wrapper.find('input').element as HTMLInputElement).value).toBe('single-memory-response')
  await wrapper.findAll('button').find(button=>button.text()==='我已记录，隐藏密码')!.trigger('click')
  expect(wrapper.findAll('button').some(button=>button.text()==='领取一次')).toBe(false)
  wrapper.unmount()
})
it('does not retry a claim after an uncertain response or a qualification prop refresh',async()=>{
  vi.mocked(callFrappePostMethod).mockRejectedValue(new Error('response lost'))
  const wrapper=mount(InitialPasswordDelivery,{props:{canClaim:false},global:{plugins:[Antd]}})
  expect(wrapper.findAll('button').some(button=>button.text()==='领取一次')).toBe(false)
  await wrapper.setProps({canClaim:true});await wrapper.findAll('button').find(button=>button.text()==='领取一次')!.trigger('click');await flushPromises()
  await wrapper.setProps({canClaim:false});await wrapper.setProps({canClaim:true})
  expect(wrapper.text()).toContain('不要反复领取');expect(wrapper.findAll('button').some(button=>button.text()==='领取一次')).toBe(false)
  expect(callFrappePostMethod).toHaveBeenCalledOnce();expect(clearFrappeCsrfToken).toHaveBeenCalledOnce();wrapper.unmount()
})
it('queries self association without an employee override',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data:{status:'unlinked'}});expect((await getMyEmployeeStatus()).status).toBe('unlinked');expect(callFrappeMethod).toHaveBeenCalledWith('hbos_portal.api.iam_people.get_my_employee_status',undefined)})
const stubs={GlobalHeader:true,PointerAtmosphere:true,PortalSidebar:true,MobilePortalNav:true,CommandPalette:true,FirstPasswordGate:{template:'<section data-first-password-gate />'},RouterView:true,'a-skeleton':true,'a-button':true,'a-alert':{props:['message'],template:'<div>{{message}}</div>'}}
it('does not send business bootstrap before a pending session completes its password gate',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue(status);const wrapper=mount(PortalLayout,{global:{stubs}});await flushPromises();expect(portal.bootstrap).not.toHaveBeenCalled();expect(wrapper.find('[data-first-password-gate]').exists()).toBe(true);wrapper.unmount()})
it('fails closed without business bootstrap when the initial security check fails',async()=>{vi.mocked(callFrappeMethod).mockRejectedValue(new Error('security unavailable'));const wrapper=mount(PortalLayout,{global:{stubs}});await flushPromises();expect(portal.bootstrap).not.toHaveBeenCalled();expect(wrapper.text()).toContain('暂时无法核对当前登录状态');wrapper.unmount()})
