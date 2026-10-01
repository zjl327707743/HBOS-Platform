import { callFrappeMethod, unwrapPortalMethod } from '@/services/frappeClient'
import { portalDataSource } from '@/services/portalProvider'

export interface LimsSpecificationItem {
  item: string
  item_name: string
  method_sop: string
  limits_type: string
  lower_limit: number | string | null
  upper_limit: number | string | null
  limits_text: string
  unit: string
  significant_digits?: number | null
  remark: string
}

export interface LimsSpecificationRow {
  specification_id: string
  spec_code: string
  spec_name: string
  material_code: string
  material_name: string
  version: string
  supersedes: string
  effective_date?: string | null
  status: string
  standard_source: string
  storage_condition: string
  retain_sample_qty: string
  remarks: string
  items?: LimsSpecificationItem[]
}

export interface LimsSpecificationDetail extends LimsSpecificationRow {
  items: LimsSpecificationItem[]
}

export interface LimsSpecificationEnvelope {
  specifications: LimsSpecificationRow[]
  total: number
  next_cursor?: string | null
  detail?: LimsSpecificationDetail | null
}

interface PortalSpecificationResponse {
  ok: boolean
  data?: { data?: LimsSpecificationEnvelope }
}

const mockSpecifications: LimsSpecificationDetail[] = [
  {
    specification_id: 'SPEC-API-AMX-V3.1', spec_code: 'SPEC-API-AMX', spec_name: '阿莫西林原料药质量标准',
    material_code: 'API-AMX-001', material_name: '阿莫西林', version: '3.1', supersedes: 'SPEC-API-AMX-V3.0',
    effective_date: '2026-09-01', status: '已生效', standard_source: '中国药典', storage_condition: '密封、避光',
    retain_sample_qty: '50 g', remarks: '', items: [
      { item: 'ASSAY', item_name: '含量', method_sop: 'SOP-QC-001', limits_type: '区间', lower_limit: 95, upper_limit: 105, limits_text: '95 - 105', unit: '%', significant_digits: 2, remark: '' },
      { item: 'WATER', item_name: '水分', method_sop: 'SOP-QC-004', limits_type: '上限', lower_limit: null, upper_limit: 3, limits_text: '≤ 3', unit: '%', significant_digits: 2, remark: '' },
    ],
  },
  {
    specification_id: 'SPEC-API-CEF-V2.4', spec_code: 'SPEC-API-CEF', spec_name: '头孢原料质量标准',
    material_code: 'API-CEF-002', material_name: '头孢原料', version: '2.4', supersedes: 'SPEC-API-CEF-V2.3',
    effective_date: '2026-08-18', status: '已生效', standard_source: '企业内控', storage_condition: '阴凉、干燥',
    retain_sample_qty: '30 g', remarks: '', items: [
      { item: 'ASSAY', item_name: '含量', method_sop: 'SOP-QC-001', limits_type: '区间', lower_limit: 98, upper_limit: 102, limits_text: '98 - 102', unit: '%', significant_digits: 2, remark: '' },
    ],
  },
  {
    specification_id: 'SPEC-FG-TAB-V1.3', spec_code: 'SPEC-FG-TAB', spec_name: '阿莫西林片质量标准',
    material_code: 'FG-TAB-003', material_name: '阿莫西林片', version: '1.3', supersedes: '',
    effective_date: '2026-09-30', status: '草稿', standard_source: '企业内控', storage_condition: '密封保存',
    retain_sample_qty: '20 片', remarks: '待质量负责人审核', items: [
      { item: 'APPEARANCE', item_name: '性状', method_sop: 'SOP-QC-011', limits_type: '记录型', lower_limit: null, upper_limit: null, limits_text: '记录型', unit: '', significant_digits: null, remark: '' },
    ],
  },
]

function filterMock(params: { keyword?: string; status?: string }) {
  const needle = String(params.keyword || '').trim().toLowerCase()
  return mockSpecifications.filter((row) => (
    (!params.status || row.status === params.status)
    && (!needle || `${row.specification_id} ${row.spec_code} ${row.spec_name} ${row.material_code} ${row.material_name} ${row.version}`.toLowerCase().includes(needle))
  ))
}

export async function listLimsSpecifications(params: {
  keyword?: string
  status?: string
  cursor?: string
  limit?: number
} = {}): Promise<LimsSpecificationEnvelope> {
  if (portalDataSource === 'mock') {
    const rows = filterMock(params)
    return { specifications: rows.map(({ items, ...row }) => ({ ...row, items: [] })), total: rows.length, next_cursor: null }
  }
  const response = await callFrappeMethod<PortalSpecificationResponse>('hbos_portal.api.specifications.get_specifications', {
    app_id: 'lims', limit: params.limit || 50, cursor: params.cursor,
    keyword: params.keyword, status: params.status,
  })
  const payload = unwrapPortalMethod(response)
  return payload.data || { specifications: [], total: 0, next_cursor: null }
}

export async function getLimsSpecification(specificationId: string): Promise<LimsSpecificationDetail | null> {
  if (portalDataSource === 'mock') return mockSpecifications.find((row) => row.specification_id === specificationId) || null
  const response = await callFrappeMethod<PortalSpecificationResponse>('hbos_portal.api.specifications.get_specifications', {
    app_id: 'lims', specification_id: specificationId,
  })
  const payload = unwrapPortalMethod(response)
  return payload.data?.detail || null
}
