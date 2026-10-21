import { iamCommand, iamQuery } from './iamAccess'

export interface AppRoleOption {
  role: string
  title: string
  native_scope: string
  risk: string
  summary: string
  permissions_note: string
}
export interface AppRoleApp {
  app_id: string
  title: string
  scope_note: string
  roles: AppRoleOption[]
  blocked: Array<{ role: string; reason: string }>
  current: string[]
}
export interface AppRoleState {
  employee: string
  user: string
  company: string
  department: string
  version: string
  native_roles: string[]
  apps: AppRoleApp[]
  is_grantor: boolean
  can_grant: boolean
  grant_requirement: string
}
export interface AppRolePreview {
  employee: string
  user: string
  app_id: string
  current: string[]
  target: string[]
  add: string[]
  remove: string[]
  unchanged: string[]
  other_roles_preserved: string[]
  changed: boolean
  version: string
  context_revision: string
  scope_note: string
}
const prefix = 'hbos_portal.api.iam_app_roles.'
export const describeAppRoles = (employee_id: string) => iamQuery<AppRoleState>(prefix + 'describe', { employee_id })
export const previewAppRoles = (employee_id: string, app_id: string, roles: string[], expected_version: string, acknowledged_global_scope: boolean) =>
  iamCommand<AppRolePreview>(prefix + 'preview', { employee_id, app_id, roles, expected_version, acknowledged_global_scope })
export const saveAppRoles = (employee_id: string, app_id: string, roles: string[], expected_version: string, context_revision: string, request_id: string, acknowledged_global_scope: boolean) =>
  iamCommand<AppRolePreview>(prefix + 'save', { employee_id, app_id, roles, expected_version, context_revision, request_id, acknowledged_global_scope })
