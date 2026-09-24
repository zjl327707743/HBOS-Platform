import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildTodoQuery,
  buildTodoRoute,
  emptySummary,
  normalizeTodoItem,
  readScalarQuery,
  retainPreviousOnError,
  sortTodoItems,
} from '../src/features/todos/todoModel.ts'

const baseItem = {
  todo_key: 'HBOS Sample Task:TASK-1:start_task',
  module: 'testing' as const,
  module_label: '检验业务',
  source_doctype: 'HBOS Sample Task',
  source_name: 'TASK-1',
  title: '开始检验',
  action: 'start_task',
  action_label: '开始检验',
  status: '已分配',
  status_label: '已分配',
  execute_mode: 'direct' as const,
  owner_type: 'user' as const,
  owner_label: '指派给我',
  assignee: 'alice@example.com',
  candidate_roles: [],
  priority: '常规',
  due_at: null,
  is_overdue: false,
  route: '/tasks',
  route_params: {},
  modified_at: '2026-09-22T10:00:00+08:00',
}

test('normalizes assigned and role labels', () => {
  const item = normalizeTodoItem({ ...baseItem, owner_type: 'role', owner_label: '' })

  assert.equal(item.owner_label, '角色待处理')
  assert.equal(item.module_label, '检验业务')
})

test('keeps previous summary when refresh fails', () => {
  const previous = { ...emptySummary(), total: 4 }

  assert.deepEqual(retainPreviousOnError(previous, { ...emptySummary(), total: 0 }, true), previous)
  assert.equal(retainPreviousOnError(previous, { ...emptySummary(), total: 2 }, false).total, 2)
})

test('builds query without user identity', () => {
  const query = buildTodoQuery({ overdue: true, keyword: '水分', limit: 20, offset: 5 })

  assert.equal(query.overdue, true)
  assert.equal(query.keyword, '水分')
  assert.equal(query.limit, 20)
  assert.equal(query.offset, 5)
  assert.equal('user' in query, false)
  assert.equal('roles' in query, false)
  assert.equal('overdue_only' in query, false)
})

test('reads a scalar route query safely', () => {
  assert.equal(readScalarQuery('TASK-1'), 'TASK-1')
  assert.equal(readScalarQuery(['TASK-1', 'TASK-2']), 'TASK-1')
  assert.equal(readScalarQuery(undefined), undefined)
  assert.equal(readScalarQuery(42), undefined)
})

test('sorts overdue items before ordinary items', () => {
  const ordinary = { ...baseItem, todo_key: 'ordinary', due_at: '2026-09-20', is_overdue: false }
  const overdue = { ...baseItem, todo_key: 'overdue', due_at: '2026-09-21', is_overdue: true }

  assert.deepEqual(sortTodoItems([ordinary, overdue]).map((item) => item.todo_key), ['overdue', 'ordinary'])
})

test('builds the six supported todo deep links', () => {
  assert.deepEqual(buildTodoRoute('/tasks', { scope: 'mine', task: 'TASK-1' }), {
    path: '/tasks',
    query: { scope: 'mine', task: 'TASK-1' },
  })
  assert.deepEqual(buildTodoRoute('/stability/schedule', { timepoint: 'TP-1' }), {
    path: '/stability/schedule',
    query: { timepoint: 'TP-1' },
  })
  assert.deepEqual(buildTodoRoute('/stability/results', { timepoint: 'TP-1', result: 'RES-1' }), {
    path: '/stability/results',
    query: { timepoint: 'TP-1', result: 'RES-1' },
  })
  assert.deepEqual(buildTodoRoute('/retention/observations', { sample: 'RET-1', observation: 'OBS-1' }), {
    path: '/retention/observations',
    query: { sample: 'RET-1', observation: 'OBS-1' },
  })
  assert.deepEqual(buildTodoRoute('/retention/usage', { usage: 'USE-1' }), {
    path: '/retention/usage',
    query: { usage: 'USE-1' },
  })
  assert.deepEqual(buildTodoRoute('/retention/disposal', { disposal: 'DSP-1', focus: 'DSP-1' }), {
    path: '/retention/disposal',
    query: { disposal: 'DSP-1', focus: 'DSP-1' },
  })
})
