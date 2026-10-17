import { iamQuery } from './iamAccess'
import type { AuditEvent, PageResult } from '@/types/iam'
export const listAuditEvents = (page = 1, page_size = 20) => iamQuery<PageResult<AuditEvent>>('hbos_portal.api.iam_audit.list_events', { page, page_size })
