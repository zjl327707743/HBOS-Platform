import { iamQuery, IamError } from './iamAccess'
import type { AuditEvent, AuditEventDetail, PageResult } from '@/types/iam'
export interface AuditSubjectFilter { subject_type?: string; subject_name?: string; date_from?: string; date_to?: string; operation?: string; result?: string }
export function listAuditEvents(page = 1, page_size = 20, filter: AuditSubjectFilter = {}) {
  const subject_type = filter.subject_type?.trim(), subject_name = filter.subject_name?.trim()
  if (Boolean(subject_type) !== Boolean(subject_name)) return Promise.reject(new IamError('请同时选择对象类型并填写准确标识。'))
  const extra = Object.fromEntries((['date_from', 'date_to', 'operation', 'result'] as const).filter(key => filter[key]).map(key => [key, filter[key]]))
  return iamQuery<PageResult<AuditEvent>>('hbos_portal.api.iam_audit.list_events', { page, page_size, ...extra, ...(subject_type && subject_name ? { subject_type, subject_name } : {}) })
}
export async function getAuditEvent(name: string) {
  const result = await iamQuery<AuditEventDetail>('hbos_portal.api.iam_audit.get_event', { name })
  if (result.name !== name || !('before' in result) || !('after' in result)) throw new IamError('记录详情无法确认，请重新读取。')
  return result
}
