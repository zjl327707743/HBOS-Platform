const ROLE_LABELS: ReadonlyArray<readonly [string, string]> = [
  ['System Manager', '系统管理员'],
  ['LIMS QP', '质量受权人'],
  ['LIMS QA Manager', 'QA 经理'],
  ['LIMS QA', 'QA'],
  ['LIMS Manager', 'LIMS 经理'],
  ['LIMS Reviewer', 'LIMS 复核人'],
  ['LIMS Analyst', 'LIMS 检验员'],
]

export function getRoleLabel(roles: readonly string[], isAuthenticated: boolean): string {
  if (!isAuthenticated) return '未登录'

  for (const [role, label] of ROLE_LABELS) {
    if (roles.includes(role)) return label
  }

  return '已登录'
}
