// Exact existing event names, used as labels only. Authorization stays on the server.
export const auditOperations = [
  { value: 'iam.people.create', label: '新建员工档案' },
  { value: 'iam.people.provision', label: '为已有员工开户' },
  { value: 'iam.people.link', label: '关联已有账号' },
  { value: 'iam.people.transfer', label: '调整主部门' },
  { value: 'iam.people.disable', label: '停用员工账号' },
  { value: 'iam.people.reset', label: '重置临时密码' },
  { value: 'role.assignment', label: '安排员工角色' },
  { value: 'role.department_default', label: '调整部门默认角色' },
  { value: 'role.draft', label: '保存或恢复角色草稿' },
  { value: 'role.publish', label: '发布角色功能' },
]
export const auditOperationLabel = (value: string) => auditOperations.find(row => row.value === value)?.label || value

export const auditResultLabel = (value: string) => ({success:'成功',refused:'被拒绝',conflict:'冲突'}[value] || value)
