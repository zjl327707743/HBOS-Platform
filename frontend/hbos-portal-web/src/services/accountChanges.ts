import axios from 'axios'
import { callFrappeMethod, normalizeFrappeError } from './frappeClient'
export type ChangeKind = 'rebind' | 'roles' | 'custody' | 'identity_restore'
export interface ChangeActions { rebind: boolean; roles: boolean; role_choices: string[]; custody: boolean; custody_needs_special_authorization: boolean; identity_restore: boolean; builtin_administrator: boolean; migrated: boolean }
interface AccountLabel { user: string; login_name: string; display_name: string }
interface IdentityLabel { fingerprint: string; display_name?: string; app_id: string; enterprise_verified: boolean }
export interface AccountChange { operation: string; kind: ChangeKind; state?: string; requires_feishu_verification?: boolean; participant?: boolean; can_return_to_initiator?: boolean; expires_in?: number; target?: AccountLabel; source?: AccountLabel; old_identity?: IdentityLabel; new_identity?: IdentityLabel; source_proven?: boolean; conflict?: boolean; allow_source_migration?: boolean; recipient_accepted?: boolean; credentials_verified?: boolean; roles?: string[]; effects?: string[]; reason?: string; ready?: boolean }
const prefix = 'hbos_portal.auth.operations.'
export const changeActions = () => callFrappeMethod<ChangeActions>(prefix + 'actions')
export const getChange = (operation: string, requestId?: string) => callFrappeMethod<AccountChange>(prefix + 'get_operation', { operation, ...(requestId ? {request_id: requestId} : {}) })
export const getParticipant = () => callFrappeMethod<AccountChange>(prefix + 'get_participant')
export const recentChanges = () => callFrappeMethod<{ changes: { name: string; kind: ChangeKind; state: string; notification_status: string }[] }>(prefix + 'recent_changes')
export async function changePost<T>(method: string, data: Record<string, unknown> = {}): Promise<T> {
  const security = await callFrappeMethod<{ csrf_token?: string }>('hbos_portal.auth.accounts.get_request_security')
  try {
    const result = await axios.post<{message: T}>(`/api/method/${prefix}${method}`, data, { withCredentials: true,
      headers: { 'X-Requested-With': 'XMLHttpRequest', ...(security.csrf_token ? { 'X-Frappe-CSRF-Token': security.csrf_token } : {}) } })
    return result.data.message
  } catch (error) {
    throw normalizeFrappeError(error, prefix + method)
  }
}
export const kindLabel = (kind: ChangeKind) => ({ rebind: '更换本人飞书', roles: '管理员职责交接', custody: 'Administrator 保管人交接', identity_restore: '旧身份的普通账号归属' }[kind])

export const stateLabel = (state: string) => ({ Invited: '等待验证', 'Identity Verified': '新身份已验证', 'Source Verified': '来源账号已验证', Accepted: '双方待最终确认', 'Credentials Prepared': '新凭据待验证', Pending: '等待验证', Ready: '等待最终确认', Completed: '已完成', Cancelled: '已取消', Expired: '已过期' }[state] || '处理中')
