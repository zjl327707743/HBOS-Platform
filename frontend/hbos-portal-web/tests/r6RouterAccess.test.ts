import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'

const capabilities = vi.hoisted(() => new Set<string>())

vi.mock('@/services/iamAccess', () => ({ canIam: (capability: string) => capabilities.has(capability) }))
vi.mock('@/services/portalSessionCoordinator', () => ({ ensurePortalSession: vi.fn(async () => ({ first_password_required: false })) }))
vi.mock('@/services/portalProvider', () => ({ portalDataSource: 'frappe' }))
vi.mock('@/router/portalGuard', () => ({ checkPortalAccess: vi.fn(async () => true) }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => ({}) }))
vi.mock('@/components/layout/PortalLayout.vue', () => ({ default: { template: '<router-view />' } }))
vi.mock('@/components/layout/LimsLayout.vue', () => ({ default: { template: '<router-view />' } }))
vi.mock('@/components/layout/InventoryLayout.vue', () => ({ default: { template: '<router-view />' } }))
vi.mock('@/components/layout/ProductionLayout.vue', () => ({ default: { template: '<router-view />' } }))
vi.mock('@/views/admin/AdminWorkspaceView.vue', () => ({ default: { template: '<router-view />' } }))
vi.mock('@/views/admin/AdminAccessUnavailableView.vue', () => ({ default: { template: '<div>unavailable</div>' } }))
vi.mock('@/views/admin/RolesAdminView.vue', () => ({ default: { template: '<div>roles</div>' } }))

import router from '@/router'

beforeEach(async () => {
  setActivePinia(createPinia())
  capabilities.clear()
  await router.push('/hbos/login')
  await flushPromises()
})

describe('R6 management landing and LIMS role route guards', () => {
  it('selects the roles landing for a manager who only has iam.roles.read', async () => {
    capabilities.add('iam.roles.read')
    await router.push('/hbos/admin')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/hbos/admin/roles')
  })

  it('applies both iam and iamCapability to the LIMS roles route', async () => {
    await router.push('/hbos/lims/roles')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/hbos/admin/unavailable')

    const record = router.resolve('/hbos/lims/roles').matched.at(-1)
    expect(record?.meta.iam).toBe(true)
    expect(record?.meta.iamCapability).toBe('iam.roles.read')

    capabilities.add('iam.roles.read')
    await router.push('/hbos/lims/roles')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/hbos/lims/roles')
  })
})
