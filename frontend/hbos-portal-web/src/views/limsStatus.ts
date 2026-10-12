const statusColors: Record<string, string> = {
  草稿: 'default', 已登记: 'blue', 检验中: 'processing', 检测中: 'processing',
  已提交: 'processing', 已复核: 'warning', 已批准: 'success', 已修订: 'error',
  检验完成: 'success', 已放行: 'success', OOS锁定: 'error', 'OOS 候选': 'error',
  已审核: 'warning', 已发布: 'success', 已生效: 'success', 已废止: 'default',
  在库: 'success', 在箱: 'success', 部分使用: 'processing', 待处理: 'warning',
  待QC批准: 'warning', 待QA审核: 'warning', 已用尽: 'default', 已销毁: 'default',
  已转出: 'default', 已执行: 'success', 已完成: 'success', 已驳回: 'error', 已取消: 'default',
}

export function statusColor(value?: string): string {
  if (!value) return 'default'
  if (statusColors[value]) return statusColors[value]
  if (value.includes('逾期') || value.includes('异常')) return 'error'
  if (value.includes('待') || value.includes('复核')) return 'warning'
  return 'default'
}

export function verdictColor(value?: string): string {
  return ({ 合格: 'success', 不合格: 'error', OOS候选: 'error', 'OOS 候选': 'error' } as Record<string, string>)[value || ''] || 'default'
}
