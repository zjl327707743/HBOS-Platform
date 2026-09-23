import assert from 'node:assert/strict'
import {
  getGroupForPath,
  getInitialExpandedGroup,
  isSidebarItemActive,
  myTodoNavItem,
  sidebarGroups,
} from '../src/components/layout/sidebarNavigation.ts'

assert.equal(getGroupForPath('/stability/results'), 'stability')
assert.equal(getGroupForPath('/retention/usage'), 'retention')
assert.equal(getInitialExpandedGroup('/stability/results'), 'stability')
assert.equal(getInitialExpandedGroup('/dashboard'), null)
assert.equal(sidebarGroups.find((group) => group.key === 'stability')?.children.length, 7)
assert.equal(isSidebarItemActive('/stability/schedule', '/stability'), false)
assert.equal(isSidebarItemActive('/stability', '/stability'), true)
assert.equal(myTodoNavItem.path, '/my-todos')
assert.equal(myTodoNavItem.badge, 'todo-total')
assert.equal(sidebarGroups.find((group) => group.key === 'stability')?.badge, undefined)
assert.equal(sidebarGroups.find((group) => group.key === 'stability')?.children.find((item) => item.key === 'stability-schedule')?.badge, 'schedule')
assert.equal(sidebarGroups.find((group) => group.key === 'stability')?.children.find((item) => item.key === 'stability-results')?.badge, 'results')

console.log('sidebar navigation model tests passed')
