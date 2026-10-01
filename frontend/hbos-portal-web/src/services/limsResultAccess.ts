import type { PortalDataSource } from '@/contracts/portal'

export function resultAccess(source: PortalDataSource, capabilities: string[], status?: string, verdict?: string, oosLocked = false) {
  const real = source === 'frappe'
  const oos = oosLocked || ['OOS候选', '不合格'].includes(verdict?.replace(/\s/g, '') || '')
  const submit = real && capabilities.includes('lims.results.submit') && status === '草稿'
  const review = real && capabilities.includes('lims.results.review') && status === '已提交'
  const approve = real && !oos && capabilities.includes('lims.results.approve') && status === '已复核'
  const readonlyReason = !real ? '演示模式只读'
    : oos ? 'OOS 候选：批准已锁定'
    : ['已批准', '已修订'].includes(status || '') ? '记录状态只读'
    : '当前权限或记录状态只读'
  return { submit, review, approve, edit: submit, readonlyReason }
}
