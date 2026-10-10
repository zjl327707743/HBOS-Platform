import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { it, expect, vi, beforeEach } from 'vitest'

const api = vi.hoisted(() => ({ status: vi.fn(), maintenance: vi.fn(), feedback: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => ({ path: '/hbos/knowledge/maintenance/versions' }), useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/services/p1Api', async () => ({ ...await vi.importActual<any>('@/services/p1Api'), getKnowledgeStatus: api.status }))
vi.mock('@/services/knowledgeMaintenanceApi', () => ({ getMaintenance: api.maintenance, getMaintenanceFeedbackPage: api.feedback, maintenanceAction: vi.fn(), previewImport: vi.fn(), uploadKnowledge: vi.fn() }))
import View from '@/views/KnowledgeMaintenanceView.vue'

const Button = defineComponent({ template: '<button><slot/></button>' })
const Drawer = defineComponent({ props: ['open'], template: '<section v-if="open"><slot/></section>' })
const Panel = defineComponent({ template: '<div><slot/></div>' })
const original = { document_id: 'DOC_SYNTHETIC', version_id: 'VER_SYNTHETIC', title: 'SYNTHETIC 流程文件', relationship: 'NEW', parse_status: 'parsed/indexed', quality_status: 'Passed', current_version: 'VER_SYNTHETIC', publication_status: 'Published' }
const dashboard = (selected: any = null) => ({ departments: [{ key: 'production', title: '合成部门' }], published_documents: [{ ...original, department: 'production' }], batches: [{ name: 'DUPLICATE', label: '合成重复任务' }, { name: 'ORIGINAL', label: '合成原任务' }], selected: selected ? { items: [selected], total: 1, page_size: 12, counts: { parsed: 1, quality_passed: 1 } } : null, import_availability: { can_parse: true } })

beforeEach(() => {
  vi.resetAllMocks()
  api.status.mockResolvedValue({ can_maintain: true })
  api.maintenance.mockImplementation((batch?: string) => Promise.resolve(dashboard(batch === 'DUPLICATE' ? { ...original, relationship: 'SAME_CONTENT_SKIP', parse_status: 'skipped_duplicate', quality_status: 'Pending' } : batch === 'ORIGINAL' ? original : null)))
})

it('opens the reviewed current version rather than duplicate upload metadata — synthetic contract', async () => {
  const w = mount(View, { global: { stubs: { 'a-button': Button, 'a-drawer': Drawer, 'a-collapse': Panel, 'a-collapse-panel': Panel, 'a-popconfirm': Panel, 'a-input-search': true, 'a-select': true, 'a-pagination': true, 'a-tag': Panel, 'a-alert': true, 'a-skeleton': true, 'a-result': true } } })
  await flushPromises()
  await w.findAll('button').find(b => b.text() === '查看版本')!.trigger('click')
  await flushPromises()
  expect(api.maintenance).toHaveBeenCalledWith('ORIGINAL', 1)
  expect(w.text()).toContain('解析完成 · 质量已核对')
  expect(w.text()).not.toContain('重复，保留原版本 · 质量待核对')
  w.unmount()
})
