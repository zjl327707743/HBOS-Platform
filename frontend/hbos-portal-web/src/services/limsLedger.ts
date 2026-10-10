import { callFrappeMethod, unwrapPortalMethod } from '@/services/frappeClient'
import { portalDataSource } from '@/services/portalProvider'

export interface LimsLedgerSample {
  name: string
  material_name: string
  material_code?: string
  batch_no: string
  sample_type: string
  sample_source?: string
  specification?: string
  spec_version?: string
  priority?: string
  status: string
  requestor?: string
  received_date?: string
  test_due_date?: string
  creation?: string
  remarks?: string
  oos_locked?: number | boolean
  report_date?: string
}

export interface LimsLedgerResult {
  result_name: string
  sample: string
  batch_no: string
  material_name: string
  item_name: string
  result_value: number | string | null
  result_text: string
  raw_value: string
  unit: string
  verdict: string
  result_status: string
  limits_type: string
  limits_text: string
  lower_limit: number | string | null
  upper_limit: number | string | null
  significant_digits?: number | null
  analyst: string
  submitted_at?: string | null
  reviewer: string
  reviewed_at?: string | null
  approver: string
  approved_at?: string | null
  superseded_by: string
  display: string
}

export interface LimsLedgerRevision {
  name: string
  result: string
  field_changed: string
  old_value: string
  new_value: string
  changed_by: string
  changed_at: string
  change_reason: string
}

export interface LimsLedgerGroup {
  type: string
  items: Array<{ material: string; count: number }>
}

export interface LimsLedgerEnvelope {
  samples: LimsLedgerSample[]
  results: LimsLedgerResult[]
  revisions: LimsLedgerRevision[]
  coas: Record<string, string>
  groups: LimsLedgerGroup[]
  total_samples: number
  next_cursor?: string | null
}

interface PortalLedgerResponse {
  ok: boolean
  data?: { data?: LimsLedgerEnvelope }
}

const mockSamples: LimsLedgerSample[] = [
  {
    name: 'SAMPLE-001', material_name: '阿莫西林', batch_no: '26092401', sample_type: '原料药',
    specification: '中国药典 2025', spec_version: 'V3.1', status: '检验中', priority: '高',
    received_date: '2026-09-24', test_due_date: '2026-09-30', oos_locked: 0,
  },
  {
    name: 'SAMPLE-031', material_name: '头孢原料', batch_no: '26092308', sample_type: '原料药',
    specification: '企业标准', spec_version: 'V2.4', status: '已登记', priority: '普通',
    received_date: '2026-09-23', test_due_date: '2026-10-01', oos_locked: 0,
  },
]

const mockResults: LimsLedgerResult[] = [
  {
    result_name: 'RESULT-001', sample: 'SAMPLE-001', batch_no: '26092401', material_name: '阿莫西林',
    item_name: '含量', result_value: 98.6, result_text: '', raw_value: '98.6', unit: '%', verdict: '合格',
    result_status: '已提交', limits_type: '区间', limits_text: '95 - 105 %', lower_limit: 95, upper_limit: 105,
    significant_digits: 2, analyst: '检验员待显示', submitted_at: '2026-09-30 09:12:00', reviewer: '', approver: '',
    superseded_by: '', display: '98.6%',
  },
  {
    result_name: 'RESULT-002', sample: 'SAMPLE-031', batch_no: '26092308', material_name: '头孢原料',
    item_name: '水分', result_value: null, result_text: '', raw_value: '', unit: '%', verdict: '', result_status: '草稿',
    limits_type: '上限', limits_text: '≤ 3 %', lower_limit: null, upper_limit: 3, significant_digits: 2,
    analyst: '当前检验员', reviewer: '', approver: '', superseded_by: '', display: '',
  },
]

function mockLedger(params: { keyword?: string; status?: string; verdict?: string }): LimsLedgerEnvelope {
  const needle = String(params.keyword || '').trim().toLowerCase()
  const results = mockResults.filter((row) => (
    (!params.status || row.result_status === params.status)
    && (!params.verdict || row.verdict === params.verdict)
    && (!needle || `${row.result_name} ${row.sample} ${row.batch_no} ${row.material_name} ${row.item_name}`.toLowerCase().includes(needle))
  ))
  const sampleIds = new Set(results.map((row) => row.sample))
  const samples = mockSamples.filter((sample) => sampleIds.has(sample.name))
  return {
    samples,
    results,
    revisions: [],
    coas: {},
    groups: [{ type: '原料药', items: [{ material: '阿莫西林', count: 1 }, { material: '头孢原料', count: 1 }] }],
    total_samples: samples.length,
    next_cursor: null,
  }
}

export async function listLimsLedger(params: {
  sample_type?: string
  material?: string
  keyword?: string
  status?: string
  verdict?: string
  limit?: number
  cursor?: string
} = {}): Promise<LimsLedgerEnvelope> {
  if (portalDataSource === 'mock') return mockLedger(params)
  const response = await callFrappeMethod<PortalLedgerResponse>('hbos_portal.api.ledger.get_ledger', {
    app_id: 'lims',
    ...params,
    limit: params.limit || 50,
  })
  const payload = unwrapPortalMethod(response)
  return payload.data || {
    samples: [], results: [], revisions: [], coas: {}, groups: [], total_samples: 0, next_cursor: null,
  }
}
