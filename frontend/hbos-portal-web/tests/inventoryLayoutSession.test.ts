import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, onUnmounted, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import InventoryLayout from '@/components/layout/InventoryLayout.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import { usePortalStore } from '@/stores/portal'
import { FrappeHttpError } from '@/services/frappeClient'
import { resetPortalSession, ensurePortalSession } from '@/services/portalSessionCoordinator'
const fixture = vi.hoisted(() => ({ user: 'inventory-reader-a', context: 'a', security: vi.fn(), caps: vi.fn() }))
const provider = vi.hoisted(() => ({ getPortalData: vi.fn(), getPortalTasks: vi.fn(), getPortalSummaries: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))
vi.mock('@/services/iamAccount', () => ({ getIamSecurity: fixture.security }))
vi.mock('@/services/iamAccess', () => ({ iamSession: { revision: 'r1', appRevisions: {} }, fetchIamAccess: fixture.caps, applyIamAccess: vi.fn(), clearIamAccess: vi.fn() }))
const data = (id = fixture.user, apps = ['inventory']) => ({ user: { id }, branding: {}, apps: apps.map(id => ({ id })), heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [] })
const mountedFor = vi.fn(), unmountedFor = vi.fn()
const Child = defineComponent({ setup() { const subject = usePortalStore().user?.id, draft = ref(''); mountedFor(subject); onUnmounted(() => unmountedFor(subject)); return { subject, draft } }, template: '<section data-test="inventory-child">{{subject}}<input v-model="draft" /></section>' })
let wrapper: VueWrapper | undefined, pinia: ReturnType<typeof createPinia>
beforeEach(() => {
  vi.useFakeTimers(); pinia = createPinia(); setActivePinia(pinia); resetPortalSession(false)
  fixture.user = 'inventory-reader-a'; fixture.context = 'a'
  fixture.security.mockReset().mockImplementation(async () => ({ user: fixture.user, session_context: fixture.context.repeat(64), first_password_required: false, proof: {} }))
  fixture.caps.mockReset().mockImplementation(async () => ({ subject_user: fixture.user, session_context: fixture.context.repeat(64), policy_revision: 'r1', capabilities: [] }))
  provider.getPortalData.mockReset().mockImplementation(async () => data()); provider.getPortalTasks.mockResolvedValue({items:[]}); provider.getPortalSummaries.mockResolvedValue({items:[]})
  mountedFor.mockClear(); unmountedFor.mockClear()
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers() })
async function render(cached = false) {
  if (cached) usePortalStore().user = data().user as never
  const router = createRouter({history:createMemoryHistory(),routes:[{path:'/hbos/inventory',component:InventoryLayout,children:[{path:'items',component:Child}]},{path:'/hbos/403',component:ForbiddenView},{path:'/hbos/login',component:defineComponent({template:'<p>登录</p>'})}]})
  await router.push('/hbos/inventory/items'); await router.isReady()
  wrapper=mount(defineComponent({template:'<RouterView />'}),{global:{plugins:[pinia,router],stubs:{GlobalHeader:true,PointerAtmosphere:true,InventoryLocalSidebar:true,MobileAppNav:true,CommandPalette:true,ASkeleton:{template:'<p data-test="session-pending">正在复核会话</p>'},AAlert:{props:['message'],template:'<p role="alert">{{message}}</p>'},AButton:{template:'<button><slot /></button>'}}}})
  return {wrapper,router}
}
async function settle() { await ensurePortalSession().catch(()=>undefined); await flushPromises() }
async function resume() { await vi.advanceTimersByTimeAsync(5100); window.dispatchEvent(new Event('focus')); window.dispatchEvent(new Event('pageshow')); document.dispatchEvent(new Event('visibilitychange')); await vi.advanceTimersByTimeAsync(151); await settle() }
it('rejects a cached ordinary user absent from the freshly authorized manifest',async()=>{provider.getPortalData.mockResolvedValue(data(fixture.user,[]));const {router,wrapper}=await render(true);await settle();expect(router.currentRoute.value.path).toBe('/hbos/403');expect(wrapper.find('[data-test="inventory-child"]').exists()).toBe(false);expect(mountedFor).not.toHaveBeenCalled()})
it('does not mount a business child before current identity and bootstrap complete',async()=>{let done!:(v:unknown)=>void;provider.getPortalData.mockReturnValue(new Promise(r=>{done=r}));const {wrapper}=await render();await flushPromises();expect(wrapper.find('[data-test="session-pending"]').exists()).toBe(true);expect(mountedFor).not.toHaveBeenCalled();done(data());await settle();expect(wrapper.get('[data-test="inventory-child"]').text()).toContain(fixture.user)})
it('retains the same input and draft through coalesced focus revalidation while refreshing native app access',async()=>{const {wrapper}=await render();await settle();await wrapper.get('input').setValue('未保存出库安排');const input=wrapper.get('input').element;await resume();expect(wrapper.get('input').element).toBe(input);expect((input as HTMLInputElement).value).toBe('未保存出库安排');expect(mountedFor).toHaveBeenCalledTimes(1);expect(unmountedFor).not.toHaveBeenCalled();expect(provider.getPortalData).toHaveBeenCalledTimes(2)})
it('revoked native app access routes to 403 and removes the retained child',async()=>{const {router,wrapper}=await render();await settle();provider.getPortalData.mockResolvedValue(data(fixture.user,[]));await resume();expect(router.currentRoute.value.path).toBe('/hbos/403');expect(wrapper.find('input').exists()).toBe(false)})
it('a new confirmed subject discards route-local drafts before showing that subject',async()=>{const {wrapper}=await render();await settle();await wrapper.get('input').setValue('前人草稿');fixture.user='inventory-reader-b';fixture.context='b';await resume();expect(wrapper.get('[data-test="inventory-child"]').text()).toContain('inventory-reader-b');expect((wrapper.get('input').element as HTMLInputElement).value).toBe('');expect(unmountedFor).toHaveBeenCalledWith('inventory-reader-a')})
it('an authenticated bootstrap denial remains forbidden rather than a false Guest redirect',async()=>{provider.getPortalData.mockRejectedValue(new FrappeHttpError(403,'你没有权限进入这个应用'));const {router,wrapper}=await render();await settle();expect(router.currentRoute.value.path).toBe('/hbos/inventory/items');expect(wrapper.find('input').exists()).toBe(false);expect(wrapper.text()).toContain('没有权限')})
it('a failed access refresh hides retained data without losing its draft and allows retry',async()=>{const {wrapper}=await render();await settle();await wrapper.get('input').setValue('保留草稿');const input=wrapper.get('input').element;provider.getPortalData.mockRejectedValue(new Error('Synthetic unavailable'));await resume();expect(wrapper.get('input').element).toBe(input);expect(wrapper.get('input').element.closest('[inert]')).not.toBeNull();provider.getPortalData.mockImplementation(async()=>data());await wrapper.get('button').trigger('click');await settle();expect(wrapper.get('input').element).toBe(input);expect((input as HTMLInputElement).value).toBe('保留草稿');expect(wrapper.get('input').element.closest('[inert]')).toBeNull()})
