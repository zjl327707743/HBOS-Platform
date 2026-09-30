import { callFrappeMethod, unwrapPortalMethod } from '@/services/frappeClient'
import { portalDataSource } from '@/services/portalProvider'

export interface LimsCoaItem {
  test_item: string
  item_name: string
  method_sop: string
  standard: string
  result: string
  verdict: string
  remark: string
}

export interface LimsCoaRow {
  coa_id: string
  sample: string
  batch_no: string
  material_code: string
  material_name: string
  spec_version: string
  report_status: string
  qa_reviewer: string
  qa_reviewed_at?: string | null
  published_by: string
  published_at?: string | null
  pdf_attachment: string
  remarks: string
  items?: LimsCoaItem[]
}

export interface LimsCoaDetail extends LimsCoaRow {
  items: LimsCoaItem[]
}

export interface LimsCoaEnvelope {
  coas: LimsCoaRow[]
  total: number
  next_cursor?: string | null
  detail?: LimsCoaDetail | null
}

interface PortalCoaResponse {
  ok: boolean
  data?: { data?: LimsCoaEnvelope }
}

const mockCoas: LimsCoaDetail[] = [
  {
    coa_id: 'HBOS-COA-2026-0007', sample: 'SAMPLE-001', batch_no: '26092401',
    material_code: 'API-AMX-001', material_name: '阿莫西林', spec_version: 'V3.1',
    report_status: '已发布', qa_reviewer: 'QA 待显示', qa_reviewed_at: '2026-09-29 15:20:00',
    published_by: '质量负责人待显示', published_at: '2026-09-30 08:30:00', pdf_attachment: '', remarks: '',
    items: [
      { test_item: 'ASSAY', item_name: '含量', method_sop: 'SOP-QC-001', standard: '95.0% - 105.0%', result: '98.6%', verdict: '合格', remark: '' },
      { test_item: 'WATER', item_name: '水分', method_sop: 'SOP-QC-004', standard: '≤ 3.0%', result: '1.2%', verdict: '合格', remark: '' },
    ],
  },
  {
    coa_id: 'HBOS-COA-2026-0008', sample: 'SAMPLE-014', batch_no: '26092903',
    material_code: 'API-CEF-002', material_name: '头孢原料', spec_version: 'V2.4',
    report_status: '已审核', qa_reviewer: 'QA 待显示', qa_reviewed_at: '2026-09-30 10:12:00',
    published_by: '', published_at: null, pdf_attachment: '', remarks: '等待质量负责人发布',
    items: [
      { test_item: 'ASSAY', item_name: '含量', method_sop: 'SOP-QC-001', standard: '98.0% - 102.0%', result: '99.1%', verdict: '合格', remark: '' },
    ],
  },
  {
    coa_id: 'HBOS-COA-2026-0009', sample: 'SAMPLE-021', batch_no: '26093001',
    material_code: 'FG-TAB-003', material_name: '阿莫西林片', spec_version: 'V1.2',
    report_status: '草稿', qa_reviewer: '', qa_reviewed_at: null,
    published_by: '', published_at: null, pdf_attachment: '', remarks: '',
    items: [
      { test_item: 'APPEARANCE', item_name: '性状', method_sop: 'SOP-QC-011', standard: '白色片剂', result: '白色片剂', verdict: '合格', remark: '' },
    ],
  },
]

function filterMock(params: { keyword?: string; status?: string }) {
  const needle = String(params.keyword || '').trim().toLowerCase()
  return mockCoas.filter((row) => (
    (!params.status || row.report_status === params.status)
    && (!needle || `${row.coa_id} ${row.sample} ${row.batch_no} ${row.material_name} ${row.spec_version}`.toLowerCase().includes(needle))
  ))
}

export async function listLimsCoas(params: {
  keyword?: string
  status?: string
  cursor?: string
  limit?: number
} = {}): Promise<LimsCoaEnvelope> {
  if (portalDataSource === 'mock') {
    const rows = filterMock(params)
    return { coas: rows.map(({ items, ...row }) => ({ ...row, items: [] })), total: rows.length, next_cursor: null }
  }
  const response = await callFrappeMethod<PortalCoaResponse>('hbos_portal.api.coa.get_coas', {
    app_id: 'lims', limit: params.limit || 50, cursor: params.cursor,
    keyword: params.keyword, status: params.status,
  })
  const payload = unwrapPortalMethod(response)
  return payload.data || { coas: [], total: 0, next_cursor: null }
}

export async function getLimsCoa(coaId: string): Promise<LimsCoaDetail | null> {
  if (portalDataSource === 'mock') return mockCoas.find((row) => row.coa_id === coaId) || null
  const response = await callFrappeMethod<PortalCoaResponse>('hbos_portal.api.coa.get_coas', {
    app_id: 'lims', coa_id: coaId,
  })
  const payload = unwrapPortalMethod(response)
  return payload.data?.detail || null
}
