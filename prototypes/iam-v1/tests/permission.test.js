import test from 'node:test'
import assert from 'node:assert/strict'
import { evaluatePermission } from '../src/permission.js'
import { createSeed } from '../src/seed.js'

// These tests verify synthetic interaction rules. They do not verify an API,
// Frappe authorization, identity proof, session revocation, or database isolation.
const allow = (scope, extra = {}) => ({ mode: 'allow', scope, ...extra })
const deny = () => ({ mode: 'deny', scope: [] })
const fixture = (id = 'e1') => {
  const data = createSeed()
  return { data, employee: data.employees.find(person => person.id === id) }
}

test('个人 APP 整体禁止覆盖具名且有资格的动作允许', () => {
  const { data, employee } = fixture()
  employee.exceptions['lims:*'] = deny()
  employee.exceptions['lims:view'] = allow(['labA'])
  employee.exceptions['lims:sign'] = allow(['labA'], { qualified: true })
  for (const action of ['*', 'view', 'sign']) {
    const result = evaluatePermission(data, employee, 'lims', action)
    assert.equal(result.allowed, false)
    assert.deepEqual(result.scope, [])
  }
})

test('继承的 APP 整体禁止也覆盖个人动作允许', () => {
  const { data, employee } = fixture()
  data.depts.find(department => department.id === 'd1').presets['lims:*'] = deny()
  employee.exceptions['lims:view'] = allow(['labA'])
  assert.equal(evaluatePermission(data, employee, 'lims', 'view').allowed, false)
})

test('个人动作明确禁止优先于部门动作允许', () => {
  const { data, employee } = fixture('e2')
  const result = evaluatePermission(data, employee, 'inventory', 'issue')
  assert.equal(result.allowed, false)
  assert.equal(result.mode, 'deny')
  delete employee.exceptions['inventory:issue']
  assert.equal(evaluatePermission(data, employee, 'inventory', 'issue').allowed, true)
})

test('APP 范围为空时有动作授权也不能进入或执行', () => {
  const { data, employee } = fixture()
  employee.exceptions['lims:*'] = allow([])
  employee.exceptions['lims:view'] = allow(['labA'])
  assert.equal(evaluatePermission(data, employee, 'lims', '*').allowed, false)
  assert.equal(evaluatePermission(data, employee, 'lims', 'view').allowed, false)
})

test('动作范围为空不解释为全部，也不回退到部门动作范围', () => {
  const { data, employee } = fixture()
  employee.exceptions['lims:view'] = allow([])
  const result = evaluatePermission(data, employee, 'lims', 'view')
  assert.equal(result.allowed, false)
  assert.deepEqual(result.scope, [])
})

test('有效动作范围只含动作、APP 与注册范围的交集', () => {
  const { data, employee } = fixture()
  employee.exceptions['lims:*'] = allow(['labA', 'unregistered'])
  employee.exceptions['lims:view'] = allow(['labA', 'labB', 'unregistered'])
  const result = evaluatePermission(data, employee, 'lims', 'view')
  assert.equal(result.allowed, true)
  assert.deepEqual(result.scope, ['labA'])
})

test('动作与 APP 范围没有交集时拒绝', () => {
  const { data, employee } = fixture()
  employee.exceptions['lims:view'] = allow(['labB'])
  const result = evaluatePermission(data, employee, 'lims', 'view')
  assert.equal(result.allowed, false)
  assert.deepEqual(result.scope, [])
})

test('调岗撤销旧普通继承、启用新继承，兼岗不自动叠加', () => {
  const { data, employee } = fixture()
  delete employee.exceptions['inventory:*']
  delete employee.exceptions['inventory:view']
  assert.equal(evaluatePermission(data, employee, 'lims', 'view').allowed, true)
  assert.equal(evaluatePermission(data, employee, 'inventory', 'view').allowed, false)
  employee.departmentId = 'd2'
  assert.equal(evaluatePermission(data, employee, 'lims', 'view').allowed, false)
  assert.equal(evaluatePermission(data, employee, 'inventory', 'view').allowed, true)
})

test('调入部门即使存在高风险预设也不会自动得到高风险动作', () => {
  const { data, employee } = fixture()
  const target = data.depts.find(department => department.id === 'd2')
  target.presets['inventory:adjust'] = allow(['warehouseA'], { qualified: true })
  employee.departmentId = 'd2'
  assert.equal(evaluatePermission(data, employee, 'inventory', 'view').allowed, true)
  assert.equal(evaluatePermission(data, employee, 'inventory', 'adjust').allowed, false)
})

test('个人高风险允许仍需合成资格标记且不能越出 APP 范围', () => {
  const { data, employee } = fixture()
  employee.exceptions['lims:sign'] = allow(['labA'])
  assert.equal(evaluatePermission(data, employee, 'lims', 'sign').allowed, false)
  employee.exceptions['lims:sign'].qualified = true
  assert.equal(evaluatePermission(data, employee, 'lims', 'sign').allowed, true)
  employee.exceptions['lims:sign'].scope = ['labB']
  assert.equal(evaluatePermission(data, employee, 'lims', 'sign').allowed, false)
})

test('平台管理员即使有平台管理资格也不自动得到 LIMS 签署', () => {
  const { data, employee } = fixture('admin')
  employee.exceptions['platform:*'] = allow(['platform'])
  employee.exceptions['platform:manage'] = allow(['platform'], { qualified: true })
  assert.equal(evaluatePermission(data, employee, 'platform', 'manage').allowed, true)
  assert.equal(evaluatePermission(data, employee, 'lims', 'view').allowed, true)
  assert.equal(evaluatePermission(data, employee, 'lims', 'sign').allowed, false)
})

test('停用或待开通人员即使留有规则也全部拒绝', () => {
  const { data, employee } = fixture()
  for (const status of ['disabled', 'pending']) {
    employee.status = status
    assert.equal(evaluatePermission(data, employee, 'lims', 'view').allowed, false)
    assert.equal(evaluatePermission(data, employee, 'inventory', 'view').allowed, false)
  }
})

test('模块及动作未注册时不会因同名规则得到权限', () => {
  const { data, employee } = fixture()
  employee.exceptions['unknown:*'] = allow(['labA'])
  employee.exceptions['unknown:view'] = allow(['labA'])
  employee.exceptions['lims:unknown'] = allow(['labA'])
  assert.equal(evaluatePermission(data, employee, 'unknown', 'view').allowed, false)
  assert.equal(evaluatePermission(data, employee, 'lims', 'unknown').allowed, false)
})
