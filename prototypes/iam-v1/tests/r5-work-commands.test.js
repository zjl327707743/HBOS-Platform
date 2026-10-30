import test, { beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import { createSeed } from '../src/seed.js'

const memory = new Map()
globalThis.localStorage = { getItem: key => memory.get(key) ?? null, setItem: (key, value) => memory.set(key, value), removeItem: key => memory.delete(key) }
const { state, ui } = await import('../src/model.js')
const { saveWorkChanges, suspendWorkApp, restoreDepartmentWork } = await import('../src/workAccess.js')
beforeEach(() => {
  Object.assign(state, createSeed())
  state.session = { employeeId: 'admin', phase: 'active', method: 'password' }
  ui.fault = 'none'; ui.busy = false; ui.error = ''; ui.notice = ''
  memory.clear()
})

test('UX-P01 无改动统一命令不写存储、不增加版本和成功日志', async () => {
  const revision = state.revision, logs = JSON.parse(JSON.stringify(state.logs))
  const result = await saveWorkChanges('employee', 'e1', 'attendance', { read: { enabled: true, scope: ['self'] } }, revision)
  assert.equal(result.ok, true)
  assert.equal(result.changed, false)
  assert.equal(state.revision, revision)
  assert.deepEqual(state.logs, logs)
  assert.equal(memory.size, 0)
  assert.equal(Object.hasOwn(state.employees.find(item => item.id === 'e1').exceptions, 'attendance:read'), false)
})

test('UX-P08 保存失败及冲突保留调用者草稿、已保存规则/版本/日志完全不变', async () => {
  for (const fault of ['save-failure', 'conflict']) {
    ui.fault = fault
    const draft = { issue: { enabled: true, scope: ['warehouseA'] } }
    const before = JSON.stringify(state), beforeDraft = JSON.stringify(draft)
    const result = await saveWorkChanges('employee', 'e1', 'inventory', draft, state.revision)
    assert.equal(result.ok, false)
    assert.equal(JSON.stringify(state), before)
    assert.equal(JSON.stringify(draft), beforeDraft)
    assert.equal(memory.size, 0)
  }
})

test('UX-P08 旧版本提交拒绝且不会产生成功日志；仅预览/取消不写状态', async () => {
  const before = JSON.stringify(state)
  const result = await saveWorkChanges('employee', 'e1', 'inventory', { issue: { enabled: true, scope: ['warehouseA'] } }, state.revision - 1)
  assert.equal(result.ok, false)
  assert.equal(JSON.stringify(state), before)
  assert.equal(memory.size, 0)
})

test('统一保存仅改目标规则，不覆盖会话/他人，记录合成目标和应用', async () => {
  const session = JSON.stringify(state.session), other = JSON.stringify(state.employees.find(item => item.id === 'e2'))
  const result = await saveWorkChanges('employee', 'e1', 'inventory', { issue: { enabled: true, scope: ['warehouseA'] } }, state.revision)
  assert.equal(result.ok, true)
  assert.equal(JSON.stringify(state.session), session)
  assert.equal(JSON.stringify(state.employees.find(item => item.id === 'e2')), other)
  assert.match(state.logs[0].label, /林舟.*库存管理/)
  assert.equal(state.logs[0].employeeId, 'e1')
  assert.equal(state.logs[0].appId, 'inventory')
})

test('UX-P06 真实统一命令停用后原动作保存；恢复只处理同一应用', async () => {
  const before = JSON.stringify(state.employees.find(item => item.id === 'e1').exceptions['inventory:view'])
  const stopped = await suspendWorkApp('e1', 'inventory', state.revision)
  assert.equal(stopped.ok, true)
  assert.equal(JSON.stringify(state.employees.find(item => item.id === 'e1').exceptions['inventory:view']), before)
  const restored = await restoreDepartmentWork('e1', 'inventory', state.revision)
  assert.equal(restored.ok, true)
  assert.equal(state.employees.find(item => item.id === 'e1').status, 'active')
  assert.equal(state.session.employeeId, 'admin')
})

test('本人主体与管理员目标分开；非管理员不能提交普通工作安排', async () => {
  state.session = { employeeId: 'e1', phase: 'active', method: 'password' }
  const before = JSON.stringify(state)
  const result = await saveWorkChanges('employee', 'e2', 'inventory', { view: { enabled: false, scope: [] } }, state.revision)
  assert.equal(result.ok, false)
  assert.equal(JSON.stringify(state), before)
})
