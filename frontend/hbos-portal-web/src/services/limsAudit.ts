import { callFrappeMethod, unwrapPortalMethod } from '@/services/frappeClient'
import { portalDataSource } from '@/services/portalProvider'

export interface LimsAuditEvent {
  name: string
  log_type: string
  doctype_target: string
  doc_name: string
  action_text: string
  field_changed: string
  old_value: string
  new_value: string
  reason: string
  user: string
  created_at: string
  checksum: string
}

export interface LimsAuditEnvelope {
  events: LimsAuditEvent[]
  total: number
  next_cursor?: string | null
  targets: string[]
}

interface PortalAuditResponse {
  ok: boolean
  data?: { data?: LimsAuditEnvelope }
}

const mockEvents: LimsAuditEvent[] = [
  {
    name: 'AUDIT-001', log_type: '提交', doctype_target: 'HBOS Test Result', doc_name: 'RESULT-001',
    action_text: '结果提交 · 自动判定 合格', field_changed: 'result_status', old_value: '草稿', new_value: '已提交',
    reason: '', user: '检验员待显示', created_at: '2026-09-30 09:12:00', checksum: 'a91bc2e61b00f3d9',
  },
  {
    name: 'AUDIT-002', log_type: '复核', doctype_target: 'HBOS Test Result', doc_name: 'RESULT-098',
    action_text: '结果复核（第二人独立）', field_changed: 'result_status', old_value: '已提交', new_value: '已复核',
    reason: '', user: '复核员待显示', created_at: '2026-09-29 16:40:00', checksum: '22d9ef84d110c9a4',
  },
]

export async function listLimsAudit(params: {
  log_type?: string
  doctype_target?: string
  user?: string
  keyword?: string
  from_date?: string
  to_date?: string
  limit?: number
  cursor?: string
} = {}): Promise<LimsAuditEnvelope> {
  if (portalDataSource === 'mock') {
    const needle = String(params.keyword || '').trim().toLowerCase()
    const events = mockEvents.filter((event) => (
      (!params.log_type || event.log_type === params.log_type)
      && (!params.doctype_target || event.doctype_target === params.doctype_target)
      && (!needle || `${event.doc_name} ${event.action_text} ${event.checksum}`.toLowerCase().includes(needle))
    ))
    return {
      events,
      total: events.length,
      next_cursor: null,
      targets: ['HBOS Sample', 'HBOS Sample Task', 'HBOS Test Result', 'HBOS Result Revision', 'HBOS COA', 'HBOS Specification'],
    }
  }
  const response = await callFrappeMethod<PortalAuditResponse>('hbos_portal.api.audit.get_audit', {
    app_id: 'lims',
    ...params,
    limit: params.limit || 50,
  })
  const payload = unwrapPortalMethod(response)
  return payload.data || { events: [], total: 0, next_cursor: null, targets: [] }
}
