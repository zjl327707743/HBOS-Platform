import { describe, expect, it } from 'vitest'
import { auditOperationLabel, auditOperations } from '@/services/auditPresentation'

describe('R6 audit operation presentation', () => {
  it.each([
    ['work.save', '保存工作安排'],
    ['work.configure', '调整应用权限'],
    ['work.suspend', '暂停应用访问'],
    ['work.reenable', '恢复应用访问'],
    ['work.restore', '恢复部门安排'],
    ['app_role.save', '保存原生应用角色'],
  ])('labels and makes %s available as an audit filter', (operation, label) => {
    expect(auditOperations).toContainEqual({ value: operation, label })
    expect(auditOperationLabel(operation)).toBe(label)
  })
})
