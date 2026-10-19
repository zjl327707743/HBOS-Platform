import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { usePortalSession } from '@/composables/usePortalSession'

const provider = vi.hoisted(() => ({ getPortalData: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))
const data = { user: { id: 'synthetic-reader' }, branding: {}, apps: [{ id: 'knowledge' }], heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [] }

describe('tab resume', () => {
  beforeEach(() => { provider.getPortalData.mockResolvedValue(data); setActivePinia(createPinia()) })
  it('does not blank content and bumps revision only after a successful recheck', async () => {
    const Probe = defineComponent({ setup() { const s = usePortalSession(); return s }, template: '<div><span v-if="sessionPending">Checking</span><span v-else>Answered content</span><i>{{ sessionRevision }}</i></div>' })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: defineComponent({ template: '<div/>' }) }] })
    await router.push('/hbos/knowledge'); await router.isReady()
    const w = mount(Probe, { global: { plugins: [router] } }); await flushPromises()
    expect(w.text()).toContain('Answered content')
    const before = Number(w.get('i').text())
    window.dispatchEvent(new Event('focus')); await flushPromises()
    expect(w.text()).toContain('Answered content')
    expect(w.text()).not.toContain('Checking')
    expect(Number(w.get('i').text())).toBeGreaterThan(before)
  })
})
