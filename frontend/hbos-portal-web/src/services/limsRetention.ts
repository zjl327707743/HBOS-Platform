import { callFrappeMethod, unwrapPortalMethod } from '@/services/frappeClient'
import { portalDataSource } from '@/services/portalProvider'

export interface LimsRetentionSample {
  name: string
  retention_product: string
  product_code: string
  product_name: string
  sample_name: string
  material_code: string
  batch_no: string
  category: string
  status: string
  source: string
  retention_date?: string | null
  expiry_date?: string | null
  retention_due_date?: string | null
  retention_qty: number
  qty_uom: string
  package_count: number
  package_spec: string
  current_qty: number
  reserved_qty: number
  available_qty: number
  observed_flag: number | boolean
  obs_year?: number | null
  obs_selected_reason: string
  next_obs_month?: number | null
  next_obs_due_date?: string | null
  obs_rule: string
  storage_condition: string
  storage_location: string
  retained_by: string
  remarks: string
}

export interface LimsRetentionProduct {
  name: string
  product_code: string
  product_name: string
  category: string
  is_active: number | boolean
  retention_qty_rule: string
  full_test_qty?: number | null
  full_test_qty_uom: string
  default_uom: string
  is_liquid: number | boolean
  is_outsource: number | boolean
  storage_condition: string
  obs_rule: string
}

export interface LimsRetentionObservation {
  name: string
  product: string
  sampleName: string
  batch: string
  monthOffset?: number | null
  planDate?: string | null
  due: string
  result?: string | null
  selectedReason: string
  obsYear?: number | null
  obs_rule?: string
  status?: string
  reviewReady?: boolean
}

export interface LimsRetentionUsage {
  name: string
  retention_name: string
  product: string
  sample_name: string
  batch: string
  qty: number
  uom: string
  scenario: string
  reason: string
  dept: string
  applicant: string
  applicant_date: string
  status: string
  stock_confirm_by?: string
  stock_qty?: number
  qc_approval?: string
  qa_approval?: string
  qm_approval?: string
  current_qty: number
  reserved_qty: number
  available_qty: number
}

export interface LimsRetentionDisposal {
  name: string
  retention_name: string
  product: string
  sample_name: string
  batch: string
  category: string
  qty: number
  uom: string
  type: string
  reason: string
  method: string
  location: string
  qa_manager_required: number | boolean
  applicant: string
  applicant_date: string
  status: string
  current_qty: number
  reserved_qty: number
  deadline?: string
  new_retention_due_date?: string
  sample_prev_status?: string
  disposal_by?: string
  monitor_by?: string
}

export interface LimsRetentionEnvelope {
  samples: LimsRetentionSample[]
  samples_total: number
  samples_next_cursor?: string | null
  products: LimsRetentionProduct[]
  products_total: number
  products_next_cursor?: string | null
  observations: LimsRetentionObservation[]
  observation_completeness: Array<{ product: string; rule: string; year: number; selected: number; cap: number | null }>
  usage: { rows: LimsRetentionUsage[]; total: number }
  disposal: { rows: LimsRetentionDisposal[]; total: number }
  summary: {
    sample_total: number
    in_stock: number
    observed: number
    near_due_30: number
    pending_usage: number
    pending_disposal: number
    due_observation: number
  }
  section: string
}

interface PortalRetentionResponse {
  ok: boolean
  data?: { data?: LimsRetentionEnvelope }
}

const mockSamples: LimsRetentionSample[] = [
  {
    name: 'RET-2026-0007', retention_product: 'RP-AMX', product_code: 'API-AMX-001', product_name: '阿莫西林原料药',
    sample_name: '阿莫西林留样', material_code: 'API-AMX-001', batch_no: '26092401', category: '关键物料', status: '在库', source: '检验完成批次',
    retention_date: '2026-09-24', expiry_date: '2028-09-23', retention_due_date: '2029-09-23', retention_qty: 120, qty_uom: 'g', package_count: 2, package_spec: '60 g / 瓶',
    current_qty: 120, reserved_qty: 20, available_qty: 100, observed_flag: 1, obs_year: 2026, obs_selected_reason: '年度观察批', next_obs_month: 12, next_obs_due_date: '2027-09-24', obs_rule: '每年选 3 批（原料药成品）', storage_condition: '密封、避光', storage_location: '留样柜 A-03', retained_by: '检验员待显示', remarks: '',
  },
  {
    name: 'RET-2026-0008', retention_product: 'RP-CEF', product_code: 'API-CEF-002', product_name: '头孢原料药',
    sample_name: '头孢原料留样', material_code: 'API-CEF-002', batch_no: '26092308', category: '成品（原料药）', status: '部分使用', source: '手工登记',
    retention_date: '2026-09-23', expiry_date: '2028-09-22', retention_due_date: '2029-09-22', retention_qty: 80, qty_uom: 'g', package_count: 1, package_spec: '80 g / 瓶',
    current_qty: 48, reserved_qty: 0, available_qty: 48, observed_flag: 1, obs_year: 2026, obs_selected_reason: '年度观察批', next_obs_month: 0, next_obs_due_date: '2026-09-28', obs_rule: '每年选 3 批（原料药成品）', storage_condition: '阴凉、干燥', storage_location: '留样柜 A-04', retained_by: '检验员待显示', remarks: '外观观察待审核',
  },
  {
    name: 'RET-2026-0009', retention_product: 'RP-TAB', product_code: 'FG-TAB-003', product_name: '阿莫西林片',
    sample_name: '阿莫西林片留样', material_code: 'FG-TAB-003', batch_no: '26093001', category: '外售产品', status: '在库', source: '检验完成批次',
    retention_date: '2026-09-30', expiry_date: '2028-09-29', retention_due_date: '2026-10-25', retention_qty: 30, qty_uom: '盒', package_count: 3, package_spec: '10 盒',
    current_qty: 30, reserved_qty: 0, available_qty: 30, observed_flag: 1, obs_year: 2026, obs_selected_reason: '外售产品每批', next_obs_month: 0, next_obs_due_date: '2026-10-30', obs_rule: '每批观察（外售产品）', storage_condition: '常温、避光', storage_location: '留样柜 B-02', retained_by: '检验员待显示', remarks: '',
  },
]

const mockProducts: LimsRetentionProduct[] = [
  { name: 'RP-AMX', product_code: 'API-AMX-001', product_name: '阿莫西林原料药', category: '关键物料', is_active: 1, retention_qty_rule: '全检量 2 倍', full_test_qty: 60, full_test_qty_uom: 'g', default_uom: 'g', is_liquid: 0, is_outsource: 0, storage_condition: '密封、避光', obs_rule: '每年选 3 批（原料药成品）' },
  { name: 'RP-CEF', product_code: 'API-CEF-002', product_name: '头孢原料药', category: '成品（原料药）', is_active: 1, retention_qty_rule: '全检量 2 倍', full_test_qty: 40, full_test_qty_uom: 'g', default_uom: 'g', is_liquid: 0, is_outsource: 0, storage_condition: '阴凉、干燥', obs_rule: '每年选 3 批（原料药成品）' },
  { name: 'RP-TAB', product_code: 'FG-TAB-003', product_name: '阿莫西林片', category: '外售产品', is_active: 1, retention_qty_rule: '按实际', full_test_qty: null, full_test_qty_uom: '', default_uom: '盒', is_liquid: 0, is_outsource: 0, storage_condition: '常温、避光', obs_rule: '每批观察（外售产品）' },
]

const mockObservations: LimsRetentionObservation[] = [
  { name: 'RET-2026-0008', product: '头孢原料药', sampleName: '头孢原料留样', batch: '26092308', monthOffset: 0, planDate: '2026-09-28', due: '待审核', result: '正常', selectedReason: '年度观察批', obsYear: 2026, obs_rule: '每年选 3 批', status: '部分使用', reviewReady: true },
  { name: 'RET-2026-0007', product: '阿莫西林原料药', sampleName: '阿莫西林留样', batch: '26092401', monthOffset: 12, planDate: '2027-09-24', due: '应观察', result: null, selectedReason: '年度观察批', obsYear: 2026, obs_rule: '每年选 3 批', status: '在库', reviewReady: false },
  { name: 'RET-2026-0009', product: '阿莫西林片', sampleName: '阿莫西林片留样', batch: '26093001', monthOffset: 0, planDate: '2026-10-30', due: '应观察', result: null, selectedReason: '外售产品每批', obsYear: 2026, obs_rule: '每批观察', status: '在库', reviewReady: false },
]

const mockUsage: LimsRetentionUsage[] = [
  { name: 'USE-2026-0012', retention_name: 'RET-2026-0007', product: '阿莫西林原料药', sample_name: '阿莫西林留样', batch: '26092401', qty: 20, uom: 'g', scenario: '检验结果分析', reason: '复核异常趋势', dept: '质量控制部', applicant: '检验员待显示', applicant_date: '2026-09-30', status: '待QC批准', current_qty: 120, reserved_qty: 20, available_qty: 100 },
]

const mockDisposal: LimsRetentionDisposal[] = [
  { name: 'DSP-2026-0004', retention_name: 'RET-2026-0008', product: '头孢原料药', sample_name: '头孢原料留样', batch: '26092308', category: '成品（原料药）', qty: 80, uom: 'g', type: '留样期满销毁', reason: '留样期至', method: '按废弃物规程处理', location: '质量废弃物暂存间', qa_manager_required: 0, applicant: '检验员待显示', applicant_date: '2026-09-30', status: '待QA审核', current_qty: 48, reserved_qty: 0, deadline: '2026-12-30', sample_prev_status: '部分使用' },
]

const mockEnvelope: LimsRetentionEnvelope = {
  samples: mockSamples, samples_total: mockSamples.length, samples_next_cursor: null,
  products: mockProducts, products_total: mockProducts.length, products_next_cursor: null,
  observations: mockObservations, observation_completeness: [{ product: '阿莫西林原料药', rule: '年度观察批', year: 2026, selected: 1, cap: 3 }],
  usage: { rows: mockUsage, total: mockUsage.length }, disposal: { rows: mockDisposal, total: mockDisposal.length },
  summary: { sample_total: 3, in_stock: 3, observed: 3, near_due_30: 1, pending_usage: 1, pending_disposal: 1, due_observation: 3 }, section: 'workbench',
}

function emptyRetentionEnvelope(section = 'workbench'): LimsRetentionEnvelope {
  return {
    samples: [], samples_total: 0, samples_next_cursor: null,
    products: [], products_total: 0, products_next_cursor: null,
    observations: [], observation_completeness: [],
    usage: { rows: [], total: 0 }, disposal: { rows: [], total: 0 },
    summary: { sample_total: 0, in_stock: 0, observed: 0, near_due_30: 0, pending_usage: 0, pending_disposal: 0, due_observation: 0 },
    section,
  }
}

export async function getLimsRetention(params: { section?: string; keyword?: string; status?: string; active?: string; limit?: number; cursor?: string } = {}): Promise<LimsRetentionEnvelope> {
  if (portalDataSource === 'mock') {
    const needle = String(params.keyword || '').trim().toLowerCase()
    const data = JSON.parse(JSON.stringify(mockEnvelope)) as LimsRetentionEnvelope
    if (needle) {
      data.samples = data.samples.filter((row) => `${row.name} ${row.product_name} ${row.sample_name} ${row.batch_no}`.toLowerCase().includes(needle))
      data.products = data.products.filter((row) => `${row.product_code} ${row.product_name} ${row.category}`.toLowerCase().includes(needle))
    }
    if (params.status) {
      data.samples = data.samples.filter((row) => row.status === params.status)
      data.usage.rows = data.usage.rows.filter((row) => row.status === params.status)
      data.disposal.rows = data.disposal.rows.filter((row) => row.status === params.status)
    }
    if (params.active) data.products = data.products.filter((row) => (params.active === '启用') === Boolean(row.is_active))
    data.samples_total = data.samples.length; data.products_total = data.products.length
    return data
  }
  const response = await callFrappeMethod<PortalRetentionResponse>('hbos_portal.api.retention.get_retention', {
    app_id: 'lims', ...params, limit: params.limit || 50,
  })
  const payload = unwrapPortalMethod(response)
  return payload.data || emptyRetentionEnvelope(params.section || 'workbench')
}
