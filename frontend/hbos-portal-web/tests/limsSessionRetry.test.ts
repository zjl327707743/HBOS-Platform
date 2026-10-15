import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import LimsLayout from '@/components/layout/LimsLayout.vue'

const provider = vi.hoisted(() => ({ getPortalData: vi.fn(), getPortalTasks: vi.fn(), getPortalSummaries: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))
vi.mock('@/services/p1Api', () => ({ getTwinStatus: vi.fn(), getTwinManifest: vi.fn() }))

const data = (apps = ['lims']) => ({ user: { id: 'synthetic-user' }, branding: {}, apps: apps.map(id => ({ id })), heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [] })
let wrapper: VueWrapper | undefined

beforeEach(() => {
  provider.getPortalData.mockReset()
  provider.getPortalData.mockRejectedValueOnce(new Error('Synthetic bootstrap outage'))
  provider.getPortalTasks.mockResolvedValue({ items: [], errors: [] })
  provider.getPortalSummaries.mockResolvedValue({ items: [], errors: [] })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined })

async function render() {
  const page = defineComponent({ template: '<p>SYNTHETIC-LIMS-CONTENT</p>' })
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/hbos/lims', component: LimsLayout, children: [{ path: '', component: page }] },
    { path: '/hbos/403', component: defineComponent({ template: '<p>SYNTHETIC-FORBIDDEN</p>' }) },
  ] })
  await router.push('/hbos/lims'); await router.isReady()
  const alert = defineComponent({ props: ['message'], setup(props, { slots }) { return () => h('div', [props.message, slots.action?.()]) } })
  const button = defineComponent({ setup(_, { slots, attrs }) { return () => h('button', attrs, slots.default?.()) } })
  wrapper = mount(defineComponent({ template: '<RouterView />' }), { global: {
    plugins: [createPinia(), router],
    stubs: { GlobalHeader: true, PointerAtmosphere: true, AppLocalSidebar: true, MobileAppNav: true, CommandPalette: true, 'a-alert': alert, 'a-button': button, 'a-skeleton': true },
  } })
  await flushPromises()
  return { router, wrapper }
}

it('a successful retry clears the old error and displays the LIMS route', async () => {
  provider.getPortalData.mockResolvedValue(data())
  const { wrapper } = await render()
  expect(wrapper.text()).toContain('Synthetic bootstrap outage')
  await wrapper.get('button').trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('SYNTHETIC-LIMS-CONTENT')
  expect(wrapper.text()).not.toContain('Synthetic bootstrap outage')
})

it('retry rechecks application access before displaying business content', async () => {
  provider.getPortalData.mockResolvedValue(data([]))
  const { router, wrapper } = await render()
  await wrapper.get('button').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.path).toBe('/hbos/403')
  expect(wrapper.text()).not.toContain('SYNTHETIC-LIMS-CONTENT')
})
