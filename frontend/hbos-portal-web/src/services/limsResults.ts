import { callFrappeAction, callFrappeMethod, unwrapPortalMethod } from '@/services/frappeClient'
import { portalDataSource } from '@/services/portalProvider'

export interface LimsResultRow {
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

export interface LimsResultDetail {
  result: LimsResultRow
  sample: Record<string, unknown>
  revisions: Array<Record<string, unknown>>
  signature_chain: {
    analyst?: string
    submitted_at?: string | null
    reviewer?: string
    reviewed_at?: string | null
    approver?: string
    approved_at?: string | null
  }
}

interface ResultEnvelope {
  results: LimsResultRow[]
  total: number
  next_cursor?: string | null
  detail?: LimsResultDetail | null
}

interface PortalResultResponse {
  ok: boolean
  data?: {
    data?: ResultEnvelope
  }
}

const mockResults: LimsResultRow[] = [
  {
    result_name: 'RESULT-001', sample: 'SAMPLE-001', batch_no: '26092401', material_name: '阿莫西林',
    item_name: '含量', result_value: 98.6, result_text: '', raw_value: '98.6', unit: '%',
    verdict: '合格', result_status: '已提交', limits_type: '区间', limits_text: '95 - 105 %',
    lower_limit: 95, upper_limit: 105, significant_digits: 2, analyst: '检验员待显示',
    reviewer: '', approver: '', superseded_by: '', display: '98.6%',
  },
  {
    result_name: 'RESULT-002', sample: 'SAMPLE-031', batch_no: '26092308', material_name: '头孢原料',
    item_name: '水分', result_value: null, result_text: '', raw_value: '', unit: '%',
    verdict: '', result_status: '草稿', limits_type: '上限', limits_text: '≤ 3 %',
    lower_limit: null, upper_limit: 3, significant_digits: 2, analyst: '当前检验员',
    reviewer: '', approver: '', superseded_by: '', display: '',
  },
]

function filterMockResults(params: { keyword?: string; status?: string; verdict?: string }) {
  const keyword = String(params.keyword || '').trim().toLowerCase()
  return mockResults.filter((row) => {
    if (params.status && row.result_status !== params.status) return false
    if (params.verdict && row.verdict !== params.verdict) return false
    if (keyword && !`${row.result_name} ${row.sample} ${row.batch_no} ${row.material_name} ${row.item_name}`.toLowerCase().includes(keyword)) return false
    return true
  })
}

export async function listLimsResults(params: {
  keyword?: string
  status?: string
  verdict?: string
  cursor?: string
  limit?: number
} = {}): Promise<ResultEnvelope> {
  if (portalDataSource === 'mock') {
    const results = filterMockResults(params)
    return { results, total: results.length, next_cursor: null }
  }
  const response = await callFrappeMethod<PortalResultResponse>('hbos_portal.api.results.get_results', {
    app_id: 'lims',
    limit: params.limit || 50,
    cursor: params.cursor,
    keyword: params.keyword,
    status: params.status,
    verdict: params.verdict,
  })
  const payload = unwrapPortalMethod(response)
  return payload.data || { results: [], total: 0, next_cursor: null }
}

export async function getLimsResult(resultId: string): Promise<LimsResultDetail | null> {
  if (portalDataSource === 'mock') {
    const result = mockResults.find((item) => item.result_name === resultId) || null
    return result ? { result, sample: {}, revisions: [], signature_chain: {} } : null
  }
  const response = await callFrappeMethod<PortalResultResponse>('hbos_portal.api.results.get_results', {
    app_id: 'lims',
    result_id: resultId,
  })
  const payload = unwrapPortalMethod(response)
  return payload.data?.detail || null
}

export function submitLimsResult(params: {
  result_name: string
  raw_value?: string
  result_value?: string
  result_text?: string
  instrument_used?: string
  proxy_reason?: string
}) {
  if (portalDataSource !== 'frappe') return Promise.reject(new Error('演示模式不允许提交检验结果。'))
  return callFrappeAction('hb_lims_app.hbos_lims.lims_service.submit_result', params)
}

export function reviewLimsResult(resultName: string) {
  if (portalDataSource !== 'frappe') return Promise.reject(new Error('演示模式不允许复核检验结果。'))
  return callFrappeAction('hb_lims_app.hbos_lims.lims_service.review_result', { result_name: resultName })
}

export function approveLimsResult(resultName: string) {
  if (portalDataSource !== 'frappe') return Promise.reject(new Error('演示模式不允许批准检验结果。'))
  return callFrappeAction('hb_lims_app.hbos_lims.lims_service.approve_result', { result_name: resultName })
}
