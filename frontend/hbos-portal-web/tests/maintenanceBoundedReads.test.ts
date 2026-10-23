import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MaintenanceView from '@/views/KnowledgeMaintenanceView.vue'

const api = vi.hoisted(() => ({ status: vi.fn(), dashboard: vi.fn(), feedback: vi.fn() }))
vi.mock('@/services/p1Api', async original => ({
  ...(await original<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
}))
vi.mock('@/services/knowledgeMaintenanceApi', async original => ({
  ...(await original<typeof import('@/services/knowledgeMaintenanceApi')>()),
  getMaintenance: api.dashboard,
  getMaintenanceFeedbackPage: api.feedback,
}))

const dashboard = (selected: unknown = null, published: unknown[] = []) => ({
  departments: [{ key: 'production', title: '生产部' }],
  published_documents: published,
  batches: [],
  selected,
  feedback: { items: [] },
  import_availability: { can_parse: true, configured: true, blocked: false },
})

const InputSearch = defineComponent({
  props: ['value'],
  emits: ['update:value'],
  methods: { onInput(e: Event) { this.$emit('update:value', (e.target as HTMLInputElement).value) } },
  template: '<input :value="value" @input="onInput" />',
})
const stubs = {
  'a-input-search': InputSearch, 'a-select': true, 'a-button': true, 'a-alert': true,
  'a-skeleton': true, 'a-result': true, 'a-tag': true, 'a-collapse': true,
  'a-collapse-panel': true, 'a-pagination': true, 'a-checkbox': true, 'a-popconfirm': true,
  'a-progress': true, 'a-steps': true, 'a-drawer': true, 'a-textarea': true,
  'a-checkbox-group': true, 'a-empty': true,
}

let wrapper: ReturnType<typeof mount> | undefined
async function view(path = '/hbos/knowledge/maintenance') {
  const pinia = createPinia(); setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/hbos/knowledge/maintenance/:rest(.*)*', component: { template: '<div/>' } }] })
  await router.push(path); await router.isReady()
  wrapper = mount(MaintenanceView, { global: { plugins: [pinia, router], stubs } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.status.mockResolvedValue({ can_maintain: true })
  api.dashboard.mockResolvedValue(dashboard())
  api.feedback.mockImplementation((page: number) => Promise.resolve({ items: [], page, page_size: 6, has_more: false }))
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers() })

describe('maintenance list stays bounded', () => {
  it('opens with a single dashboard read, not one per row', async () => {
    api.dashboard.mockResolvedValue(dashboard(null, [
      { document_id: 'DOC_1', version_id: 'VER_1', current_version: 'VER_1', title: '合成一', department: 'production' },
      { document_id: 'DOC_2', version_id: 'VER_2', current_version: 'VER_2', title: '合成二', department: 'production' },
      { document_id: 'DOC_3', version_id: 'VER_3', current_version: 'VER_3', title: '合成三', department: 'production' },
    ]))
    const w = await view()
    expect(w.text()).toContain('合成一')
    expect(api.dashboard).toHaveBeenCalledTimes(1)
  })

  it('debounces the feedback search box instead of sweeping on each keystroke', async () => {
    const w = await view('/hbos/knowledge/maintenance/feedback')
    vi.useFakeTimers()
    api.feedback.mockClear()
    const input = w.get('input')
    await input.setValue('质')
    await input.setValue('质量')
    await input.setValue('质量问题')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    // One debounced read for three keystrokes.
    expect(api.feedback.mock.calls.length).toBeLessThanOrEqual(1)
  })
})
