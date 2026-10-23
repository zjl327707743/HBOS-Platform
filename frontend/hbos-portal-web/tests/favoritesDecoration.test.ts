import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Tools from '@/components/knowledge/KnowledgeTools.vue'

const api = vi.hoisted(() => ({ page: vi.fn(), docs: vi.fn() }))
vi.mock('@/services/p1Api', async original => ({
  ...(await original<typeof import('@/services/p1Api')>()),
  getKnowledgeActivityPage: api.page,
  getKnowledgeDocumentsPage: api.docs,
  getKnowledgeActivity: async () => [],
  getKnowledgeFeedback: async () => [],
  getKnowledgeFeedbackPage: async () => ({ items: [], page: 1, page_size: 6, has_more: false }),
}))

const Button = defineComponent({ props: ['disabled'], template: '<button :disabled="disabled"><slot/></button>' })
const InputSearch = defineComponent({
  props: ['value'],
  emits: ['update:value'],
  methods: {
    onInput(event: Event) { this.$emit('update:value', (event.target as HTMLInputElement).value) },
  },
  template: '<input :value="value" @input="onInput" />',
})
const stubs = { 'a-button': Button, 'a-input-search': InputSearch, 'a-tooltip': true, 'a-alert': true, 'a-skeleton': true, 'a-empty': true, 'a-tag': true, 'a-pagination': true }

const bookmark = (id: string) => ({
  id, query: 'SYNTHETIC 收藏', titles: [`SYNTHETIC ${id}`], created_at: '2026-10-10',
  available: true, bookmark_type: 'Document', document_ids: [`DOC_${id}`], version_ids: [`VER_${id}`],
})
const doc = (id: string) => ({
  document_id: `DOC_${id}`, version_id: `VER_${id}`, title: `SYNTHETIC ${id}`, department: 'SYNTHETIC',
  space_id: 'SPACE_DEMO', document_number: null, version: null, status_note: '已共享',
})

let wrapper: ReturnType<typeof mount> | undefined
async function view() {
  wrapper = mount(Tools, { props: { view: 'favorites', subject: 'A', query: '', selectedSpace: '' }, global: { stubs } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.page.mockImplementation((_kind: string, page: number, pageSize: number) =>
    Promise.resolve({ items: [bookmark(`B${page}`)], page, page_size: pageSize, has_more: page === 1 }))
  // A large catalog: the old decoration path walked 100 pages before giving up.
  api.docs.mockImplementation((_query: string, _space: string, page: number, pageSize: number) =>
    Promise.resolve({ documents: [doc(String(page))], total: 5000, page, page_size: pageSize }))
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers() })

describe('favorites decoration does not enumerate the whole catalog', () => {
  it('reads one catalog page instead of walking up to a hundred', async () => {
    await view()
    expect(api.docs).toHaveBeenCalledTimes(1)
    expect(api.docs).toHaveBeenCalledWith('', '', 1, 50)
  })

  it('debounces the filter box and reuses the page already in memory', async () => {
    const w = await view()
    vi.useFakeTimers()
    const input = w.get('#favorite-query')
    await input.setValue('合')
    await input.setValue('合成')
    await input.setValue('合成标')
    // Nothing is requested per keystroke.
    expect(api.docs).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    // One debounced refresh, and the catalog page is not fetched again.
    expect(api.docs).toHaveBeenCalledTimes(1)
  })
})
