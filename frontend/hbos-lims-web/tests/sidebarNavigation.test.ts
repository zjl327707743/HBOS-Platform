import assert from 'node:assert/strict'
import {
  defaultRecentNavItems,
  getGroupForPath,
  getInitialExpandedGroup,
  getVisibleRecentNavItems,
  isSidebarItemActive,
  sidebarGroups,
} from '../src/components/layout/sidebarNavigation.ts'

assert.equal(getGroupForPath('/stability/results'), 'stability')
assert.equal(getGroupForPath('/retention/usage'), 'retention')
assert.equal(getInitialExpandedGroup('/stability/results'), 'stability')
assert.equal(getInitialExpandedGroup('/dashboard'), null)
assert.equal(sidebarGroups.find((group) => group.key === 'stability')?.children.length, 7)
assert.equal(isSidebarItemActive('/stability/schedule', '/stability'), false)
assert.equal(isSidebarItemActive('/stability', '/stability'), true)
assert.deepEqual(
  getVisibleRecentNavItems(defaultRecentNavItems, ['tasks']).map((item) => item.key),
  ['stability-study'],
)

console.log('sidebar navigation model tests passed')
