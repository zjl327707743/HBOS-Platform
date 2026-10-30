import test from 'node:test'
import assert from 'node:assert/strict'
import { createSeed } from '../src/seed.js'
import { evaluatePermission, previewAttendance } from '../src/permission.js'

// R4 A-stage synthetic contract checks only. These do not approve the design,
// authorize stage B, or prove any real Frappe/API/database/OAuth behavior.
const allow = scope => ({ mode: 'allow', scope })
const deny = scope => ({ mode: 'deny', scope })
function fixture(id = 'e1') {
  const data = createSeed()
  const actor = [...data.employees, ...data.nonEmployeeAccounts].find(subject => subject.id === id)
  return { data, actor }
}
const ids = response => response.rows.map(row => row.id).sort()
function assertNoData(response) {
  assert.equal(response.ok, false)
  assert.deepEqual(response.rows, [])
  assert.equal(response.total, 0)
}

test('Employee 档案与服务账号分类，未开户档案保留、工号保留前导零', () => {
  const { data } = fixture()
  assert.equal(data.employees.length, 5)
  assert.ok(data.employees.every(employee => employee.employeeId && employee.subjectType === 'employee'))
  assert.equal(data.employees.find(employee => employee.id === 'e3').accountId, '')
  assert.equal(data.employees.find(employee => employee.id === 'e1').employeeNumber, '00101')
  assert.equal(typeof data.employees.find(employee => employee.id === 'e1').employeeNumber, 'string')
  assert.equal(data.nonEmployeeAccounts.length, 1)
  assert.equal(data.nonEmployeeAccounts[0].subjectType, 'service')
  assert.equal(data.nonEmployeeAccounts[0].employeeId, null)
})

test('SELF 返回同一已确认 Employee 的当前与历史投影，不含他人字段及总数', () => {
  const { data, actor } = fixture()
  for (const record of data.attendanceRecords) record.privateSourcePayload = 'must-not-project'
  const response = previewAttendance(data, actor, { endpoint: 'self', operation: 'read' })
  assert.equal(response.ok, true)
  assert.deepEqual(ids(response), ['DEMO-CI-101', 'DEMO-CI-103'])
  assert.equal(response.total, 2)
  assert.ok(response.rows.every(row => row.employeeId === actor.employeeId))
  assert.ok(response.rows.every(row => !('privateSourcePayload' in row) && !('owner' in row)))
  assert.equal(response.operationId, 'attendance.read')
})

test('本人历史依据 Employee 外键，调岗不按当前 department 改写历史归属', () => {
  const { data, actor } = fixture()
  const before = previewAttendance(data, actor, { endpoint: 'self', operation: 'read' })
  actor.departmentId = 'd2'
  const after = previewAttendance(data, actor, { endpoint: 'self', operation: 'read' })
  assert.deepEqual(ids(after), ids(before))
  assert.equal(after.rows.find(row => row.id === 'DEMO-CI-103').eventDepartmentId, 'd2')
  assert.equal(after.rows.find(row => row.id === 'DEMO-CI-101').eventDepartmentId, 'd1')
})

test('SELF 与部门范围按记录求交，不能因 self 与 d1 字符串不同就全部拒绝', () => {
  const { data, actor } = fixture()
  actor.exceptions['attendance:*'] = allow(['d1'])
  actor.exceptions['attendance:read'] = allow(['self'])
  const response = previewAttendance(data, actor, { endpoint: 'self', operation: 'read' })
  assert.equal(response.ok, true)
  assert.deepEqual(ids(response), ['DEMO-CI-101'])
  const colleague = data.attendanceRecords.find(record => record.id === 'DEMO-CI-105')
  assert.equal(evaluatePermission(data, actor, 'attendance', 'read', colleague).allowed, false)
})

test('逆向 APP SELF 与部门动作求交也只允许本人的部门记录', () => {
  const { data, actor } = fixture()
  actor.exceptions['attendance:*'] = allow(['self'])
  actor.exceptions['attendance:read'] = allow(['d1'])
  const response = previewAttendance(data, actor, { endpoint: 'department', requestedDepartmentId: 'd1', operation: 'read' })
  assert.equal(response.ok, true)
  assert.deepEqual(ids(response), ['DEMO-CI-101'])
  assert.equal(response.total, 1)
})

test('限定部门 deny 只扣除匹配部门，不把 SELF 的其他部门历史全部拒绝', () => {
  const { data, actor } = fixture()
  actor.exceptions['attendance:*'] = allow(['self', 'd1', 'd2'])
  actor.exceptions['attendance:read'] = deny(['d1'])
  const response = previewAttendance(data, actor, { endpoint: 'self', operation: 'read' })
  assert.equal(response.ok, true)
  assert.deepEqual(ids(response), ['DEMO-CI-103'])
  assert.equal(response.total, 1)
  assert.equal(evaluatePermission(data, actor, 'attendance', 'read', data.attendanceRecords.find(record => record.id === 'DEMO-CI-101')).allowed, false)
})

test('限定 SELF deny 从部门授权扣除本人，其他已确认部门员工仍可读', () => {
  const { data, actor } = fixture()
  data.depts.find(dept => dept.id === 'd1').presets['attendance:read'] = allow(['d1'])
  actor.exceptions['attendance:*'] = allow(['d1'])
  actor.exceptions['attendance:read'] = deny(['self'])
  const response = previewAttendance(data, actor, { endpoint: 'department', requestedDepartmentId: 'd1', operation: 'read' })
  assert.equal(response.ok, true)
  assert.deepEqual(ids(response), ['DEMO-CI-105'])
  assert.ok(response.rows.every(row => row.employeeId !== actor.employeeId))
})

test('APP 整体 deny 拒绝全部动作及对象，与限定动作 deny 区分', () => {
  const { data, actor } = fixture()
  actor.exceptions['attendance:*'] = deny(['d1'])
  actor.exceptions['attendance:read'] = allow(['self', 'd1', 'd2'])
  for (const record of data.attendanceRecords) assert.equal(evaluatePermission(data, actor, 'attendance', 'read', record).allowed, false)
  assertNoData(previewAttendance(data, actor, { endpoint: 'self', operation: 'read' }))
})

test('本人接口注入他人 employee 参数不会替换 actor，也不返回他人数量', () => {
  const { data, actor } = fixture()
  const initial = actor.employeeId
  assertNoData(previewAttendance(data, actor, { endpoint: 'self', operation: 'read', requestedEmployeeId: 'DEMO-EMP-00102' }))
  assert.equal(actor.employeeId, initial)
  const response = previewAttendance(data, actor, {
    endpoint: 'self', operation: 'read', user: 'demo.e2@example.invalid', department: 'd2',
    requestedDepartmentId: 'd2', filter: { employeeId: 'DEMO-EMP-00102' },
  })
  assert.deepEqual(ids(response), ['DEMO-CI-101', 'DEMO-CI-103'])
  assert.equal(response.total, 2)
})

test('未知 endpoint 默认拒绝，不静默降级为一个允许的本人请求', () => {
  const { data, actor } = fixture()
  for (const endpoint of ['all', 'unknown', '/api/resource/Employee']) {
    assertNoData(previewAttendance(data, actor, { endpoint, operation: 'read' }))
  }
})

test('部门请求只按已确认的事件时部门，不把当前 Employee.department 当历史证据', () => {
  const { data, actor } = fixture()
  actor.exceptions['attendance:*'] = allow(['d2'])
  actor.exceptions['attendance:read'] = allow(['d2'])
  const response = previewAttendance(data, actor, { endpoint: 'department', requestedDepartmentId: 'd2', operation: 'read' })
  assert.equal(response.ok, true)
  assert.deepEqual(ids(response), ['DEMO-CI-102', 'DEMO-CI-103'])
  assert.ok(!response.rows.some(row => row.id === 'DEMO-CI-104'))
  assert.ok(!response.rows.some(row => row.id === 'DEMO-CI-101'))
})

test('本人 Employee 归属已确认时，历史部门未知不妨碍本人读取', () => {
  const { data, actor } = fixture('e2')
  const response = previewAttendance(data, actor, { endpoint: 'self', operation: 'read' })
  assert.equal(response.ok, true)
  assert.deepEqual(ids(response), ['DEMO-CI-102', 'DEMO-CI-104'])
  assert.equal(response.rows.find(row => row.id === 'DEMO-CI-104').departmentEvidenceConfirmed, false)
})

test('read 与 export 范围成对保存，不交叉组合成两个部门都可导出', () => {
  const { data, actor } = fixture()
  actor.exceptions['attendance:*'] = allow(['d1', 'd2'])
  actor.exceptions['attendance:read'] = allow(['d1'])
  actor.exceptions['attendance:export'] = allow(['d2'])
  assert.deepEqual(ids(previewAttendance(data, actor, { endpoint: 'department', requestedDepartmentId: 'd1', operation: 'read' })), ['DEMO-CI-101', 'DEMO-CI-105'])
  assertNoData(previewAttendance(data, actor, { endpoint: 'department', requestedDepartmentId: 'd1', operation: 'export' }))
  const exported = previewAttendance(data, actor, { endpoint: 'department', requestedDepartmentId: 'd2', operation: 'export' })
  assert.equal(exported.operationId, 'attendance.export')
  assert.deepEqual(ids(exported), ['DEMO-CI-102', 'DEMO-CI-103'])
  assertNoData(previewAttendance(data, actor, { endpoint: 'department', requestedDepartmentId: 'd2', operation: 'read' }))
})

test('无 Employee 的服务 / 待关联账号，即使配置显式规则也不得读取考勤', () => {
  const { data, actor } = fixture('admin')
  actor.exceptions['attendance:*'] = allow(['self', 'd1', 'd2'])
  actor.exceptions['attendance:read'] = allow(['self', 'd1', 'd2'])
  for (const type of ['service', 'pending-employee']) {
    actor.subjectType = type
    actor.relationStatus = type === 'service' ? 'not-applicable' : 'pending'
    assertNoData(previewAttendance(data, actor, { endpoint: 'department', requestedDepartmentId: 'd1', operation: 'read' }))
  }
})

test('未确认、冲突关系及停用账号默认拒绝；记录本身无可靠 Employee 也拒绝', () => {
  const { data, actor } = fixture()
  for (const status of ['unlinked', 'pending', 'conflict']) {
    actor.relationStatus = status
    assertNoData(previewAttendance(data, actor, { endpoint: 'self', operation: 'read' }))
  }
  actor.relationStatus = 'confirmed'
  const record = data.attendanceRecords.find(item => item.id === 'DEMO-CI-101')
  record.identityConfirmed = false
  assert.equal(evaluatePermission(data, actor, 'attendance', 'read', record).allowed, false)
  actor.status = 'disabled'
  assertNoData(previewAttendance(data, actor, { endpoint: 'self', operation: 'read' }))
})

test('考勤来源身份标为 conflict 时不继续开放 SELF 数据', () => {
  const { data, actor } = fixture()
  actor.attendanceIdentity.status = 'conflict'
  assertNoData(previewAttendance(data, actor, { endpoint: 'self', operation: 'read' }))
})

test('已注册部门 ID 不依赖 d 前缀；SELF 仍按该部门记录求交', () => {
  const { data, actor } = fixture()
  const department = data.depts.find(dept => dept.id === 'd1')
  department.id = 'quality-team'
  actor.departmentId = 'quality-team'
  data.apps.find(app => app.id === 'attendance').scopes.find(scope => scope.value === 'd1').value = 'quality-team'
  for (const record of data.attendanceRecords) if (record.eventDepartmentId === 'd1') record.eventDepartmentId = 'quality-team'
  actor.exceptions['attendance:*'] = allow(['quality-team'])
  actor.exceptions['attendance:read'] = allow(['self'])
  const response = previewAttendance(data, actor, { endpoint: 'self', operation: 'read' })
  assert.equal(response.ok, true)
  assert.deepEqual(ids(response), ['DEMO-CI-101'])
})
