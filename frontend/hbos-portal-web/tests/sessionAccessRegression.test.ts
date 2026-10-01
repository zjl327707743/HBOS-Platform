import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { usePortalSession } from '@/composables/usePortalSession'

const provider = vi.hoisted(() => ({ getPortalData: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))
const data = (apps: string[]) => ({ user: { id: 'synthetic-reader' }, branding: {}, apps: apps.map(id => ({id})), heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [] })
const Probe = defineComponent({ setup: usePortalSession, template: '<div><span v-if="sessionPending">Checking account</span><span v-else-if="!sessionError">Protected application content</span></div>' })
let wrapper: VueWrapper | undefined
async function render(path: string) {
  const pinia = createPinia(); setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [{path:'/:pathMatch(.*)*',component:defineComponent({template:'<div />'})}] })
  await router.push(path); await router.isReady()
  wrapper = mount(Probe, { global: {plugins:[pinia,router]} }); await flushPromises()
  return {router,wrapper}
}
beforeEach(() => provider.getPortalData.mockResolvedValue(data(['knowledge'])))
afterEach(() => { wrapper?.unmount(); wrapper = undefined })
it.each(['lims','knowledge','twin'])('E01/F08: a protected %s deep link rejects an application absent from the authorized manifest', async app => {
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
it('A07: resuming hides old protected content while account authorization is checked again', async () => {
  const {router,wrapper} = await render('/hbos/knowledge')
  let resolve!: (value: unknown) => void
  provider.getPortalData.mockReturnValue(new Promise(r => {resolve=r}))
  window.dispatchEvent(new Event('focus')); await flushPromises()
  expect(wrapper.text()).not.toContain('Protected application content')
  resolve(data([])); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/hbos/403')
})
it('C02: a normal profile recheck preserves an in-progress verification for the same account', async () => {
  const {router,wrapper} = await render('/hbos/profile')
  let resolve!: (value: unknown) => void
  provider.getPortalData.mockReturnValue(new Promise(r => {resolve=r}))
  window.dispatchEvent(new Event('focus')); await flushPromises()
  expect(wrapper.text()).toContain('Protected application content')
  resolve(data(['knowledge'])); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/hbos/profile')
})
