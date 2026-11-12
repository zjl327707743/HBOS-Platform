import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import Antd from 'ant-design-vue'
import PortalLayout from '@/components/layout/PortalLayout.vue'

const portal = vi.hoisted(() => ({ tasks: [] as unknown[], apps: [] as unknown[], branding: null, user: null, dataSource: 'mock' }))
const session = vi.hoisted(() => ({
  phase: 'ready', mounted: false, slow: false, security: null, error: '', generation: 1, resumeEvents: 0,
}))

vi.mock('@/stores/portal', () => ({ usePortalStore: () => portal }))
vi.mock('@/services/portalProvider', () => ({ portalDataSource: 'mock' }))
vi.mock('@/services/portalSessionCoordinator', () => ({
  attachPortalSession: vi.fn(() => vi.fn()), ensurePortalSession: vi.fn(), portalSession: session,
  resetPortalSession: vi.fn(), signOutPortalSession: vi.fn(),
}))
vi.mock('@/services/accountNavigation', () => ({ accountRedirect: (value: string) => value }))
vi.mock('@/services/iamAccess', () => ({ canIam: () => true }))
vi.mock('@/services/frappeClient', () => ({
  developmentObservation: false,
  frappeDiagnostics: { document: 0, security: 0, capabilities: 0, bootstrap: 0 },
}))
vi.mock('@/services/attendanceObservation', () => ({ attendanceObservation: { instance: 0, mounts: 0, unmounts: 0, requests: 0, completed: 0, stale: 0, permissions: 0, request: 0, draft: 0, applied: 0, range: '', events: [] } }))
vi.mock('@/composables/usePortalSession', () => ({ usePortalSession: () => ({ sessionPending: ref(false), sessionError: ref(null) }) }))
vi.mock('@/composables/useReadablePanels', () => ({ useReadablePanels: () => ref(false) }))

const Placeholder = defineComponent({ template: '<div />' })

describe('portal route scroller', () => {
  afterEach(() => { document.body.innerHTML = ''; vi.clearAllMocks() })

  it('starts a new route at the top of the persistent R6 content scroller', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{
      path: '/hbos', component: PortalLayout, children: [
        { path: 'admin/people', component: Placeholder },
        { path: 'profile', component: Placeholder },
      ],
    }] })
    await router.push('/hbos/admin/people')
    await router.isReady()
    const Host = defineComponent({ template: '<RouterView />' })
    const wrapper = mount(Host, { attachTo: document.body, global: { plugins: [Antd, router], stubs: {
      GlobalHeader: true, PointerAtmosphere: true, PortalSidebar: true, MobilePortalNav: true,
      CommandPalette: true, FirstPasswordGate: true, 'a-skeleton': true, 'a-alert': true,
    } } })
    const content = document.querySelector<HTMLElement>('.portal-route-content')!
    content.scrollTop = 200
    await router.push('/hbos/profile')
    await flushPromises()
    expect(content.scrollTop).toBe(0)
    wrapper.unmount()
  })
})
