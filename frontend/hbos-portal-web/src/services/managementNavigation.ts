import { canIam } from './iamAccess'

// One capability map for desktop and mobile; the router and server still enforce access.
export function managementLinks() {
  const primary = [
    { path: '/hbos/admin/people', label: '员工管理', cap: 'iam.people.read', icon: 'people' },
    { path: '/hbos/admin/departments', label: '部门应用权限', cap: 'iam.departments.read', icon: 'department' },
    { path: '/hbos/admin/roles', label: '角色与权限', cap: 'iam.roles.read', icon: 'roles' },
    { path: '/hbos/admin/audit', label: '变更记录', cap: 'iam.audit.read', icon: 'audit' },
  ].filter(row => canIam(row.cap))
  if (primary.length) return primary
  return canIam('iam.access.read')
    ? [{ path: '/hbos/admin/access', label: '原应用权限', cap: 'iam.access.read', icon: 'access' }]
    : []
}
