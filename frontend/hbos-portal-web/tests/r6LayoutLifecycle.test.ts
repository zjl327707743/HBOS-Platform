import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { useReadablePanels } from '@/composables/useReadablePanels'
const session = vi.hoisted(() => ({ generation: 1, security: { user: 'synthetic-HR-A' } }))
vi.mock('@/services/portalSessionCoordinator', () => ({ portalSession: session }))
afterEach(() => { window.dispatchEvent(new Event('hbos:session-boundary')); vi.restoreAllMocks(); document.body.innerHTML = '' })
describe('R6 layout and identity lifecycle', () => {
  it('remembers same-identity filters across unmounts and clears them at a session boundary', async () => {
    const View = defineComponent({ setup() { const search = ref(''); useManagementViewMemory('test-people', { search }); return { search } }, template: '<input v-model="search" />' })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: View }] }); await router.push('/'); await router.isReady()
    const render = () => mount(View, { global: { plugins: [router] } })
    const first = render(); await first.get('input').setValue('合成员工查询'); first.unmount()
    const second = render(); expect((second.get('input').element as HTMLInputElement).value).toBe('合成员工查询'); second.unmount()
    session.security.user = 'synthetic-HR-B'; const other = render(); expect((other.get('input').element as HTMLInputElement).value).toBe(''); other.unmount()
    session.security.user = 'synthetic-HR-A'; window.dispatchEvent(new Event('hbos:session-boundary'))
    const clean = render(); expect((clean.get('input').element as HTMLInputElement).value).toBe(''); await clean.get('input').setValue('must not be reinserted'); window.dispatchEvent(new Event('hbos:session-boundary')); clean.unmount()
    const final = render(); expect((final.get('input').element as HTMLInputElement).value).toBe(''); final.unmount()
  })
  it('uses natural scrolling when actual headers leave less than 260px, without oscillating', async () => {
    let height = 710
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1280 }); Object.defineProperty(window, 'innerHeight', { configurable: true, get: () => height })
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation(callback => { callback(0); return 1 })
    const View = defineComponent({ setup() { const root = ref<HTMLElement | null>(null), enabled = ref(true); const natural = useReadablePanels(enabled, root); return { root, natural } }, template: '<main ref="root" :data-natural="natural"><div class="r6-context-row"/><div class="r6-page-heading"/><div class="r6-page-footer"/><section class="r6-panel-frame"><header class="r6-panel-header"/><div class="r6-panel-scroll"/><footer class="r6-panel-footer"/></section></main>' })
    const wrapper = mount(View, { attachTo: document.body })
    Object.defineProperty(wrapper.element, 'clientHeight', { configurable: true, get: () => height - 76 })
    ;(wrapper.element as HTMLElement).style.padding = '24px'
    for (const [selector, value] of [['.r6-context-row', 30], ['.r6-page-heading', 90], ['.r6-page-footer', 30], ['.r6-panel-header', 150], ['.r6-panel-footer', 64]] as const) vi.spyOn(wrapper.get(selector).element, 'getBoundingClientRect').mockReturnValue({ height: value } as DOMRect)
    window.dispatchEvent(new Event('resize')); await nextTick(); expect(wrapper.attributes('data-natural')).toBe('true')
    window.dispatchEvent(new Event('resize')); await nextTick(); expect(wrapper.attributes('data-natural')).toBe('true')
    height = 1080; window.dispatchEvent(new Event('resize')); await flushPromises(); expect(wrapper.attributes('data-natural')).toBe('false')
    wrapper.unmount()
  })
})
