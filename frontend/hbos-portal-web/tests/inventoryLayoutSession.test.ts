import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, nextTick, onUnmounted, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import InventoryLayout from '@/components/layout/InventoryLayout.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import { usePortalStore } from '@/stores/portal'
import { FrappeHttpError } from '@/services/frappeClient'

const provider = vi.hoisted(() => ({
  getPortalData: vi.fn(), getPortalTasks: vi.fn(), getPortalSummaries: vi.fn(),
}))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))
vi.mock('@/services/frappeClient', async importOriginal => ({
  ...await importOriginal<typeof import('@/services/frappeClient')>(),
  hasFrappeSession: vi.fn(async () => true),
}))

function data(id = 'inventory-reader-a', apps = ['inventory']) {
  return {
    user: { id, displayName: id, avatarText: 'CI', roleLabel: 'Synthetic', department: 'Synthetic' },
    branding: {}, apps: apps.map(app => ({ id: app })),
    heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [],
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}

const mountedFor = vi.fn(), unmountedFor = vi.fn()
const InventoryChild = defineComponent({
  setup() {
    const subject = usePortalStore().user?.id
    const draft = ref('')
    mountedFor(subject)
    onUnmounted(() => unmountedFor(subject))
    return { subject, draft }
  },
  template: '<section data-test="inventory-child"><p>库存明细 {{ subject }}</p><input v-model="draft" aria-label="仓储页面暂存输入" /></section>',
})
const Root = defineComponent({ template: '<RouterView />' })
let wrapper: VueWrapper | undefined

async function render(cachedUser = false) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const portal = usePortalStore()
  if (cachedUser) portal.user = data().user
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/hbos/inventory', component: InventoryLayout, children: [{ path: 'items', component: InventoryChild }] },
      { path: '/hbos/403', component: ForbiddenView },
      { path: '/hbos/login', component: defineComponent({ template: '<p>登录</p>' }) },
    ],
  })
  await router.push('/hbos/inventory/items')
  await router.isReady()
  wrapper = mount(Root, {
    global: {
      plugins: [pinia, router],
      stubs: {
        GlobalHeader: true, PointerAtmosphere: true, InventoryLocalSidebar: true,
        MobileAppNav: true, CommandPalette: true,
        ASkeleton: { template: '<p data-test="session-pending">正在复核会话</p>' },
        AAlert: { props: ['message'], template: '<p role="alert">{{ message }}</p>' },
        ASpace: { template: '<div><slot /></div>' },
        AButton: { template: '<button><slot /></button>' },
      },
    },
  })
  return { wrapper, router, portal }
}

beforeEach(() => {
  provider.getPortalData.mockReset().mockResolvedValue(data())
  provider.getPortalTasks.mockReset().mockResolvedValue([])
  provider.getPortalSummaries.mockReset().mockResolvedValue([])
  mountedFor.mockClear()
  unmountedFor.mockClear()
})
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
})

it('denies an inventory deep link for a cached ordinary account absent from the new manifest', async () => {
  provider.getPortalData.mockResolvedValue(data('ordinary-user', []))
  const { router, wrapper } = await render(true)
  expect(wrapper.find('[data-test="inventory-child"]').exists()).toBe(false)
  await flushPromises()
  expect(provider.getPortalData).toHaveBeenCalledOnce()
  expect(router.currentRoute.value.path).toBe('/hbos/403')
  expect(router.currentRoute.value.query.app).toBe('inventory')
  expect(wrapper.text()).toContain('你没有权限进入这个应用')
  expect(mountedFor).not.toHaveBeenCalled()
})

it('does not mount an inventory child before the initial session check completes', async () => {
  const check = deferred<ReturnType<typeof data>>()
  provider.getPortalData.mockReturnValue(check.promise)
  const { wrapper } = await render()
  await nextTick()
  expect(wrapper.find('[data-test="session-pending"]').exists()).toBe(true)
  expect(mountedFor).not.toHaveBeenCalled()
  check.resolve(data())
  await flushPromises()
  expect(wrapper.get('[data-test="inventory-child"]').text()).toContain('inventory-reader-a')
  expect(mountedFor).toHaveBeenCalledOnce()
})

it('unmounts old inventory content during focus revalidation and restores a fresh same-account view', async () => {
  const { wrapper, router } = await render()
  await flushPromises()
  await wrapper.get('input').setValue('previous private draft')
  const check = deferred<ReturnType<typeof data>>()
  provider.getPortalData.mockReturnValue(check.promise)
  window.dispatchEvent(new Event('focus'))
  await nextTick()
  expect(wrapper.find('[data-test="inventory-child"]').exists()).toBe(false)
  expect(wrapper.find('[data-test="session-pending"]').exists()).toBe(true)
  expect(unmountedFor).toHaveBeenCalledWith('inventory-reader-a')
  check.resolve(data())
  await flushPromises()
  expect(router.currentRoute.value.path).toBe('/hbos/inventory/items')
  expect(wrapper.get('[data-test="inventory-child"]').text()).toContain('inventory-reader-a')
  expect((wrapper.get('input').element as HTMLInputElement).value).toBe('')
  expect(mountedFor).toHaveBeenCalledTimes(2)
})

it('routes a revoked inventory manifest to 403 without restoring the old child', async () => {
  const { wrapper, router } = await render()
  await flushPromises()
  const check = deferred<ReturnType<typeof data>>()
  provider.getPortalData.mockReturnValue(check.promise)
  window.dispatchEvent(new Event('focus'))
  await nextTick()
  expect(wrapper.find('[data-test="inventory-child"]').exists()).toBe(false)
  check.resolve(data('inventory-reader-a', []))
  await flushPromises()
  expect(router.currentRoute.value.path).toBe('/hbos/403')
  expect(wrapper.text()).toContain('你没有权限进入这个应用')
  expect(wrapper.text()).not.toContain('库存明细')
  expect(mountedFor).toHaveBeenCalledOnce()
})

it('discards route-local data when another current session publishes a different account', async () => {
  const { wrapper, portal } = await render()
  await flushPromises()
  await wrapper.get('input').setValue('previous private draft')
  portal.user = data('inventory-reader-b').user
  await nextTick()
  expect(wrapper.get('[data-test="inventory-child"]').text()).toContain('inventory-reader-b')
  expect(wrapper.text()).not.toContain('inventory-reader-a')
  expect((wrapper.get('input').element as HTMLInputElement).value).toBe('')
  expect(unmountedFor).toHaveBeenCalledWith('inventory-reader-a')
})

it('preserves the Chinese permission error after an authenticated bootstrap 403', async () => {
  const { wrapper } = await render()
  await flushPromises()
  provider.getPortalData.mockRejectedValue(new FrappeHttpError(403, 'raw internal permission error'))
  window.dispatchEvent(new Event('focus'))
  await flushPromises()
  expect(wrapper.text()).toContain('你没有权限进入这个应用')
  expect(wrapper.text()).not.toContain('raw internal permission error')
  expect(wrapper.find('[data-test="inventory-child"]').exists()).toBe(false)
})

it('shows a normalized revalidation error and keeps stale inventory data unmounted', async () => {
  const { wrapper } = await render()
  await flushPromises()
  provider.getPortalData.mockRejectedValue(new FrappeHttpError(503, 'raw upstream error'))
  window.dispatchEvent(new Event('focus'))
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toBe('HBOS 服务暂时不可用，请稍后重试。')
  expect(wrapper.text()).not.toContain('raw upstream error')
  expect(wrapper.find('[data-test="inventory-child"]').exists()).toBe(false)
})
