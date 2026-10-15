import { callFrappeMethod, callFrappePostMethod } from './frappeClient'
import type { SecurityStatus } from './accountApi'
import { iamQuery, IamError } from './iamAccess'
export interface IamSecurity extends SecurityStatus { temporary_password_state: { pending: boolean; temporary: boolean; expires_at: string | null; generation: number; can_claim: boolean }; first_password_required: boolean }
export async function getIamSecurity(expectedUser?: string) {
  const status = await callFrappeMethod<IamSecurity>('hbos_portal.auth.accounts.get_security')
  const state = status?.temporary_password_state
  if (!status?.user || status.user === 'Guest' || (expectedUser && status.user !== expectedUser) || !state || typeof status.first_password_required !== 'boolean' || typeof state.pending !== 'boolean' || typeof state.temporary !== 'boolean' || typeof state.can_claim !== 'boolean' || !Number.isInteger(state.generation)) throw new IamError('无法确认本人账号安全状态，请重新登录或重试。')
  return status
}
export const claimInitialPassword = () => callFrappePostMethod<{ claimed: boolean; temporary_password?: string; expires_at?: string; generation: number }>('hbos_portal.auth.accounts.claim_initial_password')
export interface MyEmployeeStatus { status: 'linked' | 'unlinked' | 'conflict'; employee_id?: string; employee_number?: string; department?: string; initial_password_pending?: boolean }
export const getMyEmployeeStatus = () => iamQuery<MyEmployeeStatus>('hbos_portal.api.iam_people.get_my_employee_status')
