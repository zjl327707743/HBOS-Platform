import test from 'node:test'
import assert from 'node:assert/strict'
import { createSeed } from '../src/seed.js'
import { evaluatePermission } from '../src/permission.js'
import { summarizeWorkApp, planWorkChanges, applyWorkPlan, planRestoreDepartment, planSuspendApp, planReenableApp } from '../src/work-policy.js'

// Synthetic R5 UI mappings only; no real authorization, SQL, OAuth or Owner UAT.
const allow = scope => ({ mode: 'allow', scope })
const fixture = () => { const data = createSeed(); return { data, employee: data.employees.find(item => item.id === 'e1') } }
const evaluated = (data, employeeId, action, scopeId) => evaluatePermission(data, data.employees.find(item => item.id === employeeId), 'inventory', action, { scopeId }).allowed

test('UX-P01 打开后无改动不生成例外，部门来源不变化', () => {
  const { data, employee } = fixture()
  const snapshot = JSON.stringify(data)
  const plan = planWorkChanges(data, 'employee', employee.id, 'attendance', { read: { enabled: true, scope: ['self'] } })
  assert.equal(plan.ok, true)
  assert.equal(plan.changed, false)
  assert.equal(JSON.stringify(data), snapshot)
  assert.equal(plan.after.actionRows.find(row => row.id === 'read').sourceText, '按部门安排')
  assert.deepEqual(plan.patch, [])
})

test('UX-P02 仅查询A仓，B查询与出库实际拒绝，摘要包含限制', () => {
  const { data, employee } = fixture()
  employee.exceptions['inventory:*'] = allow(['warehouseA', 'warehouseB'])
  employee.exceptions['inventory:view'] = allow(['warehouseA', 'warehouseB'])
  const plan = planWorkChanges(data, 'employee', employee.id, 'inventory', { view: { enabled: true, scope: ['warehouseA'] } })
  assert.equal(plan.ok, true)
  assert.equal(evaluated(plan.nextData, employee.id, 'view', 'warehouseA'), true)
  assert.equal(evaluated(plan.nextData, employee.id, 'view', 'warehouseB'), false)
  assert.equal(evaluated(plan.nextData, employee.id, 'issue', 'warehouseA'), false)
  assert.match(plan.after.text, /不能查询 B 仓库/)
  assert.match(plan.after.text, /不能办理出库/)
})

test('UX-P03 缩小继承A+B到A后，不会被部门默认重新放开B', () => {
  const data = createSeed(), employee = data.employees.find(item => item.id === 'e2')
  const dept = data.depts.find(item => item.id === 'd2')
  dept.presets['inventory:*'] = allow(['warehouseA', 'warehouseB'])
  dept.presets['inventory:view'] = allow(['warehouseA', 'warehouseB'])
  const plan = planWorkChanges(data, 'employee', employee.id, 'inventory', { view: { enabled: true, scope: ['warehouseA'] } })
  assert.equal(plan.ok, true)
  assert.equal(evaluated(plan.nextData, employee.id, 'view', 'warehouseB'), false)
  assert.deepEqual(plan.nextData.employees.find(item => item.id === employee.id).exceptions['inventory:view'], allow(['warehouseA']))
})

test('UX-P04 只修改单项工作，未触碰的考勤查看及来源不被快照', () => {
  const { data, employee } = fixture()
  data.depts.find(item => item.id === 'd1').presets['attendance:export'] = allow(['self'])
  // Export is unavailable in the normal editor; a no-op leaves this legacy rule intact.
  const plan = planWorkChanges(data, 'employee', employee.id, 'attendance', {})
  assert.equal(plan.ok, true)
  assert.equal(plan.after.actionRows.find(row => row.id === 'read').sourceText, '按部门安排')
  assert.equal(Object.hasOwn(plan.nextData.employees.find(item => item.id === employee.id).exceptions, 'attendance:read'), false)
  const other = planWorkChanges(data, 'employee', employee.id, 'inventory', { issue: { enabled: true, scope: ['warehouseA'] } })
  assert.equal(other.ok, true)
  assert.deepEqual(other.nextData.depts, data.depts)
  assert.deepEqual(other.nextData.employees.find(item => item.id === employee.id).exceptions['inventory:view'], employee.exceptions['inventory:view'])
})

test('UX-P05 必要入口自动配合，但隐藏的出库或重要操作不会意外被解锁', () => {
  const { data, employee } = fixture()
  delete employee.exceptions['inventory:*']
  delete employee.exceptions['inventory:view']
  const created = planWorkChanges(data, 'employee', employee.id, 'inventory', { view: { enabled: true, scope: ['warehouseA'] } })
  assert.equal(created.ok, true)
  assert.equal(evaluated(created.nextData, employee.id, 'view', 'warehouseA'), true)
  employee.exceptions['inventory:*'] = allow(['warehouseA'])
  employee.exceptions['inventory:issue'] = allow(['warehouseB'])
  const blockedWrite = planWorkChanges(data, 'employee', employee.id, 'inventory', { view: { enabled: true, scope: ['warehouseB'] } })
  assert.equal(blockedWrite.ok, false)
  assert.match(blockedWrite.error, /办理出库/)
  delete employee.exceptions['inventory:issue']
  employee.exceptions['inventory:adjust'] = { ...allow(['warehouseB']), qualified: true }
  const blockedImportant = planWorkChanges(data, 'employee', employee.id, 'inventory', { view: { enabled: true, scope: ['warehouseB'] } })
  assert.equal(blockedImportant.ok, false)
  assert.match(blockedImportant.error, /重要库存调整/)
})

test('UX-P06 只停用一人一应用，保存全部既有工作且不动他人或其他应用', () => {
  const { data, employee } = fixture()
  const originalRules = structuredClone(employee.exceptions)
  const plan = planSuspendApp(data, employee.id, 'inventory')
  assert.equal(plan.ok, true)
  for (const action of ['view', 'issue', 'adjust']) for (const scope of ['warehouseA', 'warehouseB']) assert.equal(evaluated(plan.nextData, employee.id, action, scope), false)
  const nextEmployee = plan.nextData.employees.find(item => item.id === employee.id)
  assert.deepEqual(nextEmployee.exceptions['inventory:view'], originalRules['inventory:view'])
  assert.equal(nextEmployee.status, employee.status)
  assert.deepEqual(plan.nextData.employees.find(item => item.id === 'e2'), data.employees.find(item => item.id === 'e2'))
  assert.equal(evaluatePermission(plan.nextData, nextEmployee, 'attendance', 'read').allowed, true)
  assert.equal(plan.after.sourceText, '已单独停用')
})

test('UX-P07 恢复普通部门安排只删除当前普通设置，重要及其他应用规则保持', () => {
  const { data, employee } = fixture()
  employee.exceptions['lims:*'] = allow(['labA'])
  employee.exceptions['lims:view'] = allow(['labB'])
  employee.exceptions['lims:sign'] = { ...allow(['labA']), qualified: true }
  const important = structuredClone(employee.exceptions['lims:sign'])
  const inventory = structuredClone(employee.exceptions['inventory:view'])
  const plan = planRestoreDepartment(data, employee.id, 'lims')
  assert.equal(plan.ok, true)
  const nextEmployee = plan.nextData.employees.find(item => item.id === employee.id)
  assert.equal(Object.hasOwn(nextEmployee.exceptions, 'lims:view'), false)
  assert.deepEqual(nextEmployee.exceptions['lims:sign'], important)
  assert.deepEqual(nextEmployee.exceptions['inventory:view'], inventory)
  assert.equal(evaluatePermission(plan.nextData, nextEmployee, 'lims', 'sign').allowed, true)
})

test('UX-P09 两个入口共用相同summary/plan而非各自授权来源', () => {
  const { data, employee } = fixture()
  const employeePage = summarizeWorkApp(data, 'employee', employee.id, 'inventory')
  const appPage = summarizeWorkApp(data, 'employee', employee.id, 'inventory')
  assert.deepEqual(employeePage, appPage)
  const plan = planWorkChanges(data, 'employee', employee.id, 'inventory', { issue: { enabled: true, scope: ['warehouseA'] } })
  assert.deepEqual(summarizeWorkApp(applyWorkPlan(data, plan), 'employee', employee.id, 'inventory'), plan.after)
})

test('UX-P10 部门默认本人考勤，只能各看本人且影响数从状态计算', () => {
  const { data } = fixture()
  const dept = data.depts.find(item => item.id === 'd1')
  delete dept.presets['attendance:*']; delete dept.presets['attendance:read']
  const plan = planWorkChanges(data, 'department', dept.id, 'attendance', { read: { enabled: true, scope: ['self'] } })
  assert.equal(plan.ok, true)
  assert.equal(plan.impact.rows.length, data.employees.filter(item => item.departmentId === dept.id).length)
  for (const employee of plan.nextData.employees.filter(item => item.departmentId === dept.id && item.status === 'active')) {
    const own = { employeeId: employee.employeeId, identityConfirmed: true, eventDepartmentId: dept.id, departmentEvidenceConfirmed: true }
    const other = { ...own, employeeId: 'other-confirmed-employee' }
    assert.equal(evaluatePermission(plan.nextData, employee, 'attendance', 'read', own).allowed, true)
    assert.equal(evaluatePermission(plan.nextData, employee, 'attendance', 'read', other).allowed, false)
  }
})

test('UX-P11 调岗读取新部门普通安排，个人设置和本人历史Employee保持', () => {
  const { data, employee } = fixture()
  const before = structuredClone(employee)
  const summary = summarizeWorkApp(data, 'employee', { ...employee, departmentId: 'd2' }, 'inventory')
  assert.match(summary.text, /A 仓库/)
  assert.equal(summary.actionRows.find(row => row.id === 'view').sourceText, '已单独设置')
  assert.deepEqual(employee, before)
  assert.equal(data.attendanceRecords.find(row => row.id === 'DEMO-CI-103').employeeId, employee.employeeId)
})

test('UX-P12 未开户/冲突/停用显示自然暂不可用；没有记录不等于未关联', () => {
  const { data, employee } = fixture()
  for (const changes of [{ accountId: '' }, { status: 'disabled' }, { attendanceIdentity: { status: 'conflict' } }]) {
    const actor = { ...employee, ...changes }
    const summary = summarizeWorkApp(data, 'employee', actor, 'attendance')
    assert.equal(summary.status, 'unavailable')
    assert.equal(evaluatePermission(data, actor, 'attendance', 'read').allowed, false)
  }
  data.attendanceRecords = []
  assert.equal(summarizeWorkApp(data, 'employee', employee.id, 'attendance').status, 'available')
})

test('UX-P13 导出、部门考勤、重要操作及平台管理不可由普通勾选开启', () => {
  const { data, employee } = fixture()
  assert.equal(planWorkChanges(data, 'employee', employee.id, 'attendance', { export: { enabled: true, scope: ['self'] } }).ok, false)
  assert.equal(planWorkChanges(data, 'employee', employee.id, 'attendance', { read: { enabled: true, scope: ['d1'] } }).ok, false)
  assert.equal(planWorkChanges(data, 'employee', employee.id, 'inventory', { adjust: { enabled: true, scope: ['warehouseA'] } }).ok, false)
  assert.equal(planWorkChanges(data, 'department', 'd1', 'platform', { manage: { enabled: true, scope: ['platform'] } }).ok, false)
})

test('UX-P14 新应用由元数据出现，未知应用和未授权动作不默认可用', () => {
  const { data, employee } = fixture()
  data.apps.push({ id: 'demo-extra', name: '合成新应用', actions: [{ id: 'read', name: '查看项目', highRisk: false }], scopes: [{ value: 'group-a', label: '项目A' }] })
  const summary = summarizeWorkApp(data, 'employee', employee.id, 'demo-extra')
  assert.equal(summary.name, '合成新应用')
  assert.equal(summary.status, 'none')
  assert.equal(summary.actionRows.length, 1)
  assert.equal(planWorkChanges(data, 'employee', employee.id, 'unknown', {}).ok, false)
})

test('UX-P15 不同操作分别绑定对象，不产生查询/出库与仓库笛卡尔积', () => {
  const { data, employee } = fixture()
  const plan = planWorkChanges(data, 'employee', employee.id, 'inventory', { view: { enabled: true, scope: ['warehouseA', 'warehouseB'] }, issue: { enabled: true, scope: ['warehouseA'] } })
  assert.equal(plan.ok, true)
  assert.equal(evaluated(plan.nextData, employee.id, 'view', 'warehouseB'), true)
  assert.equal(evaluated(plan.nextData, employee.id, 'issue', 'warehouseA'), true)
  assert.equal(evaluated(plan.nextData, employee.id, 'issue', 'warehouseB'), false)
  assert.deepEqual(plan.after.actionRows.find(row => row.id === 'issue').scope, ['warehouseA'])
})

test('UX-P16 重新启用先预览重要恢复清单，不确认则拒绝，原规则不丢失', () => {
  const { data, employee } = fixture()
  employee.exceptions['lims:sign'] = { ...allow(['labA']), qualified: true }
  const suspended = planSuspendApp(data, employee.id, 'lims').nextData
  const blocked = planReenableApp(suspended, employee.id, 'lims')
  assert.equal(blocked.ok, false)
  assert.equal(blocked.requiresImportantReview, true)
  assert.match(blocked.warnings.join(''), /质量签署/)
  const confirmed = planReenableApp(suspended, employee.id, 'lims', { acknowledgeImportant: true })
  assert.equal(confirmed.ok, true)
  assert.deepEqual(confirmed.nextData.employees.find(item => item.id === employee.id).exceptions['lims:sign'], employee.exceptions['lims:sign'])
})

test('取消继承权限产生真实限制，不删除规则让部门自动放开', () => {
  const data = createSeed(), employee = data.employees.find(item => item.id === 'e2')
  const plan = planWorkChanges(data, 'employee', employee.id, 'inventory', { view: { enabled: false, scope: [] } })
  assert.equal(plan.ok, true)
  assert.equal(evaluated(plan.nextData, employee.id, 'view', 'warehouseA'), false)
  assert.equal(plan.nextData.employees.find(item => item.id === employee.id).exceptions['inventory:view'].mode, 'deny')
})

test('限定deny无法无损表达时只读，编辑其他工作不覆盖该限制', () => {
  const data = createSeed(), employee = data.employees.find(item => item.id === 'e2')
  const summary = summarizeWorkApp(data, 'employee', employee.id, 'inventory')
  assert.equal(summary.actionRows.find(row => row.id === 'issue').editable, false)
  assert.equal(planWorkChanges(data, 'employee', employee.id, 'inventory', { issue: { enabled: true, scope: ['warehouseA'] } }).ok, false)
  const plan = planWorkChanges(data, 'employee', employee.id, 'inventory', { view: { enabled: true, scope: ['warehouseA', 'warehouseB'] } })
  assert.equal(plan.ok, true)
  assert.deepEqual(plan.nextData.employees.find(item => item.id === employee.id).exceptions['inventory:issue'], employee.exceptions['inventory:issue'])
})

test('个人入口确实缩小部门动作时说明范围限制；仅配合其他工作不改未触碰来源', () => {
  const data = createSeed(), employee = data.employees.find(item => item.id === 'e2'), dept = data.depts.find(item => item.id === 'd2')
  dept.presets['inventory:*'] = allow(['warehouseA', 'warehouseB'])
  dept.presets['inventory:view'] = allow(['warehouseA', 'warehouseB'])
  employee.exceptions['inventory:*'] = allow(['warehouseA'])
  const summary = summarizeWorkApp(data, 'employee', employee.id, 'inventory')
  assert.equal(summary.actionRows.find(row => row.id === 'view').sourceText, '按部门安排，已限定使用范围')
  dept.presets['inventory:view'] = allow(['warehouseA'])
  assert.equal(summarizeWorkApp(data, 'employee', employee.id, 'inventory').actionRows.find(row => row.id === 'view').sourceText, '按部门安排')
})

test('未确认部门不能编辑或生成工作分配', () => {
  const { data } = fixture()
  data.depts.push({ id: 'not-confirmed', name: '待确认组织', confirmed: false, presets: {} })
  assert.equal(planWorkChanges(data, 'department', 'not-confirmed', 'inventory', { view: { enabled: true, scope: ['warehouseA'] } }).ok, false)
})

test('只有未开放的旧导出配置不能把整个应用标为可以使用', () => {
  const { data, employee } = fixture()
  delete data.depts.find(item => item.id === 'd1').presets['attendance:read']
  employee.exceptions['attendance:export'] = allow(['self'])
  const summary = summarizeWorkApp(data, 'employee', employee.id, 'attendance')
  assert.equal(summary.status, 'none')
  assert.equal(summary.actionRows.find(row => row.id === 'export').available, false)
})

test('部门影响摘要把保留的个人应用停用也列为单独设置保持', () => {
  const { data, employee } = fixture()
  employee.exceptions['attendance:*'] = { mode: 'deny', scope: [] }
  const plan = planWorkChanges(data, 'department', 'd1', 'attendance', { read: { enabled: false, scope: [] } })
  assert.equal(plan.ok, true)
  assert.equal(plan.impact.rows.find(row => row.id === employee.id).keptPersonal, true)
  assert.ok(plan.impact.personalUnchanged >= 1)
})

test('修改继承的出库一项，不把未触碰查询快照为个人来源', () => {
  const data = createSeed(), employee = data.employees.find(item => item.id === 'e2')
  delete employee.exceptions['inventory:issue']
  const plan = planWorkChanges(data, 'employee', employee.id, 'inventory', { issue: { enabled: false, scope: [] } })
  assert.equal(plan.ok, true)
  assert.equal(plan.after.actionRows.find(row => row.id === 'view').sourceText, '按部门安排')
  assert.equal(Object.hasOwn(plan.nextData.employees.find(item => item.id === employee.id).exceptions, 'inventory:view'), false)
})

test('仅继承部门停用时，个人重新启用拒绝而不产生虚假成功计划', () => {
  const { data, employee } = fixture()
  data.depts.find(item => item.id === 'd1').presets['attendance:*'] = { mode: 'deny', scope: [] }
  const plan = planReenableApp(data, employee.id, 'attendance')
  assert.equal(plan.ok, false)
  assert.equal(plan.changed, false)
  assert.match(plan.error, /部门安排仍停用/)
})

test('重要操作已有合成配置但未满足员工资格时，实际结果仍不可用', () => {
  const { data, employee } = fixture()
  employee.checked = false
  employee.exceptions['inventory:adjust'] = { ...allow(['warehouseA']), qualified: true }
  const row = summarizeWorkApp(data, 'employee', employee.id, 'inventory').importantRows.find(item => item.id === 'adjust')
  assert.equal(row.enabled, false)
  assert.equal(row.editable, false)
})

test('入口扩展不会意外激活原来被挡住的旧导出配置', () => {
  const { data, employee } = fixture()
  data.apps.find(app => app.id === 'inventory').actions.push({ id: 'export', name: '导出库存（旧候选）', highRisk: false, availability: 'candidate' })
  employee.exceptions['inventory:export'] = allow(['warehouseB'])
  const plan = planWorkChanges(data, 'employee', employee.id, 'inventory', { view: { enabled: true, scope: ['warehouseA', 'warehouseB'] } })
  assert.equal(plan.ok, false)
  assert.match(plan.error, /导出库存/)
})

test('待关联账号可读自然考勤状态，但不能伪装员工进行配置', () => {
  const { data } = fixture()
  data.nonEmployeeAccounts.push({ id: 'pending-user', name: '合成待处理账号', status: 'active', accountId: 'pending@example.invalid', employeeId: null, subjectType: 'pending-employee', relationStatus: 'pending', exceptions: {} })
  const summary = summarizeWorkApp(data, 'employee', 'pending-user', 'attendance')
  assert.equal(summary.status, 'unavailable')
  assert.match(summary.text, /待确认/)
  assert.equal(planWorkChanges(data, 'employee', 'pending-user', 'attendance', {}).ok, false)
})
