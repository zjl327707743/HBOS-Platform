import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { resetPortalSession, ensurePortalSession } from '@/services/portalSessionCoordinator'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { usePortalSession } from '@/composables/usePortalSession'


vi.mock('@/services/iamAccount', () => ({ getIamSecurity: vi.fn(async () => ({ user: 'synthetic-reader', session_context: 'a'.repeat(64), first_password_required: false, proof: {} })) }))
vi.mock('@/services/iamAccess', () => ({ iamSession: { revision: 'r1', appRevisions: {} }, fetchIamAccess: vi.fn(async () => ({ subject_user: 'synthetic-reader', session_context: 'a'.repeat(64), policy_revision: 'r1', capabilities: [] })), applyIamAccess: vi.fn(), clearIamAccess: vi.fn() }))

const provider = vi.hoisted(() => ({ getPortalData: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))
const data = (apps: string[]) => ({ user: { id: 'synthetic-reader' }, branding: {}, apps: apps.map(id => ({id})), heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [] })
const Probe = defineComponent({ setup: usePortalSession, template: '<div><span v-if="sessionPending">Checking account</span><span v-else-if="!sessionError && !sessionBlocked">Protected application content</span></div>' })
let wrapper: VueWrapper | undefined
async function render(path: string) {
  const pinia = createPinia(); setActivePinia(pinia); resetPortalSession(false)
  const router = createRouter({ history: createMemoryHistory(), routes: [{path:'/:pathMatch(.*)*',component:defineComponent({template:'<div />'})}] })
  await router.push(path); await router.isReady()
  wrapper = mount(Probe, { global: {plugins:[pinia,router]} }); await ensurePortalSession().catch(()=>undefined); await flushPromises()
  return {router,wrapper}
}
beforeEach(() => { vi.useFakeTimers(); provider.getPortalData.mockResolvedValue(data(['knowledge'])) })
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers() })
it.each(['lims','knowledge','twin','production'])('E01/F08: a protected %s deep link rejects an application absent from the authorized manifest', async app => {
  provider.getPortalData.mockResolvedValue(data([]))
  const {router} = await render('/hbos/'+app)
  expect(router.currentRoute.value.path).toBe('/hbos/403')
  expect(router.currentRoute.value.query.app).toBe(app)
})
it('F08: an authorized application deep link remains available', async () => {
  const {router,wrapper} = await render('/hbos/knowledge')
  expect(router.currentRoute.value.path).toBe('/hbos/knowledge')
  expect(wrapper.text()).toContain('Protected application content')
})
it.each(['knowledge', 'production'])('A07: resuming %s hides old protected content while account authorization is checked again', async app => {
  provider.getPortalData.mockResolvedValue(data([app]))
  const {router,wrapper} = await render('/hbos/'+app)
  let resolve!: (value: unknown) => void
  provider.getPortalData.mockReturnValue(new Promise(r => {resolve=r}))
  await vi.advanceTimersByTimeAsync(5100); window.dispatchEvent(new Event('focus')); await vi.advanceTimersByTimeAsync(151); await flushPromises()
  expect(wrapper.text()).not.toContain('Protected application content')
  resolve(data([])); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/hbos/403')
})
it('C02: a normal profile recheck preserves an in-progress verification for the same account', async () => {
  const {router,wrapper} = await render('/hbos/profile')
  let resolve!: (value: unknown) => void
  provider.getPortalData.mockReturnValue(new Promise(r => {resolve=r}))
  await vi.advanceTimersByTimeAsync(5100); window.dispatchEvent(new Event('focus')); await vi.advanceTimersByTimeAsync(151); await flushPromises()
  expect(wrapper.text()).toContain('Protected application content')
  resolve(data(['knowledge'])); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/hbos/profile')
})
