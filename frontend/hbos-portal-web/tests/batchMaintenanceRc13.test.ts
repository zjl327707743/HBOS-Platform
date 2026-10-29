import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MaintenanceView from '@/views/KnowledgeMaintenanceView.vue'

const api = vi.hoisted(() => ({
  status: vi.fn(), dashboard: vi.fn(), feedback: vi.fn(), action: vi.fn(),
  plan: vi.fn(), submit: vi.fn(), progress: vi.fn(),
  pause: vi.fn(), resume: vi.fn(), reclaim: vi.fn(),
}))
vi.mock('@/services/p1Api', async original => ({
  ...(await original<typeof import('@/services/p1Api')>()),
  getKnowledgeStatus: api.status,
}))
vi.mock('@/services/knowledgeMaintenanceApi', async original => ({
  ...(await original<typeof import('@/services/knowledgeMaintenanceApi')>()),
  getMaintenance: api.dashboard,
  getMaintenanceFeedbackPage: api.feedback,
  maintenanceAction: api.action,
  previewImport: vi.fn(),
  uploadKnowledge: vi.fn(),
  planImport: api.plan,
  submitImport: api.submit,
  getBatchProgress: api.progress,
  pauseImport: api.pause,
  resumeImport: api.resume,
  reclaimImport: api.reclaim,
}))

const digest = 'a'.repeat(64)
const batchId = 'IMP_' + '1'.repeat(32)
const plan = {
  schema: 'rc13-batch-plan-v1', plan_sha256: digest, readonly: true, label: '合成批次',
  department: 'production', departments: ['production'], sharing_confirmed: true,
  items: [
    { index: 0, source_sha256: 'b'.repeat(64), disposition: 'NEW', submittable: true,
      conflict_reason: null, pages: 2, page_methods: ['native', 'cached_ocr'],
      filename: '合成一.md', title: '合成一', department: 'production',
      document_id: 'DOC_' + '2'.repeat(24), version_id: 'VER_' + '3'.repeat(24),
      expected_current_version: null, target: { space_id: 'DEPT_PRODUCTION', title: '生产', department: 'production' },
      evidence: { source_sha256: 'b'.repeat(64) } },
    { index: 1, source_sha256: 'c'.repeat(64), disposition: 'DUPLICATE', submittable: true,
      conflict_reason: null, pages: 1, page_methods: ['native'],
      filename: '合成二.md', title: '合成二', department: 'production',
      document_id: 'DOC_' + '4'.repeat(24), version_id: 'VER_' + '5'.repeat(24),
      expected_current_version: null, target: { space_id: 'DEPT_PRODUCTION', title: '生产', department: 'production' },
      evidence: { source_sha256: 'c'.repeat(64) } },
  ],
  counts: { total: 2, new: 1, duplicate: 1, business_update: 0, technical_repair: 0, new_upload_required: 0, anomaly: 0 },
  groups: [{ department: 'production', documents: 2, jobs: 1, duplicate_documents: 1 }],
  blocking_anomalies: 0, submittable: true, next_action: 'submit_import',
}
const receipt = {
  schema: 'rc13-batch-submit-v1', plan_sha256: digest, approval_ref: 'OWNER_SYNTHETIC',
  label: '合成批次', submitted_at: 1, actor_hash: 'd'.repeat(16), batches: [
    { batch_id: batchId, department: 'production', documents: 2, queued_documents: 2,
      job_id: 'JOB_1', status: 'Queued', active_job: 'Queued', kind: 'derivative' }],
  replayed: false,
}
const progress = (jobStatus: string, receiptStatus = 'VERIFIED') => ({
  schema: 'rc13-batch-plan-v1', batch_id: batchId, label: '合成批次', department: 'production',
  status: jobStatus === 'Running' ? 'Running' : 'Completed', last_error: null,
  job: { id: 'JOB_1', status: jobStatus, operation: 'parse', lease_generation: 3,
    lease_expires_at: 99, lease_expired: false, pause_requested: false, requested_at: 1,
    reclaims: 0, document_ids: ['DOC_' + '2'.repeat(24)] },
  items: [{ document_id: 'DOC_' + '2'.repeat(24), version_id: 'VER_' + '3'.repeat(24),
    title: '合成一', filename: '合成一.md', department: 'production', status: 'parsed/indexed',
    progress: 1, chunk_count: 8, error_code: null, publication_status: 'Published',
    retrieval_verified: { status: receiptStatus, at: 1, reason: receiptStatus === 'INVALIDATED' ? 'WITHDRAWN' : undefined } }],
  total: 1, page: 1, limit: 20,
  counts: { parsed: 1, failed: 0, queued: 0, verified: 0, invalidated: 0 },
})

const Button = defineComponent({
  props: ['disabled', 'loading'],
  emits: ['click'],
  template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot/></button>',
})
const Input = defineComponent({
  props: ['value'],
  emits: ['update:value'],
  methods: { onInput(event: Event) { this.$emit('update:value', (event.target as HTMLInputElement).value) } },
  template: '<input :value="value" @input="onInput" />',
})
const Textarea = defineComponent({
  props: ['value'],
  emits: ['update:value'],
  methods: { onInput(event: Event) { this.$emit('update:value', (event.target as HTMLTextAreaElement).value) } },
  template: '<textarea :value="value" @input="onInput" />',
})
const Alert = defineComponent({ props: ['message'], template: '<div class="alert">{{message}}</div>' })
const Tag = defineComponent({ template: '<span class="tag"><slot/></span>' })
const stubs = {
  'a-button': Button, 'a-input': Input, 'a-textarea': Textarea, 'a-alert': Alert, 'a-tag': Tag,
  'a-select': true, 'a-skeleton': true, 'a-result': true, 'a-collapse': true,
  'a-collapse-panel': true, 'a-pagination': true, 'a-checkbox': true, 'a-popconfirm': true,
  'a-progress': true, 'a-steps': true, 'a-drawer': true, 'a-checkbox-group': true,
  'a-empty': true, 'a-input-search': true,
}

let wrapper: ReturnType<typeof mount> | undefined
async function view() {
  const pinia = createPinia(); setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/hbos/knowledge/maintenance/:rest(.*)*', component: { template: '<div/>' } }] })
  await router.push('/hbos/knowledge/maintenance'); await router.isReady()
  wrapper = mount(MaintenanceView, { global: { plugins: [pinia, router], stubs } })
  await flushPromises()
  return wrapper
}
async function previewPlan() {
  const w = await view()
  await w.findAll('button').find(button => button.text() === '直接粘贴清单 JSON')!.trigger('click')
  await w.get('textarea').setValue(JSON.stringify({ schema_version: 2, sharing_confirmed: true, items: [] }))
  await w.findAll('button').find(button => button.text() === '预演清单')!.trigger('click')
  await flushPromises()
  return w
}
function button(w: ReturnType<typeof mount>, text: string) {
  return w.findAll('button').find(candidate => candidate.text() === text)!
}
beforeEach(() => {
  vi.clearAllMocks()
  api.status.mockResolvedValue({ can_maintain: true })
  api.dashboard.mockResolvedValue({
    departments: [{ key: 'production', title: '生产' }], published_documents: [], batches: [],
    selected: null, feedback: { items: [] },
    import_availability: { can_parse: true, can_batch: true, configured: true, blocked: false },
  })
  api.feedback.mockImplementation((page: number) => Promise.resolve({ items: [], page, page_size: 6, has_more: false }))
  api.plan.mockResolvedValue(plan)
  api.submit.mockResolvedValue(receipt)
  api.progress.mockResolvedValue(progress('Running'))
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers() })

describe('batch import preview', () => {
  it('shows plan_sha256, per-item classification, pages and target directory', async () => {
    const w = await previewPlan()
    expect(api.plan).toHaveBeenCalledTimes(1)
    const text = w.text()
    expect(text).toContain('plan_sha256 ' + digest)
    expect(text).toContain('新文件（已登记原件）')
    expect(text).toContain('重复，保留已处理版本')
    expect(text).toContain('2 页')
    expect(text).toContain('生产')
    expect(text).toContain('提交批量入库')
  })

  it('disables submission until the preview has no blocking anomalies', async () => {
    api.plan.mockResolvedValue({ ...plan, submittable: false, blocking_anomalies: 1,
      items: [{ ...plan.items[0], disposition: 'ANOMALY', submittable: false, conflict_reason: 'IDENTITY_CONFLICT' }] })
    const w = await previewPlan()
    expect(w.text()).toContain('存在阻断项')
    expect(button(w, '提交批量入库').attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('IDENTITY_CONFLICT')
  })
})

describe('batch submit and progress', () => {
  it('submits once with digest and approval, then polls only while Running', async () => {
    vi.useFakeTimers()
    let resolveSubmit: (value: unknown) => void = () => undefined
    api.submit.mockImplementation(() => new Promise(resolve => { resolveSubmit = resolve }))
    const w = await previewPlan()
    const approval = w.findAll('input').find(input => (input.attributes('placeholder') || '').includes('OWNER_RC13'))!
    await approval.setValue('OWNER_SYNTHETIC_APPROVAL')
    const submit = button(w, '提交批量入库')
    await submit.trigger('click')
    await submit.trigger('click')
    expect(api.submit).toHaveBeenCalledTimes(1)
    expect(api.submit).toHaveBeenCalledWith(digest, 'OWNER_SYNTHETIC_APPROVAL', '合成批次')
    resolveSubmit(receipt)
    await flushPromises()
    expect(api.progress).toHaveBeenCalledWith(batchId)
    await vi.advanceTimersByTimeAsync(4100)
    expect(api.progress.mock.calls.length).toBeGreaterThanOrEqual(2)
    expect(w.text()).toContain('检索已验证')
    api.progress.mockResolvedValue(progress('Completed'))
    await vi.advanceTimersByTimeAsync(4100)
    const settled = api.progress.mock.calls.length
    await vi.advanceTimersByTimeAsync(12_000)
    expect(api.progress.mock.calls.length).toBe(settled)
    expect(w.text()).toContain('仅在任务运行中自动轮询')
  })

  it('shows the persistent receipt as invalidated after withdrawal, not deleted', async () => {
    api.progress.mockResolvedValue(progress('Completed', 'INVALIDATED'))
    const w = await previewPlan()
    const approval = w.findAll('input').find(input => (input.attributes('placeholder') || '').includes('OWNER_RC13'))!
    await approval.setValue('OWNER_SYNTHETIC_APPROVAL')
    await button(w, '提交批量入库').trigger('click')
    await flushPromises()
    expect(w.text()).toContain('检索验证已失效（已下架）')
    expect(w.text()).toContain('撤回或换版后收据标记失效但不删除历史')
  })
})
