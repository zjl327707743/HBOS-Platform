import axios from 'axios'
import { callFrappeMethod, callFrappePostMethod } from './frappeClient'

export interface SecurityStatus {
  user: string; login_name: string; has_password: boolean; feishu_bound: boolean
  feishu_configured: boolean; feishu_stepup_available: boolean; desk_access: boolean
  administrator: boolean; administrator_link_enabled: boolean; mail_recovery_available: boolean
  can_admin_recover: boolean
}
export interface MfaResult { mfa_required?: boolean; tmp_id?: string; verified?: boolean }
export interface PendingAccount { intent: 'choose' | 'link' | 'login_mfa'; user?: string; display_name: string; csrf: string; expires_in: number }
const prefix = 'hbos_portal.auth.accounts.'
export const getSecurity = () => callFrappeMethod<SecurityStatus>(prefix + 'get_security')
export const reauthenticate = (password: string, otp: string, tmp_id: string) => callFrappePostMethod<MfaResult>(prefix + 'reauthenticate', { password, otp, tmp_id })
export const requestFeishuCode = () => callFrappePostMethod(prefix + 'request_feishu_code')
export const verifyFeishuCode = (code: string, otp: string, tmp_id: string) => callFrappePostMethod<MfaResult>(prefix + 'verify_feishu_code', { code, otp, tmp_id })
export const setPassword = (new_password: string) => callFrappePostMethod<{ changed: boolean; login_name: string }>(prefix + 'set_password', { new_password })
export const unlinkFeishu = () => callFrappePostMethod(prefix + 'unlink_feishu')
export const startLink = () => callFrappePostMethod<{ authorize_url: string }>('hbos_portal.auth.feishu.start_link')
export const getPending = () => callFrappeMethod<PendingAccount>(prefix + 'get_pending')
export const adminIssueRecovery = (user: string, reason: string) => callFrappePostMethod<{ recovery_key: string; expires_in: number }>(prefix + 'admin_issue_recovery', { user, reason })

// Guest account selection and recovery have no persistent Frappe CSRF session.
// The server validates Origin, JSON, X-Requested-With and, for pending OAuth,
// a separate cookie-bound token. No credential is persisted in the browser.
export async function guestAccountPost<T>(method: string, data: Record<string, unknown>, csrf?: string): Promise<T> {
  const security = await callFrappeMethod<{ csrf_token?: string }>(prefix + 'get_request_security')
  const response = await axios.post<{ message: T }>(`/api/method/${prefix}${method}`, data, {
    withCredentials: true, headers: { 'X-Requested-With': 'XMLHttpRequest', ...(security.csrf_token ? { 'X-Frappe-CSRF-Token': security.csrf_token } : {}), ...(csrf ? { 'X-HBOS-Pending-CSRF': csrf } : {}) },
  })
  return response.data.message
}
