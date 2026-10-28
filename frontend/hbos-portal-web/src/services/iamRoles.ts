import { iamCommand, iamQuery, IamError } from './iamAccess'
export interface RoleFeature { operation_id: string; scope_binding: string }
export interface RoleScope { scope_type: 'DEPARTMENT'|'COMPANY'; scope_ref: string; include_descendants: 0 }
export interface AppRole { id: string; app_id: string; role_key: string; title: string; boundary_kind: string; draft_version: number; draft_features: RoleFeature[]; published_release: string; published_revision: number; published_features: RoleFeature[]; releases: Array<{name:string;revision:number;published_at:string}>; registry: Array<RoleFeature & {title:string;group:string;allowed:boolean;integrated:boolean;reason:string}> }
export interface AccessOutcome { allowed: boolean; reason: string; operations: Array<{operation_id:string;label?:string;scope_type:string;scope_ref:string;allowed:boolean}> }
export interface RoleAssignment { has_role_default?: boolean; version: number; mode?: string; role_key: string; responsibilities?: RoleScope[]; effective_access?: AccessOutcome; selected_role?: {source_mode:string;source_ref:string;reason:string;role_key:string;published_revision:number}; department?:string; company?:string }
export interface RolePreview { context_revision: string; changed: boolean; reference_count?: number; effective_changed_count?: number; personal_preserved?:number; members?:Array<{employee:string;name:string;employee_number?:string;changed:boolean;before_allowed:boolean;after_allowed:boolean;reason:string}>; before?:AccessOutcome; after?:AccessOutcome }
const prefix = 'hbos_portal.api.iam_roles.'
export const roleQuery = <T>(method: string, params: Record<string,unknown> = {}) => iamQuery<T>(prefix+method, {app_id:'attendance',...params})
export const roleCommand = <T>(method: string, params: Record<string,unknown>) => iamCommand<T>(prefix+method, {app_id:'attendance',...params})
export async function loadRoles() { const value = await roleQuery<{items:AppRole[]}>('list_roles'); if(!Array.isArray(value.items)||value.items.some(row=>!Array.isArray(row.registry)||!Array.isArray(row.draft_features))) throw new IamError('角色清单无法确认。'); return value.items }
export function assertRolePreview(value: RolePreview) { if(!value || !/^[a-f0-9]{64}$/.test(value.context_revision)||typeof value.changed!=='boolean') throw new IamError('变更预览无法确认。'); return value }
