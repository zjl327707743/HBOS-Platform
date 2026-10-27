import { iamQuery, IamError } from './iamAccess'
import type { AuditEvent, PageResult } from '@/types/iam'
export interface AuditSubjectFilter { subject_type?: string; subject_name?: string }
export function listAuditEvents(page = 1, page_size = 20, filter: AuditSubjectFilter = {}) {
  const subject_type = filter.subject_type?.trim(), subject_name = filter.subject_name?.trim()
  if (Boolean(subject_type) !== Boolean(subject_name)) return Promise.reject(new IamError('请同时选择对象类型并填写准确标识。'))
  return iamQuery<PageResult<AuditEvent>>('hbos_portal.api.iam_audit.list_events', { page, page_size, ...(subject_type && subject_name ? { subject_type, subject_name } : {}) })
}
