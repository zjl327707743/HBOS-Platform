import { reactive } from 'vue'
import { callFrappeMethod, callFrappePostMethod } from './frappeClient'

export class IamError extends Error { constructor(message: string, public code = 'INVALID_RESPONSE') { super(message); this.name = 'IamError' } }
interface Envelope<T> { ok: boolean; data?: T; error?: { code?: string; message?: string } }
export function unwrapIam<T>(raw: unknown): T {
  if (!raw || typeof raw !== 'object' || !('ok' in raw)) throw new IamError('服务器返回的管理数据无法确认，请重试。')
  const value = raw as Envelope<T>
  if (value.ok !== true) throw new IamError(value.error?.message || '操作未完成，请核对权限和资料后重试。', value.error?.code || 'SERVICE_ERROR')
  if (value.data === undefined || value.data === null) throw new IamError('服务器没有返回已确认的结果。')
  return value.data
}
export async function iamQuery<T>(method: string, params?: Record<string, unknown>): Promise<T> { return unwrapIam<T>(await callFrappeMethod(method, params)) }
export async function iamCommand<T>(method: string, params: Record<string, unknown>): Promise<T> { return unwrapIam<T>(await callFrappePostMethod(method, params)) }
export function iamMessage(error: unknown): string {
  const raw = error as { status?: number; code?: string; message?: string }
  if (raw.code === 'PROOF_REQUIRED') return '本人验证已失效，请重新验证当前账号密码及已有二次认证。草稿已保留。'
  if (raw.code === 'READ_CONFLICT') return raw.message || '读取遇到暂时冲突，请重试查询。'
  if (raw.status === 409 || ['VERSION_CONFLICT', 'STALE_PREVIEW', 'CONFLICT'].includes(raw.code || '')) return '设置已被更新或预览已过期。草稿已保留，请重新读取并核对后再保存。'
  if (raw.status === 403 || raw.code === 'FORBIDDEN') return '当前操作未获授权，草稿已保留。请联系有相应管理范围的负责人。'
  return raw?.message || '请求未完成，草稿已保留，请重试。'
}
export interface Capabilities { schema_version: 1; app_roles_enabled?: boolean; subject_user: string; session_context?: string; policy_revision: string; app_revisions?: Record<string, string>; capabilities: string[] }
export const iamSession = reactive({ user: '', revision: '', rolesEnabled: false, appRevisions: {} as Record<string, string>, ready: false, loading: false, error: '', capabilities: [] as string[] })
const known = new Set(['iam.people.read','iam.people.link','iam.people.provision','iam.people.create','iam.people.transfer','iam.people.disable','iam.people.reset','iam.departments.read','iam.departments.manage','iam.access.read','iam.access.manage','iam.audit.read','iam.roles.read','iam.roles.edit','iam.roles.publish','iam.roles.assign','attendance.read','iam_demo.read'])
let generation = 0
export function clearIamAccess() { generation++; Object.assign(iamSession, { user: '', revision: '', rolesEnabled: false, appRevisions: {}, ready: false, loading: false, error: '', capabilities: [] }) }
export function validateCapabilities(raw: unknown, expectedUser?: string): Capabilities {
  const value = raw as Capabilities
  if (!value || value.schema_version !== 1 || typeof value.subject_user !== 'string' || !value.subject_user || value.subject_user === 'Guest' || (expectedUser && value.subject_user !== expectedUser) || typeof value.policy_revision !== 'string' || !Array.isArray(value.capabilities) || value.capabilities.some(id => typeof id !== 'string' || !known.has(id))) throw new IamError('无法确认当前账号的管理能力，请重新验证会话。')
  if (value.app_revisions !== undefined && (!value.app_revisions || typeof value.app_revisions !== 'object' || Array.isArray(value.app_revisions) || Object.values(value.app_revisions).some(item => typeof item !== 'string'))) throw new IamError('无法确认应用权限版本，请重试核验。')
  return value
}
export async function fetchIamAccess(expectedUser: string, context: string) {
  const result = validateCapabilities(await iamQuery('hbos_portal.api.iam_access.get_capabilities'), expectedUser)
  if (result.session_context !== context) throw new IamError('登录状态已改变，请重新核验。', 'SESSION_CHANGED')
  return result
}
export function applyIamAccess(result: Capabilities) {
  Object.assign(iamSession, { rolesEnabled: result.app_roles_enabled === true, user: result.subject_user, revision: result.policy_revision, appRevisions: result.app_revisions || {}, capabilities: result.capabilities, ready: true, loading: false, error: '' })
}
export async function loadIamAccess(expectedUser?: string) {
  const current = ++generation
  Object.assign(iamSession, { ready: false, loading: true, error: '', capabilities: [] })
  try {
    const result = validateCapabilities(await iamQuery('hbos_portal.api.iam_access.get_capabilities'), expectedUser)
    if (current !== generation) throw new IamError('会话已改变，请重新读取。')
    Object.assign(iamSession, { rolesEnabled: result.app_roles_enabled === true, user: result.subject_user, revision: result.policy_revision, appRevisions: result.app_revisions || {}, capabilities: result.capabilities, ready: true })
    return result
  } catch (e) { if (current === generation) { iamSession.error = iamMessage(e); iamSession.ready = false }; throw e }
  finally { if (current === generation) iamSession.loading = false }
}
export const canIam = (capability: string) => iamSession.ready && iamSession.capabilities.includes(capability)
export const hasManagementAccess = () => ['iam.people.read','iam.departments.read','iam.access.read','iam.roles.read','iam.audit.read'].some(canIam)
