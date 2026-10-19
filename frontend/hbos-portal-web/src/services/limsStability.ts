import { callFrappeMethod, unwrapPortalMethod } from '@/services/frappeClient'
import { portalDataSource } from '@/services/portalProvider'

export interface StabilityDashboard {
  notice_pending: number
  notice_approved: number
  protocol_pending: number
  protocol_approved: number
  product_count: number
  sample_count: number
  timepoint_count: number
  result_count: number
  timepoint_by_status: Record<string, number>
  master: { condition: number; room: number; test_item: number }
  scope?: string
}

export interface StabilityScheduleRow {
  name: string
  product_name?: string
  stability_sample?: string
  sample_name?: string
  batch_no?: string
  condition_type?: string
  storage_cond?: string
  time_point_label?: string
  plan_sample_date?: string
  actual_sample_date?: string
  plan_test_date?: string
  actual_test_date?: string
  effective_sample_due?: string
  effective_test_due?: string
  status: string
  exec_state?: string
  delay_state?: string
  sample_overdue?: number | boolean
  test_overdue?: number | boolean
  room?: string
  test_items?: Array<{ stability_test_item: string; is_required?: number | boolean }>
}

export interface StabilitySampleRow {
  name: string
  product_name?: string
  stability_product?: string
  sample_name?: string
  batch_no?: string
  storage_cond?: string
  condition_snapshot?: string
  room?: string
  storage_location?: string
  current_qty?: number
  qty_uom?: string
  in_date?: string
  start_date?: string
  status: string
  need_evaluation?: number | boolean
}

export interface StabilityResultRow {
  name: string
  timepoint?: string
  stability_sample?: string
  stability_test_item?: string
  item_snapshot?: string
  result_value?: string | number
  unit?: string
  is_qualified?: number | boolean
  is_significant_change?: number | boolean
  significant_change_basis?: string
  status: string
  analyst?: string
  test_date?: string
  spec_limit?: string
  spec_version?: string
  oos_flag?: number | boolean
  oot_flag?: number | boolean
}

export interface StabilityProduct {
  name: string
  product_code?: string
  product_name?: string
  category?: string
  default_uom?: string
  storage_cond_long?: string
  is_active?: number | boolean
}
export interface StabilityTestItem { name: string; item_code?: string; item_name?: string; result_type?: string }

export interface StabilityTrendPoint {
  name: string
  label?: string
  x?: number
  y?: number
  result_value?: number | string
  unit?: string
  status?: string
  is_significant_change?: number | boolean
  spec_limit?: string
  plan_sample_date?: string
}

export interface StabilityTrend {
  product?: string
  stability_test_item?: string
  condition_type?: string
  series: StabilityTrendPoint[]
  spec?: { limits_type?: string; lower?: number; upper?: number; text?: string; version?: string }
  trend_line?: { slope?: number; intercept?: number; r2?: number; points?: number }
  note?: string
}

export interface LimsStabilityEnvelope {
  section: string
  dashboard: StabilityDashboard
  schedule: { rows: StabilityScheduleRow[]; summary: Record<string, number> }
  samples: { rows: StabilitySampleRow[]; total: number }
  results: { rows: StabilityResultRow[]; total: number }
  products: { rows: StabilityProduct[]; total: number }
  test_items: { rows: StabilityTestItem[]; total: number }
  trend: StabilityTrend | null
  scope: string
}

interface PortalStabilityResponse { ok: boolean; data?: { data?: LimsStabilityEnvelope } }

const mockSchedule: StabilityScheduleRow[] = [
  { name: 'TP-026', product_name: '阿莫西林原料药', stability_sample: 'STB-S-023', sample_name: '26092401 稳定性样品', batch_no: '26092401', condition_type: '长期', storage_cond: '25℃ / 60%RH', time_point_label: '6 月', plan_sample_date: '2026-10-02', plan_test_date: '2026-10-07', effective_sample_due: '2026-10-05', effective_test_due: '2026-11-06', status: '待取样', exec_state: '待取样', room: '稳定性室 A', test_items: [{ stability_test_item: '有关物质', is_required: 1 }] },
  { name: 'TP-021', product_name: '头孢原料药', stability_sample: 'STB-S-018', sample_name: '26082308 稳定性样品', batch_no: '26082308', condition_type: '加速', storage_cond: '40℃ / 75%RH', time_point_label: '3 月', plan_sample_date: '2026-09-28', actual_sample_date: '2026-09-28', plan_test_date: '2026-10-03', effective_test_due: '2026-10-10', status: '检测中', exec_state: '检测中', room: '稳定性室 B', test_items: [{ stability_test_item: '含量', is_required: 1 }] },
  { name: 'TP-019', product_name: '阿莫西林片', stability_sample: 'STB-S-016', sample_name: '26072201 稳定性样品', batch_no: '26072201', condition_type: '长期', storage_cond: '25℃ / 60%RH', time_point_label: '6 月', plan_sample_date: '2026-09-24', plan_test_date: '2026-09-29', effective_test_due: '2026-10-02', status: '待检测', exec_state: '检测逾期', test_overdue: 1, room: '稳定性室 A', test_items: [{ stability_test_item: '溶出度', is_required: 1 }] },
  { name: 'TP-014', product_name: '盐酸左氧氟沙星片', stability_sample: 'STB-S-011', sample_name: '26042103 稳定性样品', batch_no: '26042103', condition_type: '长期', storage_cond: '25℃ / 60%RH', time_point_label: '6 月', plan_sample_date: '2026-09-18', actual_sample_date: '2026-09-18', plan_test_date: '2026-09-22', actual_test_date: '2026-09-23', effective_test_due: '2026-10-21', status: '已完成', exec_state: '已完成', room: '稳定性室 A', test_items: [{ stability_test_item: '性状', is_required: 1 }] },
]

const mockSamples: StabilitySampleRow[] = [
  { name: 'STB-S-023', product_name: '阿莫西林原料药', stability_product: 'STB-P-AMX', sample_name: '26092401 稳定性样品', batch_no: '26092401', storage_cond: '25℃ / 60%RH', condition_snapshot: '长期', room: '稳定性室 A', storage_location: 'A-03-02', current_qty: 86, qty_uom: 'g', in_date: '2026-09-25', start_date: '2026-09-26', status: '在箱', need_evaluation: 0 },
  { name: 'STB-S-018', product_name: '头孢原料药', stability_product: 'STB-P-CEF', sample_name: '26082308 稳定性样品', batch_no: '26082308', storage_cond: '40℃ / 75%RH', condition_snapshot: '加速', room: '稳定性室 B', storage_location: 'B-01-04', current_qty: 54, qty_uom: 'g', in_date: '2026-08-25', start_date: '2026-08-26', status: '在箱', need_evaluation: 1 },
]

const mockResults: StabilityResultRow[] = [
  { name: 'STB-R-1008', timepoint: 'TP-021', stability_sample: 'STB-S-018', stability_test_item: '含量', item_snapshot: '含量', result_value: '98.7', unit: '%', is_qualified: 1, status: '已批准', analyst: '检验员待显示', test_date: '2026-09-30', spec_limit: '95.0–105.0%', spec_version: 'V3.1' },
  { name: 'STB-R-1007', timepoint: 'TP-019', stability_sample: 'STB-S-016', stability_test_item: '溶出度', item_snapshot: '溶出度', result_value: '78.2', unit: '%', is_qualified: 1, is_significant_change: 1, significant_change_basis: '相对基线变化超过 5%', status: '待复核', analyst: '检验员待显示', test_date: '2026-09-29', spec_limit: '≥ 75%', spec_version: 'V2.0' },
]

const mockProducts: StabilityProduct[] = [
  { name: 'STB-P-AMX', product_code: 'API-AMX-001', product_name: '阿莫西林原料药', category: '原料药', default_uom: 'g', storage_cond_long: '25℃ / 60%RH', is_active: 1 },
  { name: 'STB-P-CEF', product_code: 'API-CEF-002', product_name: '头孢原料药', category: '原料药', default_uom: 'g', storage_cond_long: '25℃ / 60%RH', is_active: 1 },
]

const mockTrend: StabilityTrend = {
  product: '阿莫西林原料药', stability_test_item: '有关物质', condition_type: '长期',
  series: [{ name: '0M', label: '0 月', x: 0, y: 0.12, result_value: 0.12, unit: '%', status: '已批准', plan_sample_date: '2026-04-01' }, { name: '3M', label: '3 月', x: 3, y: 0.16, result_value: 0.16, unit: '%', status: '已批准', plan_sample_date: '2026-07-01' }, { name: '6M', label: '6 月', x: 6, y: 0.21, result_value: 0.21, unit: '%', status: '已批准', plan_sample_date: '2026-09-24', is_significant_change: 1 }],
  spec: { limits_type: '上限', upper: 0.5, text: '≤ 0.50%', version: 'V3.1' }, trend_line: { slope: 0.015, intercept: 0.115, r2: 0.99, points: 3 }, note: '趋势仅展示已批准且为当前版本的结果；统计控制限待质量部门确认。',
}

const mockEnvelope: LimsStabilityEnvelope = {
  section: 'workbench', dashboard: { notice_pending: 2, notice_approved: 8, protocol_pending: 1, protocol_approved: 7, product_count: 12, sample_count: 26, timepoint_count: 84, result_count: 198, timepoint_by_status: { wait_sample: 9, wait_test: 6, testing: 4, done: 65, cancelled: 0 }, master: { condition: 4, room: 2, test_item: 18 }, scope: '质量控制部 · 稳定性数据', },
  schedule: { rows: mockSchedule, summary: { total: 4, wait_sample: 1, wait_test: 1, testing: 1, done: 1, cancelled: 0, sample_overdue: 0, test_overdue: 1 } }, samples: { rows: mockSamples, total: 2 }, results: { rows: mockResults, total: 2 }, products: { rows: mockProducts, total: 2 }, test_items: { rows: [{ name: 'STB-ITEM-IMP', item_code: 'IMP', item_name: '有关物质' }, { name: 'STB-ITEM-ASSAY', item_code: 'ASSAY', item_name: '含量' }, { name: 'STB-ITEM-DISS', item_code: 'DISS', item_name: '溶出度' }], total: 3 }, trend: mockTrend, scope: '质量控制部 · 稳定性数据',
}

function emptyStabilityEnvelope(section = 'workbench'): LimsStabilityEnvelope {
  return {
    section,
    dashboard: { notice_pending: 0, notice_approved: 0, protocol_pending: 0, protocol_approved: 0, product_count: 0, sample_count: 0, timepoint_count: 0, result_count: 0, timepoint_by_status: {}, master: { condition: 0, room: 0, test_item: 0 }, scope: '稳定性数据' },
    schedule: { rows: [], summary: {} },
    samples: { rows: [], total: 0 },
    results: { rows: [], total: 0 },
    products: { rows: [], total: 0 },
    test_items: { rows: [], total: 0 },
    trend: null,
    scope: '稳定性数据',
  }
}

export async function getLimsStability(params: { section?: string; keyword?: string; status?: string; month?: string; condition?: string; exec_status?: string; stability_product?: string; stability_test_item?: string; condition_type?: string; limit?: number; offset?: number } = {}): Promise<LimsStabilityEnvelope> {
  if (portalDataSource === 'mock') {
    const data = JSON.parse(JSON.stringify(mockEnvelope)) as LimsStabilityEnvelope
    data.section = params.section || 'workbench'
    const q = String(params.keyword || '').trim().toLowerCase()
    if (q) {
      data.schedule.rows = data.schedule.rows.filter((row) => `${row.name} ${row.product_name} ${row.batch_no} ${row.stability_sample}`.toLowerCase().includes(q))
      data.samples.rows = data.samples.rows.filter((row) => `${row.name} ${row.product_name} ${row.batch_no}`.toLowerCase().includes(q))
      data.results.rows = data.results.rows.filter((row) => `${row.name} ${row.stability_test_item} ${row.stability_sample}`.toLowerCase().includes(q))
    }
    if (params.status) {
      data.schedule.rows = data.schedule.rows.filter((row) => row.status === params.status || row.exec_state === params.status)
      data.samples.rows = data.samples.rows.filter((row) => row.status === params.status)
      data.results.rows = data.results.rows.filter((row) => row.status === params.status)
    }
    if (params.stability_product) data.trend = data.trend && params.stability_product === 'STB-P-AMX' ? data.trend : null
    return data
  }
  const response = await callFrappeMethod<PortalStabilityResponse>('hbos_portal.api.stability.get_stability', { app_id: 'lims', ...params, limit: params.limit || 50 })
  const payload = unwrapPortalMethod(response)
  return payload.data || emptyStabilityEnvelope(params.section || 'workbench')
}
