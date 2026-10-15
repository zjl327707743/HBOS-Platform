import {expect,it,vi,beforeEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
vi.mock('@/services/frappeClient',()=>({callFrappeMethod:vi.fn(),callFrappePostMethod:vi.fn(),isUnauthenticatedError:()=>false,clearFrappeCsrfToken:vi.fn()}))
const portal=vi.hoisted(()=>({user:null,branding:null,apps:[],tasks:[],bootstrap:vi.fn(),clearSession:vi.fn()}))
vi.mock('@/stores/portal',()=>({usePortalStore:()=>portal}))
vi.mock('@/services/portalProvider',()=>({portalDataSource:'frappe'}))
vi.mock('vue-router',async(importOriginal)=>({...await importOriginal<object>(),useRoute:()=>({path:'/hbos',fullPath:'/hbos'}),useRouter:()=>({replace:vi.fn()})}))
import {callFrappeMethod,callFrappePostMethod} from '@/services/frappeClient'
import {getIamSecurity,claimInitialPassword,getMyEmployeeStatus} from '@/services/iamAccount'
import PortalLayout from '@/components/layout/PortalLayout.vue'
const status={user:'user-a',first_password_required:true,temporary_password_state:{pending:true,temporary:false,expires_at:null,generation:1,can_claim:true}}
beforeEach(()=>vi.resetAllMocks())
it('requires the current subject and complete server state before allowing the gate to open',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue(status);await expect(getIamSecurity('user-b')).rejects.toThrow();vi.mocked(callFrappeMethod).mockResolvedValue({user:'user-a'});await expect(getIamSecurity('user-a')).rejects.toThrow()})
it('claims only for the current session with no target or persistent credential storage',async()=>{const storage=vi.spyOn(Storage.prototype,'setItem');vi.mocked(callFrappePostMethod).mockResolvedValue({claimed:true,temporary_password:'one-response-only',generation:1});await claimInitialPassword();expect(callFrappePostMethod).toHaveBeenCalledWith('hbos_portal.auth.accounts.claim_initial_password');expect(storage).not.toHaveBeenCalled();storage.mockRestore()})
it('queries self association without an employee override',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue({ok:true,data:{status:'unlinked'}});expect((await getMyEmployeeStatus()).status).toBe('unlinked');expect(callFrappeMethod).toHaveBeenCalledWith('hbos_portal.api.iam_people.get_my_employee_status',undefined)})
const stubs={GlobalHeader:true,PointerAtmosphere:true,PortalSidebar:true,MobilePortalNav:true,CommandPalette:true,FirstPasswordGate:{template:'<section data-first-password-gate />'},RouterView:true,'a-skeleton':true,'a-alert':{props:['message'],template:'<div>{{message}}</div>'}}
it('does not send business bootstrap before a pending session completes its password gate',async()=>{vi.mocked(callFrappeMethod).mockResolvedValue(status);const wrapper=mount(PortalLayout,{global:{stubs}});await flushPromises();expect(portal.bootstrap).not.toHaveBeenCalled();expect(wrapper.find('[data-first-password-gate]').exists()).toBe(true);wrapper.unmount()})
it('fails closed without business bootstrap when the initial security check fails',async()=>{vi.mocked(callFrappeMethod).mockRejectedValue(new Error('security unavailable'));const wrapper=mount(PortalLayout,{global:{stubs}});await flushPromises();expect(portal.bootstrap).not.toHaveBeenCalled();expect(wrapper.text()).toContain('security unavailable');wrapper.unmount()})
